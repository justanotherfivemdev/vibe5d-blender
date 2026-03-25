import bpy
from bpy.types import Operator


class VIBE5D_OT_accept_execution(Operator):
    bl_idname = "vibe5d.accept_execution"
    bl_label = "Accept Execution"
    bl_description = "Accept the executed code and keep changes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'WARNING'}, "Not implemented")
        return {'CANCELLED'}


class VIBE5D_OT_reject_execution(Operator):
    bl_idname = "vibe5d.reject_execution"
    bl_label = "Reject Execution"
    bl_description = "Reject the executed code and undo changes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'WARNING'}, "Not implemented")
        return {'CANCELLED'}


classes = [
    VIBE5D_OT_accept_execution,
    VIBE5D_OT_reject_execution,
]
