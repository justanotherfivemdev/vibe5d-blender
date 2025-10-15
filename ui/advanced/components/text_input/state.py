from dataclasses import dataclass
from typing import List


@dataclass
class TextSelection:
    start_row: int = 0
    start_col: int = 0
    end_row: int = 0
    end_col: int = 0
    active: bool = False

    def clear(self):

        self.active = False
        self.start_row = self.start_col = self.end_row = self.end_col = 0

    def set(self, start_row: int, start_col: int, end_row: int, end_col: int):

        if (start_row, start_col) > (end_row, end_col):
            start_row, start_col, end_row, end_col = end_row, end_col, start_row, start_col

        self.start_row, self.start_col = start_row, start_col
        self.end_row, self.end_col = end_row, end_col
        self.active = True

    def contains(self, row: int, col: int) -> bool:

        if not self.active:
            return False
        return (self.start_row, self.start_col) <= (row, col) < (self.end_row, self.end_col)

    def is_single_line(self) -> bool:

        return self.start_row == self.end_row

    def copy(self) -> 'TextSelection':

        return TextSelection(
            self.start_row,
            self.start_col,
            self.end_row,
            self.end_col,
            self.active
        )


@dataclass
class TextState:
    text_lines: List[str]
    cursor_row: int
    cursor_col: int
    selection: TextSelection

    def copy(self) -> 'TextState':
        return TextState(
            text_lines=self.text_lines.copy(),
            cursor_row=self.cursor_row,
            cursor_col=self.cursor_col,
            selection=self.selection.copy()
        )
