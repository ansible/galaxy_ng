import json
import pytest
import random
import string

from ..utils import (
    get_client,
    SocialGithubClient,
    GithubAdminClient,
    cleanup_namespaces,
    build_collection,
    wait_for_task,
)
from ..utils.legacy import (
    cleanup_social_user,
    wait_for_v1_task,
)


@pytest.mark.deployment_community
def test_v3_namespace_cleanup(ansible_config, upload_artifact):

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    ns_name = 'sean_m_sullivan'
    namespaces = [ns_name + str(x) for x in range(0, 20)] + [ns_name]
    #for ns in namespaces:
    #    cleanup_namespace(ns, api_client=admin_client)
    cleanup_namespaces(namespaces, api_client=admin_client)

    # make N namespaces
    for ns in namespaces:
        resp = admin_client('_ui/v1/namespaces/', method='POST', args={'name': ns, 'groups': []})

    # add content to the first one ..
    artifact = build_collection(namespace='sean_m_sullivan', name='foo')
    task = upload_artifact(admin_config, admin_client, artifact)
    result = wait_for_task(admin_client, task)
    assert result['state'] == 'completed'

    # do cleanup on just the ones without content ...

    import epdb; epdb.st()
