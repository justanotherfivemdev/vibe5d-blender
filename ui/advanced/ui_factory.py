import logging
import time
from enum import Enum
from typing import Dict, Any, Callable, Optional

import bpy

from .components.component_registry import component_registry
from .coordinates import CoordinateSystem
from .layout_manager import layout_manager
from .views import AuthView, MainView, HistoryView, SettingsView, NoConnectionView

logger = logging.getLogger(__name__)


class ViewState(Enum):
    AUTH = "auth"
    MAIN = "main"
    HISTORY = "history"
    SETTINGS = "settings"
    NO_CONNECTION = "no_connection"


class ImprovedUIFactory:

    def __init__(self, ui_manager=None):
        self.ui_manager = ui_manager
        self.views = {}
        self.current_view = ViewState.MAIN

        from .unified_styles import UnifiedStyles as Styles
        self.styles = Styles

        self.view_callbacks: Dict[str, Callable] = {}
        self.on_view_change_callback: Optional[Callable] = None
        self.active_layout = None

        self.typewriter_active = False
        self.typewriter_message = ""
        self.typewriter_current_text = ""
        self.typewriter_component = None
        self.typewriter_timer = None
        self.typewriter_speed = 0.03
        self.typewriter_start_time = 0
        self.typewriter_char_index = 0

        self._initialize_views()
        layout_manager.register_auto_resize_callback(self._handle_viewport_change)

    def _initialize_views(self):

        self.views = {
            ViewState.AUTH: AuthView(),
            ViewState.MAIN: MainView(),
            ViewState.HISTORY: HistoryView(),
            ViewState.SETTINGS: SettingsView(),
            ViewState.NO_CONNECTION: NoConnectionView(),
        }

        for view in self.views.values():
            view.set_callbacks(
                on_view_change=self._handle_view_change,
                on_go_back=self._handle_go_back,
            )

        if ViewState.SETTINGS in self.views:
            settings_view = self.views[ViewState.SETTINGS]
            if hasattr(settings_view, 'set_refresh_callback'):
                settings_view.set_refresh_callback(self._refresh_current_view)

    def create_layout(self, viewport_width: int, viewport_height: int, **callbacks) -> Dict[str, Any]:

        try:
            self._save_unsent_text_before_ui_change()

            self.view_callbacks = callbacks

            current_view = self.views.get(self.current_view)
            if not current_view:
                logger.error(f"Current view {self.current_view.value} not found in views")
                return {'components': {}, 'all_components': [], 'layouts': {}}

            current_view.set_callbacks(**callbacks)

            layout_result = current_view.create_layout(viewport_width, viewport_height)

            if not layout_result:
                logger.error(f"View {self.current_view.value} failed to create layout")
                return {'components': {}, 'all_components': [], 'layouts': {}}

            self.active_layout = layout_result

            components = layout_result.get('components', {})
            if components:
                for comp_name, component in components.items():
                    try:
                        component_registry.register(component, comp_name)
                    except Exception as e:
                        logger.warning(f"Failed to register component {comp_name}: {e}")

            layout_manager.handle_viewport_change(viewport_width, viewport_height)

            if hasattr(current_view, 'update_layout'):
                current_view.update_layout(viewport_width, viewport_height)

            self._restore_unsent_text_after_ui_change()

            return layout_result

        except Exception as e:
            logger.error(f"Error in create_layout: {e}")
            return {'components': {}, 'all_components': [], 'layouts': {}}

    def switch_to_view(self, view_state: ViewState):
        if self.current_view == view_state:
            return

        try:
            self._save_unsent_text_before_ui_change()

            if self.current_view in self.views:
                self.views[self.current_view].cleanup()

            component_registry.cleanup_all()

            old_view = self.current_view
            self.current_view = view_state

            if view_state == ViewState.SETTINGS and ViewState.SETTINGS in self.views:
                settings_view = self.views[ViewState.SETTINGS]
                if hasattr(settings_view, 'reset_usage_fetch_state'):
                    settings_view.reset_usage_fetch_state()

            logger.info(f"Switched from {old_view.value} to {view_state.value} view")

            if self.on_view_change_callback:
                self.on_view_change_callback()

            try:
                from .manager import ui_manager
                ui_manager.save_current_ui_state()
            except Exception as e:
                logger.debug(f"Could not save UI state after view change: {e}")

        except Exception as e:
            logger.error(f"Error in switch_to_view: {e}")
            raise

    def get_current_view(self) -> ViewState:

        return self.current_view

    def get_focused_component(self):

        if self.current_view in self.views:
            return self.views[self.current_view].get_focused_component()
        return None

    def get_send_text(self) -> str:

        if self.current_view in self.views:
            view = self.views[self.current_view]
            if hasattr(view, 'get_send_text'):
                return view.get_send_text()
        return ""

    def clear_send_text(self):

        if self.current_view in self.views:
            view = self.views[self.current_view]
            if hasattr(view, 'clear_send_text'):
                view.clear_send_text()

    def _get_message_scrollview(self):

        if self.current_view == ViewState.MAIN:
            view = self.views.get(self.current_view)
            if view and hasattr(view, 'get_message_scrollview'):
                return view.get_message_scrollview()
        return None

    def _calculate_message_gap(self, message_scrollview, is_ai_response: bool, is_error_message: bool = False) -> int:

        if not message_scrollview.children:
            return self.styles.get_same_role_message_gap()

        previous_message = message_scrollview.children[0]

        if is_error_message:
            return self.styles.get_different_role_message_gap()

        previous_is_ai = (hasattr(previous_message, 'style') and
                          getattr(previous_message.style, 'border_width', 0) == 0)

        previous_is_error = (hasattr(previous_message, 'style') and
                             hasattr(previous_message.style, 'background_color') and
                             previous_message.style.background_color == (0.2, 0.1, 0.1, 1.0))

        if previous_is_error:
            return self.styles.get_different_role_message_gap()

        if previous_is_ai == is_ai_response:
            return self.styles.get_same_role_message_gap()
        else:
            return self.styles.get_different_role_message_gap()

    def add_message_to_scrollview(self, text: str, is_ai_response: bool = False):

        message_scrollview = self._get_message_scrollview()
        if not message_scrollview:
            logger.error("Message scrollview not found")
            return

        self._remove_empty_state_if_present(message_scrollview)

        from .components.message import MessageComponent

        scaled_padding = CoordinateSystem.scale_int(40)
        max_width = message_scrollview.bounds.width - scaled_padding
        if message_scrollview.show_scrollbars:
            max_width -= message_scrollview.scrollbar_width

        message_component = MessageComponent(text, 0, 0, 100, 40)

        if is_ai_response:
            message_component.style.border_color = (0, 0, 0, 0)
            message_component.style.border_width = 0
        else:
            message_component.style.border_width = 1

        message_component.auto_resize_to_content(max_width)
        message_gap = self._calculate_message_gap(message_scrollview, is_ai_response)
        component_height = message_component.bounds.height + message_gap

        for existing_child in message_scrollview.children:
            existing_child.bounds.y += component_height

        scaled_message_padding = CoordinateSystem.scale_int(20)
        if is_ai_response:
            message_x = scaled_message_padding
        else:
            message_x = message_scrollview.bounds.width - message_component.bounds.width - scaled_message_padding

        message_y = 0
        message_component.set_position(message_x, message_y)

        message_scrollview.children.insert(0, message_component)
        message_component.ui_state = message_scrollview.ui_state

        message_scrollview._update_content_bounds()
        message_scrollview.scroll_to(y=0)

        return message_component

    def add_ai_response_with_typewriter(self, text: str):

        if self.typewriter_active:
            self._stop_typewriter()

        self._set_send_button_mode(False)

        ai_component = self.add_markdown_message_to_scrollview("", is_ai_response=True)

        self.typewriter_active = True
        self.typewriter_message = text
        self.typewriter_current_text = ""
        self.typewriter_component = ai_component
        self.typewriter_start_time = time.time()
        self.typewriter_char_index = 0
        self.typewriter_speed = 0.03

        self.typewriter_timer = bpy.app.timers.register(
            self._typewriter_update,
            first_interval=self.typewriter_speed
        )

        logger.info(f"Started typewriter effect for AI markdown response: {text[:50]}...")

    def add_markdown_message_to_scrollview(self, markdown_text: str, is_ai_response: bool = False):

        message_scrollview = self._get_message_scrollview()
        if not message_scrollview:
            logger.error("Message scrollview not found")
            return

        self._remove_empty_state_if_present(message_scrollview)

        from .components.markdown_message import MarkdownMessageComponent

        scaled_padding = CoordinateSystem.scale_int(40)
        max_width = message_scrollview.bounds.width - scaled_padding
        if message_scrollview.show_scrollbars:
            max_width -= message_scrollview.scrollbar_width

        message_component = MarkdownMessageComponent(markdown_text, 0, 0, 100, 40)
        message_component.auto_resize_to_content(max_width)

        message_gap = self._calculate_message_gap(message_scrollview, is_ai_response)
        component_height = message_component.bounds.height + message_gap

        for existing_child in message_scrollview.children:
            existing_child.bounds.y += component_height

        scaled_message_padding = CoordinateSystem.scale_int(20)
        if is_ai_response:
            message_x = scaled_message_padding
        else:
            message_x = message_scrollview.bounds.width - message_component.bounds.width - scaled_message_padding

        message_y = 0
        message_component.set_position(message_x, message_y)

        message_scrollview.children.insert(0, message_component)
        message_component.ui_state = message_scrollview.ui_state

        message_scrollview._update_content_bounds()
        message_scrollview.scroll_to(y=0)

        return message_component

    def _remove_empty_state_if_present(self, message_scrollview):

        try:
            if len(message_scrollview.children) == 1:
                child = message_scrollview.children[0]
                if hasattr(child, 'get_text') and child.get_text() == "Ready when you are.":
                    message_scrollview.children.clear()
                    message_scrollview.show_scrollbars = True
                    logger.debug("Removed empty state message from scrollview")
        except Exception as e:
            logger.warning(f"Error removing empty state message: {e}")

    def _typewriter_update(self):

        if not self.typewriter_active or not self.typewriter_component:
            return None

        if self.typewriter_char_index < len(self.typewriter_message):
            self.typewriter_char_index += 1
            self.typewriter_current_text = self.typewriter_message[:self.typewriter_char_index]

            if hasattr(self.typewriter_component, 'set_markdown'):
                self.typewriter_component.set_markdown(self.typewriter_current_text)
            else:
                self.typewriter_component.set_message(self.typewriter_current_text)

            message_scrollview = self._get_message_scrollview()
            if message_scrollview:
                scaled_padding = CoordinateSystem.scale_int(40)
                max_width = message_scrollview.bounds.width - scaled_padding
                if message_scrollview.show_scrollbars:
                    max_width -= message_scrollview.scrollbar_width

                old_height = self.typewriter_component.bounds.height
                self.typewriter_component.auto_resize_to_content(max_width)
                new_height = self.typewriter_component.bounds.height

                if new_height != old_height:
                    current_y = 0

                    for i in range(len(message_scrollview.children)):
                        child = message_scrollview.children[i]

                        if i == 0:
                            child.bounds.y = 0
                            current_y = child.bounds.height
                        else:
                            child.bounds.y = current_y

                        if i < len(message_scrollview.children) - 1:
                            next_child = message_scrollview.children[i + 1]

                            current_is_ai = (hasattr(child, 'style') and
                                             getattr(child.style, 'border_width', 0) == 0)
                            next_is_ai = (hasattr(next_child, 'style') and
                                          getattr(next_child.style, 'border_width', 0) == 0)

                            if current_is_ai == next_is_ai:
                                message_gap = self.styles.get_same_role_message_gap()
                            else:
                                message_gap = self.styles.get_different_role_message_gap()

                            if i > 0:
                                current_y += child.bounds.height + message_gap
                        else:
                            if i > 0:
                                current_y += child.bounds.height

                    message_scrollview._update_content_bounds()

            if hasattr(bpy.context, 'area') and bpy.context.area:
                bpy.context.area.tag_redraw()

            import random
            next_interval = self.typewriter_speed + random.uniform(-0.01, 0.01)

            if self.typewriter_char_index > 0 and self.typewriter_message[self.typewriter_char_index - 1] in '.!?':
                next_interval += 0.1
            elif self.typewriter_message[self.typewriter_char_index - 1] in ',;:':
                next_interval += 0.05

            return max(0.01, next_interval)
        else:
            self.typewriter_current_text = self.typewriter_message

            if hasattr(self.typewriter_component, 'set_markdown'):
                self.typewriter_component.set_markdown(self.typewriter_current_text)
            else:
                self.typewriter_component.set_message(self.typewriter_current_text)

            message_scrollview = self._get_message_scrollview()
            if message_scrollview:
                scaled_padding = CoordinateSystem.scale_int(40)
                max_width = message_scrollview.bounds.width - scaled_padding
                if message_scrollview.show_scrollbars:
                    max_width -= message_scrollview.scrollbar_width
                self.typewriter_component.auto_resize_to_content(max_width)

            self._stop_typewriter()

            if hasattr(bpy.context, 'area') and bpy.context.area:
                bpy.context.area.tag_redraw()

            return None

    def _stop_typewriter(self):

        self.typewriter_active = False
        if self.typewriter_timer:
            try:
                bpy.app.timers.unregister(self.typewriter_timer)
            except:
                pass
            self.typewriter_timer = None

        self.typewriter_component = None
        self.typewriter_current_text = ""
        self.typewriter_message = ""
        self.typewriter_char_index = 0

        self._set_send_button_mode(True)

    def _set_send_button_mode(self, is_send_mode: bool):

        if self.current_view == ViewState.MAIN:
            view = self.views[self.current_view]
            if hasattr(view, 'components') and 'send_button' in view.components:
                send_button = view.components['send_button']
                if send_button and hasattr(send_button, 'set_mode'):
                    send_button.set_mode(is_send_mode)
                    if hasattr(send_button, 'set_stop_callback'):
                        send_button.set_stop_callback(self._handle_stop_generation)

    def _handle_stop_generation(self):
        try:
            from .manager import ui_manager
            if hasattr(ui_manager, '_conversation_tracking') and ui_manager._conversation_tracking:
                if not ui_manager._conversation_tracking.get('conversation_saved', False):
                    try:
                        ui_manager._save_conversation_to_history()
                    except Exception as save_error:
                        logger.error(f"Failed to save conversation data before stop: {str(save_error)}")

            from ...api.websocket_client import llm_websocket_client

            llm_websocket_client.close()

            if hasattr(ui_manager, '_reset_generation_state'):
                ui_manager._reset_generation_state()

        except Exception as e:
            logger.error(f"Error stopping generation: {e}")

        if self.typewriter_active:
            self._stop_typewriter()

    def set_view_change_callback(self, callback: Callable):

        self.on_view_change_callback = callback

    def _handle_viewport_change(self, width: int, height: int):

        if self.current_view in self.views:
            self.views[self.current_view].update_layout(width, height)
        component_registry.process_updates()

    def _handle_view_change(self, new_view: ViewState):

        self.switch_to_view(new_view)

    def _handle_go_back(self):

        self.switch_to_view(ViewState.MAIN)

    def _refresh_current_view(self):

        if self.on_view_change_callback:
            self.on_view_change_callback()

    def cleanup(self):

        if self.typewriter_active:
            self._stop_typewriter()

        for view in self.views.values():
            view.cleanup()

        component_registry.cleanup_all()

        layout_manager.containers.clear()
        layout_manager.layouts.clear()
        layout_manager.constraints.clear()
        layout_manager.container_bounds.clear()

    def get_stats(self) -> Dict[str, Any]:

        return {
            'current_view': self.current_view.value,
            'component_count': len(component_registry.get_all_components()),
            'typewriter_active': self.typewriter_active,
            'view_count': len(self.views),
        }

    def check_and_handle_connectivity(self) -> bool:

        try:
            from .views.no_connection_view import NoConnectionView

            if NoConnectionView.check_internet_connection():
                logger.debug("Internet connection is available")
                return True

            logger.warning("No internet connection detected - switching to no connection view")
            self.switch_to_view(ViewState.NO_CONNECTION)
            return False

        except Exception as e:
            logger.error(f"Error checking connectivity: {e}")
            self.switch_to_view(ViewState.NO_CONNECTION)
            return False

    def switch_to_appropriate_view_on_startup(self):

        try:
            if not self.check_and_handle_connectivity():
                return
            self.switch_to_view(ViewState.MAIN)
        except Exception as e:
            logger.error(f"Error determining startup view: {e}")
            try:
                self.switch_to_view(ViewState.MAIN)
            except Exception as fallback_error:
                logger.error(f"Failed to switch to main view as fallback: {fallback_error}")

    def add_image_message_to_scrollview(self, text: str, image_data_uri: str, is_ai_response: bool = False):

        message_component = self.add_message_to_scrollview(text, is_ai_response=is_ai_response)
        if message_component and hasattr(message_component, 'image_data_uri'):
            message_component.image_data_uri = image_data_uri
        logger.info("Added image message to scrollview")
        return message_component

    def add_error_message_to_scrollview(self, error_text: str):

        message_scrollview = self._get_message_scrollview()
        if not message_scrollview:
            logger.error("Message scrollview not found")
            return None

        self._remove_empty_state_if_present(message_scrollview)

        from .components.error_message import ErrorMessageComponent

        scaled_padding = CoordinateSystem.scale_int(40)
        max_width = message_scrollview.bounds.width - scaled_padding
        if message_scrollview.show_scrollbars:
            max_width -= message_scrollview.scrollbar_width

        error_component = ErrorMessageComponent(error_text, 0, 0, 100, 40)
        error_component.auto_resize_to_content(max_width)

        message_gap = self._calculate_message_gap(message_scrollview, False, is_error_message=True)
        component_height = error_component.bounds.height + message_gap

        for existing_child in message_scrollview.children:
            existing_child.bounds.y += component_height

        error_component.set_position(CoordinateSystem.scale_int(20), 0)
        message_scrollview.children.insert(0, error_component)
        error_component.ui_state = message_scrollview.ui_state

        message_scrollview._update_content_bounds()
        message_scrollview.scroll_to(y=0)

        logger.info("Added error message to scrollview")
        return error_component

    def _save_unsent_text_before_ui_change(self):

        try:
            if self.current_view != ViewState.MAIN:
                return

            context = bpy.context
            from ...utils.history_manager import history_manager

            current_chat_id = getattr(context.scene, 'vibe5d_current_chat_id', '')
            if current_chat_id:
                current_text = self.get_send_text()
                history_manager.save_unsent_text(context, current_chat_id, current_text)
        except Exception as e:
            logger.debug(f"Could not save unsent text before UI change: {e}")

    def _restore_unsent_text_after_ui_change(self):

        try:
            if self.current_view != ViewState.MAIN:
                return

            context = bpy.context
            from ...utils.history_manager import history_manager

            current_chat_id = getattr(context.scene, 'vibe5d_current_chat_id', '')
            if current_chat_id:
                history_manager.restore_unsent_text(context, current_chat_id)
        except Exception as e:
            logger.debug(f"Could not restore unsent text after UI change: {e}")

    def close_settings(self):

        self.switch_to_view(ViewState.MAIN)


improved_ui_factory = ImprovedUIFactory()
