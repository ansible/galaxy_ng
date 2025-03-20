import base64
import json


def user_x_rh_identity(username: str, account_number: str = "12345") -> bytes:
    title_username = username.title()

    token = {
        "entitlements": {"insights": {"is_entitled": True}},
        "identity": {
            "account_number": account_number,
            "user": {
                "username": username,
                "email": username,
                "first_name": f"{title_username}s",
                "last_name": f"{title_username}sington",
                "is_org_admin": True,
            },
            "internal": {"org_id": "54321"},
        },
    }

    return base64.b64encode(json.dumps(token).encode())
