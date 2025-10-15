import logging
from typing import List, Tuple, Callable

import blf

from .constants import DIMENSION_BUFFER

logger = logging.getLogger(__name__)


class WrapManager:

    def __init__(self, get_text_dimensions: Callable[[str], Tuple[int, int]]):
        self.wrapped_lines: List[List[str]] = [[""]]
        self.cache_valid = False
        self._last_wrap_width = 0
        self._text_content_hash = ""
        self._get_text_dimensions = get_text_dimensions

    def invalidate(self, text_lines: List[str], wrap_width: int):

        current_hash = '\n'.join(text_lines)
        if (not self.cache_valid or
                current_hash != self._text_content_hash or
                self._last_wrap_width != wrap_width):
            self.cache_valid = False
            self._text_content_hash = current_hash
            self._last_wrap_width = wrap_width

    def update(self, text_lines: List[str], wrap_width: int) -> List[List[str]]:

        if self.cache_valid:
            return self.wrapped_lines

        self.wrapped_lines = []
        for line in text_lines:
            if not line:
                self.wrapped_lines.append([""])
                continue

            wrapped_segments = self._wrap_line(line, wrap_width)
            self.wrapped_lines.append(wrapped_segments)

        self.cache_valid = True
        self._last_wrap_width = wrap_width
        return self.wrapped_lines

    def _wrap_line(self, line: str, max_width: int) -> List[str]:

        if not line:
            return [""]

        full_width, _ = self._get_text_dimensions(line)
        if full_width <= max_width:
            return [line]

        segments = []
        words = line.split(' ')
        current_segment = ""
        current_width = 0

        word_widths = {}
        space_width, _ = self._get_text_dimensions(' ')

        for word in words:
            if word not in word_widths:
                word_widths[word] = self._get_text_dimensions(word)[0]

        effective_max_width = max_width - DIMENSION_BUFFER

        for word in words:
            word_width = word_widths[word]

            if current_segment:
                test_width = current_width + space_width + word_width
                test_segment = current_segment + " " + word
            else:
                test_width = word_width
                test_segment = word

            if test_width <= effective_max_width:
                current_segment = test_segment
                current_width = test_width
            else:
                if current_segment:
                    segments.append(current_segment)
                    if word_width <= effective_max_width:
                        current_segment = word
                        current_width = word_width
                    else:
                        word_segments = self._break_long_word(word, effective_max_width)
                        segments.extend(word_segments[:-1])
                        current_segment = word_segments[-1] if word_segments else ""
                        current_width = self._get_text_dimensions(current_segment)[0] if current_segment else 0
                else:
                    word_segments = self._break_long_word(word, effective_max_width)
                    segments.extend(word_segments[:-1])
                    current_segment = word_segments[-1] if word_segments else ""
                    current_width = self._get_text_dimensions(current_segment)[0] if current_segment else 0

        if current_segment:
            segments.append(current_segment)

        return segments if segments else [line]

    def _break_long_word(self, word: str, max_width: int) -> List[str]:

        if not word:
            return [""]

        segments = []
        current_chars = ""
        current_width = 0

        for char in word:
            char_width, _ = self._get_text_dimensions(char)
            test_width = current_width + char_width

            if test_width <= max_width:
                current_chars += char
                current_width = test_width
            else:
                if current_chars:
                    segments.append(current_chars)
                current_chars = char
                current_width = char_width

        if current_chars:
            segments.append(current_chars)

        return segments if segments else [word]

    def get_total_display_lines(self) -> int:

        total = 0
        for segments in self.wrapped_lines:
            if segments:
                total += len(segments)
        return max(1, total)
