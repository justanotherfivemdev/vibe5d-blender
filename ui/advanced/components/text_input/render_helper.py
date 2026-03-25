import logging
from typing import TYPE_CHECKING

import gpu
from gpu_extras.batch import batch_for_shader

from .constants import (
    INDICATOR_OPACITY, TRACK_OPACITY, SELECTION_OPACITY,
    PLACEHOLDER_OPACITY
)
from ...types import Bounds

if TYPE_CHECKING:
    from ...renderer import UIRenderer

logger = logging.getLogger(__name__)


class RenderHelper:

    @staticmethod
    def render_cursor(cursor_x: int, cursor_y: int, cursor_height: int, cursor_color: tuple):

        gpu.state.blend_set('ALPHA')

        vertices = [
            (cursor_x, cursor_y),
            (cursor_x + 1, cursor_y),
            (cursor_x + 1, cursor_y + cursor_height),
            (cursor_x, cursor_y + cursor_height)
        ]

        indices = [(0, 1, 2), (0, 2, 3)]

        batch = batch_for_shader(
            gpu.shader.from_builtin('UNIFORM_COLOR'),
            'TRIS',
            {"pos": vertices},
            indices=indices,
        )

        gpu.shader.from_builtin('UNIFORM_COLOR').bind()
        gpu.shader.from_builtin('UNIFORM_COLOR').uniform_float("color", (*cursor_color, 1.0))

        batch.draw(gpu.shader.from_builtin('UNIFORM_COLOR'))
        gpu.state.blend_set('NONE')

    @staticmethod
    def render_scroll_indicator(renderer: 'UIRenderer', bounds: Bounds,
                                scroll_offset: int, max_scroll_offset: int,
                                content_height: int, indicator_width: int):

        if max_scroll_offset <= 0:
            return

        min_indicator_height = 20
        indicator_height = max(min_indicator_height,
                               int((content_height / (content_height + max_scroll_offset)) * content_height))

        scroll_ratio = scroll_offset / max_scroll_offset if max_scroll_offset > 0 else 0
        max_indicator_travel = content_height - indicator_height
        indicator_y_offset = int(scroll_ratio * max_indicator_travel)

        content_y = bounds.y
        indicator_x = bounds.x + bounds.width - indicator_width - 2
        indicator_y = content_y + content_height - indicator_height - indicator_y_offset

        track_bounds = Bounds(indicator_x, content_y, indicator_width, content_height)
        track_color = (0.2, 0.2, 0.2, TRACK_OPACITY)
        renderer.draw_rect(track_bounds, track_color)

        thumb_bounds = Bounds(indicator_x, indicator_y, indicator_width, indicator_height)
        thumb_color = (0.5, 0.5, 0.5, INDICATOR_OPACITY)
        renderer.draw_rect(thumb_bounds, thumb_color)

    @staticmethod
    def render_horizontal_scroll_indicator(renderer: 'UIRenderer', bounds: Bounds,
                                           scroll_offset: int, max_scroll_offset: int,
                                           content_width: int, indicator_height: int, padding_left: int):

        if max_scroll_offset <= 0:
            return

        min_indicator_width = 20
        text_width = content_width + max_scroll_offset
        indicator_width = max(min_indicator_width, int((content_width / text_width) * content_width))

        scroll_ratio = scroll_offset / max_scroll_offset if max_scroll_offset > 0 else 0
        max_indicator_travel = content_width - indicator_width
        indicator_x_offset = int(scroll_ratio * max_indicator_travel)

        indicator_y = bounds.y + 2
        indicator_x = bounds.x + padding_left + indicator_x_offset

        track_bounds = Bounds(bounds.x + padding_left, indicator_y, content_width, indicator_height)
        track_color = (0.2, 0.2, 0.2, TRACK_OPACITY)
        renderer.draw_rect(track_bounds, track_color)

        thumb_bounds = Bounds(indicator_x, indicator_y, indicator_width, indicator_height)
        thumb_color = (0.5, 0.5, 0.5, INDICATOR_OPACITY)
        renderer.draw_rect(thumb_bounds, thumb_color)

    @staticmethod
    def render_selection_rect(renderer: 'UIRenderer', x: int, y: int,
                              width: int, height: int):

        selection_color = (0.3, 0.5, 0.8, SELECTION_OPACITY)
        selection_bounds = Bounds(int(x), int(y), int(width), int(height))
        renderer.draw_rect(selection_bounds, selection_color)

    @staticmethod
    def render_placeholder(renderer: 'UIRenderer', text: str, x: int, y: int,
                           font_size: int, text_color: tuple):

        placeholder_color = (*text_color[:3], PLACEHOLDER_OPACITY)
        renderer.draw_text(text, x, y, font_size, placeholder_color)
