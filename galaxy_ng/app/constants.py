import enum


class CertificationStatus(enum.Enum):
    CERTIFIED = 'certified'
    NEEDS_REVIEW = 'needs_review'
    NOT_CERTIFIED = 'not_certified'


class DeploymentMode(enum.Enum):
    STANDALONE = 'standalone'
    INSIGHTS = 'insights'


CURRENT_UI_API_VERSION = 'v1'
ALL_UI_API_VERSION = {'v1': 'v1/'}

COMMUNITY_DOMAINS = (
    'galaxy.ansible.com',
    'galaxy-dev.ansible.com',
    'galaxy-qa.ansible.com',
)
