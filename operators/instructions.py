"""
Custom instruction operator for Vibe4D addon.

Handles managing custom instruction with auto-save.
"""

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.instructions_manager import instruction_manager
from ..utils.logger import logger


class VIBE4D_OT_save_instruction(Operator):
    """Manually save custom instruction (for testing)."""

    bl_idname = "vibe4d.save_instruction"
    bl_label = "Save Instruction"
    bl_description = "Manually save custom instruction to persistent storage"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Save instruction to storage."""
        try:
            success = instruction_manager.save_instruction(context)

            if success:
                logger.info("Manually saved custom instruction")
                self.report({'INFO'}, "Instruction saved to storage")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to save instruction")
                return {'CANCELLED'}

        except Exception as e:
            logger.error(f"Manual save instruction failed: {str(e)}")
            self.report({'ERROR'}, f"Save failed: {str(e)}")
            return {'CANCELLED'}


class VIBE4D_OT_force_save_instruction(Operator):
    """Force immediate save of custom instruction."""

    bl_idname = "vibe4d.force_save_instruction"
    bl_label = "Force Save Instruction"
    bl_description = "Force immediate save of custom instruction, bypassing debouncing"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Force save instruction to storage."""
        try:
            success = instruction_manager.force_save_instruction(context)

            if success:
                logger.info("Force saved custom instruction")
                self.report({'INFO'}, "Instruction force saved to storage")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to force save instruction")
                return {'CANCELLED'}

        except Exception as e:
            logger.error(f"Force save instruction failed: {str(e)}")
            self.report({'ERROR'}, f"Force save failed: {str(e)}")
            return {'CANCELLED'}


class VIBE4D_OT_load_instruction(Operator):
    """Manually load custom instruction (for testing)."""

    bl_idname = "vibe4d.load_instruction"
    bl_label = "Load Instruction"
    bl_description = "Manually load custom instruction from persistent storage"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Load instruction from storage."""
        try:
            success = instruction_manager.initialize_instruction(context)

            if success:
                self.report({'INFO'}, "Instruction loaded from storage")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to load instruction")
                return {'CANCELLED'}

        except Exception as e:
            logger.error(f"Manual load instruction failed: {str(e)}")
            self.report({'ERROR'}, f"Load failed: {str(e)}")
            return {'CANCELLED'}


class VIBE4D_OT_clear_instruction(Operator):
    """Clear custom instruction."""

    bl_idname = "vibe4d.clear_instruction"
    bl_label = "Clear Instruction"
    bl_description = "Clear custom instruction from both scene and storage"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Clear instruction."""
        try:
            success = instruction_manager.clear_instruction(context)

            if success:
                logger.info("Cleared custom instruction")
                self.report({'INFO'}, "Instruction cleared")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to clear instruction")
                return {'CANCELLED'}

        except Exception as e:
            logger.error(f"Clear instruction failed: {str(e)}")
            self.report({'ERROR'}, f"Clear failed: {str(e)}")
            return {'CANCELLED'}


classes = [
    VIBE4D_OT_save_instruction,
    VIBE4D_OT_force_save_instruction,
    VIBE4D_OT_load_instruction,
    VIBE4D_OT_clear_instruction,
]


def register():
    """Register all instruction operators."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister all instruction operators."""
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
