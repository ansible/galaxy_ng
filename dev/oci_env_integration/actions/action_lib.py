import time
import subprocess
import shutil
import shlex
import os


class OCIEnvIntegrationTest:
    """
    This class abstracts away all the scripts that need to be run to set up oci-env
    to run integration tests for a specific environment configuration.

    Usage:

    OCIEnvIntegrationTest(
        envs=[
            {
                "env_file": "insights.compose.env",
                "run_tests": True,
                "db_restore": "insights-fixture",
                "pytest_flags": "-m my-tests,
                "wait_before_tests": 60
            }
        ]
    )

    Params

    envs: list of environment definitions to spin up for testing. Environment
    definitions accept the following args:

        env_file (string, required): oci-env env file to use for the tests. These are all loaded
            from dev/oci_env_integration/oci_env_configs
        run_tests (boolean, required): if true, integration tests will be run inside this instance
        db_restore (string, optional): database backup to restore before running tests These are all
            loaded from dev/oci_env_integration/oci_env_configs. When defining this, omit
            the file extension (ex: fixture, not fixtur.tar.gz)
        pytest_flags (string, optional): flags to pass to pytest when running integration tests.
            oci-env automatically identifies which pytest marks to apply to tests based
            on the environment that's running, however in some cases you may want to
            override this if the test is meant to only apply to a subset of tests (such as rbac)
        wait_before_tests (int, optional): some environments need some extra time set-up configs
            that oci-env poll can't monitor. This will cause the environment to wait the given
            number of seconds before running integration tests after the stack has spun up.

    """
    do_dump_logs = False
    do_teardown = True
    flags = ""
    envs = {}
    failed = None

    def __init__(self, envs):
        for env in envs:
            env_file = env["env_file"]
            self.envs[env_file] = env
            self.envs[env_file]["env_path"] = f"dev/oci_env_integration/oci_env_configs/{env_file}"

        self.do_dump_logs = os.environ.get("GH_DUMP_LOGS", "0") == "1"
        self.do_teardown = os.environ.get("GH_TEARDOWN", "1") == "1"
        self.flags = os.environ.get("GH_FLAGS", "")

        import epdb; epdb.st()

        self.failed = False
        try:
            self.set_up_env()
            self.run_test()
        except Exception as e:
            print(e)
            self.failed = True
        finally:
            self.dump_logs()
            self.teardown()

        if self.failed:
            exit(1)

    def set_up_env(self):
        # start stack
        for env in self.envs:
            self.exec_cmd(env, "compose up -d")

        # wait for stack to come online
        for env in self.envs:
            self.exec_cmd(env, "poll --wait 10 --attempts 30")

            # There's a bug in the pulp base images where all the container services get
            # run twice, so even though the container reports it's online, the services
            # may go down again.
            time.sleep(10)
            self.exec_cmd(env, "poll --wait 2 --attempts 30")

        # set up db dumps
        for env in self.envs:
            if db_dump := self.envs[env].get("db_restore", None):
                dump_path = f"dev/oci_env_integration/test_fixtures/{db_dump}.tar.gz"

                db_backup_path = "../oci_env/db_backup/"
                if not os.path.isdir(db_backup_path):
                    os.makedirs(db_backup_path)
                shutil.copyfile(dump_path, f"{db_backup_path}{db_dump}.tar.gz")
                self.exec_cmd(env, f"db restore -f {db_dump} --migrate")
                time.sleep(10)
                self.exec_cmd(env, "poll --wait 2 --attempts 30")

    def exec_cmd(self, env, cmd):
        path = f"dev/oci_env_integration/oci_env_configs/{env}"
        exec_cmd = ["oci-env", "-e", path] + shlex.split(cmd)
        print(" ".join(exec_cmd))
        rc = subprocess.call(exec_cmd)

        assert rc == 0

    def run_test(self):
        for env in self.envs:
            pytest_flags = self.envs[env].get("pytest_flags")
            if pytest_flags is None:
                pytest_flags = ""

            if wait_time := self.envs[env].get("wait_before_tests", 20):
                print(f"waiting {wait_time} seconds")
                time.sleep(wait_time)

            if self.envs[env]["run_tests"]:
                if self.envs[env].get("test_script"):
                    self.exec_cmd(
                        env,
                        f"exec bash {self.envs[env]['test_script']}"
                        f" {pytest_flags} {self.flags}"
                    )
                else:
                    self.exec_cmd(
                        env,
                        "exec bash /src/galaxy_ng/profiles/base/run_integration.sh"
                        f" {pytest_flags} {self.flags}"
                    )

    def dump_logs(self):
        if not self.do_dump_logs:
            return
        if self.failed:
            for env in self.envs:
                self.exec_cmd(env, "compose logs")

    def teardown(self):
        if not self.do_teardown:
            return
        for env in self.envs:
            self.exec_cmd(env, "compose down -v")
