import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "standalone.compose.env",
            "run_tests": True,
            "db_restore": None,
            "pytest_flags": '-m "certified_sync or rm_sync"'
        },
        {
            "env_file": "sync-test.compose.env",
            "run_tests": False,
            "db_restore": "insights-fixture",
            "pytest_flags": None
        }
    ]
)
