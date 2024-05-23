import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "dab_jwt.compose.env",
            "run_tests": True,
            "db_restore": None,
        }
    ]
)
