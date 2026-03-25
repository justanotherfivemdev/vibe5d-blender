import logging
import threading
from typing import Dict, Any

import bpy
import gpu

from .base_view import BaseView
from ..blender_theme_integration import get_theme_color
from ..component_theming import get_themed_component_style
from ..components import Label, Button, Container, TextInput, BackButton
from ..components.base import Bounds
from ..components.image import ImageComponent
from ..coordinates import CoordinateSystem
from ..layout_manager import LayoutConfig, LayoutStrategy
from ..unified_styles import Styles

logger = logging.getLogger(__name__)


def get_font_size():
    return Styles.get_font_size()


def get_title_font_size():
    return Styles.get_font_size("title")


def get_left_margin():
    return Styles.get_left_margin()


def get_right_margin():
    return Styles.get_right_margin()


def get_container_internal_padding():
    return Styles.get_container_internal_padding()


def get_scrollview_internal_margin():
    return Styles.get_scrollview_internal_margin()


def get_scrollview_content_padding():
    return Styles.get_scrollview_content_padding()


def get_big_spacing():
    return Styles.get_big_spacing()


def get_small_spacing():
    return Styles.get_small_spacing()


def get_medium_spacing():
    return Styles.get_medium_spacing()


def get_rule_spacing():
    return Styles.get_rule_spacing()


def get_link_spacing():
    return Styles.get_link_spacing()


def get_bottom_padding():
    return Styles.get_bottom_padding()


def get_button_height():
    return Styles.get_button_height()


def get_large_button_height():
    return Styles.get_large_button_height()


def get_small_button_height():
    return Styles.get_small_button_height()


def get_label_height():
    return Styles.get_label_height()


def get_small_label_height():
    return Styles.get_small_label_height()


def get_input_height():
    return Styles.get_input_height()


def get_toggle_button_size():
    return Styles.get_toggle_button_size()


def get_go_back_button_width():
    return Styles.get_go_back_button_width()


def get_name_label_width():
    return Styles.get_name_label_width()


def get_plan_label_width():
    return Styles.get_plan_label_width()


def get_manage_sub_label_width():
    return Styles.get_manage_sub_label_width()


def get_logout_button_width():
    return Styles.get_logout_button_width()


def get_add_button_width():
    return Styles.get_add_button_width()


def get_large_add_button_width():
    return Styles.get_large_add_button_width()


def get_toggle_button_width():
    return Styles.get_toggle_button_width()


def get_delete_button_width():
    return Styles.get_delete_button_width()


def get_rule_button_left_offset():
    return Styles.get_rule_button_left_offset()


def get_link_label_width():
    return Styles.get_link_label_width()


def get_info_container_height():
    return Styles.get_info_container_height()


def get_rules_container_height():
    return Styles.get_rules_container_height()


def get_rules_scrollview_height():
    return Styles.get_rules_scrollview_height()


def get_small_radius():
    return Styles.get_small_radius()


def get_medium_radius():
    return Styles.get_medium_radius()


def get_large_radius():
    return Styles.get_large_radius()


def get_extra_large_radius():
    return Styles.get_extra_large_radius()


def get_container_radius():
    return Styles.get_container_radius()


def get_scrollbar_width():
    return Styles.get_scrollbar_width()


def get_no_border():
    return Styles.get_no_border()


def get_thin_border():
    return Styles.get_thin_border()


def get_thick_border():
    return Styles.get_thick_border()


MAX_RULE_TEXT_LENGTH = Styles.MAX_RULE_TEXT_LENGTH
TRUNCATION_SUFFIX = Styles.TRUNCATION_SUFFIX


def get_rule_toggle_x_offset():
    return get_container_internal_padding() + get_small_spacing()


def get_rule_text_x_offset():
    return get_rule_toggle_x_offset() + CoordinateSystem.scale_int(16)


TRANSPARENT_COLOR = Styles.Transparent
DARK_CONTAINER_COLOR = Styles.DarkContainer
BORDER_COLOR = Styles.Border
MUTED_TEXT_COLOR = Styles.MutedText
DISABLED_TEXT_COLOR = Styles.DisabledText
ENABLED_TEXT_COLOR = Styles.EnabledText
WHITE_TEXT_COLOR = Styles.WhiteText
LINK_COLOR = Styles.Link
LINK_HOVER_COLOR = Styles.LinkHover
LINK_HOVER_BG_COLOR = Styles.LinkHoverBg
AUTH_MESSAGE_COLOR = Styles.AuthMessage
PRIMARY_BUTTON_COLOR = Styles.PrimaryButton
DISABLED_BUTTON_COLOR = Styles.DisabledButton
LOGOUT_BUTTON_COLOR = Styles.LogoutButton
LOGOUT_BUTTON_HOVER_COLOR = Styles.LogoutButtonHover
DELETE_BUTTON_COLOR = Styles.DeleteButton
DELETE_BUTTON_HOVER_COLOR = Styles.DeleteButtonHover
HOVER_BACKGROUND_COLOR = Styles.HoverBackground
EDITING_HIGHLIGHT_COLOR = Styles.EditingHighlight
TOGGLE_ENABLED_COLOR = Styles.ToggleEnabled
TOGGLE_DISABLED_COLOR = Styles.ToggleDisabled
TOGGLE_FILL_COLOR = Styles.ToggleFill
CHECKMARK_COLOR = Styles.Checkmark


def adjustCurrectY(current_y: int, height: int, spacing: int) -> int:
    return current_y - height - spacing


def get_go_back_button_offset():
    return Styles.get_go_back_button_offset()


def get_go_back_button_side_padding():
    return Styles.get_go_back_button_side_padding()


class ToggleIconButton(Button):

    def __init__(self, enabled: bool = True, x: int = 0, y: int = 0,
                 width: int = CoordinateSystem.scale_int(14), height: int = CoordinateSystem.scale_int(14),
                 on_click=None):
        super().__init__("", x, y, width, height, corner_radius=0, on_click=on_click)

        self.enabled_state = enabled
        self.visible = True

        self.enabled_icon = ImageComponent(
            image_path="toggle-filled.png",
            x=x,
            y=y + (height - CoordinateSystem.scale_int(14)) // 2,
            width=CoordinateSystem.scale_int(14),
            height=CoordinateSystem.scale_int(14),
        )

        self.disabled_icon = ImageComponent(
            image_path="toggle-outline.png",
            x=x,
            y=y + (height - CoordinateSystem.scale_int(14)) // 2,
            width=CoordinateSystem.scale_int(14),
            height=CoordinateSystem.scale_int(14),
        )

        self.style.background_color = TRANSPARENT_COLOR
        self.style.border_width = get_no_border()
        self.style.hover_background_color = TRANSPARENT_COLOR
        self.style.focus_background_color = TRANSPARENT_COLOR
        self.style.pressed_background_color = TRANSPARENT_COLOR

    def set_enabled_state(self, enabled: bool):

        self.enabled_state = enabled

    def set_position(self, x: int, y: int):

        super().set_position(x, y)

        icon_y = y + (self.bounds.height - CoordinateSystem.scale_int(14)) // 2
        self.enabled_icon.set_position(x, icon_y)
        self.disabled_icon.set_position(x, icon_y)

    def set_size(self, width: int, height: int):

        super().set_size(width, height)

        self.enabled_icon.set_size(CoordinateSystem.scale_int(14), CoordinateSystem.scale_int(14))
        self.disabled_icon.set_size(CoordinateSystem.scale_int(14), CoordinateSystem.scale_int(14))

        icon_y = self.bounds.y + (height - CoordinateSystem.scale_int(14)) // 2
        self.enabled_icon.set_position(self.bounds.x, icon_y)
        self.disabled_icon.set_position(self.bounds.x, icon_y)

    def _render_simple_icon(self, renderer, enabled_state):

        bounds = self.bounds

        border_color = TOGGLE_ENABLED_COLOR if enabled_state else TOGGLE_DISABLED_COLOR
        fill_color = TOGGLE_FILL_COLOR if enabled_state else TRANSPARENT_COLOR

        renderer.draw_rounded_rect(bounds, border_color, get_large_radius())

        if enabled_state and fill_color[3] > 0:
            inner_bounds = Bounds(
                bounds.x + get_thick_border(), bounds.y + get_thick_border(),
                bounds.width - (get_thick_border() * 2), bounds.height - (get_thick_border() * 2)
            )
            renderer.draw_rounded_rect(inner_bounds, fill_color, get_medium_radius())

        if enabled_state:
            check_size = min(bounds.width, bounds.height) // 3
            check_x = bounds.x + bounds.width // 2 - check_size // 2
            check_y = bounds.y + bounds.height // 2 - check_size // 2

            check_bounds = Bounds(check_x, check_y, check_size, check_size // 2)
            renderer.draw_rect(check_bounds, CHECKMARK_COLOR)

    def render(self, renderer):

        if not self.visible:
            return

        self._update_pressed_state()

        if self.is_hovered or self.is_pressed:
            if self.corner_radius > 0:
                renderer.draw_rounded_rect(self.bounds, TRANSPARENT_COLOR, self.corner_radius)
            else:
                renderer.draw_rect(self.bounds, TRANSPARENT_COLOR)

        icon_y = self.bounds.y + (self.bounds.height - CoordinateSystem.scale_int(14)) // 2
        self.enabled_icon.set_position(self.bounds.x, icon_y)
        self.disabled_icon.set_position(self.bounds.x, icon_y)

        current_icon = self.enabled_icon if self.enabled_state else self.disabled_icon

        if not current_icon.image_loaded and current_icon._texture_creation_attempted:
            current_icon._texture_creation_attempted = False

        if not current_icon.image_loaded and not current_icon._texture_creation_attempted:

            if not current_icon.image_data:
                current_icon._load_image_data()

            is_valid = current_icon._is_image_data_valid()

            if is_valid:
                try:

                    success = self._create_texture_with_fallback(current_icon)
                    if success:
                        current_icon._texture_creation_attempted = True
                    else:
                        logger.error(f"All fallback methods failed for {current_icon.image_path}")
                        current_icon._texture_creation_attempted = True
                except Exception as e:
                    logger.error(f"Exception during fallback texture creation for {current_icon.image_path}: {e}")
                    current_icon._texture_creation_attempted = True
            else:
                logger.warning(f"Image data not valid for {current_icon.image_path}, skipping texture creation")
                current_icon._texture_creation_attempted = True

        if current_icon.image_loaded and current_icon.image_texture:
            try:

                render_bounds = current_icon.bounds
                texture_coords = (0.0, 0.0, 1.0, 1.0)

                renderer.draw_textured_rect(
                    x=render_bounds.x,
                    y=render_bounds.y,
                    width=render_bounds.width,
                    height=render_bounds.height,
                    texture=current_icon.image_texture,
                    texture_coords=texture_coords
                )
            except Exception as e:
                logger.error(f"Error rendering texture for {current_icon.image_path}: {e}")

                self._render_simple_icon(renderer, self.enabled_state)
        else:

            self._render_simple_icon(renderer, self.enabled_state)

    def cleanup(self):

        if self.enabled_icon:
            self.enabled_icon.cleanup()
        if self.disabled_icon:
            self.disabled_icon.cleanup()

    def _create_texture_with_fallback(self, icon_component):

        if not icon_component._is_image_data_valid():
            logger.warning(f"Image data not valid for {icon_component.image_path}")
            return False

        try:
            import array

            width = icon_component.image_data.size[0]
            height = icon_component.image_data.size[1]

            pixel_data = list(icon_component.image_data.pixels)

            if icon_component.tint_color:
                tinted_pixels = []
                for i in range(0, len(pixel_data), 4):
                    r, g, b, a = pixel_data[i:i + 4]
                    tinted_pixels.extend([
                        r * icon_component.tint_color[0],
                        g * icon_component.tint_color[1],
                        b * icon_component.tint_color[2],
                        a * icon_component.tint_color[3]
                    ])
                pixel_data = tinted_pixels

            if icon_component.opacity < 1.0:
                for i in range(3, len(pixel_data), 4):
                    pixel_data[i] *= icon_component.opacity

            formats_to_try = [
                ('RGBA32F', 'float'),
            ]

            for format_name, data_type in formats_to_try:
                try:
                    if data_type == 'float':

                        pixel_buffer = array.array('f', pixel_data)
                        gpu_buffer = gpu.types.Buffer('FLOAT', len(pixel_buffer), pixel_buffer)
                    else:

                        byte_data = [int(max(0, min(255, p * 255))) for p in pixel_data]
                        pixel_buffer = array.array('B', byte_data)
                        gpu_buffer = gpu.types.Buffer('UBYTE', len(pixel_buffer), pixel_buffer)

                    texture = gpu.types.GPUTexture(
                        size=(width, height),
                        format=format_name,
                        data=gpu_buffer
                    )

                    if texture:
                        icon_component.image_texture = texture
                        icon_component.image_loaded = True
                        return True
                    else:
                        logger.warning(f"Texture creation returned None for format {format_name}")
                        continue

                except Exception as format_error:
                    logger.warning(
                    )
                    continue

            logger.error(f"All texture formats failed for {icon_component.image_path}")
            return False

        except Exception as e:
            logger.error(f"Error in texture creation fallback for {icon_component.image_path}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False


class SettingsView(BaseView):

    def __init__(self):
        super().__init__()
        self.refresh_callback = None
        self.is_fetching_usage = False
        self.usage_data_fetched = False

    def create_layout(self, viewport_width: int, viewport_height: int) -> Dict[str, Any]:

        layouts = {}
        components = {}

        context = bpy.context
        is_authenticated = getattr(context.window_manager, 'vibe4d_authenticated', False)
        user_email = getattr(context.window_manager, 'vibe4d_user_email', '')
        user_plan = getattr(context.window_manager, 'vibe4d_user_plan', '')

        try:
            from ....utils.instructions_manager import instruction_manager
            from ....utils.storage import secure_storage

            current_instruction_in_scene = getattr(context.scene, 'vibe4d_custom_instruction', '')

            if not current_instruction_in_scene:

                saved_instruction = secure_storage.load_custom_instruction()
                if saved_instruction:
                    context.scene.vibe4d_custom_instruction = str(saved_instruction)
                    logger.info(
                    )
                else:
                    logger.debug("No saved custom instruction found in storage")
            else:
                logger.debug(
                )
        except Exception as e:
            logger.error(f"Failed to load custom instructions for settings view: {e}")

        current_usage = getattr(context.window_manager, 'vibe4d_current_usage', 0)
        usage_limit = getattr(context.window_manager, 'vibe4d_usage_limit', 100)

        if is_authenticated and not self.usage_data_fetched and not self.is_fetching_usage:
            self.usage_data_fetched = True
            self._fetch_usage_data_async()

        main_layout = self._create_layout_container(
        ,
        LayoutConfig(
            strategy=LayoutStrategy.ABSOLUTE,
            padding_top=get_container_internal_padding(),
            padding_right=get_container_internal_padding(),
            padding_bottom=get_container_internal_padding(),
            padding_left=get_container_internal_padding()
        )
        )
        layouts['main'] = main_layout

        side_padding = get_go_back_button_side_padding()
        top_offset = get_go_back_button_offset()

        go_back_button = BackButton(side_padding, 0, on_click=self._handle_go_back)

        button_y = viewport_height - top_offset - go_back_button.bounds.height
        go_back_button.set_position(side_padding, button_y)
        components['go_back_button'] = go_back_button

        content_start_y = button_y - get_small_spacing()
        current_y = content_start_y

        if is_authenticated and user_email:

            user_name = user_email.split('@')[0] if '@' in user_email else user_email

            name_label = Label(user_name, get_left_margin(), current_y, get_name_label_width(), get_label_height())
            name_label.style = get_themed_component_style("title")
            name_label.style.font_size = get_font_size()
            name_label.set_text_align("left")
            components['name_label'] = name_label

            current_y = adjustCurrectY(current_y, get_label_height(),
                                       CoordinateSystem.scale_int(6))

            plan_name = getattr(context.window_manager, 'vibe4d_plan_name', '')
            if plan_name:
                plan_display = plan_name
            else:
                plan_display = user_plan.title() if user_plan else "Free"
            plan_text = f"Plan: {plan_display}"
            plan_label = Label(plan_text, get_left_margin(), current_y, get_plan_label_width(), get_label_height())
            plan_label.style = get_themed_component_style("label")
            plan_label.style.font_size = get_font_size()
            plan_label.style.text_color = MUTED_TEXT_COLOR
            plan_label.set_text_align("left")
            components['plan_label'] = plan_label

            current_y = adjustCurrectY(current_y, get_label_height(),
                                       CoordinateSystem.scale_int(8))

            info_container = Container(get_left_margin(), current_y - get_info_container_height(),
                                       viewport_width - get_left_margin() - get_right_margin(),
                                       get_info_container_height())
            info_container.style.background_color = get_theme_color('bg_panel')
            info_container.style.border_color = BORDER_COLOR
            info_container.style.border_width = get_thin_border()
            info_container.corner_radius = get_container_radius()
            components['info_container'] = info_container

            info_current_y = current_y - get_container_internal_padding()

            email_label = Label(user_email, get_left_margin() + get_container_internal_padding(), info_current_y,
                                viewport_width - get_left_margin() - get_right_margin() - (
                                        get_container_internal_padding() * 2), get_small_label_height())
            email_label.style = get_themed_component_style("label")
            email_label.style.font_size = get_font_size()
            email_label.set_text_align("left")
            components['email_label'] = email_label

            info_current_y = adjustCurrectY(info_current_y, get_small_label_height(),
                                            CoordinateSystem.scale_int(8))

            if current_usage == 0 and usage_limit == 0:
                usage_text = "Usages left: loading..."
            else:
                usage_text = f"Usages left: {usage_limit - current_usage}/{usage_limit}"
            usage_label = Label(usage_text, get_left_margin() + get_container_internal_padding(), info_current_y,
                                viewport_width - get_left_margin() - get_right_margin() - (
                                        get_container_internal_padding() * 2), get_small_label_height())
            usage_label.style = get_themed_component_style("label")
            usage_label.style.font_size = get_font_size()
            usage_label.set_text_align("left")
            components['usage_label'] = usage_label

            info_current_y = adjustCurrectY(info_current_y, get_small_label_height(),
                                            CoordinateSystem.scale_int(8))

            manage_sub_label = Label("Manage subscription ↗", get_left_margin() + get_container_internal_padding(),
                                     info_current_y,
                                     get_manage_sub_label_width(), get_small_label_height())
            manage_sub_label.style = get_themed_component_style("label")
            manage_sub_label.style.text_color = get_theme_color('text_muted')
            manage_sub_label.style.font_size = get_font_size()
            manage_sub_label.set_text_align("left")
            manage_sub_label.add_text_segment(
                0, len("Manage subscription ↗"),
                hover_style_name="link_hover",
                clickable=True,
                hoverable=True,
                on_click=self._handle_manage_subscription,
                on_hover_start=self._handle_link_hover_start,
                on_hover_end=self._handle_link_hover_end
            )
            manage_sub_label.add_highlight_style("link_hover",
                                                 background_color=LINK_HOVER_BG_COLOR,
                                                 text_color=get_theme_color('text_selected'))
            components['manage_sub_label'] = manage_sub_label

            info_current_y = adjustCurrectY(info_current_y, get_small_label_height(),
                                            CoordinateSystem.scale_int(8))

            logout_button = Button("Log out", get_left_margin() + get_container_internal_padding(), info_current_y,
                                   get_logout_button_width(), get_large_button_height(),
                                   corner_radius=get_extra_large_radius(), on_click=self._handle_logout)
            logout_button.style.background_color = LOGOUT_BUTTON_COLOR
            logout_button.style.text_color = ENABLED_TEXT_COLOR
            logout_button.style.hover_background_color = LOGOUT_BUTTON_HOVER_COLOR
            logout_button.style.font_size = get_font_size()
            components['logout_button'] = logout_button

            current_y = adjustCurrectY(current_y, get_info_container_height(), get_big_spacing())

            instruction_section_title = Label("Custom instruction", get_left_margin(), current_y,
                                              get_plan_label_width(), get_label_height())
            instruction_section_title.style = get_themed_component_style("title")
            instruction_section_title.style.font_size = get_font_size()
            instruction_section_title.set_text_align("left")
            components['instruction_section_title'] = instruction_section_title

            current_y = adjustCurrectY(current_y, get_label_height(), get_small_spacing())

            instruction_container_height = CoordinateSystem.scale_int(140)
            instruction_container = Container(get_left_margin(), current_y - instruction_container_height,
                                              viewport_width - get_left_margin() - get_right_margin(),
                                              instruction_container_height)
            instruction_container.style.background_color = get_theme_color('bg_panel')
            instruction_container.style.border_color = BORDER_COLOR
            instruction_container.style.border_width = get_thin_border()
            instruction_container.corner_radius = get_container_radius()
            components['instruction_container'] = instruction_container

            current_instruction = getattr(context.scene, 'vibe4d_custom_instruction', '')

            instruction_current_y = current_y - get_container_internal_padding()
            instruction_input_height = instruction_container_height - (get_container_internal_padding() * 2)

            instruction_input = TextInput(
                x=get_left_margin() + get_container_internal_padding(),
                y=instruction_current_y - instruction_input_height,
                width=viewport_width - get_left_margin() - get_right_margin() - (get_container_internal_padding() * 2),
                height=instruction_input_height,
                placeholder="Type your custom instructions here...",
                multiline=True,
                auto_resize=False,
            )
            instruction_input.set_text(current_instruction)
            instruction_input.on_change = self._handle_instruction_text_change
            instruction_input.style = get_themed_component_style("input")
            instruction_input.style.font_size = get_font_size()
            instruction_input.style.background_color = TRANSPARENT_COLOR
            instruction_input.style.border_color = TRANSPARENT_COLOR
            instruction_input.style.border_width = 0
            instruction_input.style.focus_background_color = TRANSPARENT_COLOR
            instruction_input.style.focus_border_color = TRANSPARENT_COLOR
            instruction_input.style.focus_border_width = 0
            instruction_input.corner_radius = 0
            components['instruction_input'] = instruction_input

            current_y = adjustCurrectY(current_y, instruction_container_height, get_big_spacing())

            # --- LLM Provider Configuration Section ---
            provider_section_title = Label("LLM Provider", get_left_margin(), current_y,
                                           get_plan_label_width(), get_label_height())
            provider_section_title.style = get_themed_component_style("title")
            provider_section_title.style.font_size = get_font_size()
            provider_section_title.set_text_align("left")
            components['provider_section_title'] = provider_section_title

            current_y = adjustCurrectY(current_y, get_label_height(), get_small_spacing())

            # Provider selection label
            current_provider = getattr(context.scene, 'vibe4d_provider', 'openai')
            provider_display_names = {
                'vibe4d': 'Vibe4D (Cloud)',
                'openai': 'OpenAI / ChatGPT',
                'local': 'Local LLM (Ollama, LM Studio, etc.)'
            }
            provider_display = provider_display_names.get(current_provider, current_provider)

            # Provider buttons container
            provider_container_height = CoordinateSystem.scale_int(130)
            provider_container = Container(get_left_margin(), current_y - provider_container_height,
                                           viewport_width - get_left_margin() - get_right_margin(),
                                           provider_container_height)
            provider_container.style.background_color = get_theme_color('bg_panel')
            provider_container.style.border_color = BORDER_COLOR
            provider_container.style.border_width = get_thin_border()
            provider_container.corner_radius = get_container_radius()
            components['provider_container'] = provider_container

            provider_inner_y = current_y - get_container_internal_padding()

            # Provider type label
            provider_type_label = Label(f"Active: {provider_display}",
                                        get_left_margin() + get_container_internal_padding(),
                                        provider_inner_y - get_label_height(),
                                        viewport_width - get_left_margin() - get_right_margin() - (get_container_internal_padding() * 2),
                                        get_label_height())
            provider_type_label.style = get_themed_component_style("label")
            provider_type_label.style.font_size = get_font_size()
            provider_type_label.set_text_align("left")
            components['provider_type_label'] = provider_type_label

            provider_inner_y = provider_inner_y - get_label_height() - get_small_spacing()

            # Provider selection buttons
            button_width = CoordinateSystem.scale_int(90)
            button_height = CoordinateSystem.scale_int(24)
            button_x = get_left_margin() + get_container_internal_padding()
            button_spacing = CoordinateSystem.scale_int(8)

            for provider_id, provider_name in [('openai', 'OpenAI'), ('local', 'Local'), ('vibe4d', 'Vibe4D')]:
                is_active = (current_provider == provider_id)
                btn = Button(provider_name, button_x, provider_inner_y - button_height,
                             button_width, button_height)
                btn.style = get_themed_component_style("button")
                btn.style.font_size = get_font_size()
                if is_active:
                    btn.style.background_color = get_theme_color('text_selected')
                    btn.style.text_color = get_theme_color('bg_base')
                btn.on_click = lambda pid=provider_id: self._handle_provider_change(pid)
                components[f'provider_btn_{provider_id}'] = btn
                button_x += button_width + button_spacing

            provider_inner_y = provider_inner_y - button_height - get_small_spacing()

            # Provider model input
            current_provider_model = getattr(context.scene, 'vibe4d_provider_model', '')
            if current_provider == 'openai':
                model_placeholder = "gpt-4o-mini"
            elif current_provider == 'local':
                model_placeholder = "llama3"
            else:
                model_placeholder = "gpt-5-mini"

            model_label = Label("Model:", get_left_margin() + get_container_internal_padding(),
                                provider_inner_y - get_small_label_height(),
                                CoordinateSystem.scale_int(50), get_small_label_height())
            model_label.style = get_themed_component_style("label")
            model_label.style.font_size = get_font_size()
            model_label.set_text_align("left")
            components['provider_model_label'] = model_label

            model_input_x = get_left_margin() + get_container_internal_padding() + CoordinateSystem.scale_int(55)
            model_input = TextInput(
                x=model_input_x,
                y=provider_inner_y - get_small_label_height(),
                width=viewport_width - model_input_x - get_right_margin() - get_container_internal_padding(),
                height=get_small_label_height(),
                placeholder=model_placeholder,
                multiline=False,
                auto_resize=False,
            )
            model_input.set_text(current_provider_model)
            model_input.on_change = self._handle_provider_model_change
            model_input.style = get_themed_component_style("input")
            model_input.style.font_size = get_font_size()
            model_input.style.background_color = get_theme_color('bg_panel')
            model_input.style.border_color = BORDER_COLOR
            model_input.style.border_width = get_thin_border()
            model_input.corner_radius = CoordinateSystem.scale_int(4)
            components['provider_model_input'] = model_input

            current_y = adjustCurrectY(current_y, provider_container_height, get_small_spacing())

            # API Key input (for OpenAI provider)
            if current_provider in ('openai',):
                api_key_label = Label("API Key:", get_left_margin(), current_y - get_small_label_height(),
                                      viewport_width - get_left_margin() - get_right_margin(), get_small_label_height())
                api_key_label.style = get_themed_component_style("label")
                api_key_label.style.font_size = get_font_size()
                api_key_label.set_text_align("left")
                components['api_key_label'] = api_key_label

                current_y = adjustCurrectY(current_y, get_small_label_height(), CoordinateSystem.scale_int(2))

                current_api_key = getattr(context.scene, 'vibe4d_provider_api_key', '')
                api_key_display = ('•' * min(len(current_api_key), 20)) if current_api_key else ''

                api_key_input = TextInput(
                    x=get_left_margin(),
                    y=current_y - get_small_label_height(),
                    width=viewport_width - get_left_margin() - get_right_margin(),
                    height=get_small_label_height(),
                    placeholder="sk-... (your OpenAI API key)",
                    multiline=False,
                    auto_resize=False,
                )
                api_key_input.set_text(api_key_display)
                api_key_input.on_change = self._handle_api_key_change
                api_key_input.style = get_themed_component_style("input")
                api_key_input.style.font_size = get_font_size()
                api_key_input.style.background_color = get_theme_color('bg_panel')
                api_key_input.style.border_color = BORDER_COLOR
                api_key_input.style.border_width = get_thin_border()
                api_key_input.corner_radius = CoordinateSystem.scale_int(4)
                components['api_key_input'] = api_key_input

                current_y = adjustCurrectY(current_y, get_small_label_height(), get_small_spacing())

            # Base URL input (for local/openai providers)
            if current_provider in ('openai', 'local'):
                base_url_label = Label("Base URL:", get_left_margin(), current_y - get_small_label_height(),
                                       viewport_width - get_left_margin() - get_right_margin(), get_small_label_height())
                base_url_label.style = get_themed_component_style("label")
                base_url_label.style.font_size = get_font_size()
                base_url_label.set_text_align("left")
                components['base_url_label'] = base_url_label

                current_y = adjustCurrectY(current_y, get_small_label_height(), CoordinateSystem.scale_int(2))

                current_base_url = getattr(context.scene, 'vibe4d_provider_base_url', '')
                if current_provider == 'local':
                    url_placeholder = "http://localhost:11434/v1"
                else:
                    url_placeholder = "https://api.openai.com/v1"

                base_url_input = TextInput(
                    x=get_left_margin(),
                    y=current_y - get_small_label_height(),
                    width=viewport_width - get_left_margin() - get_right_margin(),
                    height=get_small_label_height(),
                    placeholder=url_placeholder,
                    multiline=False,
                    auto_resize=False,
                )
                base_url_input.set_text(current_base_url)
                base_url_input.on_change = self._handle_base_url_change
                base_url_input.style = get_themed_component_style("input")
                base_url_input.style.font_size = get_font_size()
                base_url_input.style.background_color = get_theme_color('bg_panel')
                base_url_input.style.border_color = BORDER_COLOR
                base_url_input.style.border_width = get_thin_border()
                base_url_input.corner_radius = CoordinateSystem.scale_int(4)
                components['base_url_input'] = base_url_input

                current_y = adjustCurrectY(current_y, get_small_label_height(), get_small_spacing())

            # Provider info help text
            if current_provider == 'openai':
                help_text = "Get your API key at platform.openai.com"
            elif current_provider == 'local':
                help_text = "Start Ollama/LM Studio, then use its API URL"
            else:
                help_text = "Uses Vibe4D cloud (requires license key)"

            provider_help = Label(help_text, get_left_margin(), current_y - get_small_label_height(),
                                  viewport_width - get_left_margin() - get_right_margin(), get_small_label_height())
            provider_help.style = get_themed_component_style("label")
            provider_help.style.text_color = get_theme_color('text_muted')
            provider_help.style.font_size = get_font_size()
            provider_help.set_text_align("left")
            components['provider_help'] = provider_help

            current_y = adjustCurrectY(current_y, get_small_label_height(), get_big_spacing())
            # --- End LLM Provider Section ---
        else:
            auth_message = Label("Please authenticate to access settings", get_left_margin(), current_y,
                                 viewport_width - get_left_margin() - get_right_margin(), get_label_height())
            auth_message.style = get_themed_component_style("label")
            auth_message.style.text_color = AUTH_MESSAGE_COLOR
            auth_message.style.font_size = get_font_size()
            auth_message.set_text_align("left")
            components['auth_message'] = auth_message
            current_y = adjustCurrectY(current_y, get_label_height(), get_big_spacing())

        links_section_title = Label("Vibe4D links", get_left_margin(), current_y, get_plan_label_width(),
                                    get_label_height())
        links_section_title.style = get_themed_component_style("title")
        links_section_title.style.font_size = get_font_size()
        links_section_title.set_text_align("left")
        components['links_section_title'] = links_section_title

        current_y = adjustCurrectY(current_y, get_label_height(), get_small_spacing())

        links = [
            ("Github ↗", self._handle_open_github),
            ("Website ↗", self._handle_open_website),
            ("Twitter (X) ↗", self._handle_open_twitter),
            ("Discord ↗", self._handle_open_discord)
        ]

        for i, (link_text, handler) in enumerate(links):
            link_label = Label(link_text, get_left_margin(), current_y, get_link_label_width(),
                               get_small_label_height())
            link_label.style = get_themed_component_style("label")
            link_label.style.text_color = get_theme_color('text_muted')
            link_label.style.font_size = get_font_size()
            link_label.set_text_align("left")
            link_label.add_text_segment(
                0, len(link_text),
                hover_style_name="link_hover",
                clickable=True,
                hoverable=True,
                on_click=handler,
                on_hover_start=self._handle_link_hover_start,
                on_hover_end=self._handle_link_hover_end
            )
            link_label.add_highlight_style("link_hover",
                                           background_color=TRANSPARENT_COLOR,
                                           text_color=get_theme_color('text_selected'))
            components[f'link_{i}'] = link_label
            current_y = adjustCurrectY(current_y, get_small_label_height(), get_link_spacing())

        self.components = components
        self.layouts = layouts

        return {
        :layouts,
        : components,
        :self._get_all_components()
        }

        def update_layout(self, viewport_width: int, viewport_height: int):

            if 'go_back_button' in self.components:
                go_back_button = self.components['go_back_button']
                side_padding = get_go_back_button_side_padding()
                top_offset = get_go_back_button_offset()
                button_y = viewport_height - top_offset - go_back_button.bounds.height
                go_back_button.set_position(side_padding, button_y)

                content_start_y = button_y - get_small_spacing()
                current_y = content_start_y
            else:
                current_y = viewport_height

            current_y -= get_big_spacing()

            if 'name_label' in self.components:
                self.components['name_label'].set_position(get_left_margin(), current_y)
                self.components['name_label'].set_size(get_name_label_width(), get_label_height())

            current_y = adjustCurrectY(current_y, get_label_height(), CoordinateSystem.scale_int(6))

            if 'plan_label' in self.components:
                self.components['plan_label'].set_position(get_left_margin(), current_y)
                self.components['plan_label'].set_size(get_plan_label_width(), get_label_height())

            current_y = adjustCurrectY(current_y, get_label_height(), CoordinateSystem.scale_int(-4))

            if 'info_container' in self.components:
                self.components['info_container'].set_position(get_left_margin(),
                                                               current_y - get_info_container_height())
                self.components['info_container'].set_size(viewport_width - get_left_margin() - get_right_margin(),
                                                           get_info_container_height())

            info_current_y = current_y - get_container_internal_padding() - CoordinateSystem.scale_int(12)

            if 'email_label' in self.components:
                self.components['email_label'].set_position(get_left_margin() + get_container_internal_padding(),
                                                            info_current_y)
                self.components['email_label'].set_size(
                    viewport_width - get_left_margin() - get_right_margin() - (get_container_internal_padding() * 2),
                    get_small_label_height())

            info_current_y = adjustCurrectY(info_current_y, get_small_label_height(),
                                            CoordinateSystem.scale_int(8))

            if 'usage_label' in self.components:
                self.components['usage_label'].set_position(get_left_margin() + get_container_internal_padding(),
                                                            info_current_y)
                self.components['usage_label'].set_size(
                    viewport_width - get_left_margin() - get_right_margin() - (get_container_internal_padding() * 2),
                    get_small_label_height())

            info_current_y = adjustCurrectY(info_current_y, get_small_label_height(),
                                            CoordinateSystem.scale_int(8))

            if 'manage_sub_label' in self.components:
                self.components['manage_sub_label'].set_position(get_left_margin() + get_container_internal_padding(),
                                                                 info_current_y)
                self.components['manage_sub_label'].set_size(
                    viewport_width - get_left_margin() - get_right_margin() - (get_container_internal_padding() * 2),
                    get_small_label_height())

            info_current_y = adjustCurrectY(info_current_y, get_small_label_height() + CoordinateSystem.scale_int(12),
                                            CoordinateSystem.scale_int(8))

            if 'logout_button' in self.components:
                self.components['logout_button'].set_position(get_left_margin() + get_container_internal_padding(),
                                                              info_current_y)
                self.components['logout_button'].set_size(get_logout_button_width(), get_small_button_height())

            current_y = adjustCurrectY(current_y, get_info_container_height() + CoordinateSystem.scale_int(12),
                                       get_big_spacing())

            if 'instruction_section_title' in self.components:
                self.components['instruction_section_title'].set_position(get_left_margin(), current_y)
                self.components['instruction_section_title'].set_size(get_plan_label_width(), get_label_height())

            current_y = adjustCurrectY(current_y, get_label_height() - CoordinateSystem.scale_int(12),
                                       get_small_spacing())

            instruction_container_height = CoordinateSystem.scale_int(140)
            if 'instruction_container' in self.components:
                self.components['instruction_container'].set_position(get_left_margin(),
                                                                      current_y - instruction_container_height)
                self.components['instruction_container'].set_size(
                    viewport_width - get_left_margin() - get_right_margin(),
                    instruction_container_height)

            if 'instruction_input' in self.components:
                instruction_current_y = current_y - get_container_internal_padding()
                instruction_input_height = instruction_container_height - (get_container_internal_padding() * 2)

                self.components['instruction_input'].set_position(
                    get_left_margin() + get_container_internal_padding(),
                    instruction_current_y - instruction_input_height
                )
                self.components['instruction_input'].set_size(
                    viewport_width - get_left_margin() - get_right_margin() - (get_container_internal_padding() * 2),
                    instruction_input_height
                )

            current_y = adjustCurrectY(current_y, instruction_container_height + CoordinateSystem.scale_int(12),
                                       get_big_spacing())

            if 'links_section_title' in self.components:
                self.components['links_section_title'].set_position(get_left_margin(), current_y)
                self.components['links_section_title'].set_size(get_plan_label_width(), get_label_height())

            current_y = adjustCurrectY(current_y, get_label_height(), get_small_spacing())

            for i in range(4):
                if f'link_{i}' in self.components:
                    self.components[f'link_{i}'].set_position(get_left_margin(), current_y)
                    current_y = adjustCurrectY(current_y, get_small_label_height(), get_link_spacing())

        def _handle_go_back(self):

            if self.callbacks.get('on_go_back'):
                self.callbacks['on_go_back']()
            else:

                if self.callbacks.get('on_view_change'):
                    from ..ui_factory import ViewState
                    self.callbacks['on_view_change'](ViewState.MAIN)

        def _handle_manage_subscription(self, segment):

            try:
                bpy.ops.vibe4d.manage_subscription()
            except Exception as e:
                logger.error(f"Error opening subscription management: {e}")

        def _handle_logout(self):

            try:
                bpy.ops.vibe4d.logout()

                if self.callbacks.get('on_view_change'):
                    from ..ui_factory import ViewState
                    self.callbacks['on_view_change'](ViewState.AUTH)
            except Exception as e:
                logger.error(f"Error during logout: {e}")

        def _handle_instruction_text_change(self, new_text):

            try:
                context = bpy.context

                context.scene.vibe4d_custom_instruction = new_text

                from ....utils.instructions_manager import instruction_manager
                instruction_manager.force_save_instruction(context)

            except Exception as e:
                logger.error(f"Error handling instruction text change: {e}")

        def _handle_provider_change(self, provider_id):
            """Handle provider selection change."""
            try:
                context = bpy.context
                context.scene.vibe4d_provider = provider_id

                from ....utils.settings_manager import settings_manager
                settings_manager.auto_save_settings(context)

                logger.info(f"LLM provider changed to: {provider_id}")

                # Refresh the settings view to show relevant fields
                if self.refresh_callback:
                    self.refresh_callback()

            except Exception as e:
                logger.error(f"Error changing provider: {e}")

        def _handle_api_key_change(self, new_text):
            """Handle API key input change."""
            try:
                context = bpy.context
                # Only save if it's not the masked display
                if new_text and not all(c == '•' for c in new_text):
                    context.scene.vibe4d_provider_api_key = new_text

                    from ....utils.settings_manager import settings_manager
                    settings_manager.auto_save_settings(context)

            except Exception as e:
                logger.error(f"Error saving API key: {e}")

        def _handle_base_url_change(self, new_text):
            """Handle base URL input change."""
            try:
                context = bpy.context
                context.scene.vibe4d_provider_base_url = new_text

                from ....utils.settings_manager import settings_manager
                settings_manager.auto_save_settings(context)

            except Exception as e:
                logger.error(f"Error saving base URL: {e}")

        def _handle_provider_model_change(self, new_text):
            """Handle provider model input change."""
            try:
                context = bpy.context
                context.scene.vibe4d_provider_model = new_text

                from ....utils.settings_manager import settings_manager
                settings_manager.auto_save_settings(context)

            except Exception as e:
                logger.error(f"Error saving provider model: {e}")

        def _handle_open_github(self, segment):

            try:
                import webbrowser
                webbrowser.open("https://github.com/emalakai/vibe4d-blender")
            except Exception as e:
                logger.error(f"Error opening GitHub: {e}")

        def _handle_open_website(self, segment):

            try:
                bpy.ops.vibe4d.open_website()
            except Exception as e:
                logger.error(f"Error opening website: {e}")

        def _handle_open_discord(self, segment):

            try:
                bpy.ops.vibe4d.open_discord()
            except Exception as e:
                logger.error(f"Error opening Discord: {e}")

        def _handle_open_twitter(self, segment):

            try:
                import webbrowser
                webbrowser.open("https://x.com/thevibe4d")
            except Exception as e:
                logger.error(f"Error opening Twitter: {e}")

        def _handle_link_hover_start(self, segment):

            pass

        def _handle_link_hover_end(self, segment):

            pass

        def set_refresh_callback(self, callback):

            self.refresh_callback = callback

        def reset_usage_fetch_state(self):

            self.usage_data_fetched = False
            self.is_fetching_usage = False

        def _fetch_usage_data_async(self):

            if self.is_fetching_usage:
                logger.debug("Usage data fetch already in progress, skipping")
                return

            self.is_fetching_usage = True

            usage_thread = threading.Thread(target=self._fetch_usage_data)
            usage_thread.daemon = True
            usage_thread.start()

        def _fetch_usage_data(self):

            try:
                context = bpy.context

                user_id = getattr(context.window_manager, 'vibe4d_user_id', '')
                token = getattr(context.window_manager, 'vibe4d_user_token', '')

                if not user_id or not token:
                    logger.warning("Cannot fetch usage data - missing authentication credentials")
                    return

                try:
                    from ....api.client import api_client
                except ImportError:

                    from vibe4d.api.client import api_client

                logger.info("Fetching usage data from API")

                success, data_or_error = api_client.get_usage_info(user_id, token)

                def update_ui_on_main_thread():

                    try:
                        if success:

                            usage_data = data_or_error

                            if 'plan_id' in usage_data:
                                context.window_manager.vibe4d_user_plan = usage_data['plan_id']

                            if 'plan_name' in usage_data:
                                context.window_manager.vibe4d_plan_name = usage_data['plan_name']

                            if 'current_usage' in usage_data:
                                context.window_manager.vibe4d_current_usage = usage_data['current_usage']

                            if 'limit' in usage_data:
                                context.window_manager.vibe4d_usage_limit = usage_data['limit']

                            if 'limit_type' in usage_data:
                                context.window_manager.vibe4d_limit_type = usage_data['limit_type']

                            if 'plan_id' in usage_data:
                                context.window_manager.vibe4d_plan_id = usage_data['plan_id']

                            if 'plan_name' in usage_data:
                                context.window_manager.vibe4d_plan_name = usage_data['plan_name']

                            if 'allowed' in usage_data:
                                context.window_manager.vibe4d_allowed = usage_data['allowed']

                            if 'usage_percentage' in usage_data:
                                context.window_manager.vibe4d_usage_percentage = usage_data['usage_percentage']

                            if 'remaining_requests' in usage_data:
                                context.window_manager.vibe4d_remaining_requests = usage_data['remaining_requests']

                            logger.info(
                            )

                            try:
                                from ....auth.manager import auth_manager
                                auth_manager.save_auth_state(context)
                            except Exception as e:
                                logger.debug(f"Could not save auth state: {e}")

                            if self.refresh_callback:
                                self.refresh_callback()
                            else:

                                self._notify_ui_system_of_changes()

                        else:

                            error_msg = data_or_error.get('error', 'Unknown error')
                            logger.warning(f"Failed to fetch usage data: {error_msg}")




                    except Exception as e:
                        logger.error(f"Error updating UI with usage data: {e}")

                    return None

                bpy.app.timers.register(update_ui_on_main_thread, first_interval=0.1)

            except Exception as e:
                logger.error(f"Error fetching usage data: {e}")
            finally:
                self.is_fetching_usage = False

        def _notify_ui_system_of_changes(self):

            try:

                from ..components.component_registry import component_registry
                component_registry.process_updates()

                if self.refresh_callback:
                    self.refresh_callback()
                    logger.debug("Triggered view refresh via callback")
                    return

                from ..ui_factory import improved_ui_factory
                if improved_ui_factory and hasattr(improved_ui_factory, '_refresh_current_view'):
                    improved_ui_factory._refresh_current_view()
                    logger.debug("Triggered UI factory refresh")
                    return

                from ..manager import ui_manager
                if ui_manager and hasattr(ui_manager, 'state'):

                    for component in ui_manager.state.components:
                        if hasattr(component, '_render_dirty'):
                            component._render_dirty = True

                    logger.debug("Marked UI components as dirty")

            except Exception as e:
                logger.debug(f"Could not notify UI system: {e}")

        def _force_redraw(self):

            try:

                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        area.tag_redraw()

                if hasattr(bpy.context, 'area') and bpy.context.area:
                    bpy.context.area.tag_redraw()

                if hasattr(bpy.ops.wm, 'redraw_timer'):
                    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

                try:
                    bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
                except:
                    pass

            except Exception as e:
                logger.debug(f"Could not force redraw: {e}")
