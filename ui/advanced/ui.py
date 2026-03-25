import logging

import bpy
from bpy.types import Panel

logger = logging.getLogger(__name__)

from .manager import ui_manager


def enable_overlay(target_area=None):
    ui_manager.enable_overlay(target_area)


def disable_overlay():
    ui_manager.disable_overlay()


def cleanup_overlay():
    ui_manager.cleanup()


def register():
    try:
        logger.info("UI system registered")
    except Exception as e:
        logger.error(f"Error registering UI system: {e}")
        raise


def unregister():
    try:
        ui_manager.cleanup()
        logger.info("UI system unregistered")
    except Exception as e:
        logger.error(f"Error unregistering UI system: {e}")


__all__ = [
    "enable_overlay",
    "disable_overlay",
    "cleanup_overlay",
    "register",
    "unregister",
    "ui_manager",
]
