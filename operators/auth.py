import webbrowser

import bpy
from bpy.types import Operator

from ..utils.logger import logger


class VIBE5D_OT_verify_license(Operator):
    bl_idname = "vibe5d.verify_license"
    bl_label = "Save API Key"
    bl_description = "Save API key for selected LLM provider"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            from ..utils.settings_manager import settings_manager
            settings_manager.save_settings(context)
            self.report({'INFO'}, "Provider settings saved successfully")
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Settings save error: {str(e)}")
            self.report({'ERROR'}, f"Failed to save settings: {str(e)}")
            return {'CANCELLED'}


class VIBE5D_OT_get_license_key(Operator):
    bl_idname = "vibe5d.get_license_key"
    bl_label = "Open GitHub"
    bl_description = "Open Vibe5D GitHub repository"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            github_url = "https://github.com/justanotherfivemdev/vibe5d-blender"

            logger.info("Opening GitHub page")
            webbrowser.open(github_url)

            self.report({'INFO'}, "GitHub page opened in browser")
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Failed to open GitHub page: {str(e)}")
            self.report({'ERROR'}, f"Failed to open GitHub page: {str(e)}")
            return {'CANCELLED'}


class VIBE5D_OT_open_discord(Operator):
    bl_idname = "vibe5d.open_discord"
    bl_label = "Discord"
    bl_description = "Join Vibe5D Discord community"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            discord_url = "https://discord.gg/dXAN23NwkM"

            logger.info("Opening Discord server")
            webbrowser.open(discord_url)

            self.report({'INFO'}, "Discord server opened in browser")
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Failed to open Discord: {str(e)}")
            self.report({'ERROR'}, f"Failed to open Discord: {str(e)}")
            return {'CANCELLED'}


class VIBE5D_OT_open_website(Operator):
    bl_idname = "vibe5d.open_website"
    bl_label = "Website"
    bl_description = "Visit Vibe5D GitHub repository"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            website_url = "https://github.com/justanotherfivemdev/vibe5d-blender"

            webbrowser.open(website_url)

            self.report({'INFO'}, "Website opened in browser")
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Failed to open website: {str(e)}")
            self.report({'ERROR'}, f"Failed to open website: {str(e)}")
            return {'CANCELLED'}


class VIBE5D_OT_manage_subscription(Operator):
    bl_idname = "vibe5d.manage_subscription"
    bl_label = "View Project"
    bl_description = "Open Vibe5D project page"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:

            project_url = "https://github.com/justanotherfivemdev/vibe5d-blender"

            logger.info("Opening project page")
            webbrowser.open(project_url)

            self.report({'INFO'}, "Project page opened in browser")
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Failed to open project page: {str(e)}")
            self.report({'ERROR'}, f"Failed to open project page: {str(e)}")
            return {'CANCELLED'}


class VIBE5D_OT_logout(Operator):
    bl_idname = "vibe5d.logout"
    bl_label = "Logout"
    bl_description = "No-op (hosted auth removed)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        self.report({'INFO'}, "No hosted auth to log out from")
        return {'FINISHED'}


class VIBE5D_OT_retry_auth(Operator):
    bl_idname = "vibe5d.retry_auth"
    bl_label = "Retry Connection"
    bl_description = "No-op (hosted auth removed)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        self.report({'INFO'}, "No hosted auth to retry")
        return {'FINISHED'}


class VIBE5D_OT_check_auth_status(Operator):
    bl_idname = "vibe5d.check_auth_status"
    bl_label = "Check Auth Status"
    bl_description = "No-op (hosted auth removed)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        self.report({'INFO'}, "Local/direct provider mode — no hosted auth")
        return {'FINISHED'}


class VIBE5D_OT_handle_network_error(Operator):
    bl_idname = "vibe5d.handle_network_error"
    bl_label = "Retry Connection"
    bl_description = "No-op (hosted auth removed)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        self.report({'INFO'}, "No hosted auth to retry")
        return {'FINISHED'}


class VIBE5D_OT_clear_network_error(Operator):
    bl_idname = "vibe5d.clear_network_error"
    bl_label = "Dismiss"
    bl_description = "No-op (hosted auth removed)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        return {'FINISHED'}


class VIBE5D_OT_refresh_usage(Operator):
    bl_idname = "vibe5d.refresh_usage"
    bl_label = "Refresh Usage"
    bl_description = "No-op (hosted usage tracking removed)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        self.report({'INFO'}, "No hosted usage tracking")
        return {'FINISHED'}


classes = [
    VIBE5D_OT_verify_license,
    VIBE5D_OT_get_license_key,
    VIBE5D_OT_open_discord,
    VIBE5D_OT_open_website,
    VIBE5D_OT_manage_subscription,
    VIBE5D_OT_logout,
    VIBE5D_OT_retry_auth,
    VIBE5D_OT_check_auth_status,
    VIBE5D_OT_handle_network_error,
    VIBE5D_OT_clear_network_error,
    VIBE5D_OT_refresh_usage,
]
