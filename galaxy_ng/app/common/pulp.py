from django.conf import settings
from galaxy_pulp import Configuration, ApiClient


def get_configuration():
    config = Configuration(
        host="{proto}://{host}:{port}".format(
            proto=settings.get('X_PULP_API_PROTO', 'http'),
            host=settings.X_PULP_API_HOST,
            port=settings.X_PULP_API_PORT
        ),
        username=settings.X_PULP_API_USER,
        password=settings.X_PULP_API_PASSWORD,
    )
    config.safe_chars_for_path_param = '/'
    if 'VERIFY_SSL' in settings:
        config.verify_ssl = settings.VERIFY_SSL
    return config


def get_client():
    config = get_configuration()
    return ApiClient(configuration=config)
