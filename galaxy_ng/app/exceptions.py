from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import ValidationError


class ConflictError(ValidationError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _('Data conflicts with existing entity.')
    default_code = 'conflict'
