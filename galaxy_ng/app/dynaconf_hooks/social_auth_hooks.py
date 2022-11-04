from typing import Any, Dict
from dynaconf import Dynaconf


def configure_socialauth(settings: Dynaconf) -> Dict[str, Any]:
    """Configure social auth settings for galaxy.

    This function returns a dictionary that will be merged to the settings.
    """

    data = {}

    # SOCIAL_AUTH_GITHUB_BASE_URL = \
    #   settings.get('SOCIAL_AUTH_GITHUB_BASE_URL', default='https://github.com')
    # SOCIAL_AUTH_GITHUB_API_URL = \
    #   settings.get('SOCIAL_AUTH_GITHUB_BASE_URL', default='https://api.github.com')

    SOCIAL_AUTH_GITHUB_KEY = settings.get("SOCIAL_AUTH_GITHUB_KEY", default=None)
    SOCIAL_AUTH_GITHUB_SECRET = settings.get("SOCIAL_AUTH_GITHUB_SECRET", default=None)

    if all([SOCIAL_AUTH_GITHUB_KEY, SOCIAL_AUTH_GITHUB_SECRET]):

        # Add to installed apps
        data["INSTALLED_APPS"] = ["social_django", "dynaconf_merge"]

        # Make sure the UI knows to do ext auth
        data["GALAXY_FEATURE_FLAGS__external_authentication"] = True

        backends = settings.get("AUTHENTICATION_BACKENDS", default=[])
        backends.append("galaxy_ng.social.GalaxyNGOAuth2")
        backends.append("dynaconf_merge")
        data["AUTHENTICATION_BACKENDS"] = backends
        data["DEFAULT_AUTHENTICATION_BACKENDS"] = backends
        data["GALAXY_AUTHENTICATION_BACKENDS"] = backends

        data['DEFAULT_AUTHENTICATION_CLASSES'] = [
            "rest_framework.authentication.SessionAuthentication",
            "rest_framework.authentication.TokenAuthentication",
            "rest_framework.authentication.BasicAuthentication",
        ]

        data['GALAXY_AUTHENTICATION_CLASSES'] = [
            "rest_framework.authentication.SessionAuthentication",
            "rest_framework.authentication.TokenAuthentication",
            "rest_framework.authentication.BasicAuthentication",
        ]

        data['REST_FRAMEWORK_AUTHENTICATION_CLASSES'] = [
            "rest_framework.authentication.SessionAuthentication",
            "rest_framework.authentication.TokenAuthentication",
            "rest_framework.authentication.BasicAuthentication",
        ]

        # Override the get_username step so that social users
        # are associated to existing users instead of creating
        # a whole new randomized username.
        data['SOCIAL_AUTH_PIPELINE'] = [
            'social_core.pipeline.social_auth.social_details',
            'social_core.pipeline.social_auth.social_uid',
            'social_core.pipeline.social_auth.auth_allowed',
            'social_core.pipeline.social_auth.social_user',
            # 'social_core.pipeline.user.get_username',
            'galaxy_ng.social.pipeline.user.get_username',
            # 'social_core.pipeline.user.create_user',
            'galaxy_ng.social.pipeline.user.create_user',
            'social_core.pipeline.social_auth.associate_user',
            'social_core.pipeline.social_auth.load_extra_data',
            'social_core.pipeline.user.user_details'
        ]

    return data
