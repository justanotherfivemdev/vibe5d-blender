"""
Advanced UI Panels for Vibe4D Addon
"""

import bpy
from bpy.types import Panel, Operator

classes = [
]


def register():
    """Register all panels."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister all panels."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
