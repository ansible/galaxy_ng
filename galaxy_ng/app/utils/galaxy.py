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
