from rest_framework import serializers

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole


class LegacyNamespacesSerializer(serializers.ModelSerializer):

    summary_fields = serializers.SerializerMethodField()
    # date_joined = serializers.SerializerMethodField()
    # active = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    # full_name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = LegacyNamespace
        fields = [
            'id',
            'url',
            'summary_fields',
            'created',
            'modified',
            'name',
            # 'full_name',
            # 'date_joined',
            'avatar_url',
            # 'active'
        ]

    def get_name(self, obj):
        if hasattr(obj, 'name'):
            return obj.name
        if hasattr(obj, 'username'):
            return obj.username

    def get_url(self, obj):
        return ''

    # def get_full_name(self, obj):
    #    return ''

    def get_date_joined(self, obj):
        return obj.created

    def get_summary_fields(self, obj):
        owners = obj.owners.all()
        owners = [{'id': x.id, 'username': x.username} for x in owners]
        return {'owners': owners}

    # TODO: What does this actually mean?
    # def get_active(self, obj):
    #    return True

    def get_avatar_url(self, obj):
        url = f'https://github.com/{obj.name}.png'
        return url


class LegacyNamespaceOwnerSerializer(serializers.Serializer):

    id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id']

    def get_id(self, obj):
        return obj.id


class LegacyUserSerializer(serializers.ModelSerializer):

    summary_fields = serializers.SerializerMethodField()
    date_joined = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()
    # active = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

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
            # 'active'
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


class LegacyRoleSerializer(serializers.ModelSerializer):

    username = serializers.SerializerMethodField()
    github_user = serializers.SerializerMethodField()
    github_repo = serializers.SerializerMethodField()
    github_branch = serializers.SerializerMethodField()
    commit = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    summary_fields = serializers.SerializerMethodField()
    upstream_id = serializers.SerializerMethodField()

    class Meta:
        model = LegacyRole
        fields = [
            'id',
            'upstream_id',
            'created',
            'modified',
            'github_user',
            'username',
            'github_repo',
            'github_branch',
            'commit',
            'name',
            'description',
            'summary_fields'
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

    def get_github_user(self, obj):
        """
        Return the github_user.

        The client cli will use this to build the download url
        of the role in the form of:
            https://github.com/<github_user>/<github_repo>/...
        """
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
        return obj.full_metadata.get('github_reference')

    def get_commit(self, obj):
        return obj.full_metadata.get('commit')

    def get_description(self, obj):
        return obj.full_metadata.get('description')

    def get_summary_fields(self, obj):
        versions = obj.full_metadata.get('versions', [])
        dependencies = obj.full_metadata.get('dependencies', [])
        tags = obj.full_metadata.get('tags', [])
        return {
            'dependencies': dependencies,
            'namespace': {
                'id': obj.namespace.id,
                'name': obj.namespace.name,
                'avatar_url': f'https://github.com/{obj.namespace.name}.png'
            },
            'provider_namespace': {
                'id': obj.namespace.id,
                'name': obj.namespace.name
            },
            'repository': {
                'name': obj.name,
                'original_name': obj.full_metadata.get('github_repo')
            },
            'tags': tags,
            'versions': versions
        }


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

        fields = [
            'id',
            'url',
            'related',
            'summary_fields',
            'created',
            'modified',
            'name',
            'version',
            'commit_date',
            'commit_sha',
            'download_url',
            'active'
        ]

        results = []

        for idv, version in enumerate(versions):
            ds = {}
            for field in fields:
                if field in ['created', 'modified'] and field not in version:
                    ds[field] = version.get('release_date')
                    continue
                if field == 'version':
                    ds[field] = version['name']
                    continue
                ds[field] = version.get(field)
            ds['id'] = idv
            results.append(ds)

        return results


class LegacyTaskSerializer():

    @property
    def data(self):
        return {}


class LegacySyncSerializer(serializers.Serializer):

    baseurl = serializers.CharField(
        required=False,
        default='https://galaxy.ansible.com/api/v1/roles/'
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
    alternate_role_name = serializers.CharField(required=False)

    class Meta:
        model = None
        fields = [
            'github_user',
            'github_repo',
            'alternate_role_name'
        ]


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
        fields = ['id', 'state', 'summary_fields']


class LegacyTaskDetailSerializer(serializers.Serializer):

    results = LegacyTaskResultsSerializer()

    class Meta:
        model = None
        fields = ['results']
