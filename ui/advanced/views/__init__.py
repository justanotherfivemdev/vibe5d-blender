"""
View system for different UI pages.
Separates UI logic into distinct view classes for better organization.
"""

from .auth_view import AuthView
from .base_view import BaseView
from .history_view import HistoryView
from .main_view import MainView
from .no_connection_view import NoConnectionView
from .settings_view import SettingsView

__all__ = [
    'BaseView',
    'AuthView',
    'MainView',
    'HistoryView',
    'SettingsView',
    'NoConnectionView',
]
