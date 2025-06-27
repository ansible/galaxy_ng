import json


def add_user_to_team(client, userid=None, teamid=None):
    # find the "Team Member" roledef ..
    roledefs = client.get(
        "_ui/v2/role_definitions/",
        params={
            'name': 'Team Member'
        }
    )
    roledef = roledefs['results'][0]

    # check if already assigned ...
    assignments = client.get(
        "_ui/v2/role_user_assignments/",
        params={
            'user': userid,
            'object_id': teamid,
            'role_definition': roledef['id'],
        }
    )
    if assignments['count'] > 0:
        return

    # make the assignment
    assignment = client.post(
        "_ui/v2/role_user_assignments/",
        body=json.dumps({
            'role_definition': roledef['id'],
            'user': userid,
            'object_id': teamid,
        })
    )
    assert assignment['user'] == userid
    return assignment


def remove_user_from_team(client, userid=None, teamid=None):
    # find the "Team Member" roledef ..
    roledefs = client.get(
        "_ui/v2/role_definitions/",
        params={
            'name': 'Team Member'
        }
    )
    roledef = roledefs['results'][0]

    # check if already assigned ...
    assignments = client.get(
        "_ui/v2/role_user_assignments/",
        params={
            'user': userid,
            'object_id': teamid,
            'role_definition': roledef['id'],
        }
    )
    if assignments['count'] == 0:
        return

    # delete all of the assignments
    for assignment in assignments['results']:
        client.delete(assignment['url'])
