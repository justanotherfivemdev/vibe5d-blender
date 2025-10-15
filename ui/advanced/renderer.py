import logging
import math
from collections import OrderedDict
from contextlib import contextmanager
from typing import Tuple, List, Optional

import blf
import gpu
from gpu_extras.batch import batch_for_shader

from .types import Bounds

logger = logging.getLogger(__name__)


class ClipRegion:

    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class UIRenderer:
    CORNER_SEGMENTS_SMOOTH = 8
    CORNER_SEGMENTS_HIGH_QUALITY = 12
    MAX_BATCH_CACHE_SIZE = 100
    MAX_FONT_CACHE_SIZE = 500

    def __init__(self):
        self.shader = None
        self.texture_shader = None
        self._setup_shaders()

        self._batch_cache = OrderedDict()
        self._font_cache = OrderedDict()

        self._clip_stack: List[ClipRegion] = []
        self._current_clip: Optional[ClipRegion] = None
        self._clip_push_count = 0
        self._clip_pop_count = 0

    def _setup_shaders(self):

        try:
            self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            self.texture_shader = gpu.shader.from_builtin('IMAGE')
        except Exception as e:
            logger.error(f"Failed to setup shaders: {e}")
            raise

    def cleanup(self):

        self._batch_cache.clear()
        self._font_cache.clear()
        self._clip_stack.clear()
        self._current_clip = None
        self._disable_scissor_test()

    def _add_to_cache(self, cache_dict: OrderedDict, key, value, max_size: int):

        if key in cache_dict:
            cache_dict.move_to_end(key)
        else:
            cache_dict[key] = value
            if len(cache_dict) > max_size:
                cache_dict.popitem(last=False)

    def _validate_color(self, color: Tuple[float, float, float, float]) -> bool:

        if not isinstance(color, (tuple, list)) or len(color) != 4:
            logger.error(f"Invalid color format: {color}")
            return False
        return all(0.0 <= c <= 1.0 for c in color)

    def draw_rect(self, bounds: Bounds, color: Tuple[float, float, float, float]):

        if not self._validate_color(color):
            return

        vertices = [
            (bounds.x, bounds.y),
            (bounds.x + bounds.width, bounds.y),
            (bounds.x + bounds.width, bounds.y + bounds.height),
            (bounds.x, bounds.y + bounds.height)
        ]
        indices = [(0, 1, 2), (2, 3, 0)]

        cache_key = (bounds.x, bounds.y, bounds.width, bounds.height, 'rect')

        if cache_key in self._batch_cache:
            batch = self._batch_cache[cache_key]
            self._batch_cache.move_to_end(cache_key)
        else:
            batch = batch_for_shader(self.shader, 'TRIS', {"pos": vertices}, indices=indices)
            self._add_to_cache(self._batch_cache, cache_key, batch, self.MAX_BATCH_CACHE_SIZE)

        try:
            gpu.state.blend_set('ALPHA')
            try:
                self.shader.bind()
                self.shader.uniform_float("color", color)
                batch.draw(self.shader)
            finally:
                gpu.state.blend_set('NONE')
        except Exception as e:
            logger.error(f"Error drawing rectangle: {e}", exc_info=True)

    def draw_rect_outline(self, bounds: Bounds, color: Tuple[float, float, float, float], width: int = 1):

        if width <= 0:
            return

        top_bounds = Bounds(bounds.x, bounds.y + bounds.height - width, bounds.width, width)
        self.draw_rect(top_bounds, color)

        bottom_bounds = Bounds(bounds.x, bounds.y, bounds.width, width)
        self.draw_rect(bottom_bounds, color)

        left_bounds = Bounds(bounds.x, bounds.y + width, width, bounds.height - 2 * width)
        if left_bounds.height > 0:
            self.draw_rect(left_bounds, color)

        right_bounds = Bounds(bounds.x + bounds.width - width, bounds.y + width, width, bounds.height - 2 * width)
        if right_bounds.height > 0:
            self.draw_rect(right_bounds, color)

    def draw_line(self, x1: int, y1: int, x2: int, y2: int, color: Tuple[float, float, float, float]):

        if not self._validate_color(color):
            return

        vertices = [(x1, y1), (x2, y2)]

        try:
            batch = batch_for_shader(self.shader, 'LINES', {"pos": vertices})
            self.shader.bind()
            self.shader.uniform_float("color", color)
            batch.draw(self.shader)
        except Exception as e:
            logger.error(f"Error drawing line: {e}", exc_info=True)

    def draw_text(self, text: str, x: int, y: int, size: int, color: Tuple[float, float, float, float],
                  font_id: int = 0):

        if not self._validate_color(color):
            return

        if not text:
            return

        try:
            blf.size(font_id, size)
            blf.position(font_id, x, y, 0)
            blf.color(font_id, *color)
            blf.draw(font_id, text)
        except Exception as e:
            logger.error(f"Error drawing text with font {font_id}: {e}", exc_info=True)

    def get_text_dimensions(self, text: str, size: int, font_id: int = 0) -> Tuple[int, int]:

        if not text:
            return (0, 0)

        cache_key = (text, size, font_id)

        if cache_key in self._font_cache:
            self._font_cache.move_to_end(cache_key)
            return self._font_cache[cache_key]

        try:
            blf.size(font_id, size)
            dimensions = blf.dimensions(font_id, text)
            self._add_to_cache(self._font_cache, cache_key, dimensions, self.MAX_FONT_CACHE_SIZE)
            return dimensions
        except Exception as e:
            logger.error(f"Error getting text dimensions with font {font_id}: {e}", exc_info=True)
            return (0, 0)

    def push_clip_rect(self, x: int, y: int, width: int, height: int):

        self._clip_push_count += 1

        new_clip = ClipRegion(x, y, width, height)

        if self._current_clip:
            left = max(self._current_clip.x, new_clip.x)
            bottom = max(self._current_clip.y, new_clip.y)
            right = min(self._current_clip.x + self._current_clip.width, new_clip.x + new_clip.width)
            top = min(self._current_clip.y + self._current_clip.height, new_clip.y + new_clip.height)

            if right > left and top > bottom:
                new_clip.x = left
                new_clip.y = bottom
                new_clip.width = right - left
                new_clip.height = top - bottom
            else:
                new_clip.width = 0
                new_clip.height = 0

        if self._current_clip:
            self._clip_stack.append(self._current_clip)

        self._current_clip = new_clip
        self._apply_scissor_test()

    def pop_clip_rect(self):

        self._clip_pop_count += 1

        if self._clip_push_count != self._clip_pop_count:
            logger.warning(f"Clip stack imbalance: {self._clip_push_count} pushes vs {self._clip_pop_count} pops")

        if self._clip_stack:
            self._current_clip = self._clip_stack.pop()
            self._apply_scissor_test()
        else:
            self._current_clip = None
            self._disable_scissor_test()

    @contextmanager
    def clip_rect(self, x: int, y: int, width: int, height: int):

        self.push_clip_rect(x, y, width, height)
        try:
            yield
        finally:
            self.pop_clip_rect()

    def _apply_scissor_test(self):

        if self._current_clip and self._current_clip.width > 0 and self._current_clip.height > 0:
            gpu.state.scissor_test_set(True)
            gpu.state.scissor_set(
                int(self._current_clip.x),
                int(self._current_clip.y),
                int(self._current_clip.width),
                int(self._current_clip.height)
            )
        else:
            self._disable_scissor_test()

    def _disable_scissor_test(self):

        gpu.state.scissor_test_set(False)

    def is_point_clipped(self, x: int, y: int) -> bool:

        if not self._current_clip:
            return False

        return (x < self._current_clip.x or
                x >= self._current_clip.x + self._current_clip.width or
                y < self._current_clip.y or
                y >= self._current_clip.y + self._current_clip.height)

    def is_rect_clipped(self, bounds: Bounds) -> bool:

        if not self._current_clip:
            return False

        return (bounds.x + bounds.width < self._current_clip.x or
                bounds.x >= self._current_clip.x + self._current_clip.width or
                bounds.y + bounds.height < self._current_clip.y or
                bounds.y >= self._current_clip.y + self._current_clip.height)

    def clear_caches(self):

        self._batch_cache.clear()
        self._font_cache.clear()
        self._clip_stack.clear()
        self._current_clip = None
        self._clip_push_count = 0
        self._clip_pop_count = 0
        self._disable_scissor_test()

    def _generate_corner_vertices(self, center_x: float, center_y: float, radius: int,
                                  start_angle: float, end_angle: float, segments: int):

        vertices = [(center_x, center_y)]

        for i in range(segments + 1):
            angle = start_angle + (end_angle - start_angle) * i / segments
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            vertices.append((x, y))

        indices = []
        for i in range(1, len(vertices) - 1):
            indices.append((0, i, i + 1))

        return vertices, indices

    def _generate_corner_ring(self, center_x: float, center_y: float, outer_radius: int,
                              inner_radius: int, start_angle: float, end_angle: float, segments: int):

        vertices = []
        indices = []
        vertex_count = 0

        for i in range(segments + 1):
            angle = start_angle + (end_angle - start_angle) * i / segments

            outer_x = center_x + outer_radius * math.cos(angle)
            outer_y = center_y + outer_radius * math.sin(angle)
            vertices.append((outer_x, outer_y))

            inner_x = center_x + inner_radius * math.cos(angle)
            inner_y = center_y + inner_radius * math.sin(angle)
            vertices.append((inner_x, inner_y))

            if i > 0:
                indices.append((vertex_count - 2, vertex_count, vertex_count - 1))
                indices.append((vertex_count, vertex_count + 1, vertex_count - 1))

            vertex_count += 2

        return vertices, indices

    def draw_rounded_rect(self, bounds: Bounds, color: Tuple[float, float, float, float], corner_radius: int = 0):

        if not self._validate_color(color):
            return

        max_radius = min(bounds.width, bounds.height) // 2
        corner_radius = min(corner_radius, max_radius)

        if corner_radius <= 0:
            self.draw_rect(bounds, color)
            return

        try:
            vertices = []
            indices = []
            vertex_count = 0

            center_left = bounds.x + corner_radius
            center_right = bounds.x + bounds.width - corner_radius
            center_bottom = bounds.y
            center_top = bounds.y + bounds.height

            if center_right > center_left:
                vertices.extend([
                    (center_left, center_bottom),
                    (center_right, center_bottom),
                    (center_right, center_top),
                    (center_left, center_top)
                ])
                indices.extend([
                    (vertex_count, vertex_count + 1, vertex_count + 2),
                    (vertex_count, vertex_count + 2, vertex_count + 3)
                ])
                vertex_count += 4

            left_bottom = bounds.y + corner_radius
            left_top = bounds.y + bounds.height - corner_radius

            if left_top > left_bottom:
                vertices.extend([
                    (bounds.x, left_bottom),
                    (bounds.x + corner_radius, left_bottom),
                    (bounds.x + corner_radius, left_top),
                    (bounds.x, left_top)
                ])
                indices.extend([
                    (vertex_count, vertex_count + 1, vertex_count + 2),
                    (vertex_count, vertex_count + 2, vertex_count + 3)
                ])
                vertex_count += 4

            if left_top > left_bottom:
                vertices.extend([
                    (bounds.x + bounds.width - corner_radius, left_bottom),
                    (bounds.x + bounds.width, left_bottom),
                    (bounds.x + bounds.width, left_top),
                    (bounds.x + bounds.width - corner_radius, left_top)
                ])
                indices.extend([
                    (vertex_count, vertex_count + 1, vertex_count + 2),
                    (vertex_count, vertex_count + 2, vertex_count + 3)
                ])
                vertex_count += 4

            corners = [
                (bounds.x + corner_radius, bounds.y + corner_radius, math.pi, 3 * math.pi / 2),
                (bounds.x + bounds.width - corner_radius, bounds.y + corner_radius, 3 * math.pi / 2, 2 * math.pi),
                (bounds.x + bounds.width - corner_radius, bounds.y + bounds.height - corner_radius, 0, math.pi / 2),
                (bounds.x + corner_radius, bounds.y + bounds.height - corner_radius, math.pi / 2, math.pi)
            ]

            for center_x, center_y, start_angle, end_angle in corners:
                corner_verts, corner_indices = self._generate_corner_vertices(
                    center_x, center_y, corner_radius, start_angle, end_angle, self.CORNER_SEGMENTS_SMOOTH
                )
                offset_indices = [(i + vertex_count, j + vertex_count, k + vertex_count)
                                  for i, j, k in corner_indices]
                vertices.extend(corner_verts)
                indices.extend(offset_indices)
                vertex_count += len(corner_verts)

            if vertices and indices:
                batch = batch_for_shader(self.shader, 'TRIS', {"pos": vertices}, indices=indices)
                gpu.state.blend_set('ALPHA')
                try:
                    self.shader.bind()
                    self.shader.uniform_float("color", color)
                    batch.draw(self.shader)
                finally:
                    gpu.state.blend_set('NONE')
        except Exception as e:
            logger.error(f"Error drawing rounded rectangle: {e}", exc_info=True)
            self.draw_rect(bounds, color)

    def draw_rounded_rect_outline(self, bounds: Bounds, color: Tuple[float, float, float, float], width: int = 1,
                                  corner_radius: int = 0):

        if width <= 0:
            return

        max_radius = min(bounds.width, bounds.height) // 2
        corner_radius = min(corner_radius, max_radius)

        if corner_radius <= 0:
            self.draw_rect_outline(bounds, color, width)
            return

        if bounds.height >= width:
            top_bounds = Bounds(
                bounds.x + corner_radius,
                bounds.y + bounds.height - width,
                bounds.width - 2 * corner_radius,
                width
            )
            if top_bounds.width > 0:
                self.draw_rect(top_bounds, color)

        if bounds.height >= width:
            bottom_bounds = Bounds(
                bounds.x + corner_radius,
                bounds.y,
                bounds.width - 2 * corner_radius,
                width
            )
            if bottom_bounds.width > 0:
                self.draw_rect(bottom_bounds, color)

        if bounds.width >= width:
            left_bounds = Bounds(
                bounds.x,
                bounds.y + corner_radius,
                width,
                bounds.height - 2 * corner_radius
            )
            if left_bounds.height > 0:
                self.draw_rect(left_bounds, color)

        if bounds.width >= width:
            right_bounds = Bounds(
                bounds.x + bounds.width - width,
                bounds.y + corner_radius,
                width,
                bounds.height - 2 * corner_radius
            )
            if right_bounds.height > 0:
                self.draw_rect(right_bounds, color)

        self._draw_corner_borders(bounds, color, width, corner_radius,
                                  [(math.pi, 3 * math.pi / 2),
                                   (3 * math.pi / 2, 2 * math.pi),
                                   (0, math.pi / 2),
                                   (math.pi / 2, math.pi)])

    def _draw_corner_borders(self, bounds: Bounds, color: Tuple[float, float, float, float],
                             width: int, corner_radius: int, angle_pairs: list):

        if not self._validate_color(color):
            return

        try:
            corner_centers = [
                (bounds.x + corner_radius, bounds.y + corner_radius),
                (bounds.x + bounds.width - corner_radius, bounds.y + corner_radius),
                (bounds.x + bounds.width - corner_radius, bounds.y + bounds.height - corner_radius),
                (bounds.x + corner_radius, bounds.y + bounds.height - corner_radius)
            ]

            for (center_x, center_y), (start_angle, end_angle) in zip(corner_centers, angle_pairs):
                outer_radius = corner_radius
                inner_radius = max(0, corner_radius - width)

                vertices, indices = self._generate_corner_ring(
                    center_x, center_y, outer_radius, inner_radius,
                    start_angle, end_angle, self.CORNER_SEGMENTS_HIGH_QUALITY
                )

                if vertices and indices:
                    batch = batch_for_shader(self.shader, 'TRIS', {"pos": vertices}, indices=indices)
                    gpu.state.blend_set('ALPHA')
                    try:
                        self.shader.bind()
                        self.shader.uniform_float("color", color)
                        batch.draw(self.shader)
                    finally:
                        gpu.state.blend_set('NONE')
        except Exception as e:
            logger.error(f"Error drawing corner borders: {e}", exc_info=True)

    def draw_textured_rect(self, x: int, y: int, width: int, height: int, texture, texture_coords=None):

        if not texture:
            return

        vertices = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height)
        ]

        if texture_coords:
            u_min, v_min, u_max, v_max = texture_coords
            uvs = [
                (u_min, v_min),
                (u_max, v_min),
                (u_max, v_max),
                (u_min, v_max)
            ]
        else:
            uvs = [
                (0, 0),
                (1, 0),
                (1, 1),
                (0, 1)
            ]

        indices = [(0, 1, 2), (2, 3, 0)]

        try:
            batch = batch_for_shader(
                self.texture_shader, 'TRIS',
                {"pos": vertices, "texCoord": uvs},
                indices=indices
            )

            gpu.state.blend_set('ALPHA')
            try:
                self.texture_shader.bind()
                self.texture_shader.uniform_sampler("image", texture)
                batch.draw(self.texture_shader)
            finally:
                gpu.state.blend_set('NONE')
        except Exception as e:
            logger.error(f"Error drawing textured rectangle: {e}", exc_info=True)

    def draw_rounded_textured_rect(self, bounds: Bounds, texture, corner_radius: int, texture_coords=None):

        if not texture:
            return

        max_radius = min(bounds.width, bounds.height) // 2
        corner_radius = min(corner_radius, max_radius)

        if corner_radius <= 0:
            self.draw_textured_rect(bounds.x, bounds.y, bounds.width, bounds.height, texture, texture_coords)
            return

        if texture_coords:
            u_min, v_min, u_max, v_max = texture_coords
        else:
            u_min, v_min, u_max, v_max = 0, 0, 1, 1

        u_range = u_max - u_min
        v_range = v_max - v_min

        calc_uv = lambda x, y: (
            u_min + ((x - bounds.x) / bounds.width if bounds.width > 0 else 0) * u_range,
            v_min + ((y - bounds.y) / bounds.height if bounds.height > 0 else 0) * v_range
        )

        try:
            vertices = []
            uvs = []
            indices = []
            vertex_count = 0

            center_left = bounds.x + corner_radius
            center_right = bounds.x + bounds.width - corner_radius
            center_bottom = bounds.y
            center_top = bounds.y + bounds.height

            if center_right > center_left:
                center_vertices = [
                    (center_left, center_bottom),
                    (center_right, center_bottom),
                    (center_right, center_top),
                    (center_left, center_top)
                ]
                vertices.extend(center_vertices)
                for vertex in center_vertices:
                    uvs.append(calc_uv(vertex[0], vertex[1]))
                indices.extend([
                    (vertex_count, vertex_count + 1, vertex_count + 2),
                    (vertex_count, vertex_count + 2, vertex_count + 3)
                ])
                vertex_count += 4

            left_bottom = bounds.y + corner_radius
            left_top = bounds.y + bounds.height - corner_radius

            if left_top > left_bottom:
                left_vertices = [
                    (bounds.x, left_bottom),
                    (bounds.x + corner_radius, left_bottom),
                    (bounds.x + corner_radius, left_top),
                    (bounds.x, left_top)
                ]
                vertices.extend(left_vertices)
                for vertex in left_vertices:
                    uvs.append(calc_uv(vertex[0], vertex[1]))
                indices.extend([
                    (vertex_count, vertex_count + 1, vertex_count + 2),
                    (vertex_count, vertex_count + 2, vertex_count + 3)
                ])
                vertex_count += 4

            if left_top > left_bottom:
                right_vertices = [
                    (bounds.x + bounds.width - corner_radius, left_bottom),
                    (bounds.x + bounds.width, left_bottom),
                    (bounds.x + bounds.width, left_top),
                    (bounds.x + bounds.width - corner_radius, left_top)
                ]
                vertices.extend(right_vertices)
                for vertex in right_vertices:
                    uvs.append(calc_uv(vertex[0], vertex[1]))
                indices.extend([
                    (vertex_count, vertex_count + 1, vertex_count + 2),
                    (vertex_count, vertex_count + 2, vertex_count + 3)
                ])
                vertex_count += 4

            corners = [
                (bounds.x + corner_radius, bounds.y + corner_radius, math.pi, 3 * math.pi / 2),
                (bounds.x + bounds.width - corner_radius, bounds.y + corner_radius, 3 * math.pi / 2, 2 * math.pi),
                (bounds.x + bounds.width - corner_radius, bounds.y + bounds.height - corner_radius, 0, math.pi / 2),
                (bounds.x + corner_radius, bounds.y + bounds.height - corner_radius, math.pi / 2, math.pi)
            ]

            for center_x, center_y, start_angle, end_angle in corners:
                center_vertex_idx = vertex_count
                vertices.append((center_x, center_y))
                uvs.append(calc_uv(center_x, center_y))
                vertex_count += 1

                for i in range(self.CORNER_SEGMENTS_SMOOTH + 1):
                    angle = start_angle + (end_angle - start_angle) * i / self.CORNER_SEGMENTS_SMOOTH
                    x = center_x + corner_radius * math.cos(angle)
                    y = center_y + corner_radius * math.sin(angle)
                    vertices.append((x, y))
                    uvs.append(calc_uv(x, y))

                    if i > 0:
                        indices.append((center_vertex_idx, vertex_count - 1, vertex_count))

                    vertex_count += 1

            if vertices and indices and uvs:
                batch = batch_for_shader(
                    self.texture_shader, 'TRIS',
                    {"pos": vertices, "texCoord": uvs},
                    indices=indices
                )

                gpu.state.blend_set('ALPHA')
                try:
                    self.texture_shader.bind()
                    self.texture_shader.uniform_sampler("image", texture)
                    batch.draw(self.texture_shader)
                finally:
                    gpu.state.blend_set('NONE')
        except Exception as e:
            logger.error(f"Error drawing rounded textured rectangle: {e}", exc_info=True)
            self.draw_textured_rect(bounds.x, bounds.y, bounds.width, bounds.height, texture, texture_coords)

    def draw_image(self, texture, x: int, y: int, width: int, height: int):

        if not texture:
            return
        self.draw_textured_rect(x, y, width, height, texture)

    def draw_rect_with_bottom_corners_rounded(self, bounds: Bounds, color: Tuple[float, float, float, float],
                                              corner_radius: int = 0):

        if not self._validate_color(color):
            return

        max_radius = min(bounds.width, bounds.height) // 2
        corner_radius = min(corner_radius, max_radius)

        if corner_radius <= 0:
            self.draw_rect(bounds, color)
            return

        try:
            vertices = []
            indices = []
            vertex_count = 0

            center_left = bounds.x + corner_radius
            center_right = bounds.x + bounds.width - corner_radius
            center_bottom = bounds.y
            center_top = bounds.y + bounds.height

            if center_right > center_left:
                vertices.extend([
                    (center_left, center_bottom),
                    (center_right, center_bottom),
                    (center_right, center_top),
                    (center_left, center_top)
                ])
                indices.extend([
                    (vertex_count, vertex_count + 1, vertex_count + 2),
                    (vertex_count, vertex_count + 2, vertex_count + 3)
                ])
                vertex_count += 4

            left_bottom = bounds.y + corner_radius
            left_top = bounds.y + bounds.height

            if left_top > left_bottom:
                vertices.extend([
                    (bounds.x, left_bottom),
                    (bounds.x + corner_radius, left_bottom),
                    (bounds.x + corner_radius, left_top),
                    (bounds.x, left_top)
                ])
                indices.extend([
                    (vertex_count, vertex_count + 1, vertex_count + 2),
                    (vertex_count, vertex_count + 2, vertex_count + 3)
                ])
                vertex_count += 4

            if left_top > left_bottom:
                vertices.extend([
                    (bounds.x + bounds.width - corner_radius, left_bottom),
                    (bounds.x + bounds.width, left_bottom),
                    (bounds.x + bounds.width, left_top),
                    (bounds.x + bounds.width - corner_radius, left_top)
                ])
                indices.extend([
                    (vertex_count, vertex_count + 1, vertex_count + 2),
                    (vertex_count, vertex_count + 2, vertex_count + 3)
                ])
                vertex_count += 4

            bottom_corners = [
                (bounds.x + corner_radius, bounds.y + corner_radius, math.pi, 3 * math.pi / 2),
                (bounds.x + bounds.width - corner_radius, bounds.y + corner_radius, 3 * math.pi / 2, 2 * math.pi)
            ]

            for center_x, center_y, start_angle, end_angle in bottom_corners:
                corner_verts, corner_indices = self._generate_corner_vertices(
                    center_x, center_y, corner_radius, start_angle, end_angle, self.CORNER_SEGMENTS_SMOOTH
                )
                offset_indices = [(i + vertex_count, j + vertex_count, k + vertex_count)
                                  for i, j, k in corner_indices]
                vertices.extend(corner_verts)
                indices.extend(offset_indices)
                vertex_count += len(corner_verts)

            if vertices and indices:
                batch = batch_for_shader(self.shader, 'TRIS', {"pos": vertices}, indices=indices)
                gpu.state.blend_set('ALPHA')
                try:
                    self.shader.bind()
                    self.shader.uniform_float("color", color)
                    batch.draw(self.shader)
                finally:
                    gpu.state.blend_set('NONE')
        except Exception as e:
            logger.error(f"Error drawing rectangle with bottom corners rounded: {e}", exc_info=True)
            self.draw_rect(bounds, color)

    def draw_rect_outline_with_bottom_corners_rounded(self, bounds: Bounds, color: Tuple[float, float, float, float],
                                                      width: int = 1, corner_radius: int = 0):

        if width <= 0:
            return

        max_radius = min(bounds.width, bounds.height) // 2
        corner_radius = min(corner_radius, max_radius)

        if corner_radius <= 0:
            self.draw_rect_outline(bounds, color, width)
            return

        if bounds.height >= width:
            top_bounds = Bounds(
                bounds.x,
                bounds.y + bounds.height - width,
                bounds.width,
                width
            )
            if top_bounds.width > 0:
                self.draw_rect(top_bounds, color)

        if bounds.width >= width:
            left_bounds = Bounds(
                bounds.x,
                bounds.y + corner_radius,
                width,
                bounds.height - corner_radius
            )
            if left_bounds.height > 0:
                self.draw_rect(left_bounds, color)

        if bounds.width >= width:
            right_bounds = Bounds(
                bounds.x + bounds.width - width,
                bounds.y + corner_radius,
                width,
                bounds.height - corner_radius
            )
            if right_bounds.height > 0:
                self.draw_rect(right_bounds, color)

        self._draw_corner_borders(bounds, color, width, corner_radius,
                                  [(math.pi, 3 * math.pi / 2),
                                   (3 * math.pi / 2, 2 * math.pi)])
