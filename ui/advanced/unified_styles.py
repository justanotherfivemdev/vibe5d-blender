import logging
from typing import Tuple

from .blender_theme_integration import get_theme_color
from .coordinates import CoordinateSystem
from .style_types import Style

logger = logging.getLogger(__name__)


class StylesMeta(type):
    _COLOR_MAP = {
        'Primary': 'bg_primary',
        'Panel': 'bg_panel',
        'Selected': 'bg_selected',
        'Border': 'border',
        'Text': 'text',
        'TextSelected': 'text_selected',
        'TextMuted': 'text_muted',
        'MenuBg': 'bg_menu',
        'Menu': 'bg_menu',
        'Highlight': 'bg_selected',
    }

    def __getattr__(cls, name):
        if name in cls._COLOR_MAP:
            return get_theme_color(cls._COLOR_MAP[name])
        raise AttributeError(f"type object 'UnifiedStyles' has no attribute '{name}'")


class UnifiedStyles(metaclass=StylesMeta):
    Transparent: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    DarkContainer: Tuple[float, float, float, float] = (0.15, 0.15, 0.15, 1.0)
    MutedText: Tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0)
    DisabledText: Tuple[float, float, float, float] = (0.6, 0.6, 0.6, 1.0)
    EnabledText: Tuple[float, float, float, float] = (0.9, 0.9, 0.9, 1.0)
    WhiteText: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    Link: Tuple[float, float, float, float] = (0.4, 0.7, 1.0, 1.0)
    LinkHover: Tuple[float, float, float, float] = (0.6, 0.8, 1.0, 1.0)
    LinkHoverBg: Tuple[float, float, float, float] = (0.4, 0.7, 1.0, 0.2)
    AuthMessage: Tuple[float, float, float, float] = (1.0, 0.7, 0.4, 1.0)
    PrimaryButton: Tuple[float, float, float, float] = (0.4, 0.7, 1.0, 1.0)
    DisabledButton: Tuple[float, float, float, float] = (0.3, 0.3, 0.3, 1.0)
    LogoutButton: Tuple[float, float, float, float] = (0.25, 0.25, 0.25, 1.0)
    LogoutButtonHover: Tuple[float, float, float, float] = (0.35, 0.35, 0.35, 1.0)
    DeleteButton: Tuple[float, float, float, float] = (0.6, 0.2, 0.2, 1.0)
    DeleteButtonHover: Tuple[float, float, float, float] = (0.8, 0.3, 0.3, 1.0)
    HoverBackground: Tuple[float, float, float, float] = (0.2, 0.2, 0.2, 0.5)
    EditingHighlight: Tuple[float, float, float, float] = (0.4, 0.7, 1.0, 0.3)
    ToggleEnabled: Tuple[float, float, float, float] = (0.4, 0.7, 1.0, 1.0)
    ToggleDisabled: Tuple[float, float, float, float] = (0.6, 0.6, 0.6, 1.0)
    ToggleFill: Tuple[float, float, float, float] = (0.2, 0.5, 0.8, 0.8)
    Checkmark: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)

    @classmethod
    def get_base_font_size(cls) -> int:

        return int(11 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_font_size(cls, size_type: str = "default") -> int:

        base_size = cls.get_base_font_size()

        if size_type == "title":
            return base_size + int(4 * CoordinateSystem.get_ui_scale())
        elif size_type == "small":
            return int(base_size * 0.9)
        elif size_type == "large":
            return int(base_size * 1.2)
        else:
            return base_size

    @classmethod
    def get_input_area_height(cls) -> int:
        return int(32 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_header_height(cls) -> int:
        return int(32 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_viewport_margin(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_viewport_padding_small(cls) -> int:
        return int(10 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_container_padding(cls) -> int:
        return int(10 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_margin(cls) -> int:
        return int(5 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_min_button_margin(cls) -> int:
        return int(5 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_header_gap(cls) -> int:
        return int(10 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_gap(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_message_gap(cls) -> int:
        return int(12 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_same_role_message_gap(cls) -> int:

        return int(12 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_different_role_message_gap(cls) -> int:

        return int(16 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_message_padding(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_message_area_padding(cls) -> int:
        return int(10 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_header_vertical_margin(cls) -> int:
        return int(16 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_dropdown_width(cls) -> int:
        return int(150 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_dropdown_height(cls) -> int:
        return int(22 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_dropdown_corner_radius(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_dropdown_padding_horizontal(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_dropdown_padding_vertical(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_dropdown_icon_gap(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_header_padding_horizontal(cls) -> int:
        return int(12 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_header_padding_vertical(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_header_icon_button_size(cls) -> int:
        return int(22 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_header_icon_button_corner_radius(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_header_icon_button_spacing(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_header_icon_size(cls) -> int:
        return int(14 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_send_button_size(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_send_button_corner_radius(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_send_button_icon_size(cls) -> int:
        return int(14 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_send_button_spacing(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_text_input_margin(cls) -> int:
        return int(12 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_text_input_max_height(cls) -> int:
        return int(280 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_min_message_height(cls) -> int:
        return int(100 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_scrollbar_buffer(cls) -> int:
        return int(40 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_corner_radius(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_text_input_corner_radius(cls) -> int:
        return int(8 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_text_input_padding(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_text_input_border_width(cls) -> int:
        return int(1 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_text_input_content_padding_left(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_text_input_content_padding_right_offset(cls) -> int:
        return int(8 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_message_border_width(cls) -> int:
        return int(1 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_container_height(cls) -> int:
        return int(40 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_container_width_estimate(cls) -> int:
        return int(200 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_left_margin(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_right_margin(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_container_internal_padding(cls) -> int:
        return int(8 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_scrollview_internal_margin(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_scrollview_content_padding(cls) -> int:
        return int(12 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_big_spacing(cls) -> int:
        return int(24 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_small_spacing(cls) -> int:
        return int(8 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_medium_spacing(cls) -> int:
        return int(12 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_rule_spacing(cls) -> int:
        return int(26 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_link_spacing(cls) -> int:
        return int(8 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_bottom_padding(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_height(cls) -> int:
        return int(24 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_large_button_height(cls) -> int:
        return int(24 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_small_button_height(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_label_height(cls) -> int:
        return int(11 * 1.2 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_small_label_height(cls) -> int:
        return int(11 * 1.2 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_input_height(cls) -> int:
        return int(30 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_toggle_button_size(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_go_back_button_width(cls) -> int:
        return int(100 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_name_label_width(cls) -> int:
        return int(150 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_plan_label_width(cls) -> int:
        return int(200 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_manage_sub_label_width(cls) -> int:
        return int(200 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_logout_button_width(cls) -> int:
        return int(70 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_add_button_width(cls) -> int:
        return int(50 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_large_add_button_width(cls) -> int:
        return int(60 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_toggle_button_width(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_delete_button_width(cls) -> int:
        return int(30 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_rule_button_left_offset(cls) -> int:
        return int(60 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_link_label_width(cls) -> int:
        return int(100 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_info_container_height(cls) -> int:
        return int(104 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_rules_container_height(cls) -> int:
        return int(150 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_rules_scrollview_height(cls) -> int:
        return int(100 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_small_radius(cls) -> int:
        return int(1 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_medium_radius(cls) -> int:
        return int(2 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_large_radius(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_extra_large_radius(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_container_radius(cls) -> int:
        return int(8 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_scrollbar_width(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_border(cls) -> int:
        return 0

    @classmethod
    def get_thin_border(cls) -> int:
        return 1

    @classmethod
    def get_thick_border(cls) -> int:
        return int(2 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_main_padding(cls) -> int:
        return int(10 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_content_margin(cls) -> int:
        return int(10 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_scrollview_margin(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_height_standard(cls) -> int:
        return int(24 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_height_large(cls) -> int:
        return int(30 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_new_chat_button_height(cls) -> int:
        return int(26 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_width_standard(cls) -> int:
        return int(100 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_corner_radius_standard(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_button_spacing(cls) -> int:
        return int(5 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_item_height_chat(cls) -> int:
        return int(22 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_item_height_label(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_item_spacing(cls) -> int:
        return int(5 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_go_back_button_offset(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_go_back_button_side_padding(cls) -> int:
        return int(12 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_go_back_button_icon_size(cls) -> int:
        return int(14 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_go_back_button_icon_gap(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_new_chat_button_offset(cls) -> int:
        return int(70 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_history_area_top_offset(cls) -> int:
        return int(80 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_history_area_bottom_offset(cls) -> int:
        return int(80 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_corner_radius(cls) -> int:
        return int(8 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_padding(cls) -> int:
        return int(12 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_block_icon_size(cls) -> int:
        return int(12 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_block_padding(cls) -> int:
        return int(8 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_block_text_padding(cls) -> int:
        return int(4 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_block_height(cls) -> int:
        return int(22 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_block_margin(cls) -> int:
        return int(0 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_block_corner_radius(cls) -> int:
        return int(6 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_block_min_width(cls) -> int:
        return int(0 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_min_component_width(cls) -> int:
        return int(100 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_markdown_min_component_height(cls) -> int:
        return int(0 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_style(cls, style_type: str = "default") -> Style:

        style = Style()

        if style_type == "input":
            style.background_color = cls.MenuBg
            style.focus_background_color = cls.lighten_color(cls.MenuBg, 10)
            style.border_color = cls.Border
            style.focus_border_color = cls.Border
            style.text_color = cls.Text
            style.font_size = cls.get_font_size()
            style.padding = cls.get_container_padding()

        elif style_type == "button":
            style.background_color = cls.Primary
            style.focus_background_color = tuple(min(c * 1.3, 1.0) for c in cls.Primary[:3]) + (1.0,)
            style.pressed_background_color = tuple(c * 0.8 for c in cls.Primary[:3]) + (1.0,)
            style.border_color = cls.Border
            style.focus_border_color = cls.Border
            style.pressed_border_color = tuple(c * 0.9 for c in cls.Selected[:3]) + (1.0,)
            style.text_color = cls.Text
            style.font_size = cls.get_font_size()
            style.padding = cls.get_container_padding()
            style.border_width = cls.get_thin_border()

        elif style_type == "title":
            style.background_color = cls.Transparent
            style.text_color = cls.Text
            style.font_size = cls.get_font_size("title")
            style.padding = cls.get_container_padding()
            style.border_width = cls.get_no_border()

        elif style_type == "panel":
            style.background_color = cls.Panel
            style.border_color = cls.Border
            style.text_color = cls.Text
            style.font_size = cls.get_font_size()
            style.padding = cls.get_container_padding()
            style.border_width = cls.get_thin_border()

        elif style_type == "menu":
            style.background_color = cls.MenuBg
            style.border_color = cls.Border
            style.text_color = cls.Text
            style.font_size = cls.get_font_size()
            style.padding = cls.get_container_padding()
            style.border_width = cls.get_thin_border()

        else:
            style.background_color = cls.Transparent
            style.text_color = cls.Text
            style.font_size = cls.get_font_size()
            style.padding = cls.get_container_padding() // 2
            style.border_width = cls.get_no_border()

        return style

    @classmethod
    def to_hex(cls, rgba: Tuple[float, float, float, float]) -> str:

        r, g, b = rgba[:3]
        return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"

    @classmethod
    def lighten_color(cls, rgba: Tuple[float, float, float, float], percent: float) -> Tuple[
        float, float, float, float]:

        r, g, b, a = rgba
        factor = percent / 100.0
        r = min(r + (1.0 - r) * factor, 1.0)
        g = min(g + (1.0 - g) * factor, 1.0)
        b = min(b + (1.0 - b) * factor, 1.0)
        return (r, g, b, a)

    @classmethod
    def darken_color(cls, rgba: Tuple[float, float, float, float], percent: float) -> Tuple[float, float, float, float]:

        r, g, b, a = rgba
        factor = percent / 100.0
        r = max(r * (1.0 - factor), 0.0)
        g = max(g * (1.0 - factor), 0.0)
        b = max(b * (1.0 - factor), 0.0)
        return (r, g, b, a)

    @classmethod
    def get_no_connection_icon_width(cls) -> int:
        return int(60 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_icon_height(cls) -> int:
        return int(60 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_title_width(cls) -> int:
        return int(300 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_title_height(cls) -> int:
        return int(30 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_subtitle_width(cls) -> int:
        return int(400 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_subtitle_height(cls) -> int:
        return int(40 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_button_width(cls) -> int:
        return int(160 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_button_height(cls) -> int:
        return int(30 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_gap_large(cls) -> int:
        return int(30 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_gap_medium(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_padding(cls) -> int:
        return int(20 * CoordinateSystem.get_ui_scale())

    @classmethod
    def get_no_connection_button_corner_radius(cls) -> int:
        return int(12 * CoordinateSystem.get_ui_scale())

    MAX_RULE_TEXT_LENGTH = 40
    TRUNCATION_SUFFIX = "..."
    TITLE_MAX_LENGTH = 32

    LINE_HEIGHT_ADDITION = 4
    TEXT_ESTIMATION_FACTOR = 0.6

    HEADING_SIZE_MULTIPLIERS = {
        1: 1.5,
        2: 1.3,
        3: 1.2,
        4: 1.1,
        5: 1,
        6: 1
    }

    CODE_FONT_SIZE_MULTIPLIER = 1
    INLINE_CODE_FONT_SIZE_MULTIPLIER = 1
    BOLD_FONT_SIZE_MULTIPLIER = 1


Styles = UnifiedStyles
