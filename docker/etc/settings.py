import os

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_DEFAULT_ACL = None

CONTENT_PATH_PREFIX = "/api/automation-hub/v3/artifacts/collections/"

GALAXY_API_PATH_PREFIX = "/api/automation-hub"
GALAXY_AUTHENTICATION_CLASSES = ['galaxy_ng.app.auth.auth.RHIdentityAuthentication']
GALAXY_PERMISSION_CLASSES = ['rest_framework.permissions.IsAuthenticated',
                             'galaxy_ng.app.auth.auth.RHEntitlementRequired']

GALAXY_DEPLOYMENT_MODE = 'insights'

X_PULP_CONTENT_HOST = "pulp-content-app"
X_PULP_CONTENT_PORT = 24816

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('PULP_DB_NAME', ''),
        'HOST': os.environ.get('PULP_DB_HOST', 'localhost'),
        'PORT': os.environ.get('PULP_DB_PORT', ''),
        'USER': os.environ.get('PULP_DB_USER', ''),
        'PASSWORD': os.environ.get('PULP_DB_PASSWORD', ''),
    }
}

REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES = ['rest_framework.renderers.JSONRenderer']

# Clowder
# -------
try:
    import app_common_python as clowder_config
except ImportError:
    clowder_config = None

if clowder_config and clowder_config.isClowderEnabled():
    # Database configuration
    LocalConfig = clowder_config.LoadedConfig
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': LocalConfig.database.name,
        'HOST': LocalConfig.database.hostname,
        'PORT': LocalConfig.database.port,
        'USER': LocalConfig.database.username,
        'PASSWORD': LocalConfig.database.password
    }
    # AWS S3 configuration
    AWS_S3_ENTRYPOINT_URL = 'http://{}:{}'.format(
        LocalConfig.objectStore.hostname,
        LocalConfig.objectStore.port
    )
    AWS_ACCESS_KEY_ID = LocalConfig.objectStore.accessKey
    AWS_SECRET_ACCESS_KEY = LocalConfig.objectStore.secretKey
    AWS_STORAGE_BUCKET_NAME = LocalConfig.objectStore.buckets[0].name
    del LocalConfig

# Logging
# -------
_logging_handlers = ['console']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '%(name)s:%(levelname)s: %(message)s'},
        'default': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        "collection_import": {
            "level": "DEBUG",
            "class": "pulp_ansible.app.logutils.CollectionImportHandler",
            "formatter": "simple",
        },
        # 'cloudwatch': {
        #     'level': 'INFO',
        #     'class': 'galaxy_ng.contrib.cloudwatch.CloudWatchHandler',
        # },
    },
    'root': {
        'level': 'INFO',
        'handlers': _logging_handlers,
    },
    'loggers': {
        'django': {
            'level': 'INFO',
            'handlers': _logging_handlers,
            'propagate': False,
        },
        'django.request': {
            'level': 'INFO',
            'handlers': _logging_handlers,
            'propagate': False,
        },
        'django.server': {
            'level': 'INFO',
            'handlers': _logging_handlers,
            'propagate': False,
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': _logging_handlers,
            'propagate': False,
        },
        "pulp_ansible.app.tasks.collection.import_collection": {
            "level": "INFO",
            "handlers": ["collection_import"],
            "propagate": False,
        },
    }
}
