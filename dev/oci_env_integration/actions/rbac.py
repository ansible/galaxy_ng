import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "standalone.compose.env",
            "run_tests": True,
            "db_restore": None,
            "pytest_flags": "-m rbac_roles"
        }
    ]
)


env_2 = action_lib.OCIEnvPerformanceTest(
    envs=[
        {
            "env_file": "standalone.compose.env",
            "run_tests": True,
            "db_restore": None,
            "pytest_flags": "-m rbac_roles"
        }
    ]
)
