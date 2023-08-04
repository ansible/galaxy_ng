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
        "gen_token": False
    },
    "professor": {
        "password": "professor",
        "token": None,
        "gen_token": True,
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
        "username": None,
    },
    "basic_user": {
        "namespaces": ["autohubtest2", "autohubtest3"],
        "username": {
            "ldap": "fry",
            "galaxy": "iqe_normal_user",
            "community": "iqe_normal_user",
        }
    },
    "partner_engineer": {
        "roles": ["galaxy.collection_admin", "galaxy.group_admin", "galaxy.user_admin"],
        "namespaces": ["autohubtest2", "autohubtest3", "signing"],
        "username": {
            "ldap": "professor",
            "galaxy": "jdoe",
            "community": "jdoe",
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
            "community": "notifications_admin",
        }
    },
    "iqe_admin": {
        "is_superuser": True,
        "username": {
            "ldap": "hermes",
            "galaxy": "iqe_admin",
            "community": "iqe_admin",
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
            "community": "gh01",
        }
    },
    "github_user_2": {
        "username": {
            "community": "gh02",
        }
    },
    "geerlingguy": {
        "username": {
            "community": "geerlingguy",
        }
    },
    "jctannerTEST": {
        "username": {
            "community": "jctannerTEST",
        }
    },
}

EPHEMERAL_PROFILES = {
    # ns owner to autohubtest2, not in partner engineer group, not an SSO org admin
    "basic_user": {
        "username": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-basic",
                     "vault_key": "username"},
        "password": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-basic",
                     "vault_key": "password"},
        "token": None,
    },
    # in partner engineer group, not an SSO org admin username: ansible-hub-qe-pe2
    "partner_engineer": {
        "username": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                     "vault_key": "username"},
        "password": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                     "vault_key": "password"},
        "token": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                  "vault_key": "token"},
    },
    # an SSO org admin, not in partner engineer group
    "org_admin": {
        "username": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-rbac",
                     "vault_key": "username"},
        "password": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-rbac",
                     "vault_key": "password"},
        "token": None,
    },
    # for stage env, this can be same user as partner_engineer profile
    "admin": {
        "username": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                     "vault_key": "username"},
        "password": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                     "vault_key": "password"},
        "token": {"vault_path": "secrets/qe/stage/users/ansible-hub-qe-pe",
                  "vault_key": "token"},
    }
}

SYNC_PROFILES = {
    "remote_admin": {
        "username": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                     "vault_key": "username"},
        "password": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                     "vault_key": "password"},
        "token": {"vault_path": "secrets/qe/stage/users/ansible_insights",
                  "vault_key": "token"},
    },
    "local_admin": {  # this is a superuser
        "username": "admin",
        "password": "admin",
        "token": None,
    },
    "admin": {  # this is a superuser
        "username": "admin",
        "password": "admin",
        "token": None,
    }
}

DEPLOYED_PAH_PROFILES = {
    "basic_user": {
        "username": "iqe_normal_user",
        "password": "redhat",
        "token": "abcdefghijklmnopqrstuvwxyz1234567891",
    },
    "partner_engineer": {
        "username": "jdoe",
        "password": "redhat",
        "token": "abcdefghijklmnopqrstuvwxyz1234567892",
    },
    "org_admin": {  # user is org admin in keycloak
        "username": "org-admin",
        "password": "redhat",
        "token": "abcdefghijklmnopqrstuvwxyz1234567893",
    },
    "admin": {  # this is a superuser
        "username": "notifications_admin",
        "password": "redhat",
        "token": "abcdefghijklmnopqrstuvwxyz1234567894",
    },
    "iqe_admin": {  # this is a superuser
        "username": "iqe_admin",
        "password": "redhat",
        "token": None,
    },
    "ee_admin": {
        "username": "ee_admin",
        "password": "redhat",
        "token": "abcdefghijklmnopqrstuvwxyz1234567895",
    },
}

BETA_GALAXY_STAGE_PROFILES = {
    "regular_user": {  # it's a regular django user
        "username": {"vault_path": "secrets/qe/stage/users/beta_galaxy_reg_user",
                     "vault_key": "username"},
        "password": {"vault_path": "secrets/qe/stage/users/beta_galaxy_reg_user",
                     "vault_key": "password"},
        "token": {"vault_path": "secrets/qe/stage/users/beta_galaxy_reg_user",
                  "vault_key": "token"},
    },
    "github_user": {
        "username": {"vault_path": "secrets/qe/stage/users/github_user",
                     "vault_key": "username"},
        "password": {"vault_path": "secrets/qe/stage/users/github_user",
                     "vault_key": "password"},
        "token": None
    },
    "github_user_alt": {
        "username": {"vault_path": "secrets/qe/stage/users/github_user_alt",
                     "vault_key": "username"},
        "password": {"vault_path": "secrets/qe/stage/users/github_user_alt",
                     "vault_key": "password"},
        "token": None
    },
    "admin": {  # it's an admin django user
        "username": {"vault_path": "secrets/qe/stage/users/beta_galaxy_admin",
                     "vault_key": "username"},
        "password": {"vault_path": "secrets/qe/stage/users/beta_galaxy_admin",
                     "vault_key": "password"},
        "token": {"vault_path": "secrets/qe/stage/users/beta_galaxy_admin",
                  "vault_key": "token"},
    }
}
