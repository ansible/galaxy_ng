"""test_dependencies.py - Tests of collection dependency handling."""
import logging

import attr
import pytest

from ..utils import ansible_galaxy
from ..utils import get_client
from ..utils import set_certification
from ..utils import build_collection

pytestmark = pytest.mark.qa  # noqa: F821

logger = logging.getLogger(__name__)


@attr.s
class DependencySpec:
    name = attr.ib()
    spec = attr.ib()
    retcode = attr.ib()
    xfail = attr.ib(default=False)


@pytest.mark.cli
@pytest.mark.parametrize(
    "params",
    (
        DependencySpec("normal", "1.0.0", 0),
        DependencySpec("exact", "=1.0.0", 0),
        DependencySpec("lt", "<2.0.0", 0),
        DependencySpec("lteq", "<=2.0.0", 0),
        DependencySpec("gt", ">0.9.0", 0),
        DependencySpec("gteq", ">=0.9.0", 0),
        DependencySpec("range", ">0.1.0,<1.0.1", 0),
        DependencySpec("invalid", "this is just junk", 1),
        # DependencySpec("carot", "^1.0.0", 1, xfail="galaxy-dev#104"),
        # DependencySpec("tilde", "~1.0.0", 1, xfail="galaxy-dev#104"),
        # DependencySpec("exception", ">0.0.0,!=1.0.0", 1, xfail="galaxy-dev#104"),
        # DependencySpec("missing1", "2.0.0", 1, xfail="galaxy-dev#104"),
        # DependencySpec("missing2", ">1.0.0", 1, xfail="galaxy-dev#104"),
    ),
    ids=lambda s: s.name,
)
def test_collection_dependency_install(ansible_config, published, cleanup_collections, params):
    """Collections defining dependencies can be installed and their dependencies are installed
    as well.

    Currently some scenarios are XFAIL pending open tickets:
    - Dependency specs with no matching collections (galaxy-dev#104)
    - NPM-style specs (not part of semver) are invalid
    """

    spec = params.spec
    retcode = params.retcode
    ansible_config("ansible_partner", namespace=published.namespace)
    artifact2 = build_collection(dependencies={f"{published.namespace}.{published.name}": spec})

    try:
        ansible_galaxy(
            f"collection publish {artifact2.filename} --server=automation_hub",
            check_retcode=retcode,
            ansible_config=ansible_config("ansible_partner", namespace=published.namespace)
        )
    except AssertionError:
        if params.xfail:
            return pytest.xfail()
        else:
            raise

    if retcode == 0:
        config = ansible_config("ansible_insights")
        client = get_client(config)
        set_certification(client, artifact2)

        pid = ansible_galaxy(
            f"collection install -vvv --ignore-cert \
                {artifact2.namespace}.{artifact2.name}:{artifact2.version} --server=automation_hub",
            check_retcode=False,
            ansible_config=ansible_config("ansible_insights"),
            # cleanup=False
        )

        try:
            assert (
                pid.returncode == retcode
            ), f"Unexpected {'failure' if pid.returncode else 'success'} during installing \
            {artifact2.namespace}.{artifact2.name}:{artifact2.version} \
            with dependency {published.namespace}.{published.name}{spec}"
        except AssertionError:
            raise
