import os
import subprocess
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPT = Path(__file__).parents[3] / "docker/bin/wait-for-migrations"


class TestWaitForMigrations(unittest.TestCase):
    """Exercise migration wait retries with controlled command results."""

    def _run_script(self, mode):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            bin_path = temp_path / "bin"
            bin_path.mkdir()
            state_file = temp_path / "state"

            self._write_executable(
                bin_path / "timeout",
                """
                # The migration script's timeout is not under test here.
                shift
                exec "$@"
                """,
            )
            self._write_executable(bin_path / "sleep", "exit 0")
            self._write_executable(
                bin_path / "django-admin",
                """
                count=0
                if [[ -f "${FAKE_STATE_FILE}" ]]; then
                    count=$(<"${FAKE_STATE_FILE}")
                fi
                count=$((count + 1))
                printf '%s\n' "${count}" > "${FAKE_STATE_FILE}"

                case "${FAKE_MODE}" in
                    persistent_failure)
                        printf '%s\n' "migration stderr line 1" "migration stderr line 2" >&2
                        printf '%s\n' "migration stdout line"
                        exit 7
                        ;;
                    pending_then_applied)
                        if (( count < 3 )); then
                            printf '%s\n' "[ ] app.0001_initial"
                        else
                            printf '%s\n' "[X] app.0001_initial"
                        fi
                        ;;
                    persistent_pending)
                        printf '%s\n' "[ ] app.0001_initial"
                        ;;
                    failure_then_applied)
                        if (( count == 1 )); then
                            printf '%s\n' "database unavailable" >&2
                            exit 7
                        fi
                        printf '%s\n' "[X] app.0001_initial"
                        ;;
                esac
                """,
            )

            env = os.environ.copy()
            env.update(
                {
                    "FAKE_MODE": mode,
                    "FAKE_STATE_FILE": str(state_file),
                    "PATH": f"{bin_path}{os.pathsep}{env['PATH']}",
                }
            )
            result = subprocess.run(
                [str(SCRIPT)],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            count = int(state_file.read_text())
            return result, count

    @staticmethod
    def _write_executable(path, content):
        path.write_text("#!/bin/bash\n" + textwrap.dedent(content).lstrip())
        path.chmod(0o755)

    def test_persistent_showmigrations_failure_exits_nonzero(self):
        """A persistent showmigrations failure must fail the script."""
        result, count = self._run_script("persistent_failure")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(count, 10)

    def test_pending_migrations_block_until_applied(self):
        """Pending migrations must be retried until they are applied."""
        result, count = self._run_script("pending_then_applied")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(count, 3)
        self.assertIn("Pending migrations remain", result.stderr)
        self.assertIn("[wait-for-migrations] ERROR: [ ] app.0001_initial", result.stderr)

    def test_persistent_pending_migrations_exits_nonzero(self):
        """Migrations that remain pending must fail after all retries."""
        result, count = self._run_script("persistent_pending")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(count, 10)

    def test_failure_followed_by_recovery_succeeds(self):
        """A transient showmigrations failure must recover on retry."""
        result, count = self._run_script("failure_then_applied")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(count, 2)

    def test_failure_diagnostics_remain_visible(self):
        """Command diagnostics must be included in failure logs."""
        result, _ = self._run_script("persistent_failure")

        self.assertIn("[wait-for-migrations] ERROR: migration stderr line 1", result.stderr)
        self.assertIn("[wait-for-migrations] ERROR: migration stderr line 2", result.stderr)
        self.assertIn("[wait-for-migrations] ERROR: migration stdout line", result.stderr)
