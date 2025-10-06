"""
Advanced Custom UI System for Blender
Provides a component-based overlay system with GPU rendering

This is the main module that imports and re-exports all components.
"""

import logging 
import bpy 
from bpy .types import Panel 


logger =logging .getLogger (__name__ )


from .types import EventType ,UIEvent ,Bounds ,Style 
from .coordinates import CoordinateSystem 
from .state import UIState 
from .renderer import UIRenderer 
from .components import UIComponent ,TextInput ,Label ,Button 
from .manager import UIManager ,ui_manager 
from .theme import theme_manager ,get_themed_style ,get_theme_color 
from .colors import Colors ,get_color ,PALETTE 



def enable_overlay (target_area =None ):
    """Enable the custom overlay for a specific area."""
    ui_manager .enable_overlay (target_area )


def disable_overlay ():
    """Disable the custom overlay."""
    ui_manager .disable_overlay ()


def cleanup_overlay ():
    """Remove draw handler completely."""
    ui_manager .cleanup ()


def register ():
    """Register UI components."""
    try :
        logger .info ("UI system registered")
    except Exception as e :
        logger .error (f"Error registering UI system: {e}")
        raise 


def unregister ():
    """Unregister UI components."""
    try :
        ui_manager .cleanup ()
        logger .info ("UI system unregistered")
    except Exception as e :
        logger .error (f"Error unregistering UI system: {e}")



__all__ =[

'EventType',
'UIEvent',
'Bounds',
'Style',


'CoordinateSystem',
'UIState',
'UIRenderer',
'UIManager',


'theme_manager',
'get_themed_style',
'get_theme_color',


'Colors',
'get_color',
'PALETTE',


'UIComponent',
'TextInput',
'Label',
'Button',


'ui_manager',


'enable_overlay',
'disable_overlay',
'cleanup_overlay',
'register',
'unregister',
]