import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "dab_jwt.compose.env",
            "run_tests": True,
            "db_restore": None,
            "test_script": "/src/galaxy_ng/profiles/dab_jwt/run_integration.sh"
        }
    ]
)
