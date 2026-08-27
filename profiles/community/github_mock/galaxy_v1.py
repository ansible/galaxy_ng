#!/usr/bin/env python

###############################################################################
#
#   local galaxy.ansible.com v1 API mock
#
#       Implements just enough of the galaxy.ansible.com /api/v1/ role +
#       namespace endpoints for the legacy role sync task (POST /api/v1/sync/)
#       to run hermetically in CI/dev, so the community integration tests no
#       longer depend on the live galaxy.ansible.com service.
#
#       The galaxy_ng community stack points the sync baseurl here via
#       PULP_GALAXY_LEGACY_ROLE_SYNC_URL=http://github:8082/api/v1/roles/
#
#       This is served from the same flask app/container as the github social
#       auth mock so that user identities (github ids) stay consistent between
#       the two mocks.
#
###############################################################################


import os

from flask import Blueprint
from flask import jsonify
from flask import request


galaxy_v1 = Blueprint('galaxy_v1', __name__)


# Shared with flaskapp.py's `app.run(port=...)` so the two only need to agree
# on a single env var if this mock's port ever changes.
MOCK_PORT = os.environ.get('GITHUB_MOCK_PORT', '8082')


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------
#
# github ids intentionally match the github social auth mock (USERS in
# flaskapp.py) and the ids hardcoded in the integration tests:
#   geerlingguy -> 481677
#   Wilk42      -> 30054029
GEERLINGGUY_GITHUB_ID = 481677
WILK42_GITHUB_ID = 30054029


def _avatar(ns_id):
    return f'http://github:{MOCK_PORT}/api/v1/namespaces/{ns_id}/avatar/'


def _make_versions(base_id, tags):
    """Build a list of role version dicts from a list of semver strings."""
    versions = []
    for i, tag in enumerate(tags):
        versions.append({
            'id': base_id + i,
            'name': tag,
            'version': tag,
            'created': '2023-01-01T00:00:00Z',
            'modified': '2023-06-01T00:00:00Z',
            'commit_date': '2023-01-01T00:00:00Z',
            'commit_sha': None,
            'download_url': None,
        })
    return versions


def _make_role(rid, username, name, github_repo, download_count, tags, version_tags):
    ns_id = PEOPLE_BY_USERNAME[username]['ns_id']
    versions = _make_versions(rid * 100, version_tags)
    return {
        'id': rid,
        'upstream_id': rid,
        'name': name,
        'github_user': username,
        'username': username,
        'github_repo': github_repo,
        'github_branch': 'master',
        'commit': 'a' * 40,
        'commit_message': f'commit for {name}',
        'commit_url': f'https://github.com/{username}/{github_repo}/commit/{"a" * 40}',
        'issue_tracker_url': f'https://github.com/{username}/{github_repo}/issues',
        'description': f'{name} role',
        'license': 'MIT',
        'readme': f'# {name}',
        'readme_html': f'<h1>{name}</h1>',
        'min_ansible_version': '2.9',
        'company': 'Test Company',
        'imported': '2023-01-01T00:00:00Z',
        'created': '2023-01-01T00:00:00Z',
        'modified': '2023-06-01T00:00:00Z',
        'role_type': 'ANS',
        'download_count': download_count,
        'summary_fields': {
            'namespace': {'id': ns_id, 'name': username, 'avatar_url': _avatar(ns_id)},
            'dependencies': [],
            'tags': tags,
            'versions': versions[:3],
        },
        '_versions': versions,
    }


# Single source of truth for namespace id <-> username <-> owner/github id, so
# a mismatch can't creep in across OWNERS/NAMESPACES/ROLES independently. Each
# person needs an owner id + github_id so the sync can build the matching
# (unverified) galaxy_ng user.
PEOPLE = [
    {'ns_id': 2492, 'username': 'geerlingguy', 'owner_id': 2498,
     'github_id': GEERLINGGUY_GITHUB_ID},
    {'ns_id': 1838, 'username': 'Wilk42', 'owner_id': 33901, 'github_id': WILK42_GITHUB_ID},
    {'ns_id': 3001, 'username': 'bertvv', 'owner_id': 3101, 'github_id': 1000101},
    {'ns_id': 3002, 'username': 'robertdebock', 'owner_id': 3102, 'github_id': 1000102},
    {'ns_id': 3003, 'username': 'arillso', 'owner_id': 3103, 'github_id': 1000103},
    {'ns_id': 3004, 'username': 'nickjj', 'owner_id': 3104, 'github_id': 1000104},
    {'ns_id': 3005, 'username': 'oefenweb', 'owner_id': 3105, 'github_id': 1000105},
    # tag-counting fixtures for test_api_ui_v1_tags_roles
    {'ns_id': 3006, 'username': '6nsh', 'owner_id': 3106, 'github_id': 1000106},
    {'ns_id': 3007, 'username': '0x28d', 'owner_id': 3107, 'github_id': 1000107},
]
PEOPLE_BY_USERNAME = {p['username']: p for p in PEOPLE}

# namespace_id -> owners list.
OWNERS = {
    p['ns_id']: [{'id': p['owner_id'], 'username': p['username'], 'github_id': p['github_id']}]
    for p in PEOPLE
}


def _make_namespace(ns_id, name):
    return {
        'id': ns_id,
        'url': '',
        'name': name,
        'avatar_url': _avatar(ns_id),
        'company': None,
        'email': None,
        'description': f'{name} namespace',
        'created': '2023-01-01T00:00:00Z',
        'modified': '2023-06-01T00:00:00Z',
        'summary_fields': {
            'owners': OWNERS[ns_id],
            'provider_namespaces': [],
        },
        'related': {
            'owners': f'/api/v1/namespaces/{ns_id}/owners/',
        },
    }


NAMESPACES = {p['ns_id']: _make_namespace(p['ns_id'], p['username']) for p in PEOPLE}


# Ordered role catalog. Order matters: the sync applies ``limit`` client-side,
# so geerlingguy's 5 roles come first (unfiltered limit=5 -> exactly those),
# then 5 more roles from other namespaces (unfiltered limit=10 -> 10 distinct
# roles), then Wilk42 (only ever synced via an explicit owner__username filter).
ROLES = [
    _make_role(10908, 'geerlingguy', 'ansible',
               'ansible-role-ansible', 1000,
               ['ansible', 'automation', 'system'],
               ['1.0.0', '1.1.0', '2.0.0', '2.2.0', '2.3.0']),
    _make_role(10909, 'geerlingguy', 'adminer',
               'ansible-role-adminer', 500,
               ['adminer', 'web', 'database'],
               ['1.0.0', '1.1.0']),
    _make_role(10910, 'geerlingguy', 'docker',
               'ansible-role-docker', 2500,
               ['docker', 'containers', 'system'],
               ['1.0.0', '2.0.0', '3.0.0']),
    _make_role(10911, 'geerlingguy', 'nginx',
               'ansible-role-nginx', 1500,
               ['nginx', 'web', 'system'],
               ['1.0.0', '2.0.0']),
    _make_role(10912, 'geerlingguy', 'mysql',
               'ansible-role-mysql', 3000,
               ['mysql', 'database', 'system'],
               ['1.0.0', '2.0.0', '3.0.0']),
    _make_role(20001, 'bertvv', 'httpd',
               'ansible-role-httpd', 100,
               ['httpd', 'web'],
               ['1.0.0']),
    _make_role(20002, 'robertdebock', 'bootstrap',
               'ansible-role-bootstrap', 200,
               ['bootstrap', 'system'],
               ['1.0.0', '2.0.0']),
    _make_role(20003, 'arillso', 'java',
               'ansible-role-java', 300,
               ['java', 'development'],
               ['1.0.0']),
    _make_role(20004, 'nickjj', 'postgresql',
               'ansible-role-postgresql', 400,
               ['postgresql', 'database'],
               ['1.0.0']),
    _make_role(20005, 'oefenweb', 'redis',
               'ansible-role-redis', 600,
               ['redis', 'database'],
               ['1.0.0', '1.1.0']),
    _make_role(21352, 'Wilk42', 'kerb_ldap_setup',
               'kerb_ldap_setup', 50,
               ['ldap', 'security'],
               ['1.0.0']),
    # extra 'docker'-tagged roles for test_api_ui_v1_tags_roles. Combined with
    # geerlingguy/docker (tags docker,containers,system) the aggregate tag
    # counts become docker=3, system=2, containers=1 -> a deterministic
    # top-2 sort by count (docker, system).
    _make_role(20006, '6nsh', 'docker',
               'ansible-role-docker', 70,
               ['docker', 'system'],
               ['1.0.0']),
    _make_role(20007, '0x28d', 'docker_ce',
               'ansible-role-docker_ce', 80,
               ['docker'],
               ['1.0.0']),
]

# Structurally enforce the ordering contract documented above so a reordered
# or inserted fixture fails loudly here instead of in an unrelated test file.
assert [r['username'] for r in ROLES[:5]] == ['geerlingguy'] * 5
assert 'Wilk42' not in {r['username'] for r in ROLES[:10]}

ROLES_BY_ID = {r['id']: r for r in ROLES}


def _public_role(role):
    """Return a role dict without the internal ``_versions`` helper key."""
    return {k: v for k, v in role.items() if not k.startswith('_')}


def _paginated(results):
    """Single-page envelope: nothing here ever actually paginates."""
    return {
        'count': len(results),
        'next': None,
        'next_link': None,
        'previous': None,
        'previous_link': None,
        'results': results,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@galaxy_v1.route('/api/v1/roles/', methods=['GET'])
def list_roles():
    owner = request.args.get('owner__username')
    name = request.args.get('name')

    results = ROLES
    if owner:
        # galaxy.ansible.com's owner__username filter is case-insensitive
        # (see test_community_namespace_rbac.py: 'Wilk42' and 'wilk42' both
        # resolve to the same role), so mirror that here.
        results = [r for r in results if r['username'].lower() == owner.lower()]
    if name:
        results = [r for r in results if r['name'] == name]

    return jsonify(_paginated([_public_role(r) for r in results]))


@galaxy_v1.route('/api/v1/roles/<int:rid>/', methods=['GET'])
def role_detail(rid):
    role = ROLES_BY_ID.get(rid)
    if role is None:
        return jsonify({'detail': 'Not found'}), 404
    return jsonify(_public_role(role))


@galaxy_v1.route('/api/v1/roles/<int:rid>/versions', methods=['GET'])
@galaxy_v1.route('/api/v1/roles/<int:rid>/versions/', methods=['GET'])
def role_versions(rid):
    role = ROLES_BY_ID.get(rid)
    if role is None:
        return jsonify({'detail': 'Not found'}), 404
    return jsonify(_paginated(role['_versions']))


@galaxy_v1.route('/api/v1/namespaces/<int:nsid>/', methods=['GET'])
def namespace_detail(nsid):
    ns = NAMESPACES.get(nsid)
    if ns is None:
        return jsonify({'detail': 'Not found'}), 404
    return jsonify(ns)


@galaxy_v1.route('/api/v1/namespaces/<int:nsid>/owners/', methods=['GET'])
def namespace_owners(nsid):
    if nsid not in NAMESPACES:
        return jsonify({'detail': 'Not found'}), 404
    # new-galaxy style: a bare list (see get_namespace_owners_details)
    return jsonify(OWNERS.get(nsid, []))
