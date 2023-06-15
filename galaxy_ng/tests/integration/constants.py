"""Constants usable by multiple test modules."""

USERNAME_ADMIN = "ansible-insights"
USERNAME_CONSUMER = "autohubtest3"
USERNAME_PUBLISHER = "autohubtest2"

# time.sleep() seconds for checks that poll in a loop
SLEEP_SECONDS_POLLING = 1

# time.sleep() seconds for checks that wait once
SLEEP_SECONDS_ONETIME = 3

DEFAULT_DISTROS = {
    'community': {'basepath': 'community'},
    'published': {'basepath': 'published'},
    'rejected': {'basepath': 'rejected'},
    'rh-certified': {'basepath': 'rh-certified'},
    'staging': {'basepath': 'staging'}
}


CREDENTIALS = {
    "iqe_normal_user": {
        "password": "redhat",
        "token": "abcdefghijklmnopqrstuvwxyz1234567891",
        "group": "ns_group_for_tests",
    },
    "jdoe": {
        "password": "redhat",
        "token": "abcdefghijklmnopqrstuvwxyz1234567892",
        "group": "system:partner-engineers",
    },
    "org-admin": {
        "username": "org-admin",
        "password": "redhat",
        "group": "ns_group_for_tests",
        "token": "abcdefghijklmnopqrstuvwxyz1234567893",
    },
    "notifications_admin": {
        "password": "redhat",
        "token": "abcdefghijklmnopqrstuvwxyz1234567894",
    },
    "iqe_admin": {
        "password": "redhat",
        "token": None,
    },
    "professor": {
        "password": "professor",
        "token": None,
        "gen_token": False,
    },
    "hermes": {
        "password": "hermes",
        "token": None,
        "gen_token": True,
    },
    "fry": {
        "password": "fry",
        "group": "ship_crew",
        "token": None,
        "gen_token": True,
    },
    "ee_admin": {
        "password": "redhat",
        "token": "abcdefghijklmnopqrstuvwxyz1234567895",
        "group": "ee_group_for_tests"
    },
    "gh01": {
        "password": "redhat",
        "token": None,
    },
    "gh02": {
        "password": "redhat",
        "token": None,
    },
    "geerlingguy": {
        "password": "redhat",
        "token": None,
    },
    "jctannerTEST": {
        "password": "redhat",
        "token": None,
    },
    None: {
        "password": None,
        "token": None,
    }
}

PROFILES = {
    "anonymous_user": {
        "username": {
            "ldap": None,
            "galaxy": None,
        }
    },
    "basic_user": {
        "namespaces": ["autohubtest2", "autohubtest3"],
        "username": {
            "ldap": "fry",
            "galaxy": "iqe_normal_user",
        }
    },
    "partner_engineer": {
        "roles": ["galaxy.collection_admin", "galaxy.group_admin", "galaxy.user_admin"],
        "namespaces": ["autohubtest2", "autohubtest3", "signing"],
        "username": {
            "ldap": "professor",
            "galaxy": "jdoe",
        }
    },
    "org_admin": {  # user is org admin in keycloak
        "namespaces": ["autohubtest2", "autohubtest2"],
        "username": {
            "ldap": "fry",
            "galaxy": "org-admin",
        }
    },
    "admin": {
        "is_superuser": True,
        "username": {
            "ldap": "professor",
            "galaxy": "notifications_admin",
            "github": "notifications_admin",
        }
    },
    "iqe_admin": {
        "is_superuser": True,
        "username": {
            "ldap": "hermes",
            "galaxy": "iqe_admin",
        }
    },
    "ee_admin": {
        "roles": ["galaxy.execution_environment_admin"],
        "username": {
            "ldap": "fry",
            "galaxy": "ee_admin",
        }
    },

    "github_user_1": {
        "username": {
            "github": "gh01",
        }
    },
    "github_user_2": {
        "username": {
            "github": "gh02",
        }
    },
    "geerlingguy": {
        "username": {
            "github": "geerlingguy",
        }
    },
    "jctannerTEST": {
        "username": {
            "github": "jctannerTEST",
        }
    },
}
