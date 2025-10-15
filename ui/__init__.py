import bpy

from . import advanced
from .properties import register_properties, unregister_properties

classes = []

__all__ = ['classes', 'advanced', 'register_properties', 'unregister_properties']


def register():
    register_properties()

    advanced.register()


def unregister():
    advanced.unregister()

    unregister_properties()
