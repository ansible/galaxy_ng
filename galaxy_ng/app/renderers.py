from rest_framework.renderers import BrowsableAPIRenderer


class CustomBrowsableAPIRenderer(BrowsableAPIRenderer):
    """Overrides the standard DRF Browsable API renderer."""

    def show_form_for_method(self, view, method, request, obj):
        """Display forms only for superuser."""
        if request.user.is_superuser:
            return super().show_form_for_method(view, method, request, obj)
        return False
