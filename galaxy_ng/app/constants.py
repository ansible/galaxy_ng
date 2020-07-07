import enum


class CertificationStatus(enum.Enum):
    CERTIFIED = 'certified'
    NEEDS_REVIEW = 'needs_review'
    NOT_CERTIFIED = 'not_certified'


class DeploymentMode(enum.Enum):
    STANDALONE = 'standalone'
    INSIGHTS = 'insights'


class UIAPIVersions(enum.Enum):
    CURRENT = 'v1'
    ALL = {'v1': 'v1/'}
