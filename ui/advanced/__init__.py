"""
Advanced UI system for Vibe4D addon.
Provides a next-level custom UI with components, views, and advanced rendering.
"""

from .manager import UIManager ,ui_manager 
from .state import UIState 
from .renderer import UIRenderer 
from .types import Bounds ,CursorType ,EventType ,UIEvent 
from .theme import theme_manager ,get_themed_style 
from .colors import Colors 
from .blender_theme_integration import blender_theme ,get_theme_color 
from .component_theming import component_themer ,get_component_color 
from .ui_factory import ImprovedUIFactory ,ViewState 
from .layout_manager import layout_manager 
from .coordinates import CoordinateSystem 
from .viewport_button import viewport_button 


from .components import *
from .views import *
from .ui_state_manager import ui_state_manager ,UIStateManager 


from .import panels 
from .import ui 


classes =[]

__all__ =[
'UIManager',
'ui_manager',
'UIState',
'UIRenderer',
'Bounds',
'CursorType',
'EventType',
'UIEvent',
'theme_manager',
'get_themed_style',
'Colors',
'blender_theme',
'get_theme_color',
'component_themer',
'get_component_color',
'ImprovedUIFactory',
'ViewState',
'layout_manager',
'CoordinateSystem',
'ui_state_manager',
'UIStateManager',
'viewport_button',
'classes',
'panels',
'ui',
]

import logging 

logger =logging .getLogger (__name__ )

def register ():
    """Register the advanced UI system."""


    panels .register ()
    ui .register ()


    def delayed_viewport_button_enable ():
        try :
            viewport_button .enable ()
        except Exception as e :
            logger .error (f"Failed to enable viewport button: {e}")
        return None 

    import bpy 
    bpy .app .timers .register (delayed_viewport_button_enable ,first_interval =1.0 )


def unregister ():
    """Unregister the advanced UI system."""

    viewport_button .disable ()


    if ui_manager :
        ui_manager .cleanup ()


    try :
        from .components .url_image import cleanup_url_image_manager 
        cleanup_url_image_manager ()
    except Exception as e :
        logger .debug (f"Could not cleanup URL image manager: {e}")


    ui .unregister ()
    panels .unregister ()