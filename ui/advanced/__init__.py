from . import ui
from .blender_theme_integration import blender_theme, get_theme_color
from .component_theming import component_themer, get_component_color, get_themed_component_style

from .components import *
from .coordinates import CoordinateSystem
from .layout_manager import layout_manager
from .manager import UIManager, ui_manager
from .renderer import UIRenderer
from .state import UIState
from .types import Bounds, CursorType, EventType, UIEvent
from .ui_factory import ImprovedUIFactory, ViewState
from .ui_state_manager import ui_state_manager, UIStateManager
from .unified_styles import Styles
from .viewport_button import viewport_button
from .views import *

classes = []

__all__ = [
    'ui',
    'blender_theme',
    'get_theme_color',
    'component_themer',
    'get_component_color',
    'get_themed_component_style',
    'CoordinateSystem',
    'layout_manager',
    'UIManager',
    'ui_manager',
    'UIRenderer',
    'UIState',
    'Bounds',
    'CursorType',
    'EventType',
    'UIEvent',
    'ImprovedUIFactory',
    'ViewState',
    'ui_state_manager',
    'UIStateManager',
    'Styles',
    'viewport_button',
    'classes',
]

import logging

logger = logging.getLogger(__name__)


def register():
    ui.register()

    def delayed_viewport_button_enable():
        try:
            viewport_button.enable()
        except Exception as e:
            logger.error(f"Failed to enable viewport button: {e}")
        return None

    import bpy
    bpy.app.timers.register(delayed_viewport_button_enable, first_interval=1.0)


def unregister():
    viewport_button.disable()

    if ui_manager:
        ui_manager.cleanup()

    try:
        from .components.url_image import cleanup_url_image_manager
        cleanup_url_image_manager()
    except Exception as e:
        logger.debug(f"Could not cleanup URL image manager: {e}")

    ui.unregister()
