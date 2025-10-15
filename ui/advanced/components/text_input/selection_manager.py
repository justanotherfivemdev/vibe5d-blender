import logging
from typing import List, Tuple, Optional

from .state import TextSelection

logger = logging.getLogger(__name__)


class SelectionManager:

    def __init__(self):
        self.selection = TextSelection()
        self.anchor_row = 0
        self.anchor_col = 0
        self._selecting = False
        self._selection_start_row = 0
        self._selection_start_col = 0
        self._mouse_press_pos: Optional[Tuple[int, int]] = None
        self._has_dragged = False

    def start_selection(self, row: int, col: int, mouse_x: int, mouse_y: int):

        self._selecting = True
        self._selection_start_row = row
        self._selection_start_col = col
        self._has_dragged = False
        self._mouse_press_pos = (mouse_x, mouse_y)
        self.selection.clear()

    def update_drag(self, row: int, col: int, mouse_x: int, mouse_y: int, drag_threshold: int):

        if not self._selecting:
            return False

        if self._mouse_press_pos:
            dx = abs(mouse_x - self._mouse_press_pos[0])
            dy = abs(mouse_y - self._mouse_press_pos[1])
            if dx > drag_threshold or dy > drag_threshold:
                self._has_dragged = True

        self.selection.set(
            self._selection_start_row, self._selection_start_col,
            row, col
        )
        return True

    def end_selection(self, row: int, col: int) -> bool:

        if not self._selecting:
            return False

        self.selection.set(
            self._selection_start_row, self._selection_start_col,
            row, col
        )

        should_clear = (not self._has_dragged and
                        self._selection_start_row == row and
                        self._selection_start_col == col)

        self._selecting = False
        self._has_dragged = False
        self._mouse_press_pos = None

        return should_clear

    def start_keyboard_selection(self, anchor_row: int, anchor_col: int):

        self.anchor_row = anchor_row
        self.anchor_col = anchor_col

    def update_keyboard_selection(self, cursor_row: int, cursor_col: int):

        self.selection.set(
            self.anchor_row, self.anchor_col,
            cursor_row, cursor_col
        )

    def get_selected_text(self, text_lines: List[str]) -> str:

        if not self.selection.active:
            return ""

        if self.selection.is_single_line():
            line = text_lines[self.selection.start_row]
            return line[self.selection.start_col:self.selection.end_col]
        else:
            lines = []
            for row in range(self.selection.start_row, self.selection.end_row + 1):
                line = text_lines[row]
                if row == self.selection.start_row:
                    lines.append(line[self.selection.start_col:])
                elif row == self.selection.end_row:
                    lines.append(line[:self.selection.end_col])
                else:
                    lines.append(line)
            return '\n'.join(lines)

    def delete_selected_text(self, text_lines: List[str]) -> Tuple[List[str], int, int]:

        if not self.selection.active:
            return text_lines, -1, -1

        new_lines = text_lines.copy()

        if self.selection.is_single_line():
            line = new_lines[self.selection.start_row]
            new_line = line[:self.selection.start_col] + line[self.selection.end_col:]
            new_lines[self.selection.start_row] = new_line
        else:
            start_line = new_lines[self.selection.start_row]
            end_line = new_lines[self.selection.end_row]

            merged_line = start_line[:self.selection.start_col] + end_line[self.selection.end_col:]

            del new_lines[self.selection.start_row:self.selection.end_row + 1]
            new_lines.insert(self.selection.start_row, merged_line)

        cursor_row = self.selection.start_row
        cursor_col = self.selection.start_col
        self.selection.clear()

        return new_lines, cursor_row, cursor_col

    def select_all(self, text_lines: List[str]):

        if text_lines:
            self.selection.set(0, 0, len(text_lines) - 1, len(text_lines[-1]))
