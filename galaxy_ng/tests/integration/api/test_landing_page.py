"""test_landing_page.py - Test related to landing page endpoint.
"""
import pytest

from ..utils import get_client


@pytest.mark.cloud_only
def test_landing_page(ansible_config):
    """Tests whether the landing page returns the expected fields and numbers."""

    api_client = get_client(
        config=ansible_config("basic_user"), request_token=True, require_auth=True
    )

    resultsDict = api_client("/api/automation-hub/_ui/v1/landing-page")

    assert resultsDict["estate"]["items"][0]
    assert resultsDict["estate"]["items"][0]["shape"]["title"] == "Collections"

    # NOTE: this count is dependent on other tests that run beforehand which add collections
    # assert resultsDict["estate"]["items"][0]["count"] == 0

    assert resultsDict["estate"]["items"][1]
    assert resultsDict["estate"]["items"][1]["shape"]["title"] == "Partners"

    # NOTE: this count is dependent on other tests that run beforehand which add namespaces
    # assert resultsDict["estate"]["items"][1]["count"] == 2

    assert resultsDict["recommendations"]['recs']
    assert len(resultsDict["recommendations"]['recs']) == 1

    assert resultsDict["configTryLearn"]["configure"]
    assert len(resultsDict["configTryLearn"]["configure"]) == 1

    assert resultsDict["configTryLearn"]["try"]
    assert len(resultsDict["configTryLearn"]["try"]) == 2

    assert resultsDict["configTryLearn"]["learn"]
    assert len(resultsDict["configTryLearn"]["learn"]) == 3
