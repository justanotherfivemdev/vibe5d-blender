import logging
from collections import deque
from typing import List

from .state import TextState, TextSelection

logger = logging.getLogger(__name__)


class UndoManager:

    def __init__(self, max_history: int = 500):
        self._history: deque[TextState] = deque(maxlen=max_history)
        self._history_index = -1
        self._save_on_next_change = True

    def save_state(self, text_lines: List[str], cursor_row: int, cursor_col: int,
                   selection: TextSelection):

        if not self._save_on_next_change:
            return

        current_state = TextState(
            text_lines=text_lines.copy(),
            cursor_row=cursor_row,
            cursor_col=cursor_col,
            selection=selection.copy()
        )

        while len(self._history) > self._history_index + 1:
            self._history.pop()

        self._history.append(current_state)
        self._history_index = len(self._history) - 1
        self._save_on_next_change = False

    def enable_save(self):

        self._save_on_next_change = True

    def disable_save(self):

        self._save_on_next_change = False

    def can_undo(self) -> bool:

        return len(self._history) > 0 and self._history_index > 0

    def can_redo(self) -> bool:

        return self._history_index < len(self._history) - 1

    def undo(self) -> TextState:

        if not self.can_undo():
            return None

        self._history_index -= 1
        return self._history[self._history_index].copy()

    def redo(self) -> TextState:

        if not self.can_redo():
            return None

        self._history_index += 1
        return self._history[self._history_index].copy()
