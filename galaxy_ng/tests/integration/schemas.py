#!/usr/bin/env python3


schema_objectlist = {
    'type': 'object',
    'additional_properties': False,
    'required': ['data', 'links', 'meta'],
    'properties': {
        'data': {'type': 'array'},
        'links': {'type': 'object'},
        'meta': {'type': 'object'},
    }
}


schema_userlist = {
    'type': 'object',
    'additional_properties': False,
    'required': ['data', 'links', 'meta'],
    'properties': {
        'data': {'type': 'array'},
        'links': {'type': 'object'},
        'meta': {'type': 'object'},
    }
}


schema_user = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'id',
        'first_name',
        'last_name',
        'date_joined',
        'email',
        'is_superuser',
        'groups',
        'auth_provider'
    ],
    'properties': {
        'id': {'type': 'number'},
        'first_name': {'type': 'string'},
        'last_name': {'type': 'string'},
        'date_joined': {'type': 'string'},
        'email': {'type': 'string'},
        'is_superuser': {'type': 'boolean'},
        'groups': {'type': 'array'},
        'auth_provider': {'type': 'array'},
    }
}


schema_me = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'id',
        'first_name',
        'last_name',
        'date_joined',
        'email',
        'is_anonymous',
        'is_superuser',
        'groups',
        'auth_provider'
    ],
    'properties': {
        'id': {'type': 'number'},
        'first_name': {'type': 'string'},
        'last_name': {'type': 'string'},
        'date_joined': {'type': 'string'},
        'email': {'type': 'string'},
        'is_superuser': {'type': 'boolean'},
        'is_anonymous': {'type': 'boolean'},
        'groups': {'type': 'array'},
        'auth_provider': {'type': 'array'},
    }
}


schema_settings = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'GALAXY_AUTO_SIGN_COLLECTIONS',
        'GALAXY_COLLECTION_SIGNING_SERVICE',
        'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS',
        'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD',
        'GALAXY_FEATURE_FLAGS',
        'GALAXY_MINIMUM_PASSWORD_LENGTH',
        'GALAXY_REQUIRE_CONTENT_APPROVAL',
        'GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL',
        'GALAXY_SIGNATURE_UPLOAD_ENABLED',
        'GALAXY_TOKEN_EXPIRATION',
        'GALAXY_CONTAINER_SIGNING_SERVICE',
    ],
    'properties': {
        'GALAXY_AUTO_SIGN_COLLECTIONS': {'type': 'boolean'},
        'GALAXY_COLLECTION_SIGNING_SERVICE': {'type': 'string'},
        'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS': {'type': 'boolean'},
        'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD': {'type': 'boolean'},
        'GALAXY_FEATURE_FLAGS': {'type': 'object'},
        'GALAXY_MINIMUM_PASSWORD_LENGTH': {'type': ['number', 'null']},  # FIXME
        'GALAXY_REQUIRE_CONTENT_APPROVAL': {'type': 'boolean'},
        'GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL': {'type': 'boolean'},
        'GALAXY_SIGNATURE_UPLOAD_ENABLED': {'type': 'boolean'},
        'GALAXY_TOKEN_EXPIRATION': {'type': ['number', 'null']},  # FIXME
        'GALAXY_CONTAINER_SIGNING_SERVICE': {'type': 'string'},
    }
}


schema_featureflags = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'collection_signing',
        'signatures_enabled',
        'require_upload_signatures',
        'can_create_signatures',
        'can_upload_signatures',
        'collection_auto_sign',
        'display_signatures',
        'execution_environments',
        'container_signing',
        '_messages',
    ],
    'properties': {
        'collection_signing': {'type': 'boolean'},
        'signatures_enabled': {'type': 'boolean'},
        'require_upload_signatures': {'type': 'boolean'},
        'can_create_signatures': {'type': 'boolean'},
        'can_upload_signatures': {'type': 'boolean'},
        'collection_auto_sign': {'type': 'boolean'},
        'display_signatures': {'type': 'boolean'},
        'execution_environments': {'type': 'boolean'},
        'container_signing': {'type': 'boolean'},
        '_messages': {'type': 'array'},
    }
}


schema_distro = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'base_path',
        'name',
        'pulp_id',
        'repository'
    ],
    'properties': {
        'base_path': {'type': 'string'},
        'name': {'type': 'string'},
        'pulp_id': {'type': 'string'},
        'repository': {'type': 'object'}
    }
}


schema_distro_repository = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'content_count',
        'description',
        'gpgkey',
        'name',
        'pulp_id',
        'pulp_last_updated'
    ],
    'properties': {
        'countent_count': {'type': 'number'},
        'description': {'type': ['string', 'null']},
        'gpgkey': {'type': ['string', 'null']},
        'name': {'type': 'string'},
        'pulp_id': {'type': 'string'},
        'pulp_last_updated': {'type': 'string'},
    }
}


schema_remote = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'auth_url',
        'ca_cert',
        'client_cert',
        'created_at',
        'download_concurrency',
        'last_sync_task',
        'name',
        'pk',
        'policy',
        'proxy_url',
        'proxy_username',
        'pulp_href',
        'rate_limit',
        'repositories',
        'requirements_file',
        'signed_only',
        'tls_validation',
        'updated_at',
        'url',
        'username',
        'write_only_fields',
    ],
    'properties': {
        'auth_url': {'type': ['string', 'null']},
        'ca_cert': {'type': ['string', 'null']},
        'client_cert': {'type': ['string', 'null']},
        'created_at': {'type': 'string'},
        'download_concurrency': {'type': ['number', 'null']},
        'last_sync_task': {'type': 'object'},
        'name': {'type': 'string'},
        'pk': {'type': 'string'},
        'policy': {'type': 'string'},
        'proxy_url': {'type': ['string', 'null']},
        'proxy_username': {'type': ['string', 'null']},
        'pulp_href': {'type': 'string'},
        'rate_limit': {'type': 'number'},
        'repositories': {'type': 'array'},
        'requirements_file': {'type': ['string', 'null']},
        'signed_only': {'type': 'boolean'},
        'tls_validation': {'type': 'boolean'},
        'updated_at': {'type': 'string'},
        'url': {'type': 'string'},
        'username': {'type': ['string', 'null']},
        'write_only_fields': {'type': 'array'},
    }
}


schema_group = {
    'type': 'object',
    'additional_properties': False,
    'required': ['id', 'name', 'pulp_href'],
    'properties': {
        'id': {'type': 'number'},
        'name': {'type': 'string'},
        'pulp_href': {'type': 'string'}
    }
}


schema_collectionversion = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'contents',
        'created_at',
        'id',
        'metadata',
        'name',
        'namespace',
        # 'repository_list',
        'requires_ansible',
        'sign_state',
        'version',
    ],
    'properties': {
        'contents': {'type': 'array'},
        'created_at': {'type': 'string'},
        'id': {'type': 'string'},
        'metadata': {'type': 'object'},
        'name': {'type': 'string'},
        'namespace': {'type': 'string'},
        'repository_list': {'type': 'array'},
        'requires_ansible': {'type': 'string'},
        'sign_state': {'type': 'string'},
        'version': {'type': 'string'},
    }
}


schema_collectionversion_metadata = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'authors',
        'contents',
        'dependencies',
        'description',
        'documentation',
        'homepage',
        'issues',
        'license',
        'repository',
        'signatures',
        'tags',
    ],
    'properties': {
        'authors': {'type': 'array'},
        'contents': {'type': 'array'},
        'dependencies': {'type': 'object'},
        'description': {'type': 'string'},
        'documentation': {'type': 'string'},
        'homepage': {'type': 'string'},
        'issues': {'type': 'string'},
        'license': {'type': 'array'},
        'repository': {'type': 'string'},
        'signatures': {'type': 'array'},
        'tags': {'type': 'array'},
    }
}


schema_collection_import = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'created_at',
        'finished_at',
        'id',
        'name',
        'namespace',
        'started_at',
        'state',
        'updated_at',
        'version'
    ],
    'properties': {
        'created_at': {'type': 'string'},
        'finished_at': {'type': 'string'},
        'id': {'type': 'string'},
        'name': {'type': 'string'},
        'namespace': {'type': 'string'},
        'started_at': {'type': 'string'},
        'state': {'type': 'string'},
        'updated_at': {'type': 'string'},
        'version': {'type': 'string'},
    }
}


schema_collection_import_detail = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'created_at',
        'finished_at',
        'id',
        'messages',
        'name',
        'namespace',
        'started_at',
        'state',
        'updated_at',
        'version'
    ],
    'properties': {
        'created_at': {'type': 'string'},
        'error': {'type': ['object', 'null']},
        'finished_at': {'type': 'string'},
        'messages': {'type': 'array'},
        'id': {'type': 'string'},
        'name': {'type': 'string'},
        'namespace': {'type': 'string'},
        'started_at': {'type': 'string'},
        'state': {'type': 'string'},
        'updated_at': {'type': 'string'},
        'version': {'type': 'string'},
    }
}


schema_ee_namespace_detail = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'name',
        'my_permissions',
        'owners',
        'groups',
    ],
    'properties': {
        'name': {'type': 'string'},
        'my_permissions': {'type': ['array', 'null']},
        'owners': {'type': ['array', 'null']},
        'groups': {'type': ['array', 'null']},
    }
}


schema_ee_registry = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'ca_cert',
        'client_cert',
        'created_at',
        'download_concurrency',
        'is_indexable',
        'last_sync_task',
        'name',
        'pk',
        'policy',
        'proxy_url',
        'rate_limit',
        'tls_validation',
        'updated_at',
        'url',
        'write_only_fields',
    ],
    'properties': {
        'ca_cert': {'type': ['string', 'null']},
        'client_cert': {'type': ['string', 'null']},
        'created_at': {'type': 'string'},
        'download_concurrency': {'type': ['number', 'null']},
        'is_indexable': {'type': 'boolean'},
        'last_sync_task': {'type': 'object'},
        'name': {'type': 'string'},
        'pk': {'type': 'string'},
        'policy': {'type': 'string'},
        'proxy_url': {'type': ['string', 'null']},
        'rate_limit': {'type': ['number', 'null']},
        'tls_validation': {'type': 'boolean'},
        'updated_at': {'type': 'string'},
        'url': {'type': 'string'},
        'write_only_fields': {'type': 'array'},
    }
}


schema_task = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'task',
    ],
    'properties': {
        'task': {'type': 'string'},
    }
}


schema_task_detail = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'child_tasks',
        'created_resources',
        'error',
        'finished_at',
        'logging_cid',
        'name',
        'parent_task',
        'progress_reports',
        'pulp_created',
        'pulp_href',
        'reserved_resources_record',
        'started_at',
        'state',
        'task_group',
        'worker'
    ],
    'properties': {
        'child_tasks': {'type': 'array'},
        'created_resources': {'type': 'array'},
        'error': {'type': ['object', 'null']},
        'finished_at': {'type': ['string', 'null']},
        'logging_cid': {'type': 'string'},
        'name': {'type': 'string'},
        'parent_task': {'type': ['string', 'null']},
        'progress_reports': {'type': 'array'},
        'pulp_created': {'type': 'string'},
        'pulp_href': {'type': 'string'},
        'reserved_resources_record': {'type': 'array'},
        'started_at': {'type': ['string', 'null']},
        'state': {'type': 'string'},
        'task_group': {'type': ['string', 'null']},
        'worker': {'type': ['string', 'null']},
    }
}

schema_namespace_detail = {
    'type': 'object',
    'additional_properties': False,
    'required': [
        'id',
        'groups',
        'name',
        'pulp_href',
    ],
    'properties': {
        'avatar_url': {'type': 'string'},
        'company': {'type': 'string'},
        'description': {'type': 'string'},
        'email': {'type': 'string'},
        'groups': {'type': 'array'},
        'id': {'type': 'number'},
        'links': {'type': 'array'},
        'name': {'type': 'string'},
        'pulp_href': {'type': 'string'},
        'related_field': {'type': 'object'},
        'resources': {'type': 'string'},
    }
}
