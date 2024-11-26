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

from .search import (
    SearchListView
)


__all__ = (
    # AI/Wisdom
    "AIDenyIndexAddView",
    "AIDenyIndexDetailView",
    "AIDenyIndexListView",
    # Signing
    "CollectionSignView",
    # sync
    "ContainerSyncRegistryView",
    # controller
    "ControllerListView",
    # feature_flags
    "FeatureFlagsView",
    # index_execution_environments
    "IndexRegistryEEView",
    # landing_page
    "LandingPageView",
    # auth
    "LoginView",
    "LogoutView",
    # Search
    "SearchListView",
    # settings
    "SettingsView",

)
