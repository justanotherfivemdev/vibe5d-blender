import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.logger import logger


class VIBE4D_OT_authenticate(Operator):
    bl_idname = "vibe4d.authenticate"
    bl_label = "Authenticate"
    bl_description = "Authenticate with Vibe4D service"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            logger.info("Authentication operator called")

            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            self.report({'ERROR'}, f"Authentication failed: {str(e)}")
            return {'CANCELLED'}


classes = [
    VIBE4D_OT_authenticate,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
