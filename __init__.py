bl_info = {
    "name": "Vibe5D",
    "author": "Vibe5D Community",
    "version": (0, 4, 0),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Vibe5D",
    "description": "Open-source Blender AI assistant — use OpenAI or local LLMs",
    "doc_url": "",
    "tracker_url": "https://github.com/justanotherfivemdev/vibe5d-blender",
    "category": "Development",
}

import bpy
from bpy.app.handlers import persistent

from . import api
from . import auth
from . import engine
from . import llm
from . import operators
from . import ui
from . import utils
from .auth.manager import auth_manager
from .utils.instructions_manager import instruction_manager
from .utils.logger import logger
from .utils.settings_manager import settings_manager

_registered_timers = []

query = api.query
execute = api.execute
scene_context = api.scene_context
get_query_formats = api.get_query_formats
table_counts = api.table_counts
viewport = api.viewport
add_viewport_render = api.add_viewport_render
see_viewport = api.see_viewport
see_render = api.see_render
render_async = api.render_async
get_render_result = api.get_render_result
cancel_render = api.cancel_render
list_active_renders = api.list_active_renders
render_with_callback = api.render_with_callback
screenshot_object = api.screenshot_object


@persistent
def load_auth_and_settings_on_file_load(file):
    try:
        if bpy.context.scene:
            is_authenticated = getattr(bpy.context.window_manager, 'vibe5d_authenticated', False)
            if not is_authenticated:
                auth_manager.initialize_auth(bpy.context)

            settings_manager.initialize_settings(bpy.context)
            instruction_manager.initialize_instruction(bpy.context)
    except Exception as e:
        logger.debug(f"Failed to load auth/settings/instructions on file load: {str(e)}")


@persistent
def recover_ui_overlay_on_file_load(file):
    def delayed_recovery():

        try:
            from .ui.advanced.manager import ui_manager
            from .ui.advanced.ui_state_manager import ui_state_manager

            recovery_success = ui_state_manager.recover_ui_state(bpy.context, ui_manager)
            if not recovery_success:
                logger.debug("No UI state to recover or recovery not needed")

        except Exception as e:
            logger.error(f"Error in UI recovery: {e}")
            import traceback
            logger.error(traceback.format_exc())

        return None

    try:
        bpy.app.timers.register(delayed_recovery, first_interval=0.1)
    except Exception as e:
        logger.error(f"Failed to schedule UI recovery: {e}")


@persistent
def ensure_viewport_button_handler(file):
    def delayed_handler_check():

        try:
            if hasattr(bpy.context, 'window_manager') and bpy.context.window_manager:
                try:
                    bpy.ops.vibe5d.viewport_button_handler('INVOKE_DEFAULT')
                    logger.debug("Viewport button modal handler started after file load")
                except RuntimeError as e:
                    if "already running" in str(e).lower():
                        logger.debug("Viewport button modal handler already running")
                    else:
                        logger.warning(f"Failed to start viewport button modal handler: {e}")
        except Exception as e:
            logger.debug(f"Error checking viewport button handler: {e}")
        return None

    try:
        bpy.app.timers.register(delayed_handler_check, first_interval=0.2)
    except Exception as e:
        logger.debug(f"Failed to schedule viewport button handler check: {e}")


@persistent
def auto_open_chat_ui_on_file_load(file):
    if file:
        logger.debug(f"Skipping auto-open for existing file: {file}")
        return

    def delayed_ui_open():

        try:
            from .ui.advanced.manager import ui_manager

            if ui_manager.is_ui_active():
                logger.debug("Chat UI already active, skipping auto-open")
                return None

            MIN_VIEWPORT_WIDTH = 800
            MIN_VIEWPORT_HEIGHT = 600
            target_area = None
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D' and area.width > MIN_VIEWPORT_WIDTH and area.height > MIN_VIEWPORT_HEIGHT:
                    target_area = area
                    break

            if not target_area:
                logger.debug("No suitable 3D viewport found for auto-opening chat UI")
                return None

            try:
                with bpy.context.temp_override(area=target_area):
                    bpy.ops.vibe5d.show_advanced_ui()
            except Exception as e:
                logger.error(f"Failed to auto-open chat UI using operator: {e}")

        except Exception as e:
            logger.error(f"Error in auto-open chat UI handler: {e}")
            import traceback
            logger.error(traceback.format_exc())

        return None

    try:
        bpy.app.timers.register(delayed_ui_open, first_interval=0.1)
    except Exception as e:
        logger.error(f"Failed to schedule auto-open chat UI: {e}")


def register():
    try:
        logger.info("=== Registering Vibe5D Addon ===")

        ui.register()
        operators.register()
        auth.register()
        api.register()
        llm.register()
        engine.register()
        utils.register()

        if load_auth_and_settings_on_file_load not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(load_auth_and_settings_on_file_load)

        if recover_ui_overlay_on_file_load not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(recover_ui_overlay_on_file_load)

        if ensure_viewport_button_handler not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(ensure_viewport_button_handler)

        if auto_open_chat_ui_on_file_load not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(auto_open_chat_ui_on_file_load)

        def delayed_modal_handler_start():
            try:
                if hasattr(bpy.context, 'window_manager') and bpy.context.window_manager:
                    bpy.ops.vibe5d.viewport_button_handler('INVOKE_DEFAULT')
                else:
                    logger.warning("Context not ready for modal handler, will retry on file load")
            except Exception as e:
                logger.warning(f"Failed to start viewport button modal handler: {e}")
            return None

        try:
            bpy.app.timers.register(delayed_modal_handler_start, first_interval=0.2)
            _registered_timers.append(delayed_modal_handler_start)
        except Exception as e:
            logger.warning(f"Failed to schedule viewport button modal handler: {e}")

        try:
            if bpy.context.scene:
                auth_manager.initialize_auth(bpy.context)
                settings_manager.initialize_settings(bpy.context)
                instruction_manager.initialize_instruction(bpy.context)
        except Exception as e:
            logger.debug(f"Failed to load initial auth/settings/instructions: {str(e)}")

        logger.info("Vibe5D addon registered successfully")

    except Exception as e:
        logger.error(f"Failed to register Vibe5D addon: {str(e)}")
        raise


def unregister():
    try:
        logger.info("=== Unregistering Vibe5D Addon ===")

        try:
            if bpy.context.scene:
                settings_manager.save_settings(bpy.context)
                instruction_manager.save_instruction(bpy.context)
        except Exception as e:
            logger.debug(f"Failed to save settings/instructions on unregister: {str(e)}")

        for timer_fn in _registered_timers:
            try:
                bpy.app.timers.unregister(timer_fn)
            except Exception:
                pass
        _registered_timers.clear()

        if load_auth_and_settings_on_file_load in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(load_auth_and_settings_on_file_load)
        if recover_ui_overlay_on_file_load in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(recover_ui_overlay_on_file_load)
        if ensure_viewport_button_handler in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(ensure_viewport_button_handler)
        if auto_open_chat_ui_on_file_load in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(auto_open_chat_ui_on_file_load)

        utils.unregister()
        engine.unregister()
        llm.unregister()
        api.unregister()
        auth.unregister()
        operators.unregister()
        ui.unregister()

        logger.info("Vibe5D addon unregistered successfully")

    except Exception as e:
        logger.error(f"Failed to unregister Vibe5D addon: {str(e)}")


if __name__ == "__main__":
    register()
