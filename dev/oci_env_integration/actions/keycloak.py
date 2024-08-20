import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "keycloak.compose.env",
            "run_tests": True,
            "db_restore": None,

            # the keycloak profile performs some setup after the service
            # comes online
            "wait_before_tests": 120
        }
    ]
)


env_2 = action_lib.OCIEnvPerformanceTest(
    envs=[
        {
            "env_file": "keycloak.compose.env",
            "run_tests": True,
            "db_restore": None,
        }
    ]
)
