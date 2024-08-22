import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "ldap.compose.env",
            "run_tests": True,
            "db_restore": None,
        }
    ]
)