"""Constants usable by multiple test modules."""

USERNAME_ADMIN = "ansible-insights"
USERNAME_CONSUMER = "autohubtest3"
USERNAME_PUBLISHER = "autohubtest2"

# time.sleep() seconds for checks that poll in a loop
SLEEP_SECONDS_POLLING = 1

# time.sleep() seconds for checks that wait once
SLEEP_SECONDS_ONETIME = 3

DEFAULT_DISTROS = {
    'community': {'basepath': 'community'},
    'published': {'basepath': 'published'},
    'rejected': {'basepath': 'rejected'},
    'rh-certified': {'basepath': 'rh-certified'},
    'staging': {'basepath': 'staging'}
}
