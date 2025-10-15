import logging
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .wrap_manager import WrapManager

logger = logging.getLogger(__name__)


class CursorManager:

    def __init__(self, wrap_manager: 'WrapManager'):
        self.row = 0
        self.col = 0
        self._wrap_manager = wrap_manager

    def validate(self, text_lines: List[str]):

        if not text_lines:
            self.row = 0
            self.col = 0
            return

        if self.row < 0:
            logger.warning(f"Cursor row {self.row} is negative, resetting to 0")
            self.row = 0
        elif self.row >= len(text_lines):
            logger.warning(f"Cursor row {self.row} out of bounds, clamping to {len(text_lines) - 1}")
            self.row = len(text_lines) - 1

        if self.row < len(text_lines):
            max_col = len(text_lines[self.row])
            if self.col < 0:
                logger.warning(f"Cursor col {self.col} is negative, resetting to 0")
                self.col = 0
            elif self.col > max_col:
                logger.warning(f"Cursor col {self.col} out of bounds, clamping to {max_col}")
                self.col = max_col

    def clamp_to_bounds(self, text_lines: List[str]):

        if not text_lines:
            self.row = 0
            self.col = 0
            return

        self.row = max(0, min(self.row, len(text_lines) - 1))
        if self.row < len(text_lines):
            self.col = max(0, min(self.col, len(text_lines[self.row])))

    def move_left(self, text_lines: List[str]):

        if self.col > 0:
            self.col -= 1
        elif self.row > 0:
            self.row -= 1
            self.col = len(text_lines[self.row])

    def move_right(self, text_lines: List[str]):

        current_line = text_lines[self.row]
        if self.col < len(current_line):
            self.col += 1
        elif self.row < len(text_lines) - 1:
            self.row += 1
            self.col = 0

    def move_up(self, text_lines: List[str]):

        if self.row > 0:
            self.row -= 1
            self.col = min(self.col, len(text_lines[self.row]))

    def move_down(self, text_lines: List[str]):

        if self.row < len(text_lines) - 1:
            self.row += 1
            self.col = min(self.col, len(text_lines[self.row]))

    def move_word_left(self, text_lines: List[str]):

        current_line = text_lines[self.row]

        while self.col > 0 and current_line[self.col - 1].isspace():
            self.col -= 1

        while self.col > 0 and not current_line[self.col - 1].isspace():
            self.col -= 1

    def move_word_right(self, text_lines: List[str]):

        current_line = text_lines[self.row]

        while self.col < len(current_line) and not current_line[self.col].isspace():
            self.col += 1

        while self.col < len(current_line) and current_line[self.col].isspace():
            self.col += 1

    def move_to_line_start(self):

        self.col = 0

    def move_to_line_end(self, text_lines: List[str]):

        self.col = len(text_lines[self.row])

    def move_to_document_start(self):

        self.row = 0
        self.col = 0

    def move_to_document_end(self, text_lines: List[str]):

        if text_lines:
            self.row = len(text_lines) - 1
            self.col = len(text_lines[self.row])
        else:
            self.row = 0
            self.col = 0

    def to_display_position(self, text_lines: List[str]) -> Tuple[int, int]:

        return self.position_to_display(self.row, self.col, text_lines)

    def position_to_display(self, row: int, col: int, text_lines: List[str]) -> Tuple[int, int]:

        wrapped_lines = self._wrap_manager.wrapped_lines

        row = max(0, min(row, len(text_lines) - 1)) if text_lines else 0
        if row < len(text_lines):
            col = max(0, min(col, len(text_lines[row])))

        display_row = 0
        for line_idx in range(min(row, len(wrapped_lines))):
            display_row += len(wrapped_lines[line_idx])

        if row < len(wrapped_lines):
            segments = wrapped_lines[row]
            if not segments:
                return display_row, 0

            char_count = 0

            for seg_idx, segment in enumerate(segments):
                segment_start = char_count
                segment_end = char_count + len(segment)

                if col >= segment_start and (col <= segment_end or seg_idx == len(segments) - 1):
                    display_col = col - segment_start
                    display_col = max(0, min(display_col, len(segment)))
                    display_row += seg_idx
                    return display_row, display_col

                char_count = segment_end

        return display_row, 0

    def from_display_position(self, display_row: int, display_col: int, text_lines: List[str]) -> Tuple[int, int]:

        wrapped_lines = self._wrap_manager.wrapped_lines

        display_row = max(0, display_row)
        display_col = max(0, display_col)

        current_display_row = 0
        for line_idx, segments in enumerate(wrapped_lines):
            if not segments:
                continue

            line_display_rows = len(segments)
            if current_display_row + line_display_rows > display_row:
                segment_idx = display_row - current_display_row
                segment_idx = max(0, min(segment_idx, len(segments) - 1))

                if segment_idx < len(segments):
                    char_offset = sum(len(segments[i]) for i in range(segment_idx))
                    final_col = char_offset + display_col

                    if line_idx < len(text_lines):
                        max_col = len(text_lines[line_idx])
                        final_col = min(final_col, max_col)

                    return line_idx, final_col

            current_display_row += line_display_rows

        if text_lines:
            return len(text_lines) - 1, len(text_lines[-1])
        return 0, 0
