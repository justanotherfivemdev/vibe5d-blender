import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class TextOperations:

    @staticmethod
    def insert_text(text_lines: List[str], cursor_row: int, cursor_col: int,
                    text: str, multiline: bool) -> Tuple[List[str], int, int]:

        new_lines = text_lines.copy()

        if not multiline:
            text = text.replace('\n', ' ').replace('\r', ' ')

        insert_lines = text.split('\n')

        if len(insert_lines) == 1:
            current_line = new_lines[cursor_row]
            new_line = current_line[:cursor_col] + text + current_line[cursor_col:]
            new_lines[cursor_row] = new_line
            new_col = cursor_col + len(text)
            return new_lines, cursor_row, new_col
        else:
            if not multiline:
                combined_text = ' '.join(insert_lines)
                current_line = new_lines[cursor_row]
                new_line = current_line[:cursor_col] + combined_text + current_line[cursor_col:]
                new_lines[cursor_row] = new_line
                new_col = cursor_col + len(combined_text)
                return new_lines, cursor_row, new_col
            else:
                current_line = new_lines[cursor_row]

                new_lines[cursor_row] = current_line[:cursor_col] + insert_lines[0]

                for i, line in enumerate(insert_lines[1:-1], 1):
                    new_lines.insert(cursor_row + i, line)

                last_line = insert_lines[-1] + current_line[cursor_col:]
                new_lines.insert(cursor_row + len(insert_lines) - 1, last_line)

                new_row = cursor_row + len(insert_lines) - 1
                new_col = len(insert_lines[-1])
                return new_lines, new_row, new_col

    @staticmethod
    def delete_backward(text_lines: List[str], cursor_row: int, cursor_col: int) -> Tuple[List[str], int, int]:

        new_lines = text_lines.copy()

        if cursor_col > 0:
            current_line = new_lines[cursor_row]
            new_line = current_line[:cursor_col - 1] + current_line[cursor_col:]
            new_lines[cursor_row] = new_line
            return new_lines, cursor_row, cursor_col - 1
        elif cursor_row > 0:
            current_line = new_lines.pop(cursor_row)
            new_row = cursor_row - 1
            new_col = len(new_lines[new_row])
            new_lines[new_row] += current_line
            return new_lines, new_row, new_col

        return text_lines, cursor_row, cursor_col

    @staticmethod
    def delete_forward(text_lines: List[str], cursor_row: int, cursor_col: int) -> Tuple[List[str], int, int]:

        new_lines = text_lines.copy()
        current_line = new_lines[cursor_row]

        if cursor_col < len(current_line):
            new_line = current_line[:cursor_col] + current_line[cursor_col + 1:]
            new_lines[cursor_row] = new_line
        elif cursor_row < len(new_lines) - 1:
            next_line = new_lines.pop(cursor_row + 1)
            new_lines[cursor_row] += next_line

        return new_lines, cursor_row, cursor_col

    @staticmethod
    def insert_newline(text_lines: List[str], cursor_row: int, cursor_col: int) -> Tuple[List[str], int, int]:

        new_lines = text_lines.copy()
        current_line = new_lines[cursor_row]
        new_line = current_line[cursor_col:]
        new_lines[cursor_row] = current_line[:cursor_col:]

        new_row = cursor_row + 1
        new_lines.insert(new_row, new_line)

        return new_lines, new_row, 0
