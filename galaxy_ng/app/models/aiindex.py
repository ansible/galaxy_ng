from django.core.validators import RegexValidator
from django.db import models

SCOPES = (
    ("namespace", "Namespace"),
    ("legacy_namespace", "Legacy Namespace"),
)


# This regex is the most restrictive pattern that applies
# to both Namespace and LegacyNamespace.
namespace_validator = RegexValidator(
    r"^[a-z0-9_]+$", message="Reference must be a valid namespace name."
)


class AIIndexDenyList(models.Model):
    """Stores the list of content that are not allowed to be added into AI Index/Wisdom.

    Data from this model is exposed on the /ai_index/ endpoint and any namespace added
    to the table is opt-out from ai scanning.

    The reference field is a namespace name in case of namespace scope, and a
    legacy role namespace name in case of legacy_namespace scope.
    """

    scope = models.CharField(choices=SCOPES, max_length=255)
    reference = models.CharField(
        max_length=255,
        validators=[namespace_validator],
    )

    class Meta:
        unique_together = ("scope", "reference")
