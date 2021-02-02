import base64


def user_x_rh_identity(username, account_number=None):
    account_number = account_number or "12345"
    title_username = username.title()
    token_json = """{
        "entitlements":
            {"insights":
                {"is_entitled": true}
            },
        "identity":
            {"account_number": "%(account_number)s",
            "user":
                {"username": "%(username)s",
                "email": "%(username)s",
                "first_name": "%(title_username)s",
                "last_name": "%(title_username)sington",
                "is_org_admin": true
                },
            "internal": {"org_id": "54321"}
            }
            }""" % {'username': username, 'title_username': title_username,
                    'account_number': account_number}

    token_b64 = base64.b64encode(token_json.encode())

    return token_b64
