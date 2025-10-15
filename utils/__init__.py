from .json_utils import BlenderJSONEncoder, to_json_serializable
from .logger import logger
from .scene_handler import scene_handler
from .settings_manager import settings_manager
from .storage import secure_storage

classes = []

__all__ = ['classes', 'logger', 'secure_storage', 'settings_manager', 'scene_handler', 'BlenderJSONEncoder',
           ]


def register():
    scene_handler.register()
    pass


def unregister():
    scene_handler.unregister()
    pass
