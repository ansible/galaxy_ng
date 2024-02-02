import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "standalone.compose.env",
            "run_tests": True,
            "run_playbooks": False,
            "db_restore": None,
            "pytest_flags": "-m iqe_rbac_test"
        }
    ]
)
