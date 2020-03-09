import enum


class CertificationStatus(enum.Enum):
    CERTIFIED = 'certified'
    NEEDS_REVIEW = 'needs_review'
    NOT_CERTIFIED = 'not_certified'
