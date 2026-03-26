import bpy
from bpy.types import Operator

from ..engine.executor import code_executor
from ..utils.logger import logger


class VIBE5D_OT_accept_execution(Operator):
    bl_idname = "vibe5d.accept_execution"
    bl_label = "Accept Execution"
    bl_description = "Accept the executed code and keep changes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        success = code_executor.accept_execution(context)
        if success:
            context.scene.vibe5d_execution_pending = False
            self.report({'INFO'}, "Execution accepted")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No pending execution to accept")
            return {'CANCELLED'}


class VIBE5D_OT_reject_execution(Operator):
    bl_idname = "vibe5d.reject_execution"
    bl_label = "Reject Execution"
    bl_description = "Reject the executed code and undo changes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        success = code_executor.reject_execution(context)
        if success:
            self.report({'INFO'}, "Execution rejected — changes rolled back")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Rollback failed or no pending execution")
            return {'CANCELLED'}


classes = [
    VIBE5D_OT_accept_execution,
    VIBE5D_OT_reject_execution,
]
