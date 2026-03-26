import time
import webbrowser

import bpy
from bpy.types import Operator

from ..api.client import api_client
from ..auth.manager import auth_manager
from ..utils.logger import logger


class VIBE5D_OT_verify_license(Operator):
    bl_idname = "vibe5d.verify_license"
    bl_label = "Save API Key"
    bl_description = "Save API key for selected LLM provider"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            # In Vibe5D, this just confirms the provider settings are saved
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
    bl_description = "Logout and clear authentication data"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            from ..auth.manager import auth_manager

            auth_manager.clear_auth_state(context)

            context.window_manager.vibe5d_status = "Ready"

            self.report({'INFO'}, "Logged out successfully")
            logger.info("User logged out")

            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            self.report({'ERROR'}, f"Logout failed: {str(e)}")
            return {'CANCELLED'}


class VIBE5D_OT_retry_auth(Operator):
    bl_idname = "vibe5d.retry_auth"
    bl_label = "Retry Connection"
    bl_description = "Retry authentication validation after network error"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            logger.info("Retrying authentication validation")

            context.window_manager.vibe5d_network_error = False
            context.window_manager.vibe5d_status = "Retrying connection..."

            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

            user_id = getattr(context.window_manager, 'vibe5d_user_id', '')
            token = getattr(context.window_manager, 'vibe5d_user_token', '')
            plan = getattr(context.window_manager, 'vibe5d_user_plan', '')

            if not user_id or not token:
                logger.error("No credentials available for retry")
                context.window_manager.vibe5d_status = "No credentials to retry"
                self.report({'ERROR'}, "No saved credentials available")
                return {'CANCELLED'}

            is_valid, error_type = api_client.validate_user_token(user_id, token)

            if is_valid:

                context.window_manager.vibe5d_authenticated = True
                context.window_manager.vibe5d_status = f"Authenticated ({plan} plan)" if plan else "Authenticated"
                context.window_manager.vibe5d_network_error = False

                auth_manager.last_validation_time = time.time()

                auth_manager.update_usage_info(context)

                logger.info("Authentication retry successful")
                self.report({'INFO'}, "Connection restored successfully")
                return {'FINISHED'}

            elif error_type == "network":

                context.window_manager.vibe5d_network_error = True
                context.window_manager.vibe5d_status = f"Authenticated ({plan} plan) - API temporarily unavailable" if plan else "Authenticated - API temporarily unavailable"

                logger.warning("Authentication retry failed - network still unavailable")
                self.report({'WARNING'}, "API still unavailable - please try again later")
                return {'CANCELLED'}

            else:

                logger.warning("Authentication retry failed - invalid credentials")
                context.window_manager.vibe5d_network_error = False

                auth_manager.clear_auth_state(context)

                self.report({'ERROR'}, "Authentication failed - please log in again")
                return {'CANCELLED'}

        except Exception as e:
            logger.error(f"Authentication retry error: {str(e)}")
            context.window_manager.vibe5d_status = "Retry failed"
            context.window_manager.vibe5d_network_error = True
            self.report({'ERROR'}, f"Retry failed: {str(e)}")
            return {'CANCELLED'}


class VIBE5D_OT_check_auth_status(Operator):
    bl_idname = "vibe5d.check_auth_status"
    bl_label = "Check Auth Status"
    bl_description = "Check current authentication status"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            if auth_manager.is_authenticated(context):
                user_info = auth_manager.get_user_info(context)
                if user_info:
                    email = user_info['email']
                    plan = user_info['plan']
                    self.report({'INFO'}, f"Authenticated as {email} ({plan} plan)")
                else:
                    self.report({'INFO'}, "Authenticated")
            else:
                self.report({'INFO'}, "Not authenticated")

            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Failed to check auth status: {str(e)}")
            self.report({'ERROR'}, f"Failed to check status: {str(e)}")
            return {'CANCELLED'}


class VIBE5D_OT_handle_network_error(Operator):
    bl_idname = "vibe5d.handle_network_error"
    bl_label = "Retry Connection"
    bl_description = "Retry connecting to LLM provider"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            if auth_manager.initialize_auth(context):
                context.window_manager.vibe5d_network_error = False
                self.report({'INFO'}, "Connection restored!")
                return {'FINISHED'}
            else:
                context.window_manager.vibe5d_network_error = True
                self.report({'WARNING'}, "Still unable to connect to API")
                return {'FINISHED'}

        except Exception as e:
            logger.error(f"Network error handling failed: {str(e)}")
            context.window_manager.vibe5d_network_error = True
            self.report({'ERROR'}, f"Connection retry failed: {str(e)}")
            return {'CANCELLED'}


class VIBE5D_OT_clear_network_error(Operator):
    bl_idname = "vibe5d.clear_network_error"
    bl_label = "Dismiss"
    bl_description = "Dismiss network error notification"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.window_manager.vibe5d_network_error = False
        return {'FINISHED'}


class VIBE5D_OT_refresh_usage(Operator):
    bl_idname = "vibe5d.refresh_usage"
    bl_label = "Refresh Usage"
    bl_description = "Refresh usage information from API"
    bl_options = {'REGISTER'}

    def execute(self, context):

        try:
            from ..auth.manager import auth_manager

            if not auth_manager.is_authenticated(context):
                self.report({'ERROR'}, "Not authenticated")
                return {'CANCELLED'}

            logger.info("Manually refreshing usage information")

            success = auth_manager.update_usage_info(context)

            if success:
                current_usage = getattr(context.window_manager, 'vibe5d_current_usage', 0)
                usage_limit = getattr(context.window_manager, 'vibe5d_usage_limit', 0)
                usage_percentage = getattr(context.window_manager, 'vibe5d_usage_percentage', 0.0)

                self.report({'INFO'}, f"Usage updated: {current_usage}/{usage_limit} ({usage_percentage:.1f}%)")
                logger.info("Usage information refreshed successfully")
            else:
                self.report({'WARNING'}, "Failed to refresh usage information")
                logger.warning("Failed to refresh usage information")

            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Usage refresh error: {str(e)}")
            self.report({'ERROR'}, f"Usage refresh failed: {str(e)}")
            return {'CANCELLED'}


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
