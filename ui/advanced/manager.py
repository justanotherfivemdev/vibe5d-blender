import hashlib
import logging
import time
from typing import Optional, Tuple, TYPE_CHECKING, Dict, Any

import bpy
from bpy.types import SpaceView3D

from .components import TextInput
from .coordinates import CoordinateSystem
from .layout_manager import layout_manager
from .renderer import UIRenderer
from .state import UIState
from .types import Bounds, CursorType
from .ui_factory import ImprovedUIFactory, ViewState
from .ui_state_manager import ui_state_manager
from .unified_styles import Styles
from ...utils.error_utils import create_error_context
from ...utils.history_manager import history_manager
from ...utils.logger import logger

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PerformanceConfig:
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"

    def __init__(self, level: str = CONSERVATIVE):
        self.level = level
        self._configure_for_level()

    def _configure_for_level(self):
        if self.level == self.CONSERVATIVE:
            self.timer_interval = 0.1
            self.ui_scale_check_interval = 1
            self.theme_check_interval = 3
            self.viewport_enforce_interval = 0.5
            self.animation_fps = 30
            self.cursor_blink_cycle = 1.2
            self.enable_selective_redraw = True
        elif self.level == self.BALANCED:
            self.timer_interval = 1.0
            self.ui_scale_check_interval = 5
            self.theme_check_interval = 10
            self.viewport_enforce_interval = 3
            self.animation_fps = 15
            self.cursor_blink_cycle = 1.5
            self.enable_selective_redraw = True
        elif self.level == self.AGGRESSIVE:
            self.timer_interval = 2.0
            self.ui_scale_check_interval = 10
            self.theme_check_interval = 20
            self.viewport_enforce_interval = 5
            self.animation_fps = 10
            self.cursor_blink_cycle = 2.0
            self.enable_selective_redraw = True

    def get_animation_interval(self) -> float:
        return 1.0 / self.animation_fps

    def should_check_ui_scale(self, counter: int) -> bool:
        return counter >= self.ui_scale_check_interval

    def should_check_theme(self, counter: int) -> bool:
        return counter >= self.theme_check_interval

    def should_enforce_viewport(self, counter: int) -> bool:
        return counter >= self.viewport_enforce_interval


class UIManager:
    def __init__(self):
        self.performance_config = PerformanceConfig(PerformanceConfig.CONSERVATIVE)

        self.state = UIState()
        self.layout_manager = layout_manager
        self.factory = ImprovedUIFactory()

        self.renderer = UIRenderer()
        self.draw_handler = None
        self.cursor_redraw_handler = None

        self.components = []
        self.ui_layout = None
        self._resize_timer = None

        self._cursor_requests = []

        self._mouse_pressed = False
        self._mouse_pressed_component = None
        self._last_hovered_component = None

        self._theme_check_counter = 0
        self._viewport_enforce_counter = 0

        self._viewport_resize_debounce_delay = 0.1
        self._pending_viewport_size = None

        self._is_generating = False
        self._current_ai_component = None
        self._active_client = None
        self._last_content_length = 0
        self._last_tool_call_state = None
        self._content_after_tool_call = False
        self._last_sent_prompt = None
        self._last_request_data = None

        self._tool_completion_blocks_created = set()
        self._tool_start_blocks_created = set()
        self._active_tool_components = {}

        self._attached_image_path = None
        self._attached_image_data_uri = None

        self._conversation_tracking = {
            'user_message': None,
            'final_content': None,
            'tool_calls': [],
            'tool_responses': [],
            'assistant_message_id': None,
            'conversation_saved': False,
        }

        self.factory.set_view_change_callback(self._recreate_ui_for_view_change)

        self._current_ui_scale = None
        self._ui_scale_check_counter = 0

        self._ui_recreation_in_progress = False
        self._ui_recreation_lock_start_time = None

    def set_performance_level(self, level: str):
        try:
            old_level = self.performance_config.level
            self.performance_config = PerformanceConfig(level)
            logger.info(f"Performance level changed from {old_level} to {level}")

            if self.cursor_redraw_handler:
                bpy.app.timers.unregister(self.cursor_redraw_handler)
                self.cursor_redraw_handler = bpy.app.timers.register(
                    self._enforce_ui_settings,
                    first_interval=self.performance_config.timer_interval,
                )
        except Exception as e:
            logger.error(f"Error setting performance level: {e}")

    def get_performance_level(self) -> str:
        return self.performance_config.level

    def get_performance_info(self) -> Dict[str, Any]:
        config = self.performance_config
        return {
            'level': config.level,
            'timer_interval': config.timer_interval,
            'ui_scale_check_interval': config.ui_scale_check_interval,
            'theme_check_interval': config.theme_check_interval,
            'viewport_enforce_interval': config.viewport_enforce_interval,
            'animation_fps': config.animation_fps,
            'cursor_blink_cycle': config.cursor_blink_cycle,
            'enable_selective_redraw': config.enable_selective_redraw,
        }

    def apply_aggressive_optimizations(self):
        self.set_performance_level(PerformanceConfig.AGGRESSIVE)

    def apply_conservative_optimizations(self):
        self.set_performance_level(PerformanceConfig.CONSERVATIVE)

    def apply_balanced_optimizations(self):
        self.set_performance_level(PerformanceConfig.BALANCED)

    def _initialize_ui_layout(self):
        if self.state.viewport_width == 0 or self.state.viewport_height == 0:
            return

        try:
            self.ui_layout = self.factory.create_layout(
                self.state.viewport_width,
                self.state.viewport_height,
                on_send=self._handle_send,
                on_add=self._handle_add,
                on_history=self._handle_history,
                on_settings=self._handle_settings,
                on_model_change=self._handle_model_change,
                on_auth_submit=self._handle_auth_submit,
                on_get_license=self._handle_get_license,
                on_stop_generation=self.factory._handle_stop_generation,
            )

            if not self.ui_layout:
                self.components = {}
                return

            self.components = self.ui_layout.get('components', {})
            self.state.components.clear()
            for component in self.ui_layout.get('all_components', []):
                self.state.add_component(component)

            for component in self.state.components:
                if hasattr(component, 'update_layout'):
                    component.update_layout()
                if hasattr(component, '_dimension_cache') and hasattr(component, 'invalidate'):
                    component._dimension_cache.clear()
                    component.invalidate()

            focused_component = self.factory.get_focused_component()
            if focused_component:
                self.state.set_focus(focused_component)
        except Exception as e:
            logger.error(f"Error initializing UI layout: {e}")
            self.ui_layout = None
            self.components = {}

    def _update_layout(self):
        if not self.ui_layout or self.state.viewport_width == 0 or self.state.viewport_height == 0:
            return

        self.factory._handle_viewport_change(self.state.viewport_width, self.state.viewport_height)

    def _on_viewport_resize_finished(self):
        try:
            if self._pending_viewport_size is None:
                return None

            width, height = self._pending_viewport_size
            self.state.update_viewport_size(width, height)

            if self.ui_layout is None:
                self._initialize_ui_layout()
            else:
                self._update_layout()

            self._pending_viewport_size = None
            self._request_redraw()
        except Exception as e:
            logger.error(f"Error in viewport resize finished callback: {e}")
        finally:
            self._resize_timer = None
        return None

    def attach_image_reference(self, filepath: str):
        import base64
        import os

        try:
            ext = os.path.splitext(filepath)[1].lower()
            mime_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.bmp': 'image/bmp',
                '.tiff': 'image/tiff',
                '.webp': 'image/webp',
            }
            mime_type = mime_map.get(ext, 'image/png')

            with open(filepath, 'rb') as f:
                image_bytes = f.read()

            encoded = base64.b64encode(image_bytes).decode('utf-8')
            self._attached_image_path = filepath
            self._attached_image_data_uri = f"data:{mime_type};base64,{encoded}"

            if self.factory and hasattr(self.factory, 'show_image_attachment_indicator'):
                self.factory.show_image_attachment_indicator(os.path.basename(filepath))

            self._request_redraw()
            logger.info(f"Image reference attached: {os.path.basename(filepath)}")
        except Exception as e:
            logger.error(f"Failed to attach image reference: {e}")
            self._attached_image_path = None
            self._attached_image_data_uri = None

    def clear_image_reference(self):
        self._attached_image_path = None
        self._attached_image_data_uri = None

        if self.factory and hasattr(self.factory, 'hide_image_attachment_indicator'):
            self.factory.hide_image_attachment_indicator()

        self._request_redraw()

    def handle_message_send(self, text: str):
        if text.strip():
            self._handle_send_with_text(text.strip())

    def _handle_send(self):
        text = self.factory.get_send_text() if self.factory else ""
        if not text.strip():
            return
        self.factory.clear_send_text()
        self._handle_send_with_text(text.strip())

    def _handle_send_with_text(self, text: str):
        if self.components is None or self._is_generating:
            return

        try:
            current_chat_id = getattr(bpy.context.scene, 'vibe5d_current_chat_id', '')
            if current_chat_id:
                history_manager.clear_unsent_text(bpy.context, current_chat_id)
        except Exception:
            pass

        try:
            import os

            display_text = text
            if self._attached_image_path:
                filename = os.path.basename(self._attached_image_path)
                display_text = f"{text}\n\n📎 {filename}"

            self.factory.add_message_to_scrollview(display_text, is_ai_response=False)
            self._is_generating = True
            self._last_content_length = 0
            self._last_tool_call_state = None
            self._content_after_tool_call = False
            self.factory._set_send_button_mode(False)
            self._current_ai_component = self.factory.add_markdown_message_to_scrollview("", is_ai_response=True)

            image_data_uri = self._attached_image_data_uri
            self.clear_image_reference()

            self._start_real_api_generation(text, image_data_uri=image_data_uri)
            self._request_redraw()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self._reset_generation_state()

    def _start_real_api_generation(self, prompt: str, image_data_uri: str = None):
        """Route to the OpenAI-compatible client for both 'openai' and 'local' providers."""
        try:
            self._start_conversation_tracking(prompt)
            self._last_sent_prompt = prompt

            context = bpy.context
            provider = getattr(context.scene, 'vibe5d_provider', 'openai')
            self._start_openai_generation(prompt, context, provider, image_data_uri=image_data_uri)
        except Exception as e:
            logger.error(f"Error starting generation: {e}")
            self._handle_api_error(f"Failed to start generation: {e}")

    def _start_openai_generation(self, prompt: str, context, provider: str, image_data_uri: str = None):
        try:
            from ...llm.request_builder import LLMRequestBuilder
            from ...api.openai_client import openai_client

            if not openai_client.is_ready_for_new_request():
                openai_client.close()

            api_key = getattr(context.scene, 'vibe5d_provider_api_key', '')
            base_url = getattr(context.scene, 'vibe5d_provider_base_url', '')
            provider_model = getattr(context.scene, 'vibe5d_provider_model', '')

            if provider == 'local':
                base_url = base_url or 'http://localhost:11434/v1'
                provider_model = provider_model or 'llama3'
            else:
                base_url = base_url or 'https://api.openai.com/v1'
                provider_model = provider_model or 'gpt-4o-mini'

            request = LLMRequestBuilder.build_openai_chat_request(
                context=context,
                prompt=prompt,
                api_key=api_key,
                base_url=base_url,
                model=provider_model,
                image_data_uri=image_data_uri,
            )

            self._last_request_data = request
            self._active_client = openai_client
            success = openai_client.send_prompt_request(
                request_data=request,
                on_progress=self._handle_api_progress,
                on_complete=self._handle_api_complete,
                on_error=self._handle_api_error,
            )
            if not success:
                self._handle_api_error("Failed to start generation")
        except Exception as e:
            logger.error(f"Error starting OpenAI generation: {e}")
            self._handle_api_error(f"Failed to start generation: {e}")

    def _handle_api_progress(self, response):
        bpy.app.timers.register(lambda: self._update_ui_from_progress(response), first_interval=0.0)

    def _update_ui_from_progress(self, response):
        try:
            if not self._is_generating:
                return None

            tool_status = getattr(response, 'current_tool_status', None)
            tool_name = getattr(response, 'current_tool_name', None)
            call_id = getattr(response, 'current_tool_call_id', None)

            if tool_status == 'started' and tool_name and call_id:
                tool_call_data = {
                    'call_id': call_id,
                    'function': {
                        'name': tool_name,
                        'arguments': getattr(response, 'current_tool_arguments', '{}'),
                    },
                    'status': 'started',
                }
                self._track_tool_call(tool_call_data)
                if call_id not in self._tool_start_blocks_created:
                    status_block = self._get_tool_status_block(tool_name, 'started')
                    if status_block:
                        component = self.factory.add_markdown_message_to_scrollview(status_block, is_ai_response=True)
                        self._active_tool_components[call_id] = component
                        self._current_ai_component = component
                        self._tool_start_blocks_created.add(call_id)

            if tool_status == 'completed' and tool_name and call_id:
                success = getattr(response, 'current_tool_success', False)
                tool_response_data = {
                    'call_id': call_id,
                    'content': getattr(response, 'current_tool_result', '{}'),
                    'success': success,
                }
                self._track_tool_response(tool_response_data)
                completion_block = self._get_tool_status_block(tool_name, 'completed', success)
                if completion_block:
                    if not self._update_tool_component(call_id, completion_block):
                        self._current_ai_component = self.factory.add_markdown_message_to_scrollview(
                            completion_block,
                            is_ai_response=True,
                        )
                    self._cleanup_completed_tool_component(call_id)
                    self._tool_completion_blocks_created.add(call_id)
                    self._content_after_tool_call = True

            search_status = getattr(response, 'current_search_status', None)
            search_query = getattr(response, 'current_search_query', None)
            if search_status == 'started' and search_query:
                search_call_id = f"websearch_{hashlib.md5(search_query.encode()).hexdigest()[:8]}"
                self._track_tool_call({
                    'call_id': search_call_id,
                    'function': {'name': 'web_search', 'arguments': f'{{"query": "{search_query}"}}'},
                    'status': 'started',
                })
                self._current_ai_component = self.factory.add_markdown_message_to_scrollview(
                    f"[Searching web: {search_query}]",
                    is_ai_response=True,
                )
            elif search_status == 'completed' and search_query:
                result_count = getattr(response, 'current_search_result_count', 0)
                success = getattr(response, 'current_search_success', False)
                ui_message = f"Found {result_count} results" if success and result_count else (
                    "Web search completed" if success else "Web search failed"
                )
                self._track_tool_response({
                    'call_id': f"websearch_{hashlib.md5(search_query.encode()).hexdigest()[:8]}",
                    'content': ui_message,
                    'success': success,
                    'ui_message': ui_message,
                    'tool_name': 'web_search',
                })
                self._current_ai_component = self.factory.add_markdown_message_to_scrollview(
                    f"[{ui_message}: {search_query}]",
                    is_ai_response=True,
                )

            content = getattr(response, 'output_content', '') or ''
            if content:
                message_id = getattr(response, 'message_id', None)
                if message_id:
                    self._track_assistant_message(message_id, content)

                if self._content_after_tool_call and len(content) > self._last_content_length:
                    new_content = content[self._last_content_length:].strip()
                    if new_content:
                        self._current_ai_component = self.factory.add_markdown_message_to_scrollview(
                            new_content,
                            is_ai_response=True,
                        )
                        self._content_after_tool_call = False
                elif self._current_ai_component:
                    if hasattr(self._current_ai_component, 'set_markdown'):
                        self._current_ai_component.set_markdown(content)
                    elif hasattr(self._current_ai_component, 'set_message'):
                        self._current_ai_component.set_message(content)
                else:
                    self._current_ai_component = self.factory.add_markdown_message_to_scrollview(
                        content,
                        is_ai_response=True,
                    )

                self._last_content_length = len(content)
                self._request_redraw()
        except Exception as e:
            logger.error(f"Error updating progress UI: {e}")
        return None

    def _handle_api_complete(self, response):
        bpy.app.timers.register(lambda: self._complete_generation(response), first_interval=0.0)

    def _complete_generation(self, response):
        try:
            self._is_generating = False
            self.factory._set_send_button_mode(True)

            final_content = getattr(response, 'output_content', '') or ''
            message_id = getattr(response, 'message_id', None) or f"msg_{int(time.time() * 1000)}"
            self._track_assistant_message(message_id, final_content)

            # Handle tool calls returned by the model
            tool_calls = getattr(response, 'tool_calls', None) or []
            if tool_calls and getattr(response, 'tool_call_completed', False):
                self._process_tool_calls(response, tool_calls, final_content)
                return None

            if final_content:
                if self._current_ai_component:
                    if hasattr(self._current_ai_component, 'set_markdown'):
                        self._current_ai_component.set_markdown(final_content)
                    elif hasattr(self._current_ai_component, 'set_message'):
                        self._current_ai_component.set_message(final_content)
                else:
                    self._current_ai_component = self.factory.add_markdown_message_to_scrollview(
                        final_content,
                        is_ai_response=True,
                    )

            if not self._conversation_tracking.get('conversation_saved', False):
                self._save_conversation_to_history()

            usage = getattr(response, 'usage_info', None) or {}
            if usage:
                logger.debug(f"Generation usage: {usage}")

            if not getattr(response, 'success', True):
                logger.error(f"API generation failed: {getattr(response, 'error', 'Generation failed')}")
        except Exception as e:
            logger.error(f"Error completing generation: {e}")
        finally:
            self._reset_generation_state()
            self._request_redraw()
        return None

    def _process_tool_calls(self, response, tool_calls, assistant_content):
        """Execute tool calls returned by the model and send results back."""
        try:
            from ...engine.tools import tools_manager
            from ...api.openai_client import openai_client
            import json as _json

            context = bpy.context
            tool_results = []

            for tc in tool_calls:
                call_id = tc.get("id", "")
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                raw_args = func.get("arguments", "{}")

                try:
                    arguments = _json.loads(raw_args) if raw_args and raw_args.strip() else {}
                except _json.JSONDecodeError:
                    arguments = {}

                # Show tool execution in the UI
                status_block = self._get_tool_status_block(tool_name, 'started')
                if status_block:
                    self.factory.add_markdown_message_to_scrollview(status_block, is_ai_response=True)
                    self._request_redraw()

                success, result = tools_manager.handle_tool_call(tool_name, arguments, context)

                result_str = _json.dumps(result) if isinstance(result, dict) else str(result)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_str,
                })

                completion_block = self._get_tool_status_block(tool_name, 'completed', success)
                if completion_block:
                    self.factory.add_markdown_message_to_scrollview(completion_block, is_ai_response=True)
                    self._request_redraw()

            # Re-use the stored request data from the original call so the
            # full conversation context (history, instructions, schema) is
            # preserved.  Fall back to a fresh build if not available.
            if self._last_request_data:
                followup_request = dict(self._last_request_data)
                followup_request["messages"] = list(self._last_request_data.get("messages", []))
            else:
                from ...llm.request_builder import LLMRequestBuilder

                api_key = getattr(context.scene, 'vibe5d_provider_api_key', '')
                base_url = getattr(context.scene, 'vibe5d_provider_base_url', '')
                provider = getattr(context.scene, 'vibe5d_provider', 'openai')
                provider_model = getattr(context.scene, 'vibe5d_provider_model', '')

                if provider == 'local':
                    base_url = base_url or 'http://localhost:11434/v1'
                    provider_model = provider_model or 'llama3'
                else:
                    base_url = base_url or 'https://api.openai.com/v1'
                    provider_model = provider_model or 'gpt-4o-mini'

                followup_request = LLMRequestBuilder.build_openai_chat_request(
                    context=context,
                    prompt=self._last_sent_prompt or "",
                    api_key=api_key,
                    base_url=base_url,
                    model=provider_model,
                )

            # Append assistant message with tool_calls and tool result messages
            assistant_msg = {"role": "assistant", "content": assistant_content or ""}
            assistant_msg["tool_calls"] = tool_calls
            followup_request["messages"].append(assistant_msg)
            followup_request["messages"].extend(tool_results)

            self._is_generating = True
            self.factory._set_send_button_mode(False)
            self._current_ai_component = self.factory.add_markdown_message_to_scrollview("", is_ai_response=True)

            self._active_client = openai_client
            if not openai_client.is_ready_for_new_request():
                openai_client.close()

            success = openai_client.send_prompt_request(
                request_data=followup_request,
                on_progress=self._handle_api_progress,
                on_complete=self._handle_api_complete,
                on_error=self._handle_api_error,
            )
            if not success:
                self._handle_api_error("Failed to send tool results back to model")

        except Exception as e:
            logger.error(f"Error processing tool calls: {e}")
            self._reset_generation_state()
            self._request_redraw()

    def _handle_api_error(self, error):
        bpy.app.timers.register(lambda: self._handle_error_ui_update(error), first_interval=0.0)

    def _handle_error_ui_update(self, error):
        try:
            if self._conversation_tracking and not self._conversation_tracking.get('conversation_saved', False):
                self._save_conversation_to_history()

            error_context = create_error_context(str(error))
            error_content = error_context['formatted_message']

            if self.components:
                self.factory.add_error_message_to_scrollview(error_content)
            elif self._current_ai_component:
                if hasattr(self._current_ai_component, 'set_markdown'):
                    self._current_ai_component.set_markdown(error_content)
                elif hasattr(self._current_ai_component, 'set_message'):
                    self._current_ai_component.set_message(error_content)

            try:
                history_manager.add_error_message(bpy.context, error_content)
            except Exception as save_error:
                logger.debug(f"Failed to save error message: {save_error}")
        except Exception as e:
            logger.error(f"Error handling API error: {e}")
        finally:
            self._reset_generation_state()
            self._request_redraw()
        return None

    def _reset_generation_state(self):
        self._is_generating = False
        self._last_content_length = 0
        self._last_tool_call_state = None
        self._content_after_tool_call = False
        self._current_ai_component = None
        self._active_client = None
        self._last_request_data = None
        self._cleanup_active_client()
        if self.factory:
            self.factory._set_send_button_mode(True)
        self._reset_conversation_tracking()

    def _cleanup_active_client(self):
        try:
            from ...api.openai_client import openai_client
            if not openai_client.is_ready_for_new_request():
                openai_client.close()
        except Exception:
            pass

    def cleanup(self):
        if self._is_generating and self._conversation_tracking and not self._conversation_tracking.get('conversation_saved', False):
            try:
                self._save_conversation_to_history()
            except Exception as e:
                logger.error(f"Failed to save conversation during cleanup: {e}")

        self._cleanup_websocket_connection()

        if self.draw_handler:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
            self.draw_handler = None

        if self.cursor_redraw_handler:
            try:
                bpy.app.timers.unregister(self.cursor_redraw_handler)
            except Exception:
                pass
            self.cursor_redraw_handler = None

        if self._resize_timer is not None:
            try:
                bpy.app.timers.unregister(self._resize_timer)
            except Exception:
                pass
            self._resize_timer = None

        if self.components:
            self.components.clear()
        self.state.reset()
        self.factory.cleanup()

    def _start_conversation_tracking(self, user_prompt: str):
        self._conversation_tracking = {
            'user_message': user_prompt,
            'final_content': None,
            'tool_calls': [],
            'tool_responses': [],
            'assistant_message_id': None,
            'conversation_saved': False,
        }
        self._tool_completion_blocks_created.clear()
        self._tool_start_blocks_created.clear()
        self._active_tool_components.clear()

    def _reset_conversation_tracking(self):
        self._conversation_tracking = {
            'user_message': None,
            'final_content': None,
            'tool_calls': [],
            'tool_responses': [],
            'assistant_message_id': None,
            'conversation_saved': False,
        }
        self._tool_completion_blocks_created.clear()
        self._tool_start_blocks_created.clear()
        self._active_tool_components.clear()
        self._last_sent_prompt = None

    def _track_assistant_message(self, message_id: str, content: str = ""):
        self._conversation_tracking['assistant_message_id'] = message_id
        if content:
            self._conversation_tracking['final_content'] = content

    def _track_tool_call(self, tool_call_data: dict):
        call_id = tool_call_data.get('call_id')
        if any(existing.get('call_id') == call_id for existing in self._conversation_tracking['tool_calls']):
            return
        self._conversation_tracking['tool_calls'].append(tool_call_data)

    def _track_tool_response(self, tool_response_data: dict):
        call_id = tool_response_data.get('call_id')
        if any(existing.get('call_id') == call_id for existing in self._conversation_tracking['tool_responses']):
            return
        self._conversation_tracking['tool_responses'].append(tool_response_data)

    def _save_conversation_to_history(self):
        if self._conversation_tracking.get('conversation_saved'):
            return

        try:
            context = bpy.context
            user_message = self._conversation_tracking.get('user_message')
            if user_message:
                history_manager.add_message(context, 'user', user_message)

            final_content = self._conversation_tracking.get('final_content') or ''
            tool_calls = self._conversation_tracking.get('tool_calls', [])
            openai_tool_calls = None
            if tool_calls:
                openai_tool_calls = []
                for tool_call in sorted(tool_calls, key=lambda item: item.get('call_id', '')):
                    openai_tool_calls.append({
                        'id': tool_call.get('call_id', f"call_{len(openai_tool_calls)}"),
                        'type': 'function',
                        'function': {
                            'name': tool_call.get('function', {}).get('name', 'unknown'),
                            'arguments': tool_call.get('function', {}).get('arguments', '{}'),
                        },
                    })

            if final_content or openai_tool_calls:
                history_manager.add_message(
                    context,
                    'assistant',
                    final_content,
                    tool_calls=openai_tool_calls,
                )

            for tool_response in sorted(self._conversation_tracking.get('tool_responses', []), key=lambda item: item.get('call_id', '')):
                full_content = tool_response.get('content') or tool_response.get('ui_message', 'Tool response')
                history_manager.add_message(
                    context,
                    'tool',
                    full_content,
                    tool_call_id=tool_response.get('call_id'),
                )

                image_data = tool_response.get('image_data')
                if image_data and isinstance(image_data, dict):
                    data_uri = image_data.get('data_uri')
                    message_text = image_data.get('message_text')
                    call_id = tool_response.get('call_id')
                    if data_uri and message_text and call_id:
                        history_manager.add_message_after_tool_response(
                            context,
                            'assistant',
                            message_text,
                            call_id,
                            image_data=data_uri,
                        )

            self._conversation_tracking['conversation_saved'] = True
        except Exception as e:
            logger.error(f"Failed to save conversation to history: {e}")

    def _handle_add(self):
        try:
            self._reset_generation_state()
            view = self.factory.views.get(self.factory.current_view)
            if view and hasattr(view, 'get_message_scrollview'):
                message_scrollview = view.get_message_scrollview()
                if message_scrollview:
                    message_scrollview.children.clear()
                    message_scrollview._update_content_bounds()

            history_manager.create_new_chat(bpy.context)
            bpy.context.scene.vibe5d_output_content = ""
            bpy.context.scene.vibe5d_final_code = ""
            bpy.context.scene.vibe5d_guide_content = ""
            if view and hasattr(view, '_show_empty_chat_message'):
                view._show_empty_chat_message()
            self._request_redraw()
        except Exception as e:
            logger.error(f"Error starting new chat: {e}")

    def _handle_history(self):
        self.factory.switch_to_view(ViewState.HISTORY)

    def _handle_settings(self):
        self.factory.switch_to_view(ViewState.SETTINGS)

    def _handle_model_change(self, selected_model: str):
        try:
            model_mapping = {
                'Claude Sonnet 4.5': 'claude-sonnet-4-5',
                'GPT-4o': 'gpt-4o',
                'GPT-4o Mini': 'gpt-4o-mini',
            }
            bpy.context.scene.vibe5d_model = model_mapping.get(
                selected_model,
                selected_model.lower().replace(' ', '-'),
            )
        except Exception as e:
            logger.error(f"Error updating model selection: {e}")

    def _handle_auth_submit(self):
        self._authenticate_success()

    def _handle_get_license(self):
        logger.info("Get license clicked")

    def authenticate_success(self):
        self._authenticate_success()

    def _authenticate_success(self):
        self.factory.switch_to_view(ViewState.MAIN)

    def _delayed_init_check(self):
        try:
            if self.state.is_enabled and self.state.target_area and (not self.ui_layout or not self.state.components):
                if not self.force_ui_reinitialization():
                    bpy.app.timers.register(self._retry_init, first_interval=1.0)
        except Exception as e:
            logger.error(f"Error in delayed init check: {e}")
        return None

    def _retry_init(self):
        try:
            if self.state.is_enabled and self.state.target_area and (not self.ui_layout or not self.state.components):
                self.force_ui_reinitialization()
        except Exception as e:
            logger.error(f"Error retrying UI initialization: {e}")
        return None

    def enable_overlay(self, target_area=None):
        try:
            self.state.target_area = target_area
            self.state.is_enabled = True
            self._original_workspace = bpy.context.window.workspace
            self._original_screen = bpy.context.window.screen
            self._current_ui_scale = CoordinateSystem.get_ui_scale()
            ui_state_manager.save_ui_state(bpy.context, self, target_area)
            self.factory.switch_to_appropriate_view_on_startup()
            if self.draw_handler is None:
                self.draw_handler = SpaceView3D.draw_handler_add(self._draw_callback, (), 'WINDOW', 'POST_PIXEL')
            try:
                bpy.ops.vibe5d.ui_modal_handler('INVOKE_DEFAULT')
            except Exception as e:
                logger.warning(f"Failed to start modal handler: {e}")
            self._redraw_viewports()
            bpy.app.timers.register(self._delayed_init_check, first_interval=0.5)
            self.cursor_redraw_handler = bpy.app.timers.register(
                self._enforce_ui_settings,
                first_interval=self.performance_config.timer_interval,
            )
        except Exception as e:
            logger.error(f"Error enabling overlay: {e}")
            raise

    def disable_overlay(self):
        if not self.state.is_enabled:
            return

        try:
            ui_state_manager.clear_ui_state(bpy.context)
        except Exception:
            pass

        if self.draw_handler:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
            self.draw_handler = None

        if self.cursor_redraw_handler:
            try:
                bpy.app.timers.unregister(self.cursor_redraw_handler)
            except Exception:
                pass
            self.cursor_redraw_handler = None

        self.state.is_enabled = False
        self.state.target_area = None
        self.state.components.clear()
        self.state.focused_component = None
        self._current_ui_scale = None
        self._ui_scale_check_counter = 0
        self._ui_recreation_in_progress = False
        self._ui_recreation_lock_start_time = None
        self.reset_cursor_to_default()
        self.factory.cleanup()
        self._redraw_viewports()

    def _draw_callback(self):
        region = None
        try:
            if not self.state.is_enabled or not self.state.target_area:
                return

            context = bpy.context
            region = context.region
            area = context.area
            if not region or area != self.state.target_area:
                return

            new_width, new_height = region.width, region.height
            if self.state.viewport_width != new_width or self.state.viewport_height != new_height:
                if self.state.viewport_width == 0 or self.state.viewport_height == 0:
                    self.state.update_viewport_size(new_width, new_height)
                    if self.ui_layout is None:
                        self._initialize_ui_layout()
                    else:
                        self._update_layout()
                else:
                    self._pending_viewport_size = (new_width, new_height)
                    if self._resize_timer is not None:
                        try:
                            bpy.app.timers.unregister(self._resize_timer)
                        except Exception:
                            pass
                    self._resize_timer = bpy.app.timers.register(
                        self._on_viewport_resize_finished,
                        first_interval=self._viewport_resize_debounce_delay,
                    )

            if self.ui_layout is None:
                self._initialize_ui_layout()
            if not self.state.components:
                self._initialize_ui_layout()
            if not self.state.components:
                self._draw_error_message(region)
                return

            self.renderer.draw_rect(Bounds(0, 0, region.width, region.height), Styles.Panel)
            visible_components = [component for component in self.state.components if component.is_visible()]
            if not visible_components:
                self._draw_error_message(region)
                return

            for component in visible_components:
                try:
                    component.render(self.renderer)
                except Exception as e:
                    logger.error(f"Error rendering {type(component).__name__}: {e}")

            if self.state.focused_component and isinstance(self.state.focused_component, TextInput):
                self._schedule_cursor_redraw()
        except Exception as e:
            logger.error(f"Error in draw callback: {e}")
            if region:
                self._draw_error_message(region)

    def _draw_error_message(self, region):
        try:
            self.renderer.draw_rect(Bounds(0, 0, region.width, region.height), (0.1, 0.1, 0.1, 0.9))
            from .components import Label
            error_label = Label(
                "UI Loading Error - Please try reopening",
                10,
                region.height // 2,
                region.width - 20,
                30,
            )
            error_label.style.text_color = (1.0, 0.3, 0.3, 1.0)
            error_label.render(self.renderer)
        except Exception as e:
            logger.error(f"Error drawing error message: {e}")

    def _schedule_animation_redraw(self):
        self._request_redraw()

    def _schedule_cursor_redraw(self):
        self._request_redraw()

    def _enforce_ui_settings(self):
        try:
            if not self.state.is_enabled or not self.state.target_area:
                return self.performance_config.timer_interval

            if self._check_ui_scale_changes():
                self._handle_ui_scale_change()

            return self.performance_config.timer_interval
        except Exception as e:
            logger.error(f"Error enforcing UI settings: {e}")
            return None

    def _redraw_viewports(self):
        try:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        except Exception as e:
            logger.error(f"Error redrawing viewports: {e}")

    def _request_redraw(self):
        self._selective_redraw()

    def _selective_redraw(self):
        if self.state.target_area and hasattr(self.state.target_area, 'tag_redraw'):
            self.state.target_area.tag_redraw()

    def is_ui_active(self) -> bool:
        if not self.state.is_enabled or not self.state.target_area:
            return False
        try:
            return any(area == self.state.target_area for area in bpy.context.screen.areas)
        except Exception:
            return False

    def handle_mouse_event(self, context, event) -> str:
        try:
            if not self.state.is_enabled or not self.state.target_area:
                return 'PASS_THROUGH'

            if not self._mouse_in_target_area(event):
                if self._last_hovered_component:
                    from .types import UIEvent, EventType
                    self._last_hovered_component.handle_event(UIEvent(EventType.MOUSE_LEAVE, event.mouse_x, event.mouse_y))
                    self._last_hovered_component = None
                self.reset_cursor_to_default()
                return 'PASS_THROUGH'

            mouse_x, mouse_y = self._screen_to_region_coords(event, self.state.target_area)
            if mouse_x is None or mouse_y is None:
                return 'PASS_THROUGH'

            self.state.mouse_x = mouse_x
            self.state.mouse_y = mouse_y
            self._update_cursor_for_mouse_position(mouse_x, mouse_y)

            from .types import UIEvent, EventType
            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                component = self.state.get_component_at_point(mouse_x, mouse_y)
                if component:
                    self._mouse_pressed = True
                    self._mouse_pressed_component = component
                    component.handle_event(UIEvent(EventType.MOUSE_PRESS, mouse_x, mouse_y))
                    self.state.set_focus(component)
                else:
                    self.state.set_focus(None)
                    self._mouse_pressed = False
                    self._mouse_pressed_component = None
                self._request_redraw()
                return 'RUNNING_MODAL'

            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                if self._mouse_pressed_component:
                    self._mouse_pressed_component.handle_event(UIEvent(EventType.MOUSE_RELEASE, mouse_x, mouse_y))
                    current_component = self.state.get_component_at_point(mouse_x, mouse_y)
                    if current_component == self._mouse_pressed_component:
                        self._mouse_pressed_component.handle_event(UIEvent(EventType.MOUSE_CLICK, mouse_x, mouse_y))
                self._mouse_pressed = False
                self._mouse_pressed_component = None
                self._request_redraw()
                return 'RUNNING_MODAL'

            if event.type == 'MOUSEMOVE' and self._mouse_pressed and self._mouse_pressed_component:
                self._mouse_pressed_component.handle_event(UIEvent(EventType.MOUSE_DRAG, mouse_x, mouse_y))
                self._request_redraw()
                return 'RUNNING_MODAL'

            if event.type == 'MOUSEMOVE':
                component = self.state.get_component_at_point(mouse_x, mouse_y)
                if self._last_hovered_component and self._last_hovered_component != component:
                    self._last_hovered_component.handle_event(UIEvent(EventType.MOUSE_LEAVE, mouse_x, mouse_y))
                if component and component != self._last_hovered_component:
                    component.handle_event(UIEvent(EventType.MOUSE_ENTER, mouse_x, mouse_y))
                if component:
                    component.handle_event(UIEvent(EventType.MOUSE_MOVE, mouse_x, mouse_y))
                self._last_hovered_component = component
                return 'RUNNING_MODAL'

            if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and event.value == 'PRESS':
                component = self.state.get_component_at_point(mouse_x, mouse_y)
                if component:
                    component.handle_event(UIEvent(
                        EventType.MOUSE_WHEEL,
                        mouse_x,
                        mouse_y,
                        data={'wheel_direction': 'UP' if event.type == 'WHEELUPMOUSE' else 'DOWN'},
                    ))
                    self._request_redraw()
                    return 'RUNNING_MODAL'

            if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'MOUSEMOVE'}:
                return 'RUNNING_MODAL'
        except Exception as e:
            logger.error(f"Error handling mouse event: {e}")
        return 'PASS_THROUGH'

    def handle_keyboard_event(self, context, event) -> str:
        try:
            if not self.state.is_enabled or not self.state.target_area or not self.state.focused_component:
                return 'PASS_THROUGH'

            from .types import UIEvent, EventType
            consumed = False
            if event.value == 'PRESS':
                key_name = event.type
                modifiers = []
                if event.ctrl:
                    modifiers.append('CTRL')
                if event.shift:
                    modifiers.append('SHIFT')
                if event.alt:
                    modifiers.append('ALT')
                if modifiers:
                    key_name = '_'.join(modifiers) + '_' + event.type

                if (not modifiers or modifiers == ['SHIFT']) and len(event.unicode) == 1 and event.unicode.isprintable():
                    consumed = self.state.focused_component.handle_event(UIEvent(EventType.TEXT_INPUT, unicode=event.unicode))
                else:
                    consumed = self.state.focused_component.handle_event(UIEvent(EventType.KEY_PRESS, key=key_name))

                if event.type == 'SPACE' and not modifiers and (len(event.unicode) != 1 or not event.unicode.isprintable()):
                    consumed = self.state.focused_component.handle_event(UIEvent(EventType.TEXT_INPUT, unicode=' ')) or consumed

            if consumed:
                self._request_redraw()
                return 'RUNNING_MODAL'

            if isinstance(self.state.focused_component, TextInput):
                return 'RUNNING_MODAL'
        except Exception as e:
            logger.error(f"Error handling keyboard event: {e}")
        return 'PASS_THROUGH'

    def _mouse_in_target_area(self, event) -> bool:
        if not self.state.target_area:
            return False
        return (
            self.state.target_area.x <= event.mouse_x <= self.state.target_area.x + self.state.target_area.width
            and self.state.target_area.y <= event.mouse_y <= self.state.target_area.y + self.state.target_area.height
        )

    def _screen_to_region_coords(self, event, area) -> Tuple[Optional[int], Optional[int]]:
        if not area:
            return None, None
        for region in area.regions:
            if region.type == 'WINDOW':
                region_x, region_y = CoordinateSystem.screen_to_region(event.mouse_x, event.mouse_y, area, region)
                if 0 <= region_x <= area.width and 0 <= region_y <= area.height:
                    return region_x, region_y
        return None, None

    def _check_ui_scale_changes(self) -> bool:
        try:
            current_scale = CoordinateSystem.get_ui_scale()
            if self._current_ui_scale is None:
                self._current_ui_scale = current_scale
                return False
            if abs(current_scale - self._current_ui_scale) > 0.01:
                self._current_ui_scale = current_scale
                return True
        except Exception as e:
            logger.error(f"Error checking UI scale changes: {e}")
        return False

    def _handle_ui_scale_change(self):
        try:
            self._set_ui_recreation_lock(True)
            if self.state.viewport_width > 0 and self.state.viewport_height > 0:
                self._recreate_ui_for_view_change(is_view_change=False)
        except Exception as e:
            logger.error(f"Error handling UI scale change: {e}")
        finally:
            self._set_ui_recreation_lock(False)

    def _set_ui_recreation_lock(self, locked: bool):
        self._ui_recreation_in_progress = locked
        self._ui_recreation_lock_start_time = time.time() if locked else None

    def _is_ui_recreation_locked(self) -> bool:
        if self._ui_recreation_in_progress and self._ui_recreation_lock_start_time:
            if time.time() - self._ui_recreation_lock_start_time > 5.0:
                self._set_ui_recreation_lock(False)
                return False
        return self._ui_recreation_in_progress

    def set_cursor(self, cursor_type: CursorType, is_override: bool = False):
        self._cursor_requests.append({
            'action': 'set',
            'cursor_type': cursor_type,
            'is_override': is_override,
        })

    def clear_cursor_override(self):
        self._cursor_requests.append({'action': 'clear_override'})

    def reset_cursor_to_default(self):
        self._cursor_requests.append({'action': 'reset'})

    def request_cursor_change(self, cursor_type: CursorType):
        self.set_cursor(cursor_type)

    def _update_cursor_for_mouse_position(self, mouse_x: int, mouse_y: int):
        try:
            component = self.state.get_component_at_point(mouse_x, mouse_y)
            self.request_cursor_change(component.get_cursor_type() if component else CursorType.DEFAULT)
        except Exception as e:
            logger.error(f"Error updating cursor: {e}")

    def _recreate_ui_for_view_change(self, is_view_change: bool = True):
        if self.state.viewport_width == 0 or self.state.viewport_height == 0:
            return

        lock_was_already_set = self._is_ui_recreation_locked()
        if not lock_was_already_set:
            self._set_ui_recreation_lock(True)

        try:
            self.state.components.clear()
            if hasattr(layout_manager, 'containers'):
                layout_manager.containers.clear()
                layout_manager.layouts.clear()
                layout_manager.constraints.clear()
                if hasattr(layout_manager, 'container_bounds'):
                    layout_manager.container_bounds.clear()

            self.ui_layout = self.factory.create_layout(
                self.state.viewport_width,
                self.state.viewport_height,
                on_send=self._handle_send,
                on_add=self._handle_add,
                on_history=self._handle_history,
                on_settings=self._handle_settings,
                on_model_change=self._handle_model_change,
                on_auth_submit=self._handle_auth_submit,
                on_get_license=self._handle_get_license,
                on_stop_generation=self.factory._handle_stop_generation,
            )
            self.components = self.ui_layout.get('components', {})
            for component in self.ui_layout.get('all_components', []):
                self.state.add_component(component)
            focused_component = self.factory.get_focused_component()
            if focused_component and is_view_change:
                self.state.set_focus(focused_component)
            self._request_redraw()
        finally:
            if not lock_was_already_set:
                self._set_ui_recreation_lock(False)

    def demo_no_connection_view(self):
        self.factory.switch_to_view(ViewState.NO_CONNECTION)

    def test_connectivity_and_update_view(self):
        self.factory.check_and_handle_connectivity()

    def _get_tool_status_block(self, tool_name: str, status: str, success: bool = True) -> str:
        started = {
            'execute': '[Writing code]',
            'query': '[Reading scene]',
            'web_search_preview': '[Searching web]',
            'viewport': '[Capturing viewport]',
            'see_viewport': '[Capturing viewport]',
            'add_viewport_render': '[Capturing viewport]',
            'see_render': '[Rendering scene]',
        }
        completed = {
            'execute': '[Code executed]' if success else '[Code execution failed]',
            'query': '[Scene read]' if success else '[Scene reading failed]',
            'web_search_preview': '[Found results]' if success else '[Web search failed]',
            'viewport': '[Viewport captured]' if success else '[Viewport capture failed]',
            'see_viewport': '[Viewport captured]' if success else '[Viewport capture failed]',
            'add_viewport_render': '[Viewport captured]' if success else '[Viewport capture failed]',
            'see_render': '[Render captured]' if success else '[Render failed]',
        }
        if status == 'started':
            return started.get(tool_name, '[Using tool]')
        if status == 'completed':
            return completed.get(tool_name, '[Tool completed]' if success else '[Tool failed]')
        return ''

    def _update_tool_component(self, call_id: str, new_content: str):
        try:
            component = self._active_tool_components.get(call_id)
            if component and hasattr(component, 'set_markdown'):
                component.set_markdown(new_content)
                return True
        except Exception as e:
            logger.error(f"Error updating tool component for {call_id}: {e}")
        return False

    def _stop_animations_for_completed_tool(self, component, content: str):
        return None

    def _is_completed_tool_block(self, text: str) -> bool:
        text_lower = text.lower()
        indicators = [
            'code executed',
            'scene read',
            'found results',
            'viewport captured',
            'render captured',
            'tool completed',
        ]
        return any(indicator in text_lower for indicator in indicators)

    def _cleanup_completed_tool_component(self, call_id: str):
        if call_id in self._active_tool_components:
            del self._active_tool_components[call_id]
            return True
        return False

    def handle_external_tool_call(self, tool_call_data: dict):
        try:
            self._track_tool_call({
                'call_id': tool_call_data.get('call_id'),
                'function': {
                    'name': tool_call_data.get('tool_name'),
                    'arguments': tool_call_data.get('arguments', '{}'),
                },
                'status': 'executed',
            })
        except Exception as e:
            logger.error(f"Failed to handle external tool call: {e}")

    def handle_external_tool_response(self, tool_response_data: dict):
        try:
            call_id = tool_response_data.get('call_id')
            history_content = tool_response_data.get('content', '{}')
            ui_message = tool_response_data.get('ui_message') or 'Tool response received'
            tracked_data = {
                'call_id': call_id,
                'content': history_content,
                'success': tool_response_data.get('success', True),
                'ui_message': ui_message,
            }
            image_data = tool_response_data.get('image_data')
            if image_data and isinstance(image_data, dict):
                tracked_data['image_data'] = image_data
            self._track_tool_response(tracked_data)
        except Exception as e:
            logger.error(f"Failed to handle external tool response: {e}")

    def save_current_ui_state(self):
        try:
            if self.state.is_enabled and self.state.target_area:
                ui_state_manager.save_ui_state(bpy.context, self, self.state.target_area)
        except Exception as e:
            logger.debug(f"Could not save current UI state: {e}")

    def force_ui_reinitialization(self):
        try:
            self.state.components.clear()
            self.ui_layout = None
            self.components = {}
            if hasattr(layout_manager, 'containers'):
                layout_manager.containers.clear()
                layout_manager.layouts.clear()
                layout_manager.constraints.clear()
                if hasattr(layout_manager, 'container_bounds'):
                    layout_manager.container_bounds.clear()

            if self.state.viewport_width > 0 and self.state.viewport_height > 0:
                self._initialize_ui_layout()
                if self.ui_layout and self.state.components:
                    self._request_redraw()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error during UI reinitialization: {e}")
            return False

    def save_current_unsent_text(self):
        try:
            context = bpy.context
            current_chat_id = getattr(context.scene, 'vibe5d_current_chat_id', '')
            if current_chat_id:
                current_text = self.factory.get_send_text() if self.factory else ''
                history_manager.save_unsent_text(context, current_chat_id, current_text)
        except Exception as e:
            logger.debug(f"Could not save unsent text: {e}")

    def restore_current_unsent_text(self):
        try:
            context = bpy.context
            current_chat_id = getattr(context.scene, 'vibe5d_current_chat_id', '')
            if current_chat_id:
                history_manager.restore_unsent_text(context, current_chat_id)
        except Exception as e:
            logger.debug(f"Could not restore unsent text: {e}")


ui_manager = UIManager()
