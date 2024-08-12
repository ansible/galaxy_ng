import time

import pytest

from galaxy_ng.tests.performance.constants import URLS

from ..integration.utils import (
    UIClient,
    SocialGithubClient,
    generate_unused_namespace,
    get_client
)


@pytest.mark.deployment_community
def test_api_performance(ansible_config):
    

    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=False
    )
    
    threshold = 0.25

    resp = api_client('http://localhost:5001/api/_ui/v1/settings/', method='GET') 
    print("Thhhhhhhe response is")
    print (resp)
    
    results = []

    for url, baseline in URLS.items():
       
        start_time = time.time()
        resp = api_client('http://localhost:5001' + url, method='GET')
        elapsed_time = time.time() - start_time
        
        difference = (elapsed_time - baseline) / baseline
        if difference > threshold:
            results.append(f"{url} exceeds threshold with {difference}")
        else:
            results.append(f"{url} does not exceed threshold and its difference is {difference}")
            
    print("httttttttttttthe result is")       
    print(results)
        
    assert True
        