import subprocess
import os
from pytest import skip


def _set_settings(text):
    with open("/etc/pulp/settings.py", "w") as f:
        f.write("\n".join(text))

    services = "pulpcore-api pulpcore-content pulpcore-worker@1 pulpcore-worker@2"
    stop = f"s6-rc -d change {services}".split(" ")
    start = f"s6-rc -d change {services}".split(" ")
    subprocess.run(stop)
    subprocess.run(start)


def _get_settings():
    with open("/etc/pulp/settings.py", "r") as f:
        return f.read().splt("\n")


def with_oci_env_setting(settings):
    def decorator(function):
        def wrapper(*args, **kwargs):
            if not os.path.isdir('/opt/oci-env/'):
                skip(reason="@with_oci_env_setting tests only work when run in oci-env")

            current_settings = _get_settings()
            new_settings = current_settings + [f"{x}={settings[x]}" for x in settings]
            _set_settings(new_settings)
            try:
                result = function(*args, **kwargs)
                _set_settings(current_settings)
                return result
            except: # noqa
                _set_settings(current_settings)
                raise
        return wrapper
    return decorator
