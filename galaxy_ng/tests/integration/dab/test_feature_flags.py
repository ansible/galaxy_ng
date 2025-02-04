
def test_feature_flags_endpoint_is_exposed(galaxy_client):
    """
    We want the download url to point at the gateway
    """
    gc = galaxy_client("admin")
    flag_url = "feature_flags_state/"
    resp = gc.get(flag_url)
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'application/json'
