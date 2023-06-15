import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "insights.compose.env",
            "run_tests": True,
            "db_restore": None,
            "pytest_flags": '-m "not standalone_only and not community_only and not rbac_roles and not iqe_rbac_test and not sync and not rm_sync and not x_repo_search and not rbac_repos"'
        }
    ]
)
