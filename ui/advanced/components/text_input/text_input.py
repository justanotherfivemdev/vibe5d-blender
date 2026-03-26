import logging
import math
import time
from typing import Tuple, Optional, Callable, TYPE_CHECKING

import blf

from .constants import (
    CURSOR_BLINK_INTERVAL, SCROLL_SENSITIVITY, SCROLL_MARGIN, SCROLL_SPEED,
    LINE_HEIGHT_MULTIPLIER, FONT_BASELINE_OFFSET_RATIO, SAFETY_MARGIN_RATIO,
    HEIGHT_CHANGE_THRESHOLD, DRAG_THRESHOLD
)
from .cursor_manager import CursorManager
from .mouse_helper import MouseHelper
from .render_helper import RenderHelper
from .scroll_manager import ScrollManager
from .selection_manager import SelectionManager
from .state import TextState
from .text_operations import TextOperations
from .undo_manager import UndoManager
from .wrap_manager import WrapManager
from ..base import UIComponent
from ...coordinates import CoordinateSystem
from ...types import EventType, UIEvent, CursorType, Bounds
from ...unified_styles import UnifiedStyles

if TYPE_CHECKING:
    from ...renderer import UIRenderer

logger = logging.getLogger(__name__)


def _get_scaled_constant(base_value: int) -> int:
    return int(base_value * CoordinateSystem.get_ui_scale())


class TextInput(UIComponent):

    def __init__(self, x: int = 0, y: int = 0, width: int = 600, height: int = 300,
                 placeholder: str = "", auto_resize: bool = True, min_height: int = 60,
                 max_height: int = 800, corner_radius: int = 8, multiline: bool = True,
                 content_padding_top: int = 0, content_padding_left: int = 0,
                 content_padding_right: int = 0, content_padding_bottom: int = 0):
        super().__init__(x, y, width, height)

        self.placeholder = placeholder
        self.auto_resize = auto_resize
        self.min_height = min_height
        self.max_height = max_height
        self.corner_radius = corner_radius
        self.multiline = multiline

        self.content_padding_top = content_padding_top
        self.content_padding_left = content_padding_left
        self.content_padding_right = content_padding_right
        self.content_padding_bottom = content_padding_bottom

        self._text_lines = [""]

        self._wrap_manager = WrapManager(self.get_text_dimensions)
        self._cursor_manager = CursorManager(self._wrap_manager)
        self._selection_manager = SelectionManager()
        self._scroll_manager = ScrollManager()
        self._undo_manager = UndoManager()
        self._mouse_helper = MouseHelper(self._wrap_manager, self.get_text_dimensions)

        self._cursor_visible = True
        self._last_cursor_toggle = time.time()
        self._dimension_cache = {}
        self._render_dirty = True

        self.on_submit: Optional[Callable[[], None]] = None
        self.on_change: Optional[Callable[[str], None]] = None

        self._key_handlers = self._build_key_dispatch_table()

        self.apply_themed_style("input")
        self.cursor_type = CursorType.TEXT

        if not self.multiline:
            line_height = self._get_line_height()
            total_padding = self._get_total_padding_vertical()
            recommended_height = line_height + total_padding
            absolute_minimum = UnifiedStyles.get_font_size() + total_padding

            self.auto_resize = False
            self.min_height = absolute_minimum

            if height == 300:
                self.max_height = recommended_height
                self.set_size(width, recommended_height)
            else:
                self.max_height = max(height, absolute_minimum)

        if height < self.min_height:
            self.set_size(width, self.min_height)

        self._save_initial_state()

        self._setup_event_handlers()

    def _setup_event_handlers(self):

        self.add_event_handler(EventType.MOUSE_CLICK, self._on_mouse_click)
        self.add_event_handler(EventType.MOUSE_PRESS, self._on_mouse_press)
        self.add_event_handler(EventType.MOUSE_DRAG, self._on_mouse_drag)
        self.add_event_handler(EventType.MOUSE_RELEASE, self._on_mouse_release)
        self.add_event_handler(EventType.MOUSE_MOVE, self._on_mouse_move)
        self.add_event_handler(EventType.MOUSE_ENTER, self._on_mouse_enter)
        self.add_event_handler(EventType.MOUSE_LEAVE, self._on_mouse_leave)

        if self.multiline:
            self.add_event_handler(EventType.MOUSE_WHEEL, self._on_mouse_wheel)
        else:
            self.add_event_handler(EventType.MOUSE_WHEEL, self._on_mouse_wheel_horizontal)

        self.add_event_handler(EventType.TEXT_INPUT, self._on_text_input)
        self.add_event_handler(EventType.KEY_PRESS, self._on_key_press)

    def _get_total_padding_vertical(self) -> int:

        padding_value = UnifiedStyles.get_text_input_padding()
        border_width = UnifiedStyles.get_text_input_border_width()
        return (padding_value * 2) + self.content_padding_top + self.content_padding_bottom + (border_width * 2)

    def _get_total_padding_horizontal(self) -> int:

        padding_value = UnifiedStyles.get_text_input_padding()
        border_width = UnifiedStyles.get_text_input_border_width()
        return (padding_value * 2) + self.content_padding_left + self.content_padding_right + (border_width * 2)

    def _get_content_area_bounds(self) -> Tuple[int, int, int, int]:

        padding_value = UnifiedStyles.get_text_input_padding()
        content_x = self.bounds.x + padding_value + self.content_padding_left
        content_y = self.bounds.y + padding_value + self.content_padding_bottom
        content_width = self.bounds.width - self._get_total_padding_horizontal()
        content_height = self.bounds.height - self._get_total_padding_vertical()
        return content_x, content_y, content_width, content_height

    def _get_line_height(self) -> int:

        scaled_font_size = UnifiedStyles.get_font_size()
        return math.ceil(scaled_font_size * LINE_HEIGHT_MULTIPLIER)

    def _get_text_usable_width(self) -> int:

        usable_width = self.bounds.width - self._get_total_padding_horizontal()
        min_safety_margin = _get_scaled_constant(4)
        min_usable_width = _get_scaled_constant(30)
        safety_margin = max(min_safety_margin, math.ceil(usable_width * SAFETY_MARGIN_RATIO))
        usable_width -= safety_margin
        return max(min_usable_width, usable_width)

    def get_text_dimensions(self, text: str, font_size: int = None) -> Tuple[int, int]:

        if font_size is None:
            font_size = UnifiedStyles.get_font_size()

        current_ui_scale = CoordinateSystem.get_ui_scale()
        cache_key = (text, font_size, current_ui_scale)

        if cache_key not in self._dimension_cache:
            try:
                blf.size(0, font_size)
            except Exception as e:
                logger.warning(f"Failed to set font size: {e}")
                blf.size(0, font_size)

            self._dimension_cache[cache_key] = blf.dimensions(0, text)

        return self._dimension_cache[cache_key]

    def _update_word_wrap(self):

        wrap_width = self._get_text_usable_width()
        self._wrap_manager.invalidate(self._text_lines, wrap_width)
        self._wrap_manager.update(self._text_lines, wrap_width)
        self._cursor_manager.clamp_to_bounds(self._text_lines)
        self._update_scrolling_and_resize()

    def _update_scrolling_and_resize(self):

        if not self.multiline:
            return

        total_display_lines = self._wrap_manager.get_total_display_lines()
        line_height = self._get_line_height()
        content_height = total_display_lines * line_height
        required_height = content_height + self._get_total_padding_vertical() + (0.6 * line_height)

        if self.auto_resize:
            new_height = max(self.min_height, min(self.max_height, required_height))

            visible_content_height = new_height - self._get_total_padding_vertical()
            if required_height > new_height:
                self._scroll_manager.update_vertical_scrollability(content_height, visible_content_height)
            else:
                self._scroll_manager.update_vertical_scrollability(0, visible_content_height)

            height_diff = abs(new_height - self.bounds.height)
            if height_diff > HEIGHT_CHANGE_THRESHOLD:
                old_height = self.bounds.height
                self.set_size(self.bounds.width, new_height)

                visible_content_height = new_height - self._get_total_padding_vertical()
                if required_height > new_height:
                    self._scroll_manager.update_vertical_scrollability(content_height, visible_content_height)
                else:
                    self._scroll_manager.update_vertical_scrollability(0, visible_content_height)
        else:

            current_height = self.bounds.height
            visible_content_height = current_height - self._get_total_padding_vertical()

            if content_height > visible_content_height:
                self._scroll_manager.update_vertical_scrollability(content_height, visible_content_height)
            else:
                self._scroll_manager.update_vertical_scrollability(0, visible_content_height)

        self._ensure_cursor_visible()

    def _mark_dirty(self):

        self._render_dirty = True
        wrap_width = self._get_text_usable_width()
        self._wrap_manager.invalidate(self._text_lines, wrap_width)

        if not self.multiline:
            self._update_horizontal_scroll_state()
            self._ensure_cursor_visible_horizontal()

        if self.ui_state and self.ui_state.target_area:
            try:
                from ...manager import ui_manager
                if ui_manager and hasattr(ui_manager, '_selective_redraw'):
                    ui_manager._selective_redraw()
                else:
                    self.ui_state.target_area.tag_redraw()
            except ImportError:
                self.ui_state.target_area.tag_redraw()

    def _on_text_changed(self):

        self.invalidate()

        if self.auto_resize:
            wrap_width = self._get_text_usable_width()
            self._wrap_manager.invalidate(self._text_lines, wrap_width)
            self._update_word_wrap()

        if self.on_change:
            self.on_change(self.text)

    def _insert_text(self, text: str):

        self._undo_manager.save_state(
            self._text_lines,
            self._cursor_manager.row,
            self._cursor_manager.col,
            self._selection_manager.selection
        )

        if self._selection_manager.selection.active:
            self._delete_selection()

        new_lines, new_row, new_col = TextOperations.insert_text(
            self._text_lines,
            self._cursor_manager.row,
            self._cursor_manager.col,
            text,
            self.multiline
        )

        self._text_lines = new_lines
        self._cursor_manager.row = new_row
        self._cursor_manager.col = new_col

        self._on_text_changed()

        if self.multiline:
            self._ensure_cursor_visible()
        else:
            self._ensure_cursor_visible_horizontal()

        self._undo_manager.enable_save()

    def _delete_selection(self):

        new_lines, cursor_row, cursor_col = self._selection_manager.delete_selected_text(self._text_lines)
        self._text_lines = new_lines
        self._cursor_manager.row = cursor_row
        self._cursor_manager.col = cursor_col

    def _ensure_cursor_visible(self):

        if not self._scroll_manager.is_vertically_scrollable:
            return

        _, _, _, visible_height = self._get_content_area_bounds()
        line_height = self._get_line_height()
        self._scroll_manager.ensure_cursor_visible_vertical(
            self._cursor_manager, line_height, visible_height, self._text_lines
        )

    def _ensure_cursor_visible_horizontal(self):

        if self.multiline or not self._scroll_manager.is_horizontally_scrollable:
            return

        text = self._text_lines[0] if self._text_lines else ""
        text_before_cursor = text[:self._cursor_manager.col]
        cursor_x_offset = self.get_text_dimensions(text_before_cursor)[0] if text_before_cursor else 0

        available_width = self._get_text_usable_width()
        self._scroll_manager.ensure_cursor_visible_horizontal(cursor_x_offset, available_width, SCROLL_MARGIN)

    def _update_horizontal_scroll_state(self):

        if self.multiline or not self._text_lines:
            self._scroll_manager.update_horizontal_scrollability(0, 0)
            return

        text = self._text_lines[0]
        if not text:
            self._scroll_manager.update_horizontal_scrollability(0, 0)
            return

        text_width, _ = self.get_text_dimensions(text)
        available_width = self._get_text_usable_width()
        self._scroll_manager.update_horizontal_scrollability(text_width, available_width)

    def _on_text_input(self, event: UIEvent) -> bool:

        if hasattr(event, 'unicode') and event.unicode:
            if self._selection_manager.selection.active:
                self._delete_selection()
            self._insert_text(event.unicode)
            return True
        return False

    def _on_key_press(self, event: UIEvent) -> bool:

        if not self.focused:
            return False

        if event.key in self._key_handlers:
            try:
                self._key_handlers[event.key](event)
            except Exception as e:
                logger.error(f"Error handling key {event.key}: {e}")
        else:
            self._handle_dynamic_keys(event)

        return True

    def _handle_dynamic_keys(self, event: UIEvent) -> bool:

        if event.key.startswith('ALT_'):
            return True
        if event.key.startswith('CTRL_') and any(event.key.endswith(str(i)) for i in range(10)):
            return True
        if event.key.startswith('SHIFT_') and any(event.key.endswith(str(i)) for i in range(10)):
            return True
        if event.key in ['G', 'R', 'S', 'E', 'I', 'P', 'B', 'L', 'U', 'H', 'J', 'K', 'M', 'Q', 'W', 'T']:
            return True
        return False

    def _build_key_dispatch_table(self) -> dict:

        return {
            'BACK_SPACE': self._handle_backspace,
            'DEL': self._handle_delete,
            'RET': self._handle_submit,
            'NUMPAD_ENTER': self._handle_enter_key,

            'LEFT_ARROW': lambda e: self._handle_arrow_key('LEFT', False, False),
            'RIGHT_ARROW': lambda e: self._handle_arrow_key('RIGHT', False, False),
            'UP_ARROW': lambda e: self._handle_arrow_key('UP', False, False),
            'DOWN_ARROW': lambda e: self._handle_arrow_key('DOWN', False, False),
            'HOME': lambda e: self._handle_home_key(False),
            'END': lambda e: self._handle_end_key(False),
            'PAGE_UP': lambda e: self._handle_page_key('UP', False),
            'PAGE_DOWN': lambda e: self._handle_page_key('DOWN', False),

            'SHIFT_LEFT_ARROW': lambda e: self._handle_arrow_key('LEFT', True, False),
            'SHIFT_RIGHT_ARROW': lambda e: self._handle_arrow_key('RIGHT', True, False),
            'SHIFT_UP_ARROW': lambda e: self._handle_arrow_key('UP', True, False),
            'SHIFT_DOWN_ARROW': lambda e: self._handle_arrow_key('DOWN', True, False),
            'SHIFT_HOME': lambda e: self._handle_home_key(True),
            'SHIFT_END': lambda e: self._handle_end_key(True),
            'SHIFT_PAGE_UP': lambda e: self._handle_page_key('UP', True),
            'SHIFT_PAGE_DOWN': lambda e: self._handle_page_key('DOWN', True),

            'CTRL_LEFT_ARROW': lambda e: self._handle_arrow_key('LEFT', False, True),
            'CTRL_RIGHT_ARROW': lambda e: self._handle_arrow_key('RIGHT', False, True),
            'CTRL_HOME': lambda e: self._handle_ctrl_home_end('HOME', False),
            'CTRL_END': lambda e: self._handle_ctrl_home_end('END', False),
            'CTRL_SHIFT_HOME': lambda e: self._handle_ctrl_home_end('HOME', True),
            'CTRL_SHIFT_END': lambda e: self._handle_ctrl_home_end('END', True),
            'CTRL_SHIFT_LEFT_ARROW': lambda e: self._handle_arrow_key('LEFT', True, True),
            'CTRL_SHIFT_RIGHT_ARROW': lambda e: self._handle_arrow_key('RIGHT', True, True),

            'CTRL_A': self._handle_select_all,
            'CTRL_C': self._handle_copy,
            'CTRL_V': self._handle_paste,
            'CTRL_X': self._handle_cut,

            'CTRL_Z': self._handle_undo,
            'CTRL_Y': self._handle_redo,
            'CTRL_SHIFT_Z': self._handle_redo,

            'ESC': self._handle_escape,

            'TAB': self._block_key,
            'LEFT_CTRL': self._block_key,
            'RIGHT_CTRL': self._block_key,
            'LEFT_ALT': self._block_key,
            'RIGHT_ALT': self._block_key,
            'LEFT_SHIFT': self._block_key,
            'RIGHT_SHIFT': self._block_key,
            'F1': self._block_key, 'F2': self._block_key, 'F3': self._block_key,
            'F4': self._block_key, 'F5': self._block_key, 'F6': self._block_key,
            'F7': self._block_key, 'F8': self._block_key, 'F9': self._block_key,
            'F10': self._block_key, 'F11': self._block_key, 'F12': self._block_key,
        }

    def _block_key(self, event: UIEvent) -> bool:

        return True

    def _handle_undo(self, event: UIEvent) -> bool:

        state = self._undo_manager.undo()
        if state:
            self._restore_state(state)
        return True

    def _handle_redo(self, event: UIEvent) -> bool:

        state = self._undo_manager.redo()
        if state:
            self._restore_state(state)
        return True

    def _restore_state(self, state: TextState):

        self._undo_manager.disable_save()
        self._text_lines = state.text_lines.copy()
        self._cursor_manager.row = state.cursor_row
        self._cursor_manager.col = state.cursor_col
        self._selection_manager.selection = state.selection.copy()
        self._on_text_changed()
        self._undo_manager.enable_save()

    def _handle_backspace(self, event: UIEvent = None) -> bool:

        self._undo_manager.save_state(
            self._text_lines,
            self._cursor_manager.row,
            self._cursor_manager.col,
            self._selection_manager.selection
        )

        if self._selection_manager.selection.active:
            self._delete_selection()
        else:
            new_lines, new_row, new_col = TextOperations.delete_backward(
                self._text_lines,
                self._cursor_manager.row,
                self._cursor_manager.col
            )
            self._text_lines = new_lines
            self._cursor_manager.row = new_row
            self._cursor_manager.col = new_col

        self._on_text_changed()
        self._ensure_cursor_visible()
        self._undo_manager.enable_save()
        return True

    def _handle_delete(self, event: UIEvent = None) -> bool:

        self._undo_manager.save_state(
            self._text_lines,
            self._cursor_manager.row,
            self._cursor_manager.col,
            self._selection_manager.selection
        )

        if self._selection_manager.selection.active:
            self._delete_selection()
        else:
            new_lines, new_row, new_col = TextOperations.delete_forward(
                self._text_lines,
                self._cursor_manager.row,
                self._cursor_manager.col
            )
            self._text_lines = new_lines
            self._cursor_manager.row = new_row
            self._cursor_manager.col = new_col

        self._on_text_changed()
        self._ensure_cursor_visible()
        self._undo_manager.enable_save()
        return True

    def _handle_arrow_key(self, direction: str, shift_held: bool, ctrl_held: bool):

        if not shift_held and self._selection_manager.selection.active:
            self._selection_manager.selection.clear()
        elif shift_held and not self._selection_manager.selection.active:
            self._selection_manager.start_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )

        if direction == 'LEFT':
            if ctrl_held:
                self._cursor_manager.move_word_left(self._text_lines)
            else:
                self._cursor_manager.move_left(self._text_lines)
        elif direction == 'RIGHT':
            if ctrl_held:
                self._cursor_manager.move_word_right(self._text_lines)
            else:
                self._cursor_manager.move_right(self._text_lines)
        elif direction == 'UP':
            self._cursor_manager.move_up(self._text_lines)
        elif direction == 'DOWN':
            self._cursor_manager.move_down(self._text_lines)

        if shift_held:
            self._selection_manager.update_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )

        if self.multiline:
            self._ensure_cursor_visible()
        else:
            self._ensure_cursor_visible_horizontal()

    def _handle_home_key(self, shift_held: bool):

        if shift_held and not self._selection_manager.selection.active:
            self._selection_manager.start_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )
        elif not shift_held:
            self._selection_manager.selection.clear()

        self._cursor_manager.move_to_line_start()

        if shift_held:
            self._selection_manager.update_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )

    def _handle_end_key(self, shift_held: bool):

        if shift_held and not self._selection_manager.selection.active:
            self._selection_manager.start_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )
        elif not shift_held:
            self._selection_manager.selection.clear()

        self._cursor_manager.move_to_line_end(self._text_lines)

        if shift_held:
            self._selection_manager.update_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )

    def _handle_page_key(self, direction: str, shift_held: bool):

        if not shift_held and self._selection_manager.selection.active:
            self._selection_manager.selection.clear()
        elif shift_held and not self._selection_manager.selection.active:
            self._selection_manager.start_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )

        _, _, _, visible_height = self._get_content_area_bounds()
        line_height = self._get_line_height()
        lines_per_page = max(1, visible_height // line_height)

        if direction == 'UP':
            for _ in range(lines_per_page):
                if self._cursor_manager.row > 0:
                    self._cursor_manager.move_up(self._text_lines)
                else:
                    break
        else:
            for _ in range(lines_per_page):
                if self._cursor_manager.row < len(self._text_lines) - 1:
                    self._cursor_manager.move_down(self._text_lines)
                else:
                    break

        if shift_held:
            self._selection_manager.update_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )

        self._ensure_cursor_visible()

    def _handle_ctrl_home_end(self, key: str, shift_held: bool):

        if not shift_held and self._selection_manager.selection.active:
            self._selection_manager.selection.clear()
        elif shift_held and not self._selection_manager.selection.active:
            self._selection_manager.start_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )

        if key == 'HOME':
            self._cursor_manager.move_to_document_start()
        else:
            self._cursor_manager.move_to_document_end(self._text_lines)

        if shift_held:
            self._selection_manager.update_keyboard_selection(
                self._cursor_manager.row,
                self._cursor_manager.col
            )

        self._ensure_cursor_visible()

    def _handle_enter_key(self, event: UIEvent = None) -> bool:

        if not self.multiline:
            return self._handle_submit(event)

        self._undo_manager.save_state(
            self._text_lines,
            self._cursor_manager.row,
            self._cursor_manager.col,
            self._selection_manager.selection
        )

        if self._selection_manager.selection.active:
            self._delete_selection()

        new_lines, new_row, new_col = TextOperations.insert_newline(
            self._text_lines,
            self._cursor_manager.row,
            self._cursor_manager.col
        )
        self._text_lines = new_lines
        self._cursor_manager.row = new_row
        self._cursor_manager.col = new_col

        self._on_text_changed()
        self._ensure_cursor_visible()
        self._undo_manager.enable_save()
        return True

    def _handle_submit(self, event: UIEvent = None) -> bool:

        text = self.text.strip()
        if text and self.on_submit:
            self.on_submit()
        return True

    def _handle_select_all(self, event: UIEvent = None) -> bool:

        self._selection_manager.select_all(self._text_lines)
        return True

    def _handle_copy(self, event: UIEvent = None) -> bool:

        text_to_copy = self._selection_manager.get_selected_text(self._text_lines)
        if not text_to_copy:
            text_to_copy = self.text
        self._copy_to_clipboard(text_to_copy)
        return True

    def _handle_paste(self, event: UIEvent = None) -> bool:

        try:
            import bpy
            clipboard_text = bpy.context.window_manager.clipboard
            if clipboard_text:
                self._undo_manager.save_state(
                    self._text_lines,
                    self._cursor_manager.row,
                    self._cursor_manager.col,
                    self._selection_manager.selection
                )
                if self._selection_manager.selection.active:
                    self._delete_selection()
                self._insert_text(clipboard_text)
        except Exception as e:
            logger.error(f"Failed to paste from clipboard: {e}")
        return True

    def _handle_cut(self, event: UIEvent = None) -> bool:

        if self._selection_manager.selection.active:
            self._undo_manager.save_state(
                self._text_lines,
                self._cursor_manager.row,
                self._cursor_manager.col,
                self._selection_manager.selection
            )
            text_to_cut = self._selection_manager.get_selected_text(self._text_lines)
            self._copy_to_clipboard(text_to_cut)
            self._delete_selection()
            self._on_text_changed()
            self._ensure_cursor_visible()
            self._undo_manager.enable_save()
        return True

    def _copy_to_clipboard(self, text: str):

        try:
            import bpy
            bpy.context.window_manager.clipboard = text
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")

    def _handle_escape(self, event: UIEvent) -> bool:

        if self.ui_state:
            self.ui_state.set_focus(None)
        return True

    def _on_mouse_click(self, event: UIEvent) -> bool:

        if not self.get_bounds().contains_point(event.mouse_x, event.mouse_y):
            return False

        if self._selection_manager.selection.active:
            return True

        self._update_word_wrap()

        content_x, content_y, content_width, content_height = self._get_content_area_bounds()
        logical_row, logical_col = self._mouse_helper.get_cursor_position_from_mouse(
            event.mouse_x, event.mouse_y,
            content_x, content_y, content_width, content_height,
            self._text_lines, self._get_line_height(),
            self._scroll_manager.vertical_offset, self.multiline,
            self._scroll_manager.horizontal_offset
        )

        self._cursor_manager.row = logical_row
        self._cursor_manager.col = logical_col
        self._selection_manager.selection.clear()

        self._ensure_cursor_visible()

        if self.ui_state:
            self.ui_state.set_focus(self)

        return True

    def _on_mouse_press(self, event: UIEvent) -> bool:

        if not self.get_bounds().contains_point(event.mouse_x, event.mouse_y):
            return False

        self._update_word_wrap()

        content_x, content_y, content_width, content_height = self._get_content_area_bounds()
        logical_row, logical_col = self._mouse_helper.get_cursor_position_from_mouse(
            event.mouse_x, event.mouse_y,
            content_x, content_y, content_width, content_height,
            self._text_lines, self._get_line_height(),
            self._scroll_manager.vertical_offset, self.multiline,
            self._scroll_manager.horizontal_offset
        )

        self._cursor_manager.row = logical_row
        self._cursor_manager.col = logical_col

        self._selection_manager.start_selection(logical_row, logical_col, event.mouse_x, event.mouse_y)

        if self.ui_state:
            self.ui_state.set_focus(self)

        return True

    def _on_mouse_drag(self, event: UIEvent) -> bool:

        if not self._selection_manager._selecting:
            return False

        content_x, content_y, content_width, content_height = self._get_content_area_bounds()
        logical_row, logical_col = self._mouse_helper.get_cursor_position_from_mouse(
            event.mouse_x, event.mouse_y,
            content_x, content_y, content_width, content_height,
            self._text_lines, self._get_line_height(),
            self._scroll_manager.vertical_offset, self.multiline,
            self._scroll_manager.horizontal_offset
        )

        if self._scroll_manager.is_vertically_scrollable:
            padding = UnifiedStyles.get_text_input_padding()
            content_y_rel = event.mouse_y - (self.bounds.y + padding)
            content_height_val = self.bounds.height - (2 * padding)

            if content_y_rel < SCROLL_MARGIN:
                self._scroll_manager.scroll_vertically_by(SCROLL_SPEED)
            elif content_y_rel > content_height_val - SCROLL_MARGIN:
                self._scroll_manager.scroll_vertically_by(-SCROLL_SPEED)
        elif self._scroll_manager.is_horizontally_scrollable:
            click_x = event.mouse_x - content_x

            if click_x < SCROLL_MARGIN:
                self._scroll_manager.scroll_horizontally_by(-SCROLL_SPEED)
            elif click_x > content_width - SCROLL_MARGIN:
                self._scroll_manager.scroll_horizontally_by(SCROLL_SPEED)

        self._selection_manager.update_drag(logical_row, logical_col, event.mouse_x, event.mouse_y, DRAG_THRESHOLD)

        return True

    def _on_mouse_release(self, event: UIEvent) -> bool:

        if not self._selection_manager._selecting:
            return False

        content_x, content_y, content_width, content_height = self._get_content_area_bounds()
        logical_row, logical_col = self._mouse_helper.get_cursor_position_from_mouse(
            event.mouse_x, event.mouse_y,
            content_x, content_y, content_width, content_height,
            self._text_lines, self._get_line_height(),
            self._scroll_manager.vertical_offset, self.multiline,
            self._scroll_manager.horizontal_offset
        )

        should_clear = self._selection_manager.end_selection(logical_row, logical_col)
        if should_clear:
            self._selection_manager.selection.clear()

        self._cursor_manager.row = logical_row
        self._cursor_manager.col = logical_col

        return True

    def _on_mouse_move(self, event: UIEvent) -> bool:

        return False

    def _on_mouse_enter(self, event: UIEvent) -> bool:

        self.cursor_type = CursorType.TEXT
        return True

    def _on_mouse_leave(self, event: UIEvent) -> bool:

        self.cursor_type = CursorType.DEFAULT
        return True

    def _on_mouse_wheel(self, event: UIEvent) -> bool:

        if not self._scroll_manager.is_vertically_scrollable:
            return False

        if not self.get_bounds().contains_point(event.mouse_x, event.mouse_y):
            return False

        scroll_delta = 0
        if 'wheel_direction' in event.data:
            scroll_delta = SCROLL_SENSITIVITY if event.data['wheel_direction'] == 'DOWN' else -SCROLL_SENSITIVITY
        elif hasattr(event, 'wheel_delta'):
            scroll_delta = -event.wheel_delta * SCROLL_SENSITIVITY

        if scroll_delta != 0:
            changed = self._scroll_manager.scroll_vertically_by(scroll_delta)
            if changed:
                self._render_dirty = True
            return True

        return False

    def _on_mouse_wheel_horizontal(self, event: UIEvent) -> bool:

        if self.multiline or not self._scroll_manager.is_horizontally_scrollable:
            return False

        if not self.get_bounds().contains_point(event.mouse_x, event.mouse_y):
            return False

        scroll_delta = 0
        if 'wheel_direction' in event.data:
            scroll_delta = SCROLL_SENSITIVITY if event.data['wheel_direction'] == 'DOWN' else -SCROLL_SENSITIVITY
        elif hasattr(event, 'wheel_delta'):
            scroll_delta = -event.wheel_delta * SCROLL_SENSITIVITY

        if scroll_delta != 0:
            changed = self._scroll_manager.scroll_horizontally_by(scroll_delta)
            if changed:
                self._render_dirty = True
            return True

        return False

    def render(self, renderer: 'UIRenderer'):

        current_time = time.time()
        if current_time - self._last_cursor_toggle > CURSOR_BLINK_INTERVAL:
            self._cursor_visible = not self._cursor_visible
            self._last_cursor_toggle = current_time

        content_x, content_y, content_width, content_height = self._get_content_area_bounds()

        self._update_word_wrap()

        if not self.multiline:
            self._update_horizontal_scroll_state()

        bg_color = self.style.focus_background_color if self.focused else self.style.background_color
        renderer.draw_rounded_rect(self.bounds, bg_color, self.corner_radius)

        is_scrollable = self._scroll_manager.is_vertically_scrollable or self._scroll_manager.is_horizontally_scrollable
        if is_scrollable:
            if self.multiline:
                renderer.push_clip_rect(content_x, content_y, content_width, content_height)
            else:
                renderer.push_clip_rect(content_x, content_y - CoordinateSystem.scale_int(8),
                                        content_width, self.bounds.height + CoordinateSystem.scale_int(16))

        if self._selection_manager.selection.active:
            self._render_selection(renderer, content_x, content_y, content_width, content_height)

        line_height = self._get_line_height()

        if self.text:
            self._render_text_content(renderer, content_x, content_y, content_width, content_height, line_height)
        else:
            self._render_placeholder(renderer, content_x, content_y, content_width, line_height)

        if self.focused:
            self._render_cursor(content_x, content_y, content_width, content_height, line_height)

        if is_scrollable:
            renderer.pop_clip_rect()

        border_color = self.style.focus_border_color if self.focused else self.style.border_color
        renderer.draw_rounded_rect_outline(self.bounds, border_color, self.style.border_width, self.corner_radius)

        if self._scroll_manager.is_vertically_scrollable:
            self._render_scroll_indicator(renderer, content_x, content_y, content_width, content_height)
        elif self._scroll_manager.is_horizontally_scrollable and self.multiline:
            self._render_horizontal_scroll_indicator(renderer, content_width)

        self._render_dirty = False

    def _render_text_content(self, renderer: 'UIRenderer', start_x: int, start_y: int,
                             width: int, height: int, line_height: int):

        if not self._text_lines or (len(self._text_lines) == 1 and not self._text_lines[0]):
            return

        font_size = UnifiedStyles.get_font_size()

        if not self.multiline:
            self._render_single_line_text(renderer, start_x, start_y, line_height)
            return

        visible_height = height
        first_visible_line = max(0, self._scroll_manager.vertical_offset // line_height)
        last_visible_line = min(
            self._wrap_manager.get_total_display_lines() - 1,
            (self._scroll_manager.vertical_offset + visible_height) // line_height + 1
        )

        text_start_y = start_y + height - line_height
        current_display_line = 0

        for line_idx, line_segments in enumerate(self._wrap_manager.wrapped_lines):
            if not line_segments or (len(line_segments) == 1 and not line_segments[0]):
                current_display_line += 1
                continue

            for segment_idx, segment in enumerate(line_segments):
                if first_visible_line <= current_display_line <= last_visible_line:
                    line_y = text_start_y - (
                                current_display_line * line_height) + self._scroll_manager.vertical_offset

                    if (line_y >= start_y - line_height and line_y <= start_y + height):
                        if segment.strip():
                            renderer.draw_text(segment, start_x, line_y, font_size, self.style.text_color)

                current_display_line += 1

    def _render_single_line_text(self, renderer: 'UIRenderer', start_x: int, start_y: int, line_height: int):

        if not self._text_lines or not self._text_lines[0]:
            return

        text = self._text_lines[0]
        if not text.strip():
            return

        text_y = self._get_single_line_text_baseline_y()

        if self._scroll_manager.is_horizontally_scrollable:
            text_x = start_x - self._scroll_manager.horizontal_offset
        else:
            text_x = start_x

        renderer.draw_text(text, text_x, text_y, UnifiedStyles.get_font_size(), self.style.text_color)

    def _get_single_line_text_baseline_y(self) -> int:

        container_center_y = self.bounds.y + (self.bounds.height // 2)
        baseline_offset = UnifiedStyles.get_font_size() * FONT_BASELINE_OFFSET_RATIO
        return container_center_y - baseline_offset

    def _render_placeholder(self, renderer: 'UIRenderer', start_x: int, start_y: int,
                            width: int, line_height: int):

        if not self.placeholder:
            return

        if not self.multiline:
            placeholder_y = self._get_single_line_text_baseline_y()
            RenderHelper.render_placeholder(renderer, self.placeholder, start_x, placeholder_y,
                                            UnifiedStyles.get_font_size(), self.style.text_color)
            return

        usable_width = self._get_text_usable_width()
        wrapped_segments = self._wrap_manager._wrap_line(self.placeholder, usable_width)

        content_x, content_y, content_width, content_height = self._get_content_area_bounds()
        text_start_y = content_y + content_height - line_height

        for i, segment in enumerate(wrapped_segments):
            if segment.strip():
                segment_y = text_start_y - (i * line_height)
                RenderHelper.render_placeholder(renderer, segment, start_x, segment_y,
                                                UnifiedStyles.get_font_size(), self.style.text_color)

    def _render_cursor(self, content_x: int, content_y: int, content_width: int,
                       content_height: int, line_height: int):

        if not (self._cursor_visible and self.focused):
            return

        if not self.multiline:
            self._render_single_line_cursor(content_x, line_height)
            return

        if self._cursor_manager.row >= len(self._text_lines):
            return

        wrapped_segments = self._wrap_manager.wrapped_lines[self._cursor_manager.row]
        if not wrapped_segments:
            wrapped_segments = [""]

        chars_processed = 0
        cursor_segment_index = 0
        cursor_x_in_segment = 0
        cursor_found = False

        for i, segment in enumerate(wrapped_segments):
            segment_length = len(segment)

            if chars_processed + segment_length >= self._cursor_manager.col:
                cursor_segment_index = i
                cursor_x_in_segment = self._cursor_manager.col - chars_processed
                cursor_x_in_segment = max(0, min(cursor_x_in_segment, segment_length))
                cursor_found = True
                break
            chars_processed += segment_length

        if not cursor_found:
            cursor_segment_index = len(wrapped_segments) - 1
            if wrapped_segments and wrapped_segments[-1]:
                cursor_x_in_segment = len(wrapped_segments[-1])
            else:
                cursor_x_in_segment = 0

        cursor_x_offset = 0
        if cursor_x_in_segment > 0 and cursor_segment_index < len(wrapped_segments):
            segment_text_before_cursor = wrapped_segments[cursor_segment_index][:cursor_x_in_segment]
            if segment_text_before_cursor:
                cursor_x_offset = self.get_text_dimensions(segment_text_before_cursor)[0]

        cursor_x = content_x + cursor_x_offset

        display_lines_before = 0
        for row in range(self._cursor_manager.row):
            if row < len(self._wrap_manager.wrapped_lines):
                display_lines_before += len(self._wrap_manager.wrapped_lines[row])

        display_lines_before += cursor_segment_index

        text_start_y = content_y + content_height - line_height
        cursor_y = text_start_y - (display_lines_before * line_height) + self._scroll_manager.vertical_offset

        visible_top = content_y
        visible_bottom = content_y + content_height

        if cursor_y >= visible_top - line_height and cursor_y <= visible_bottom:
            cursor_height = line_height - 2
            RenderHelper.render_cursor(cursor_x, cursor_y, cursor_height, self.style.cursor_color)

    def _render_single_line_cursor(self, content_x: int, line_height: int):

        text = self._text_lines[0] if self._text_lines else ""
        text_before_cursor = text[:self._cursor_manager.col]
        cursor_x_offset = 0
        if text_before_cursor:
            cursor_x_offset = self.get_text_dimensions(text_before_cursor)[0]

        cursor_x = content_x + cursor_x_offset
        if self._scroll_manager.is_horizontally_scrollable:
            cursor_x -= self._scroll_manager.horizontal_offset

        container_center_y = self.bounds.y + (self.bounds.height // 2)
        font_size = UnifiedStyles.get_font_size()
        cursor_y = container_center_y - (font_size // 2)

        cursor_height = font_size + 2
        RenderHelper.render_cursor(cursor_x, cursor_y, cursor_height, self.style.cursor_color)

    def _render_selection(self, renderer: 'UIRenderer', content_x: int, content_y: int,
                          content_width: int, content_height: int):

        if not self._selection_manager.selection.active:
            return

        if not self.multiline:
            self._render_single_line_selection(renderer, content_x, content_y, content_width)
            return

        line_height = self._get_line_height()
        selection = self._selection_manager.selection

        start_display_row, start_display_col = self._cursor_manager.position_to_display(
            selection.start_row, selection.start_col, self._text_lines
        )
        end_display_row, end_display_col = self._cursor_manager.position_to_display(
            selection.end_row, selection.end_col, self._text_lines
        )

        if (start_display_row, start_display_col) > (end_display_row, end_display_col):
            start_display_row, start_display_col, end_display_row, end_display_col = end_display_row, end_display_col, start_display_row, start_display_col

        first_visible_line = max(0, self._scroll_manager.vertical_offset // line_height)
        last_visible_line = min(
            self._wrap_manager.get_total_display_lines() - 1,
            (self._scroll_manager.vertical_offset + content_height) // line_height + 1
        )

        for display_row in range(max(start_display_row, first_visible_line),
                                 min(end_display_row + 1, last_visible_line + 1)):
            selection_y = content_y + content_height - line_height - (
                    display_row * line_height) + self._scroll_manager.vertical_offset

            if (selection_y + line_height < content_y or selection_y > content_y + content_height):
                continue

            line_start_col = start_display_col if display_row == start_display_row else 0

            if display_row == end_display_row:
                line_end_col = end_display_col
            else:
                logical_row, segment_idx = self._mouse_helper._find_logical_line_from_display_line(display_row)
                if (logical_row < len(self._wrap_manager.wrapped_lines) and
                        segment_idx < len(self._wrap_manager.wrapped_lines[logical_row])):
                    line_end_col = len(self._wrap_manager.wrapped_lines[logical_row][segment_idx])
                else:
                    line_end_col = 0

            logical_row, segment_idx = self._mouse_helper._find_logical_line_from_display_line(display_row)
            if (logical_row < len(self._wrap_manager.wrapped_lines) and
                    segment_idx < len(self._wrap_manager.wrapped_lines[logical_row])):
                line_text = self._wrap_manager.wrapped_lines[logical_row][segment_idx]
            else:
                continue

            if line_start_col > 0:
                start_text = line_text[:line_start_col]
                selection_start_x = content_x + self.get_text_dimensions(start_text)[0]
            else:
                selection_start_x = content_x

            if line_end_col < len(line_text):
                end_text = line_text[:line_end_col]
                selection_end_x = content_x + self.get_text_dimensions(end_text)[0]
            else:
                selection_end_x = content_x + self.get_text_dimensions(line_text)[0]

            selection_width = max(1, selection_end_x - selection_start_x)
            selection_height = line_height

            RenderHelper.render_selection_rect(
                renderer, selection_start_x, selection_y,
                selection_width, selection_height
            )

    def _render_single_line_selection(self, renderer: 'UIRenderer', content_x: int,
                                      content_y: int, content_width: int):

        if not self._text_lines:
            return

        text = self._text_lines[0]
        if not text:
            return

        selection = self._selection_manager.selection
        start_col = min(selection.start_col, selection.end_col)
        end_col = max(selection.start_col, selection.end_col)

        start_text = text[:start_col] if start_col > 0 else ""
        end_text = text[:end_col] if end_col > 0 else ""

        start_x_offset = self.get_text_dimensions(start_text)[0] if start_text else 0
        end_x_offset = self.get_text_dimensions(end_text)[0] if end_text else 0

        selection_start_x = content_x + start_x_offset
        selection_end_x = content_x + end_x_offset

        if self._scroll_manager.is_horizontally_scrollable:
            selection_start_x -= self._scroll_manager.horizontal_offset
            selection_end_x -= self._scroll_manager.horizontal_offset

        container_center_y = self.bounds.y + (self.bounds.height // 2)
        font_size = UnifiedStyles.get_font_size()
        selection_y = container_center_y - (font_size // 2)

        if (selection_end_x >= content_x and selection_start_x <= content_x + content_width):
            visible_start_x = max(selection_start_x, content_x)
            visible_end_x = min(selection_end_x, content_x + content_width)

            if visible_end_x > visible_start_x:
                RenderHelper.render_selection_rect(
                    renderer, visible_start_x, selection_y,
                    visible_end_x - visible_start_x, font_size + 2
                )

    def _render_scroll_indicator(self, renderer: 'UIRenderer', content_x: int,
                                 content_y: int, content_width: int, content_height: int):

        indicator_width = _get_scaled_constant(4)
        bounds = Bounds(content_x, content_y, content_width, content_height)
        RenderHelper.render_scroll_indicator(
            renderer, bounds,
            self._scroll_manager.vertical_offset,
            self._scroll_manager.max_vertical_offset,
            content_height, indicator_width
        )

    def _render_horizontal_scroll_indicator(self, renderer: 'UIRenderer', content_width: int):

        indicator_height = _get_scaled_constant(4)
        padding = UnifiedStyles.get_text_input_padding()
        padding_left = padding + self.content_padding_left
        bounds = Bounds(self.bounds.x, self.bounds.y, self.bounds.width, self.bounds.height)
        RenderHelper.render_horizontal_scroll_indicator(
            renderer, bounds,
            self._scroll_manager.horizontal_offset,
            self._scroll_manager.max_horizontal_offset,
            content_width, indicator_height, padding_left
        )

    def _save_initial_state(self):

        self._undo_manager.save_state(
            self._text_lines,
            self._cursor_manager.row,
            self._cursor_manager.col,
            self._selection_manager.selection
        )

    @property
    def text(self) -> str:

        return '\n'.join(self._text_lines)

    @text.setter
    def text(self, value: str):

        new_lines = value.split('\n') if value else [""]
        if self._text_lines != new_lines:
            self._undo_manager.save_state(
                self._text_lines,
                self._cursor_manager.row,
                self._cursor_manager.col,
                self._selection_manager.selection
            )
            self._text_lines = new_lines

            if self._cursor_manager.row >= len(self._text_lines):
                self._cursor_manager.row = len(self._text_lines) - 1
            if self._cursor_manager.row >= 0 and self._cursor_manager.row < len(self._text_lines):
                if self._cursor_manager.col > len(self._text_lines[self._cursor_manager.row]):
                    self._cursor_manager.col = len(self._text_lines[self._cursor_manager.row])

            self._selection_manager.selection.clear()
            self._on_text_changed()

    def set_text(self, text: str):

        self.text = text

    def get_text(self) -> str:

        return self.text

    def set_size(self, width: int, height: int):

        old_width = self.bounds.width
        super().set_size(width, height)
        if old_width != width:
            self._render_dirty = True
            wrap_width = self._get_text_usable_width()
            self._wrap_manager.invalidate(self._text_lines, wrap_width)

    def invalidate(self):

        self._render_dirty = True
        wrap_width = self._get_text_usable_width()
        self._wrap_manager.invalidate(self._text_lines, wrap_width)

        if not self.multiline:
            self._update_horizontal_scroll_state()
            self._ensure_cursor_visible_horizontal()

        if self.ui_state and self.ui_state.target_area:
            self.ui_state.target_area.tag_redraw()

    def scroll_to_top(self):

        self._scroll_manager.scroll_to_top()
        self._render_dirty = True

    def scroll_to_bottom(self):

        self._scroll_manager.scroll_to_bottom()
        self._render_dirty = True

    def get_scroll_info(self) -> dict:

        return self._scroll_manager.get_scroll_info()
