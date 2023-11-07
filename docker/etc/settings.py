# FIXME(cutwater): Refactoring required. Merge this settings file into
#                  main galaxy_ng/app/settings.py file.
#                  Split the configuration if necessary.
import os


DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_DEFAULT_ACL = None

CONTENT_PATH_PREFIX = "/api/automation-hub/v3/artifacts/collections/"
ANSIBLE_API_HOSTNAME = os.environ.get('PULP_CONTENT_ORIGIN')

GALAXY_API_PATH_PREFIX = "/api/automation-hub"
GALAXY_AUTHENTICATION_CLASSES = ['galaxy_ng.app.auth.auth.RHIdentityAuthentication']

# GALAXY_AUTO_SIGN_COLLECTIONS = True
# GALAXY_COLLECTION_SIGNING_SERVICE = "ansible-default"
"""
By default the signing variables are not set.
if one want to enable signing, then set the following variables
on the per environment basis. e.g: export PULP_GALAXY_....
"""

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

# FIXME(cutwater): This looks redundant and should be removed.
REDIS_HOST = os.environ.get('PULP_REDIS_HOST')
REDIS_PORT = os.environ.get('PULP_REDIS_PORT')

REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES = ['rest_framework.renderers.JSONRenderer']

_enabled_handlers = ['console']
_extra_handlers = {}

# Clowder
# -------
try:
    import app_common_python as clowder_config
except ImportError:
    clowder_config = None


def _make_aws_endpoint(config):
    scheme = 'https' if config.tls else 'http'
    port = config.port

    if "amazonaws.com" in config.hostname:
        global AWS_S3_ADDRESSING_STYLE, AWS_S3_SIGNATURE_VERSION
        AWS_S3_ADDRESSING_STYLE = "virtual"
        AWS_S3_SIGNATURE_VERSION = "s3v4"
    netloc = config.hostname
    if ((scheme == 'http' and port != 80)
            or (scheme == 'https' and port != 443)):
        netloc = f"{netloc}:{port}"

    return f"{scheme}://{netloc}"


if clowder_config and clowder_config.isClowderEnabled():
    _LoadedConfig = clowder_config.LoadedConfig

    # Database configuration
    if _LoadedConfig.database.rdsCa:
        DB_SSLROOTCERT = _LoadedConfig.rds_ca()
    else:
        DB_SSLROOTCERT = ""
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _LoadedConfig.database.name,
        'HOST': _LoadedConfig.database.hostname,
        'PORT': _LoadedConfig.database.port,
        'USER': _LoadedConfig.database.username,
        'PASSWORD': _LoadedConfig.database.password,
        'OPTIONS': {
            'sslmode': _LoadedConfig.database.sslMode,
            'sslrootcert': DB_SSLROOTCERT
        }
    }

    # AWS S3 configuration
    AWS_S3_ENDPOINT_URL = _make_aws_endpoint(_LoadedConfig.objectStore)
    AWS_ACCESS_KEY_ID = _LoadedConfig.objectStore.buckets[0].accessKey
    AWS_SECRET_ACCESS_KEY = _LoadedConfig.objectStore.buckets[0].secretKey
    AWS_S3_REGION_NAME = _LoadedConfig.objectStore.buckets[0].region
    AWS_STORAGE_BUCKET_NAME = _LoadedConfig.objectStore.buckets[0].name

    # Redis configuration
    REDIS_HOST = _LoadedConfig.inMemoryDb.hostname
    REDIS_PORT = _LoadedConfig.inMemoryDb.port
    REDIS_PASSWORD = _LoadedConfig.inMemoryDb.password
    REDIS_DB = 0
    REDIS_SSL = os.environ.get("PULP_REDIS_SSL") == "true"

    REDIS_URL = "{scheme}://{password}{host}:{port}/{db}".format(
        scheme=("rediss" if REDIS_SSL else "redis"),
        password=f":{REDIS_PASSWORD}@" if REDIS_PASSWORD else "",
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
    )

    try:
        with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace') as f:
            K8S_NAMESPACE = f.read()
    except OSError:
        K8S_NAMESPACE = None

    # Cloudwatch configuration
    CLOUDWATCH_ACCESS_KEY_ID = _LoadedConfig.logging.cloudwatch.accessKeyId
    CLOUDWATCH_SECRET_ACCESS_KEY = _LoadedConfig.logging.cloudwatch.secretAccessKey
    CLOUDWATCH_REGION_NAME = _LoadedConfig.logging.cloudwatch.region
    CLOUDWATCH_LOGGING_GROUP = _LoadedConfig.logging.cloudwatch.logGroup
    CLOUDWATCH_LOGGING_STREAM_NAME = K8S_NAMESPACE

    if all((
            CLOUDWATCH_ACCESS_KEY_ID,
            CLOUDWATCH_SECRET_ACCESS_KEY,
            CLOUDWATCH_LOGGING_STREAM_NAME
    )):
        _enabled_handlers.append("cloudwatch")
        _extra_handlers["cloudwatch"] = {
            "level": "INFO",
            "class": "galaxy_ng.contrib.cloudwatch.CloudWatchHandler",
        }

    del _LoadedConfig

# Logging
# -------
LOGGING = {
    "dynaconf_merge": True,
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

    },
    'root': {
        'level': 'INFO',
        'handlers': _enabled_handlers,
    },
    'loggers': {
        'django': {
            'level': 'INFO',
            'handlers': _enabled_handlers,
            'propagate': False,
        },
        'django.request': {
            'level': 'INFO',
            'handlers': _enabled_handlers,
            'propagate': False,
        },
        'django.server': {
            'level': 'INFO',
            'handlers': _enabled_handlers,
            'propagate': False,
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': _enabled_handlers,
            'propagate': False,
        },
        "pulp_ansible.app.tasks.collection.import_collection": {
            "level": "INFO",
            "handlers": ["collection_import"],
            "propagate": False,
        },
    }
}
LOGGING["handlers"].update(_extra_handlers)
