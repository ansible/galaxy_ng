import action_lib
import sys

rbac_parallel_group = None

rbac_parallel_group = sys.argv[1] if len(sys.argv) == 2 else None
rbac_marker = rbac_parallel_group if rbac_parallel_group else "rbac_roles"

pytest_flags = "-m {0}".format(rbac_marker)

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "standalone.compose.env",
            "run_tests": True,
            "db_restore": None,
            "pytest_flags": pytest_flags
        }
    ]
)
