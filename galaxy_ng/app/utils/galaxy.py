import logging
import requests
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


def uuid_to_int(uuid):
    """Cast a uuid to a reversable int"""
    return int(uuid.replace("-", ""), 16)


def int_to_uuid(num):
    """Reverse an int() casted uuid"""

    d = str(hex(num)).replace("0x", "")
    if len(d) < 32:
        padding = 32 - len(d)
        padding = '0' * padding
        d = padding + d

    uuid = f"{d[0:8]}-{d[8:12]}-{d[12:16]}-{d[16:20]}-{d[20:]}"
    return uuid


def paginated_results(next_url):
    """Iterate through a paginated query and combine the results."""
    parsed = urlparse(next_url)
    _baseurl = parsed.scheme + '://' + parsed.netloc
    results = []
    while next_url:
        logger.info(f'fetch {next_url}')
        rr = requests.get(next_url)
        ds = rr.json()
        results.extend(ds['results'])
        if ds['next_link']:
            next_url = _baseurl + ds['next_link']
        else:
            next_url = None
    return results


def upstream_role_iterator(
    baseurl=None,
    limit=None,
    github_user=None,
    github_repo=None,
    role_name=None
):
    """Abstracts the pagination of v1 roles into a generator with error handling."""
    logger.info(f'baseurl1: {baseurl}')
    if baseurl is None or not baseurl:
        baseurl = 'https://galaxy.ansible.com/api/v1/roles'
    logger.info(f'baseurl2: {baseurl}')

    # normalize the upstream url
    parsed = urlparse(baseurl)
    _baseurl = parsed.scheme + '://' + parsed.netloc

    # default to baseurl or construct from parameters
    next_url = baseurl
    params = []
    if github_user or github_repo or role_name:
        if github_user:
            params.append(f'owner__username={github_user}')
        if role_name:
            params.append(f'name={role_name}')
        next_url = _baseurl + '/api/v1/roles/?' + '&'.join(params)

    namespace_cache = {}

    pagenum = 0
    role_count = 0
    while next_url:
        logger.info(f'fetch {pagenum} {next_url}')

        page = requests.get(next_url)

        # Some upstream pages return ISEs for whatever reason.
        if page.status_code >= 500:
            if 'page=' in next_url:
                next_url = next_url.replace(f'page={pagenum}', f'page={pagenum+1}')
            else:
                next_url = next_url.rstrip('/') + '/?page={pagenum+1}'
            pagenum += 1
            continue

        ds = page.json()

        # iterate each role
        for rdata in ds['results']:

            remote_id = rdata['id']
            role_upstream_url = _baseurl + f'/api/v1/roles/{remote_id}/'
            logger.info(f'fetch {role_upstream_url}')

            role_page = requests.get(role_upstream_url)
            if role_page.status_code == 404:
                continue

            role_data = None
            try:
                role_data = role_page.json()
                if role_data.get('detail', '').lower().strip() == 'not found':
                    continue
            except Exception:
                continue

            # Get the namespace+owners
            ns_id = role_data['summary_fields']['namespace']['id']
            if ns_id not in namespace_cache:
                ns_url = _baseurl + f'/api/v1/namespaces/{ns_id}/'
                namespace_data = requests.get(ns_url).json()
                namespace_cache[ns_id] = namespace_data
            else:
                namespace_data = namespace_cache[ns_id]

            # Get all of the versions because they have more info than the summary
            versions_url = role_upstream_url + 'versions'
            role_versions = paginated_results(versions_url)

            # send the role
            role_count += 1
            yield namespace_data, role_data, role_versions

            # break early if count reached
            if limit is not None and role_count >= limit:
                break

        # break early if count reached
        if limit is not None and role_count >= limit:
            break

        # break if no next page
        if not ds.get('next_link'):
            break

        pagenum += 1
        next_url = _baseurl + ds['next_link']
