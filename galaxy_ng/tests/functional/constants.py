"""Constants for Pulp Galaxy plugin tests."""
from urllib.parse import urljoin

from pulp_smash.constants import PULP_FIXTURES_BASE_URL
from pulp_smash.pulp3.constants import (
    BASE_DISTRIBUTION_PATH,
    BASE_PUBLICATION_PATH,
    BASE_REMOTE_PATH,
    BASE_REPO_PATH,
    BASE_CONTENT_PATH,
)

# FIXME: list any download policies supported by your plugin type here.
# If your plugin supports all download policies, you can import this
# from pulp_smash.pulp3.constants instead.
# DOWNLOAD_POLICIES = ["immediate", "streamed", "on_demand"]
DOWNLOAD_POLICIES = ["immediate"]

# FIXME: replace 'unit' with your own content type names, and duplicate as necessary for each type
GALAXY_CONTENT_NAME = "galaxy.unit"

# FIXME: replace 'unit' with your own content type names, and duplicate as necessary for each type
GALAXY_CONTENT_PATH = urljoin(BASE_CONTENT_PATH, "galaxy/units/")

GALAXY_REMOTE_PATH = urljoin(BASE_REMOTE_PATH, "galaxy/galaxy/")

GALAXY_REPO_PATH = urljoin(BASE_REPO_PATH, "galaxy/galaxy/")

GALAXY_PUBLICATION_PATH = urljoin(BASE_PUBLICATION_PATH, "galaxy/galaxy/")

GALAXY_DISTRIBUTION_PATH = urljoin(BASE_DISTRIBUTION_PATH, "galaxy/galaxy/")

# FIXME: replace this with your own fixture repository URL and metadata
GALAXY_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "galaxy/")
"""The URL to a galaxy repository."""

# FIXME: replace this with the actual number of content units in your test fixture
GALAXY_FIXTURE_COUNT = 3
"""The number of content units available at :data:`GALAXY_FIXTURE_URL`."""

GALAXY_FIXTURE_SUMMARY = {GALAXY_CONTENT_NAME: GALAXY_FIXTURE_COUNT}
"""The desired content summary after syncing :data:`GALAXY_FIXTURE_URL`."""

# FIXME: replace this with the location of one specific content unit of your choosing
GALAXY_URL = urljoin(GALAXY_FIXTURE_URL, "")
"""The URL to an galaxy file at :data:`GALAXY_FIXTURE_URL`."""

# FIXME: replace this with your own fixture repository URL and metadata
GALAXY_INVALID_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "galaxy-invalid/")
"""The URL to an invalid galaxy repository."""

# FIXME: replace this with your own fixture repository URL and metadata
GALAXY_LARGE_FIXTURE_URL = urljoin(PULP_FIXTURES_BASE_URL, "galaxy_large/")
"""The URL to a galaxy repository containing a large number of content units."""

# FIXME: replace this with the actual number of content units in your test fixture
GALAXY_LARGE_FIXTURE_COUNT = 25
"""The number of content units available at :data:`GALAXY_LARGE_FIXTURE_URL`."""
