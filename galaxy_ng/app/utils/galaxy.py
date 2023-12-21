import logging
import requests
import time
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


def generate_unverified_email(github_id):
    return str(github_id) + '@GALAXY.GITHUB.UNVERIFIED.COM'


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


def safe_fetch(url):
    rr = None
    counter = 0
    while True:
        counter += 1
        logger.info(f'fetch {url}')
        rr = requests.get(url)
        if rr.status_code < 500:
            return rr

        if counter >= 5:
            return rr

        logger.info(f'ERROR:{rr.status_code} waiting 60s to refetch {url}')
        time.sleep(60)

    return rr


def paginated_results(next_url):
    """Iterate through a paginated query and combine the results."""
    parsed = urlparse(next_url)
    _baseurl = parsed.scheme + '://' + parsed.netloc
    results = []
    while next_url:
        logger.info(f'pagination fetch {next_url}')
        rr = safe_fetch(next_url)
        if rr.status_code == 404:
            break

        ds = rr.json()

        results.extend(ds['results'])
        if 'next' in ds:
            next_url = ds['next']
        elif ds['next_link']:
            next_url = _baseurl + ds['next_link']
        else:
            next_url = None

        if next_url and not next_url.startswith(_baseurl + '/api/v1'):
            next_url = _baseurl + '/api/v1' + next_url

        if next_url and not next_url.startswith(_baseurl):
            next_url = _baseurl + next_url

    return results


def find_namespace(baseurl=None, name=None, id=None):
    if baseurl is None or not baseurl:
        baseurl = 'https://old-galaxy.ansible.com'
    baseurl += '/api/v1/namespaces'
    logger.info(f'find_namespace baseurl:{baseurl} name:{name} id:{id}')

    parsed = urlparse(baseurl)
    _baseurl = parsed.scheme + '://' + parsed.netloc

    ns_name = None
    ns_info = None

    if name:
        qurl = baseurl + f'/?name={name}'
        rr = safe_fetch(qurl)
        ds = rr.json()

        ns_info = ds['results'][0]
        ns_name = ns_info['name']

    elif id:
        qurl = baseurl + f'/{id}/'
        rr = safe_fetch(qurl)
        ds = rr.json()

        ns_name = ds['name']
        ns_info = ds

    # get the owners too
    ns_id = ns_info['id']
    owners = []
    next_owners_url = _baseurl + f'/api/v1/namespaces/{ns_id}/owners/'
    while next_owners_url:
        o_data = safe_fetch(next_owners_url).json()
        for owner in o_data['results']:
            owners.append(owner)
        if not o_data.get('next'):
            break
        next_owners_url = _baseurl + o_data['next_link']

    ns_info['summary_fields']['owners'] = owners

    return ns_name, ns_info


def get_namespace_owners_details(baseurl, ns_id):
    # get the owners too
    owners = []
    next_owners_url = baseurl + f'/api/v1/namespaces/{ns_id}/owners/'
    while next_owners_url:
        logger.info(f'fetch {next_owners_url}')
        o_data = safe_fetch(next_owners_url).json()
        if isinstance(o_data, dict):
            # old galaxy
            for owner in o_data['results']:
                owners.append(owner)
            if not o_data.get('next'):
                break
            if 'next_link' in o_data and not o_data.get('next_link'):
                break
            next_owners_url = baseurl + o_data['next_link']
        else:
            # new galaxy
            for owner in o_data:
                owners.append(owner)
            break
    return owners


def upstream_namespace_iterator(
    baseurl=None,
    limit=None,
    start_page=None,
    require_content=True,
):
    """Abstracts the pagination of v2 collections into a generator with error handling."""
    if baseurl is None or not baseurl:
        baseurl = 'https://old-galaxy.ansible.com/api/v1/namespaces'
    if not baseurl.rstrip().endswith('/api/v1/namespaces'):
        baseurl = baseurl.rstrip() + '/api/v1/namespaces'
    logger.info(f'upstream_namespace_iterator baseurl:{baseurl}')

    # normalize the upstream url
    parsed = urlparse(baseurl)
    _baseurl = parsed.scheme + '://' + parsed.netloc

    # default to baseurl or construct from parameters
    next_url = baseurl

    pagenum = 0
    namespace_count = 0

    if start_page:
        pagenum = start_page
        next_url = next_url + f'?page={pagenum}'

    while next_url:
        logger.info(f'fetch {pagenum} {next_url}')

        page = safe_fetch(next_url)

        # Some upstream pages return ISEs for whatever reason.
        if page.status_code >= 500:
            if 'page=' in next_url:
                next_url = next_url.replace(f'page={pagenum}', f'page={pagenum+1}')
            else:
                next_url = next_url.rstrip('/') + '/?page={pagenum+1}'
            pagenum += 1
            continue

        ds = page.json()
        total = ds['count']

        for ndata in ds['results']:

            if not ndata['summary_fields']['content_counts'] and require_content:
                continue

            ns_id = ndata['id']

            # get the owners too
            ndata['summary_fields']['owners'] = get_namespace_owners_details(_baseurl, ns_id)

            # send the collection
            namespace_count += 1
            yield total, ndata

            # break early if count reached
            if limit is not None and namespace_count >= limit:
                break

        # break early if count reached
        if limit is not None and namespace_count >= limit:
            break

        # break if no next page
        if not ds.get('next_link'):
            break

        pagenum += 1
        next_url = _baseurl + ds['next_link']


def upstream_collection_iterator(
    baseurl=None,
    limit=None,
    collection_namespace=None,
    collection_name=None,
    get_versions=True,
    start_page=None,
):
    """Abstracts the pagination of v2 collections into a generator with error handling."""
    if baseurl is None or not baseurl:
        baseurl = 'https://old-galaxy.ansible.com/api/v2/collections'
    logger.info(f'upstream_collection_iterator baseurl:{baseurl}')

    # normalize the upstream url
    parsed = urlparse(baseurl)
    _baseurl = parsed.scheme + '://' + parsed.netloc

    # default to baseurl or construct from parameters
    next_url = baseurl

    '''
    params = []
    if github_user or github_repo or role_name:
        if github_user:
            params.append(f'owner__username={github_user}')
        if role_name:
            params.append(f'name={role_name}')
        next_url = _baseurl + '/api/v1/roles/?' + '&'.join(params)
    '''

    namespace_cache = {}

    if collection_namespace or collection_name:
        if collection_namespace and not collection_name:
            # get the namespace ID first ...
            ns_name, ns_data = find_namespace(baseurl=baseurl, name=collection_namespace)
            ns_id = ns_data['id']
            next_url = (
                baseurl
                + f'/api/internal/ui/search/?keywords={collection_namespace}'
                + '&order_by=-relevance&type=collection'
            )

            collection_count = -1
            while next_url:
                page = safe_fetch(next_url)
                ds = page.json()
                collections = ds['collection']['results']
                for cdata in collections:

                    if cdata['namespace']['name'] != collection_namespace:
                        continue

                    collection_count += 1
                    if limit and collection_count >= limit:
                        return

                    # Get the namespace+owners
                    ns_id = cdata['namespace']['id']
                    if ns_id not in namespace_cache:
                        logger.info(_baseurl + f'/api/v1/namespaces/{ns_id}/')
                        ns_url = _baseurl + f'/api/v1/namespaces/{ns_id}/'
                        namespace_data = safe_fetch(ns_url).json()
                        # logger.info(namespace_data)
                        namespace_cache[ns_id] = namespace_data

                        # get the owners too
                        namespace_cache[ns_id]['summary_fields']['owners'] = \
                            get_namespace_owners_details(_baseurl, ns_id)

                    else:
                        namespace_data = namespace_cache[ns_id]

                    # get the versions
                    if get_versions:
                        versions_url = (
                            baseurl
                            + '/api/v2/collections/'
                            + cdata["namespace"]["name"]
                            + '/'
                            + cdata["name"]
                            + '/versions/'
                        )
                        collection_versions = paginated_results(versions_url)
                    else:
                        collection_versions = []

                    yield namespace_data, cdata, collection_versions

                # no pagination in search results?
                return

        if collection_name and not collection_namespace:
            raise Exception('name without namespace not supported yet')

        # https://galaxy.ansible.com/api/v2/collections/geerlingguy/mac/
        url = _baseurl + f'/api/v2/collections/{collection_namespace}/{collection_name}/'
        cdata = safe_fetch(url).json()
        collection_versions = paginated_results(cdata['versions_url'])

        # Get the namespace+owners
        ns_id = cdata['namespace']['id']
        if ns_id not in namespace_cache:
            logger.info(_baseurl + f'/api/v1/namespaces/{ns_id}/')
            ns_url = _baseurl + f'/api/v1/namespaces/{ns_id}/'
            namespace_data = safe_fetch(ns_url).json()
            namespace_cache[ns_id] = namespace_data

            # get the owners too
            namespace_cache[ns_id]['summary_fields']['owners'] = \
                get_namespace_owners_details(_baseurl, ns_id)

        else:
            namespace_data = namespace_cache[ns_id]

        yield namespace_data, cdata, collection_versions
        return

    pagenum = 0
    collection_count = 0
    next_url = _baseurl + '/api/v2/collections/'
    while next_url:
        logger.info(f'fetch {pagenum} {next_url}')

        page = safe_fetch(next_url)

        # Some upstream pages return ISEs for whatever reason.
        if page.status_code >= 500:
            if 'page=' in next_url:
                next_url = next_url.replace(f'page={pagenum}', f'page={pagenum+1}')
            else:
                next_url = next_url.rstrip('/') + '/?page={pagenum+1}'
            pagenum += 1
            continue

        ds = page.json()

        for cdata in ds['results']:

            # Get the namespace+owners
            ns_id = cdata['namespace']['id']
            if ns_id not in namespace_cache:
                logger.info(_baseurl + f'/api/v1/namespaces/{ns_id}/')
                ns_url = _baseurl + f'/api/v1/namespaces/{ns_id}/'
                namespace_data = safe_fetch(ns_url).json()
                # logger.info(namespace_data)
                namespace_cache[ns_id] = namespace_data

                # get the owners too
                namespace_cache[ns_id]['summary_fields']['owners'] = \
                    get_namespace_owners_details(_baseurl, ns_id)

            else:
                namespace_data = namespace_cache[ns_id]

            # get the versions
            if get_versions:
                collection_versions = paginated_results(cdata['versions_url'])
            else:
                collection_versions = []

            # send the collection
            collection_count += 1
            yield namespace_data, cdata, collection_versions

            # break early if count reached
            if limit is not None and collection_count >= limit:
                break

        # break early if count reached
        if limit is not None and collection_count >= limit:
            break

        # break if no next page
        if not ds.get('next_link'):
            break

        pagenum += 1
        next_url = _baseurl + ds['next_link']


def upstream_role_iterator(
    baseurl=None,
    limit=None,
    github_user=None,
    github_repo=None,
    role_name=None,
    get_versions=True,
    start_page=None,
):
    """Abstracts the pagination of v1 roles into a generator with error handling."""
    if baseurl is None or not baseurl:
        baseurl = 'https://old-galaxy.ansible.com/api/v1/roles'
    logger.info(f'upstream_role_iterator baseurl:{baseurl}')

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
    else:
        next_url = _baseurl + '/api/v1/roles/'

    if start_page:
        if '?' in next_url:
            next_url += f'&page={start_page}'
        else:
            next_url = next_url.rstrip('/') + f'/?page={start_page}'

    namespace_cache = {}

    pagenum = 0
    role_count = 0
    while next_url:
        logger.info(f'fetch {pagenum} {next_url} role-count:{role_count} ...')

        page = safe_fetch(next_url)

        # Some upstream pages return ISEs for whatever reason.
        if page.status_code >= 500:
            logger.error(f'{next_url} returned 500ISE. incrementing the page manually')
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

            # role_page = requests.get(role_upstream_url)
            role_page = safe_fetch(role_upstream_url)
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
                logger.info(_baseurl + f'/api/v1/namespaces/{ns_id}/')
                ns_url = _baseurl + f'/api/v1/namespaces/{ns_id}/'

                nsd_rr = safe_fetch(ns_url)
                try:
                    namespace_data = nsd_rr.json()
                except requests.exceptions.JSONDecodeError:
                    continue
                namespace_cache[ns_id] = namespace_data

                # get the owners too
                namespace_cache[ns_id]['summary_fields']['owners'] = \
                    get_namespace_owners_details(_baseurl, ns_id)

            else:
                namespace_data = namespace_cache[ns_id]

            # Get all of the versions because they have more info than the summary
            if get_versions:
                versions_url = role_upstream_url + 'versions'
                role_versions = paginated_results(versions_url)
            else:
                role_versions = []

            # send the role
            role_count += 1
            yield namespace_data, role_data, role_versions

            # break early if count reached
            if limit is not None and role_count >= limit:
                break

        # break early if count reached
        if limit is not None and role_count >= limit:
            break

        if ds.get('next'):
            next_url = ds['next']
        elif ds.get('next_link'):
            next_url = ds['next_link']
        else:
            # break if no next page
            break

        api_prefix = '/api/v1'
        if not next_url.startswith(_baseurl):
            if not next_url.startswith(api_prefix):
                next_url = _baseurl + api_prefix + next_url
            else:
                next_url = _baseurl + next_url

        pagenum += 1
