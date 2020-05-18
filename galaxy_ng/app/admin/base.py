
import logging

from guardian.admin import GuardedModelAdmin

log = logging.getLogger(__name__)


class BaseModelAdmin(GuardedModelAdmin):
    pass


class PulpModelAdmin(BaseModelAdmin):
    pulp_readonly_fields = ("pulp_id", "pulp_created", "pulp_last_updated")
    pulp_fields = ("pulp_id", "pulp_created", "pulp_last_updated")

    def get_readonly_fields(self, request, obj=None):
        res = self.pulp_readonly_fields
        return res
    #     res = self.pulp_readonly_fields + tuple(super().get_readonly_fields(request, obj))
    #     if read_only:
    #         res += self.get_fields(request, obj)
    #     return res

    def get_fields(self, request, obj=None):
        return self.pulp_fields + tuple(super().get_fields(request, obj))
