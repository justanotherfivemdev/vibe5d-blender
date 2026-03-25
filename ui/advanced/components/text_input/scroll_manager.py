import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cursor_manager import CursorManager

logger = logging.getLogger(__name__)


class ScrollManager:

    def __init__(self):
        self.vertical_offset = 0
        self.max_vertical_offset = 0
        self.horizontal_offset = 0
        self.max_horizontal_offset = 0
        self.is_vertically_scrollable = False
        self.is_horizontally_scrollable = False

    def update_vertical_scrollability(self, content_height: int, visible_height: int):

        if content_height > visible_height and visible_height > 0:
            self.is_vertically_scrollable = True
            self.max_vertical_offset = max(0, content_height - visible_height)
            self.vertical_offset = max(0, min(self.vertical_offset, self.max_vertical_offset))
        else:

            was_scrollable = self.is_vertically_scrollable
            self.is_vertically_scrollable = False
            self.max_vertical_offset = 0

            if was_scrollable:
                self.vertical_offset = 0

    def update_horizontal_scrollability(self, text_width: int, available_width: int):

        if text_width > available_width:
            self.is_horizontally_scrollable = True
            self.max_horizontal_offset = text_width - available_width
            self.horizontal_offset = max(0, min(self.horizontal_offset, self.max_horizontal_offset))
        else:
            self.is_horizontally_scrollable = False
            self.horizontal_offset = 0
            self.max_horizontal_offset = 0

    def scroll_vertically_by(self, delta: int) -> bool:

        if not self.is_vertically_scrollable:
            return False

        old_offset = self.vertical_offset
        self.vertical_offset = max(0, min(self.vertical_offset + delta, self.max_vertical_offset))
        return self.vertical_offset != old_offset

    def scroll_horizontally_by(self, delta: int) -> bool:

        if not self.is_horizontally_scrollable:
            return False

        old_offset = self.horizontal_offset
        self.horizontal_offset = max(0, min(self.horizontal_offset + delta, self.max_horizontal_offset))
        return self.horizontal_offset != old_offset

    def scroll_to_line(self, display_line: int, line_height: int, visible_height: int):

        if not self.is_vertically_scrollable:
            return

        line_y_offset = display_line * line_height

        if line_y_offset < self.vertical_offset:
            self.vertical_offset = line_y_offset
        elif line_y_offset + line_height > self.vertical_offset + visible_height:
            self.vertical_offset = line_y_offset + line_height - visible_height

        self.vertical_offset = max(0, min(self.vertical_offset, self.max_vertical_offset))

    def ensure_cursor_visible_vertical(self, cursor_manager: 'CursorManager',
                                       line_height: int, visible_height: int, text_lines: list):

        if not self.is_vertically_scrollable:
            return

        display_row, _ = cursor_manager.to_display_position(text_lines)
        self.scroll_to_line(display_row, line_height, visible_height)

    def ensure_cursor_visible_horizontal(self, cursor_x_offset: int, available_width: int, margin: int):

        if not self.is_horizontally_scrollable:
            return

        cursor_screen_x = cursor_x_offset - self.horizontal_offset

        if cursor_screen_x < margin:
            self.horizontal_offset = max(0, cursor_x_offset - margin)
        elif cursor_screen_x > available_width - margin:
            self.horizontal_offset = min(
                self.max_horizontal_offset,
                cursor_x_offset - available_width + margin
            )

    def scroll_to_top(self):

        self.vertical_offset = 0

    def scroll_to_bottom(self):

        self.vertical_offset = self.max_vertical_offset

    def get_scroll_info(self) -> dict:

        return {
            'is_scrollable': self.is_vertically_scrollable,
            'offset': self.vertical_offset,
            'max_offset': self.max_vertical_offset,
            'scroll_percentage': (
                (self.vertical_offset / self.max_vertical_offset * 100)
                if self.max_vertical_offset > 0 else 0
            )
        }
