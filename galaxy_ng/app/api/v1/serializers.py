import datetime

from rest_framework import serializers

from pulpcore.plugin.util import get_url

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.models.namespace import Namespace
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole, LegacyRoleTag
from galaxy_ng.app.api.v1.models import LegacyRoleDownloadCount
from galaxy_ng.app.api.v1.utils import sort_versions

from galaxy_ng.app.utils.galaxy import (
    uuid_to_int
)


class LegacyNamespacesSerializer(serializers.ModelSerializer):

    summary_fields = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    related = serializers.SerializerMethodField()

    class Meta:
        model = LegacyNamespace
        fields = [
            'id',
            'url',
            'summary_fields',
            'created',
            'modified',
            'name',
            'avatar_url',
            'related',
        ]

    def get_related(self, obj):
        return {
            'provider_namespaces': None,
            'content': None,
            'owners': f'/api/v1/namespaces/{obj.id}/owners/',
        }

    def get_name(self, obj):
        if hasattr(obj, 'name'):
            return obj.name
        if hasattr(obj, 'username'):
            return obj.username

    def get_url(self, obj):
        return ''

    def get_date_joined(self, obj):
        return obj.created

    def get_summary_fields(self, obj):

        owners = []
        if obj.namespace:
            owner_objects = get_v3_namespace_owners(obj.namespace)
            owners = [{'id': x.id, 'username': x.username} for x in owner_objects]

        # link the v1 namespace to the v3 namespace so that users
        # don't need to query the database to figure it out.
        providers = []
        if obj.namespace:
            pulp_href = get_url(obj.namespace)
            providers.append({
                'id': obj.namespace.id,
                'name': obj.namespace.name,
                'pulp_href': pulp_href,
            })

        return {'owners': owners, 'provider_namespaces': providers}

    def get_avatar_url(self, obj):

        # prefer the provider avatar url
        if obj.namespace and obj.namespace.avatar_url:
            return obj.namespace.avatar_url

        url = f'https://github.com/{obj.name}.png'
        return url


class LegacyNamespaceOwnerSerializer(serializers.Serializer):

    id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id']

    def get_id(self, obj):
        return obj.id


class LegacyNamespaceProviderSerializer(serializers.ModelSerializer):

    pulp_href = serializers.SerializerMethodField()

    class Meta:
        model = Namespace
        fields = [
            'id',
            'name',
            'pulp_href'
        ]

    def get_pulp_href(self, obj):
        return get_url(obj)


class LegacyUserSerializer(serializers.ModelSerializer):

    summary_fields = serializers.SerializerMethodField()
    date_joined = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()
    # active = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    github_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'url',
            'summary_fields',
            'created',
            # 'modified',
            'username',
            'full_name',
            'date_joined',
            'avatar_url',
            'github_id',
        ]

    def get_username(self, obj):
        if hasattr(obj, 'name'):
            return obj.name
        if hasattr(obj, 'username'):
            return obj.username

    def get_url(self, obj):
        return ''

    def get_full_name(self, obj):
        return ''

    def get_created(self, obj):
        return self.get_date_joined(obj)

    def get_date_joined(self, obj):
        # return obj.created
        if hasattr(obj, '_created'):
            return obj._created
        if hasattr(obj, 'date_joined'):
            return obj.date_joined

    def get_summary_fields(self, obj):
        return {}

    # TODO: What does this actually mean?
    # def get_active(self, obj):
    #    return True

    def get_avatar_url(self, obj):
        if hasattr(obj, 'name'):
            username = obj.name
        elif hasattr(obj, 'username'):
            username = obj.username
        url = f'https://github.com/{username}.png'
        return url

    def get_github_id(self, obj):

        # have to defer this import because of the other
        # deployment profiles trying to access the missing
        # database table.
        from social_django.models import UserSocialAuth

        try:
            social_user = UserSocialAuth.objects.filter(user=obj).first()
            if not social_user:
                return None
            return int(social_user.uid)
        except Exception:
            return None

        return None


class LegacyRoleSerializer(serializers.ModelSerializer):

    # core cli uses this field to emit the list of
    # results from a role search so it must exit
    username = serializers.SerializerMethodField()

    # this has to be the real github org/user so that
    # role installs will work
    github_user = serializers.SerializerMethodField()

    # this has to be the real github repository name
    # so that role installs will work
    github_repo = serializers.SerializerMethodField()

    # this is the default or non-default branch
    # the cli will use will installing the role.
    # in old galaxy this was internall renamed to
    # import_branch.
    github_branch = serializers.SerializerMethodField()

    imported = serializers.SerializerMethodField()

    commit = serializers.SerializerMethodField()
    commit_message = serializers.SerializerMethodField()

    description = serializers.SerializerMethodField()
    summary_fields = serializers.SerializerMethodField()
    upstream_id = serializers.SerializerMethodField()
    download_count = serializers.SerializerMethodField()

    class Meta:
        model = LegacyRole
        fields = [
            'id',
            'upstream_id',
            'created',
            'modified',
            'imported',
            'github_user',
            'username',
            'github_repo',
            'github_branch',
            'commit',
            'commit_message',
            'name',
            'description',
            'summary_fields',
            'download_count',
        ]

    def get_id(self, obj):
        return obj.pulp_id

    def get_upstream_id(self, obj):
        """
        Return the upstream id.

        This ID comes from the original source of the role
        if it was sync'ed from an upstream source.
        """
        return obj.full_metadata.get('upstream_id')

    def get_url(self, obj):
        return None

    def get_created(self, obj):
        if hasattr(obj, '_created'):
            return obj._created
        if hasattr(obj, 'date_joined'):
            return obj.date_joined

    def get_modified(self, obj):
        return obj.pulp_created

    def get_imported(self, obj):
        return obj.full_metadata.get('imported')

    def get_github_user(self, obj):
        """
        Return the github_user.

        The client cli will use this to build the download url
        of the role in the form of:
            https://github.com/<github_user>/<github_repo>/...
        """
        if obj.full_metadata.get('github_user'):
            return obj.full_metadata['github_user']
        return obj.namespace.name

    def get_username(self, obj):
        return obj.namespace.name

    def get_github_repo(self, obj):
        """
        Return the github_repo.

        The client cli will use this to build the download url
        of the role in the form of:
            https://github.com/<github_user>/<github_repo>/...
        """
        return obj.full_metadata.get('github_repo')

    def get_github_branch(self, obj):
        """
        Return the github branch.

        If the role has no version, this value will be used as the version
        at install time. If not branch is given, the cli will default to
        the "master" branch.
        """
        if obj.full_metadata.get('github_reference'):
            return obj.full_metadata.get('github_reference')
        return obj.full_metadata.get('github_branch')

    def get_commit(self, obj):
        return obj.full_metadata.get('commit')

    def get_commit_message(self, obj):
        return obj.full_metadata.get('commit_message')

    def get_description(self, obj):
        return obj.full_metadata.get('description')

    def get_summary_fields(self, obj):
        dependencies = obj.full_metadata.get('dependencies', [])
        tags = obj.full_metadata.get('tags', [])

        versions = obj.full_metadata.get('versions', [])
        if versions:
            # FIXME - we can't assume they're all sorted yet
            versions = sort_versions(versions)
            versions = versions[::-1]
            if len(versions) > 10:
                versions = versions[:11]
            versions = [LegacyRoleVersionSummary(obj, x).to_json() for x in versions]

        provider_ns = None
        if obj.namespace and obj.namespace.namespace:
            pulp_href = get_url(obj.namespace.namespace)
            provider_ns = {
                'id': obj.namespace.namespace.id,
                'name': obj.namespace.namespace.name,
                'pulp_href': pulp_href
            }

        # FIXME - repository is a bit hacky atm
        repository = {}
        if obj.full_metadata.get('repository'):
            repository = obj.full_metadata.get('repository')
        if not repository.get('name'):
            repository['name'] = obj.full_metadata.get('github_repo')
        if not repository.get('original_name'):
            repository['original_name'] = obj.full_metadata.get('github_repo')

        # prefer the provider avatar url
        avatar_url = f'https://github.com/{obj.namespace.name}.png'
        if obj.namespace and obj.namespace.namespace:
            if obj.namespace.namespace.avatar_url:
                avatar_url = obj.namespace.namespace.avatar_url

        return {
            'dependencies': dependencies,
            'namespace': {
                'id': obj.namespace.id,
                'name': obj.namespace.name,
                'avatar_url': avatar_url
            },
            'provider_namespace': provider_ns,
            'repository': repository,
            'tags': tags,
            'versions': versions
        }

    def get_download_count(self, obj):
        counter = LegacyRoleDownloadCount.objects.filter(legacyrole=obj).first()
        if counter:
            return counter.count
        return 0


class LegacyRoleRepositoryUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=False, max_length=50)
    original_name = serializers.CharField(required=False, allow_blank=False, max_length=50)

    def is_valid(self, raise_exception=False):
        # Check for any unexpected fields
        extra_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if extra_fields:
            self._errors = {field: ["Unexpected field."] for field in extra_fields}
        else:
            # Continue with the original validation logic
            super(serializers.Serializer, self).is_valid(raise_exception=raise_exception)

        return not bool(self._errors)


class LegacyRoleUpdateSerializer(serializers.Serializer):
    github_user = serializers.CharField(required=False, allow_blank=False, max_length=50)
    github_repo = serializers.CharField(required=False, allow_blank=False, max_length=50)
    github_branch = serializers.CharField(required=False, allow_blank=False, max_length=50)
    repository = LegacyRoleRepositoryUpdateSerializer(required=False)

    def is_valid(self, raise_exception=False):
        # Check for any unexpected fields
        extra_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if extra_fields:
            self._errors = {field: ["Unexpected field."] for field in extra_fields}
        else:
            # Continue with the original validation logic
            super(serializers.Serializer, self).is_valid(raise_exception=raise_exception)

        return not bool(self._errors)


class LegacyRoleContentSerializer(serializers.ModelSerializer):

    readme = serializers.SerializerMethodField()
    readme_html = serializers.SerializerMethodField()

    class Meta:
        model = LegacyRole
        fields = [
            'readme',
            'readme_html'
        ]

    def get_readme(self, obj):
        return obj.full_metadata.get('readme', '')

    def get_readme_html(self, obj):
        return obj.full_metadata.get('readme_html', '')


class LegacyRoleVersionSummary:
    """
    Shim serializer to be replaced once role versions
    become first class objects.
    """
    def __init__(self, role, version):
        self.role = role
        self.version = version

    def to_json(self):

        # old galaxy has a field for the real tag value
        # and that is what gets returned for the name
        name = self.version.get('tag')
        if not name:
            name = self.version.get('name')

        return {
            'id': self.version.get('id'),
            'name': name,
            'release_date': self.version.get('commit_date'),
        }


class LegacyRoleVersionDetail:
    """
    Shim serializer to be replaced once role versions
    become first class objects.
    """
    def __init__(self, role, version):
        self.role = role
        self.version = version

    def to_json(self):

        # old galaxy has a field for the real tag value
        # and that is what gets returned for the name
        name = self.version.get('tag')
        if not name:
            name = self.version.get('name')

        # "https://github.com/andrewrothstein/ansible-miniconda/archive/v2.0.0.tar.gz"
        github_user = self.role.full_metadata.get('github_user')
        github_repo = self.role.full_metadata.get('github_repo')
        download_url = f'https://github.com/{github_user}/{github_repo}/archive/{name}.tar.gz'

        return {
            'id': self.version.get('id'),
            'name': name,
            'version': self.version.get('version'),
            'created': self.version.get('created'),
            'modified': self.version.get('modified'),
            'commit_date': self.version.get('commit_date'),
            'commit_sha': self.version.get('commit_sha'),
            'download_url': download_url,
        }


class LegacyRoleVersionsSerializer(serializers.ModelSerializer):

    count = serializers.SerializerMethodField()
    next = serializers.SerializerMethodField()
    next_link = serializers.SerializerMethodField()
    previous = serializers.SerializerMethodField()
    previous_link = serializers.SerializerMethodField()
    results = serializers.SerializerMethodField()

    class Meta:
        model = LegacyRole
        fields = [
            'count',
            'next',
            'next_link',
            'previous',
            'previous_link',
            'results'
        ]

    def get_count(self, obj):
        return len(obj.full_metadata.get('versions', []))

    def get_next(self, obj):
        return None

    def get_next_link(self, obj):
        return None

    def get_previous(self, obj):
        return None

    def get_previous_link(self, obj):
        return None

    def get_results(self, obj):

        versions = obj.full_metadata.get('versions', [])
        versions = sort_versions(versions)

        results = []

        for idv, version in enumerate(versions):
            results.append(LegacyRoleVersionDetail(obj, version).to_json())

        return results


class LegacyTaskSerializer():

    @property
    def data(self):
        return {}


class LegacySyncSerializer(serializers.Serializer):

    baseurl = serializers.CharField(
        required=False,
        default='https://old-galaxy.ansible.com/api/v1/roles/'
    )
    github_user = serializers.CharField(required=False)
    role_name = serializers.CharField(required=False)
    role_version = serializers.CharField(required=False)
    limit = serializers.IntegerField(required=False)

    class Meta:
        model = None
        fields = [
            'baseurl'
            'github_user',
            'role_name',
            'role_version',
            'limit'
        ]


class LegacyImportSerializer(serializers.Serializer):

    github_user = serializers.CharField()
    github_repo = serializers.CharField()
    alternate_namespace_name = serializers.CharField(required=False)
    alternate_role_name = serializers.CharField(required=False)
    alternate_clone_url = serializers.CharField(required=False)
    github_reference = serializers.CharField(required=False)

    class Meta:
        model = None
        fields = [
            'github_user',
            'github_repo',
            'alternate_namespace_name',
            'alternate_role_name',
            'alternate_clone_url',
            'github_reference',
        ]


class LegacyImportListSerializer(serializers.Serializer):

    id = serializers.SerializerMethodField()
    pulp_id = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()
    modified = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    summary_fields = serializers.SerializerMethodField()

    class Meta:
        model = None
        fields = [
            'id',
            'pulp_id',
            'created',
            'modified',
            'state',
            'summary_fields',
        ]

    def get_id(self, obj):
        return uuid_to_int(str(obj.task.pulp_id))

    def get_pulp_id(self, obj):
        return obj.task.pulp_id

    def get_created(self, obj):
        return obj.task.pulp_created

    def get_modified(self, obj):
        return obj.task.pulp_last_updated

    def get_state(self, obj):
        state_map = {
            'COMPLETED': 'SUCCESS'
        }
        state = obj.task.state.upper()
        state = state_map.get(state, state)
        return state

    def get_summary_fields(self, obj):
        return {
            'request_username': obj.task.kwargs.get('request_username'),
            'github_user': obj.task.kwargs.get('github_user'),
            'github_repo': obj.task.kwargs.get('github_repo'),
            'github_reference': obj.task.kwargs.get('github_reference'),
            'alternate_role_name': obj.task.kwargs.get('alternate_role_name'),
        }


class LegacySyncTaskResponseSerializer(serializers.Serializer):

    task = serializers.CharField()

    class Meta:
        model = None
        fields = ['task']


class LegacyTaskQuerySerializer(serializers.Serializer):

    class Meta:
        model = None
        fields = ['id']


class LegacyTaskSummaryTaskMessagesFieldsSerializer(serializers.Serializer):

    id = serializers.DateTimeField()
    message_type = serializers.CharField()
    message_text = serializers.CharField()
    state = serializers.CharField()

    class Meta:
        model = None
        fields = ['id', 'message_type', 'message_text', 'state']


class LegacyTaskSummaryFieldsSerializer(serializers.Serializer):

    task_messages = LegacyTaskSummaryTaskMessagesFieldsSerializer(many=True)

    class Meta:
        model = None
        fields = ['task_messages']


class LegacyTaskResultsSerializer(serializers.Serializer):

    state = serializers.CharField()
    id = serializers.IntegerField()
    summary_fields = LegacyTaskSummaryFieldsSerializer()

    class Meta:
        model = None
        fields = [
            'id',
            'state',
            'summary_fields'
        ]


class LegacyTaskDetailSerializer(serializers.Serializer):

    results = LegacyTaskResultsSerializer()

    class Meta:
        model = None
        fields = ['results']


class LegacyRoleImportDetailSerializer(serializers.Serializer):

    STATE_MAP = {
        'COMPLETED': 'SUCCESS'
    }

    MSG_TYPE_MAP = {
        'RUNNING': 'INFO',
        'WAITING': 'INFO',
        'COMPLETED': 'SUCCESS'
    }

    id = serializers.SerializerMethodField()
    pulp_id = serializers.SerializerMethodField()
    role_id = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()
    summary_fields = serializers.SerializerMethodField()

    class Meta:
        model = None
        fields = [
            'id',
            'pulp_id',
            'state',
            'role_id',
            'summary_fields',
        ]

    def get_role_id(self, obj):
        if obj.role:
            return obj.role.id
        return None

    def get_state(self, obj):
        task = obj.task
        return self.STATE_MAP.get(task.state.upper(), task.state.upper())

    def get_id(self, obj):
        return uuid_to_int(str(obj.task.pulp_id))

    def get_pulp_id(self, obj):
        return str(obj.task.pulp_id)

    def get_error(self, obj):
        return {
            'code': None,
            'description': None,
            'traceback': None
        }

    def get_summary_fields(self, obj):
        task = obj.task

        task_messages = []

        for message in obj.messages:
            msg_type = self.MSG_TYPE_MAP.get(message['level'], message['level'])
            ts = datetime.datetime.utcfromtimestamp(message['time']).isoformat()
            msg_state = self.STATE_MAP.get(message['state'].upper(), message['state'].upper())
            msg = {
                'id': ts,
                'state': msg_state,
                'message_type': msg_type,
                'message_text': message['message']
            }
            task_messages.append(msg)

        return {
            'request_username': task.kwargs.get('request_username'),
            'github_user': task.kwargs.get('github_user'),
            'github_repo': task.kwargs.get('github_repo'),
            'github_reference': task.kwargs.get('github_reference'),
            'alternate_role_name': task.kwargs.get('alternate_role_name'),
            'task_messages': task_messages
        }


class LegacyRoleTagSerializer(serializers.ModelSerializer):

    count = serializers.IntegerField(read_only=True)

    class Meta:
        model = LegacyRoleTag
        fields = ['name', 'count']
