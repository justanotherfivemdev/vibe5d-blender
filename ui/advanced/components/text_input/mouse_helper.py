import logging
from typing import Tuple, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .wrap_manager import WrapManager

logger = logging.getLogger(__name__)


class MouseHelper:

    def __init__(self, wrap_manager: 'WrapManager',
                 get_text_dimensions: Callable[[str], Tuple[int, int]]):
        self._wrap_manager = wrap_manager
        self._get_text_dimensions = get_text_dimensions

    def get_cursor_position_from_mouse(self, mouse_x: int, mouse_y: int,
                                       content_x: int, content_y: int,
                                       content_width: int, content_height: int,
                                       text_lines: list, line_height: int,
                                       scroll_offset: int, multiline: bool,
                                       horizontal_scroll_offset: int = 0) -> Tuple[int, int]:

        click_x = mouse_x - content_x
        click_y = mouse_y - content_y

        tolerance = 10
        click_x = max(-tolerance, min(click_x, content_width + tolerance))
        click_y = max(-tolerance, min(click_y, content_height + tolerance))

        if not multiline:
            click_x += horizontal_scroll_offset
            text = text_lines[0] if text_lines else ""
            logical_col = self._find_column_from_click_x_single_line(text, click_x)
            return 0, logical_col

        text_start_y = content_y + content_height - line_height
        y_offset_from_text_start = text_start_y - click_y - scroll_offset
        display_line = max(0, int(y_offset_from_text_start // line_height))

        logical_row, segment_idx = self._find_logical_line_from_display_line(display_line)

        if logical_row >= len(text_lines):
            if text_lines:
                logical_row = len(text_lines) - 1
                logical_col = len(text_lines[logical_row])
            else:
                logical_row = 0
                logical_col = 0
        else:
            logical_col = self._find_column_from_click_x(logical_row, segment_idx, click_x, text_lines)

        return logical_row, logical_col

    def _find_logical_line_from_display_line(self, display_line: int) -> Tuple[int, int]:

        wrapped_lines = self._wrap_manager.wrapped_lines
        current_display_line = 0

        for logical_row, segments in enumerate(wrapped_lines):
            if not segments:
                segments = [""]

            num_segments = len(segments)

            if current_display_line + num_segments > display_line:
                segment_idx = display_line - current_display_line
                return logical_row, max(0, min(segment_idx, num_segments - 1))

            current_display_line += num_segments

        if wrapped_lines:
            return len(wrapped_lines) - 1, 0
        return 0, 0

    def _find_column_from_click_x(self, logical_row: int, segment_idx: int,
                                  click_x: int, text_lines: list) -> int:

        wrapped_lines = self._wrap_manager.wrapped_lines

        if logical_row >= len(text_lines) or logical_row >= len(wrapped_lines):
            return 0

        line_text = text_lines[logical_row]
        segments = wrapped_lines[logical_row]

        if not segments or segment_idx >= len(segments):
            return len(line_text)

        char_offset = sum(len(segments[i]) for i in range(segment_idx) if i < len(segments))
        segment_text = segments[segment_idx]

        if not segment_text:
            return char_offset

        segment_width, _ = self._get_text_dimensions(segment_text)
        if click_x >= segment_width:
            if segment_idx == len(segments) - 1:
                return len(line_text)
            else:
                return char_offset + len(segment_text)

        best_col_in_segment = 0
        best_distance = float('inf')

        for col_in_segment in range(len(segment_text) + 1):
            text_part = segment_text[:col_in_segment]
            text_width, _ = self._get_text_dimensions(text_part)
            distance = abs(text_width - click_x)

            if distance < best_distance:
                best_distance = distance
                best_col_in_segment = col_in_segment

        final_col = char_offset + best_col_in_segment
        return min(final_col, len(line_text))

    def _find_column_from_click_x_single_line(self, text: str, click_x: int) -> int:

        if not text:
            return 0

        text_width, _ = self._get_text_dimensions(text)
        if click_x >= text_width:
            return len(text)

        best_col = 0
        best_distance = float('inf')

        for col in range(len(text) + 1):
            text_part = text[:col]
            part_width, _ = self._get_text_dimensions(text_part)
            distance = abs(part_width - click_x)

            if distance < best_distance:
                best_distance = distance
                best_col = col

        return best_col
