import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "insights.compose.env",
            "run_tests": True,
            "db_restore": None,

            # The minio client can take a long time to install
            "wait_before_tests": 120
        }
    ]
)