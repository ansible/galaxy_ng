from .auth import (
    LoginView,
    LogoutView,
)
from .feature_flags import FeatureFlagsView

from .controller import ControllerListView

from .settings import SettingsView
from .sync import ContainerSyncRemoteView, ContainerSyncRegistryView

from .index_execution_environments import IndexRegistryEEView

__all__ = (
    # auth
    "LoginView",
    "LogoutView",

    # feature_flags
    "FeatureFlagsView",

    # controller
    "ControllerListView",

    # settings
    "SettingsView",

    # sync
    "ContainerSyncRemoteView",
    "ContainerSyncRegistryView",

    # index_execution_environments
    "IndexRegistryEEView",
)
