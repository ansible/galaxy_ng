from django.contrib.postgres.aggregates import JSONBAgg
from django.contrib.postgres.search import SearchQuery
from django.db.models import (
    Exists,
    F,
    FloatField,
    Func,
    JSONField,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.fields.json import KT
from django.db.models.functions import Coalesce
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from pulp_ansible.app.models import (
    AnsibleCollectionDeprecated,
    CollectionDownloadCount,
    CollectionVersion,
)
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui.serializers import SearchResultsSerializer
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.models.namespace import Namespace

FILTER_PARAMS = [
    "keywords",
    "type",
    "deprecated",
    "name",
    "namespace",
    "tags",
    "platform",
    "search_type",
]
SORT_PARAM = "order_by"
SORTABLE_FIELDS = ["name", "namespace_name", "download_count", "last_updated", "relevance"]
SORTABLE_FIELDS += [f"-{item}" for item in SORTABLE_FIELDS]
DEFAULT_SEARCH_TYPE = "websearch"  # websearch,sql
QUERYSET_VALUES = [
    "namespace_avatar",
    "content_list",
    "deprecated",
    "description_text",
    "download_count",
    "last_updated",
    "name",
    "namespace_name",
    "platform_names",
    "tag_names",
    "content_type",
    "latest_version",
    "search",
    "relevance",
]
RANK_NORMALIZATION = 32


class SearchListView(api_base.GenericViewSet, mixins.ListModelMixin):
    """Search collections and roles"""

    permission_classes = [AllowAny]
    serializer_class = SearchResultsSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("search_type", enum=["sql", "websearch"], default=DEFAULT_SEARCH_TYPE),
            OpenApiParameter(
                "keywords",
                description=(
                    "Search term to be queried against search vector if search_type is websearch "
                    "or SQL ilike if search_type is sql"
                ),
            ),
            OpenApiParameter("type", enum=["collection", "role"]),
            OpenApiParameter("deprecated", OpenApiTypes.BOOL),
            OpenApiParameter("name", description="Executes iexact filter on name"),
            OpenApiParameter("namespace", description="Executes iexact filter on namespace"),
            OpenApiParameter("tags", many=True),
            OpenApiParameter("platform"),
            OpenApiParameter("order_by", enum=SORTABLE_FIELDS),
        ]
    )
    def list(self, *args, **kwargs):
        """Lists Search results for Collections + Roles.
        Aggregates search from Collections and Roles in the same results set.


        ## filtering

        - **search_type:** ["sql", "websearch"]
        - **keywords:** string
            - queried against name,namespace,description,tags,platform
            - when search_type is websearch allows operators e.g: "this OR that AND (A OR B) -C"
            - when search_type is sql performs a SQL ilike on the same fields
        - **type:** ["collection", "role"]
        - **deprecated:** boolean
        - **name:** string (iexact query)
        - **namespace:** string (iexact query)
        - **tags:** string[] (allows multiple &tags=..&tags=..)
        - **platform:** string

        ## Sorting

        Sorting is performed by passing `order_by` parameter, optionally prefixed with `-` for DESC,
        the allowed fields are:

        - name
        - namespace_name
        - download_count
        - last_updated
        - relevance (only when search_type is websearch)

        ## Pagination

        Pagination is based on `limit` and `offset` parameters.

        ## Results

        Results are embedded in the pagination serializer including
        `meta:count` and `links:first,previous,next,last`.

        The `data` key contains the results in the format::

        ```python
        {
          "name": "brunogphmzthghu",
          "namespace": "brunovrhvjkdh",
          "description": "Lorem ipsum dolor sit amet, consectetur adipisicing elit.",
          "type": "role",
          "latest_version": "1.4.9",
          "avatar_url": "https://github.com/brunogphmzthghu.png,
          "contents": [],
          "download_count": 9999,
          "last_updated": "2023-11-09T15:17:01.235457Z",
          "deprecated": false,
          "tags": ["development", "java", "python"],
          "platforms": [{"name": "Ubuntu", "versions": ["jammy", "focal"]}]
        }
        ```
        """
        return super().list(*args, **kwargs)

    def get_queryset(self):
        """Returns the UNION ALL from CollectionVersion and LegacyRole"""
        request = self.request
        self.filter_params = self.get_filter_params(request)
        self.sort = self.get_sorting_param(request)
        qs = self.get_search_results(self.filter_params, self.sort)
        return qs

    def get_search_results(self, filter_params, sort):
        """Validates filter_params, builds each queryset and then unionize and apply filters."""
        type = filter_params.get("type", "").lower()
        if type not in ("role", "collection", ""):
            raise ValidationError("'type' must be ['collection', 'role']")

        search_type = filter_params.get("search_type", DEFAULT_SEARCH_TYPE)
        if search_type not in ("sql", "websearch"):
            raise ValidationError("'search_type' must be ['sql', 'websearch']")
        keywords = filter_params.get("keywords")
        query = None
        if keywords and search_type == "websearch":
            query = SearchQuery(keywords, search_type="websearch")

        collections = self.get_collection_queryset(query=query)
        roles = self.get_role_queryset(query=query)
        result_qs = self.filter_and_sort(collections, roles, filter_params, sort, type, query=query)
        return result_qs

    def get_filter_params(self, request):
        """Aggregates the allowed filter params and the list of tags"""
        data = {k.lower(): v for k, v in request.query_params.items() if k.lower() in FILTER_PARAMS}
        if tags := request.query_params.getlist("tags"):
            data["tags"] = tags
        return data

    def get_sorting_param(self, request):
        """Validates the sorting parameter is valid."""
        search_type = request.query_params.get("search_type", DEFAULT_SEARCH_TYPE)
        default_sort = "-download_count,-relevance"
        if search_type == "sql":
            default_sort = "-download_count,-last_updated"
        sort = request.query_params.get(SORT_PARAM, default_sort).split(",")
        for item in sort:
            if item not in SORTABLE_FIELDS:
                raise ValidationError(f"{SORT_PARAM} requires one of {SORTABLE_FIELDS}")
        if ("relevance" in sort or "-relevance" in sort) and search_type != "websearch":
            raise ValidationError("'order_by=relevance' works only with 'search_type=websearch'")
        return sort

    def get_collection_queryset(self, query=None):
        """Build the CollectionVersion queryset from annotations."""
        deprecated_qs = AnsibleCollectionDeprecated.objects.filter(
            namespace=OuterRef("namespace"), name=OuterRef("name")
        )
        download_count_qs = CollectionDownloadCount.objects.filter(
            namespace=OuterRef("namespace"), name=OuterRef("name")
        )
        namespace_qs = Namespace.objects.filter(name=OuterRef("namespace"))

        relevance = Value(0)
        if query:
            relevance = Func(
                F("search_vector"),
                query,
                RANK_NORMALIZATION,
                function="ts_rank",
                output_field=FloatField(),
            )

        # The order of the fields here is important, must match the role_queryset
        qs = (
            CollectionVersion.objects.annotate(
                namespace_name=F("namespace"),
                description_text=F("description"),
                platform_names=Value([], JSONField()),  # There is no platforms for collections
                tag_names=JSONBAgg("tags__name"),
                content_type=Value("collection"),
                last_updated=F("timestamp_of_interest"),
                deprecated=Exists(deprecated_qs),
                download_count=Coalesce(
                    Subquery(download_count_qs.values("download_count")[:1]), Value(0)
                ),
                latest_version=F("version"),
                content_list=F("contents"),
                namespace_avatar=Subquery(namespace_qs.values("_avatar_url")),
                search=F("search_vector"),
                relevance=relevance,
            )
            .values(*QUERYSET_VALUES)
            .filter(is_highest=True)
        )
        return qs

    def get_role_queryset(self, query=None):
        """Build the LegacyRole queryset from annotations."""
        relevance = Value(0)
        if query:
            relevance = Func(
                F("search"),
                query,
                RANK_NORMALIZATION,
                function="ts_rank",
                output_field=FloatField(),
            )
        # The order of the fields here is important, must match the collection_queryset
        qs = LegacyRole.objects.annotate(
            namespace_name=F("namespace__name"),
            description_text=KT("full_metadata__description"),
            platform_names=F("full_metadata__platforms"),
            tag_names=F("full_metadata__tags"),
            content_type=Value("role"),
            last_updated=F("created"),
            deprecated=Value(False),  # there is no deprecation for roles
            download_count=Coalesce(F("legacyroledownloadcount__count"), Value(0)),
            latest_version=KT("full_metadata__versions__-1__version"),
            content_list=Value([], JSONField()),  # There is no contents for roles
            namespace_avatar=F("namespace__namespace___avatar_url"),  # v3 namespace._avatar_url
            search=F("legacyrolesearchvector__search_vector"),
            relevance=relevance,
        ).values(*QUERYSET_VALUES)
        return qs

    def filter_and_sort(self, collections, roles, filter_params, sort, type="", query=None):
        """Apply filters individually on each queryset and then combine to sort."""
        facets = {}
        if deprecated := filter_params.get("deprecated"):
            if deprecated.lower() not in ("true", "false"):
                raise ValidationError("'deprecated' filter must be 'true' or 'false'")
            facets["deprecated"] = deprecated.lower() == "true"
        if name := filter_params.get("name"):
            facets["name__iexact"] = name
        if namespace := filter_params.get("namespace"):
            facets["namespace_name__iexact"] = namespace
        if facets:
            collections = collections.filter(**facets)
            roles = roles.filter(**facets)

        if tags := filter_params.get("tags"):
            tag_filter = Q()
            for tag in tags:
                tag_filter &= Q(tag_names__icontains=tag)
            collections = collections.filter(tag_filter)
            roles = roles.filter(tag_filter)

        if platform := filter_params.get("platform"):
            roles = roles.filter(full_metadata__platforms__icontains=platform)
            collections = collections.filter(platform_names=platform)  # never match but required

        if query:
            collections = collections.filter(search=query)
            roles = roles.filter(search=query)
        elif keywords := filter_params.get("keywords"):  # search_type=sql
            query = (
                Q(name__icontains=keywords)
                | Q(namespace_name__icontains=keywords)
                | Q(description_text__icontains=keywords)
                | Q(tag_names__icontains=keywords)
                | Q(platform_names__icontains=keywords)
            )
            collections = collections.filter(query)
            roles = roles.filter(query)

        if type.lower() == "role":
            qs = roles.order_by(*sort)
        elif type.lower() == "collection":
            qs = collections.order_by(*sort)
        else:
            qs = collections.union(roles, all=True).order_by(*sort)
        return qs


def test():
    """For testing."""
    from pprint import pprint

    print()
    print(f"{' START ':#^40}")
    s = SearchListView()
    data = s.get_search_results({"type": "", "keywords": "java web"}, sort="-relevance")
    print(f"{' SQLQUERY ':#^40}")
    print(data._query)
    print(f"{' COUNT ':#^40}")
    print(data.count())
    print(f"{' FIRST 2 ':#^40}")
    pprint(list(data[:2]))
    print(f"{' END ':#^40}")


if __name__ == "__main__":
    test()
