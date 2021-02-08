"""
This module is temporarily added to address the
issue AAH-291.

The change that this module is solving
is going to be implemented on pulpcore
and then this module and its references
can be removed or replaces with pulpcore
implementation.
"""
from typing import List, Tuple, Optional
from urllib3.util import parse_url, Url


def get_parsed_url(parsed: Url, auth_items: Optional[List[Optional[str]]]) -> str:
    """
    parsed: Url instance
    auth_items: Optional list of str ["user": "password"]
    returns: str e.g: http://user:pass@foo.bar:9999
    """
    return Url(
        scheme=parsed.scheme,
        auth=auth_items and ":".join(auth_items) or None,
        host=parsed.host,
        port=parsed.port,
        path=parsed.path,
        query=parsed.query,
        fragment=parsed.fragment,
    ).url


def strip_auth_from_url(url: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Gets a full proxy address and strips its auth
    # url: http://bruno:1234@foo.bar:9999/zaz/traz/?a#e;w
    # returns: tuple, e.g: "http://foo.bar:9999/zaz/traz/?a#e;w", bruno, 1234
    """

    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    parsed = parse_url(url)
    auth = parsed.auth and parsed.auth.split(":")
    username = auth and auth[0] or None
    password = auth and len(auth) > 1 and auth[1] or None
    return (
        get_parsed_url(parsed, None),
        username,
        password,
    )


def join_proxy_url(address: str, username: Optional[str], password: Optional[str]) -> str:
    """
    Gets a splitted address, username, password
    returns: Joined URL forming proxy_url
    """
    # http://username:password@address

    if not address.startswith(("http://", "https://")):
        address = "http://" + address

    parsed = parse_url(address)
    auth_items = []

    if username:
        auth_items.append(str(username))

        # password is set only if there is a username
        # to avoid it being set as e.g: http://:1234@foo.bar
        if password:
            auth_items.append(str(password))

    return get_parsed_url(parsed, auth_items)
