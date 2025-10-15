import bpy
from bpy.app.handlers import persistent

from .logger import logger


class SceneChangeHandler:

    def __init__(self):
        self.registered = False
        self._last_scene_name = None
        self._file_new_flag = False
        self._in_view_change = False

    def register(self):
        if self.registered:
            return

        self._last_scene_name = None
        bpy.app.handlers.depsgraph_update_post.append(self._on_scene_update)
        bpy.app.handlers.undo_post.append(self._on_undo_redo)
        bpy.app.handlers.redo_post.append(self._on_undo_redo)
        bpy.app.handlers.depsgraph_update_pre.append(self._detect_scene_change)
        bpy.app.handlers.load_post.append(self._on_file_load)
        bpy.app.handlers.load_pre.append(self._on_file_load_pre)
        self.registered = True

    def unregister(self):
        if not self.registered:
            return

        handlers = [
            (bpy.app.handlers.depsgraph_update_post, self._on_scene_update),
            (bpy.app.handlers.undo_post, self._on_undo_redo),
            (bpy.app.handlers.redo_post, self._on_undo_redo),
            (bpy.app.handlers.depsgraph_update_pre, self._detect_scene_change),
            (bpy.app.handlers.load_post, self._on_file_load),
            (bpy.app.handlers.load_pre, self._on_file_load_pre),
        ]

        for handler_list, handler_func in handlers:
            if handler_func in handler_list:
                handler_list.remove(handler_func)

        self.registered = False

    @persistent
    def _on_scene_update(self, scene, depsgraph):
        try:
            context = bpy.context
            if not context.scene or not getattr(context.scene, 'vibe4d_execution_pending', False):
                return

            has_changes = any(
                update.is_updated_transform or update.is_updated_geometry
                for update in depsgraph.updates
            )

            if has_changes:
                self._auto_accept_execution(context)
        except Exception as e:
            logger.error(f"Error in scene update handler: {e}")

    @persistent
    def _on_undo_redo(self, *args):
        try:
            context = bpy.context
            if context.scene and getattr(context.scene, 'vibe4d_execution_pending', False):
                self._auto_accept_execution(context)
        except Exception as e:
            logger.error(f"Error in undo/redo handler: {e}")

    @persistent
    def _detect_scene_change(self, scene, depsgraph):
        try:
            context = bpy.context
            if not context.scene:
                return

            current_scene_name = context.scene.name

            if self._last_scene_name is None:
                self._last_scene_name = current_scene_name
                return

            if self._last_scene_name != current_scene_name:
                logger.info(f"Scene change: {self._last_scene_name} -> {current_scene_name}")
                self._handle_scene_switch(context, self._last_scene_name, current_scene_name)

            self._last_scene_name = current_scene_name
        except Exception as e:
            logger.error(f"Error in scene change detection: {e}")

    def _handle_scene_switch(self, context, old_scene_name: str, new_scene_name: str):
        try:
            logger.info(f"Scene switch: {old_scene_name} -> {new_scene_name}")

            from .history_manager import history_manager
            history_manager.on_scene_change(context)

            self._reload_ui_for_scene_switch(new_scene_name)
        except Exception as e:
            logger.error(f"Error handling scene switch: {e}")

    def _reload_ui_for_scene_switch(self, new_scene_name: str):
        try:
            from ..ui.advanced.manager import ui_manager

            if not ui_manager.is_ui_active():
                return

            if not (hasattr(ui_manager, 'factory') and ui_manager.factory):
                return

            self._clear_message_scrollview(ui_manager)

            def delayed_ui_recreation():
                try:
                    if bpy.context.scene.name == new_scene_name:
                        ui_manager._recreate_ui_for_view_change(is_view_change=True)
                        if ui_manager.state.target_area:
                            ui_manager.state.target_area.tag_redraw()
                    else:
                        logger.warning(

                        )
                except Exception as e:
                    logger.error(f"Error in delayed UI recreation: {e}")
                return None

            bpy.app.timers.register(delayed_ui_recreation, first_interval=0.1)
        except Exception as e:
            logger.error(f"Failed to reload UI for scene change: {e}")

    def _clear_message_scrollview(self, ui_manager):
        try:
            if not (hasattr(ui_manager.factory, 'views') and ui_manager.factory.views):
                return

            from ..ui.advanced.ui_factory import ViewState
            main_view = ui_manager.factory.views.get(ViewState.MAIN)

            if main_view and hasattr(main_view, 'components'):
                message_scrollview = main_view.components.get('message_scrollview')
                if message_scrollview:
                    message_scrollview.clear_children()
                    message_scrollview._update_content_bounds()
        except Exception as e:
            logger.error(f"Error clearing message scrollview: {e}")

    def _auto_accept_execution(self, context):
        try:
            if not getattr(context.scene, 'vibe4d_execution_pending', False):
                return

            context.scene.vibe4d_execution_pending = False

            props_to_clear = [
                ,
            ,
            ,

            ]

            for prop in props_to_clear:
                if hasattr(context.scene, prop):
                    try:
                        del context.scene[prop]
                    except:
                        pass

            if hasattr(context.scene, 'vibe4d_scene_modified'):
                context.scene.vibe4d_scene_modified = False

            logger.info("Auto-accepted execution due to scene changes")

            try:
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            except:
                pass
        except Exception as e:
            logger.error(f"Error in auto-accept execution: {e}")

    @persistent
    def _on_file_load(self, *args):
        try:
            context = bpy.context
            if not context.scene:
                return

            current_scene_name = context.scene.name

            if current_scene_name == "Scene" and self._last_scene_name != "Scene":
                try:
                    from ..ui.advanced.manager import ui_manager
                    if ui_manager.is_ui_active():
                        ui_manager._recreate_ui_for_view_change(is_view_change=True)
                        if ui_manager.state.target_area:
                            ui_manager.state.target_area.tag_redraw()
                except Exception as e:
                    logger.error(f"Error recreating UI for new file: {e}")

            if self._last_scene_name is None:
                self._last_scene_name = current_scene_name
                return

            if self._last_scene_name != current_scene_name:
                self._handle_scene_switch(context, self._last_scene_name, current_scene_name)

            self._last_scene_name = current_scene_name
        except Exception as e:
            logger.error(f"Error in file load handler: {e}")

    @persistent
    def _on_file_load_pre(self, *args):
        try:
            self._file_new_flag = True

            try:
                from ..ui.advanced.manager import ui_manager

                if ui_manager.is_ui_active():
                    self._clear_message_scrollview(ui_manager)
                    self._last_scene_name = None
            except Exception as e:
                logger.error(f"Error clearing UI for file operation: {e}")
        except Exception as e:
            logger.error(f"Error in file load pre handler: {e}")

    def check_and_clear_file_new_flag(self) -> bool:
        if self._in_view_change:
            return False

        flag_was_set = self._file_new_flag
        self._file_new_flag = False
        return flag_was_set

    def set_view_change_flag(self, in_view_change: bool):
        self._in_view_change = in_view_change

    def is_in_view_change(self) -> bool:
        return self._in_view_change


scene_handler = SceneChangeHandler()
