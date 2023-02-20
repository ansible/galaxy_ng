from .auth import (
    LoginView,
    LogoutView,
)
from .feature_flags import FeatureFlagsView

from .controller import ControllerListView

from .settings import SettingsView
from .landing_page import LandingPageView
from .sync import ContainerSyncRegistryView
from .signing import CollectionSignView

from .index_execution_environments import IndexRegistryEEView

from .ai_index import (
    AIDenyIndexAddView,
    AIDenyIndexListView,
    AIDenyIndexDetailView,
)

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

    # landing_page
    "LandingPageView",

    # sync
    "ContainerSyncRegistryView",

    # index_execution_environments
    "IndexRegistryEEView",

    # Signing
    "CollectionSignView",

    # AI/Wisdom
    "AIDenyIndexAddView",
    "AIDenyIndexListView",
    "AIDenyIndexDetailView"
)
