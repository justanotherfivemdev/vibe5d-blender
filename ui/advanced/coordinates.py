from typing import Tuple

import bpy


class CoordinateSystem:

    @staticmethod
    def get_ui_scale() -> float:

        try:
            return bpy.context.preferences.system.ui_scale
        except (AttributeError, RuntimeError):

            return 1.0

    @staticmethod
    def scale_value(value: float) -> float:

        return value * CoordinateSystem.get_ui_scale()

    @staticmethod
    def scale_int(value: int) -> int:

        return int(value * CoordinateSystem.get_ui_scale())

    @staticmethod
    def screen_to_region(screen_x: int, screen_y: int, area, region) -> Tuple[int, int]:

        if not area or not region:
            return screen_x, screen_y

        area_x = screen_x - area.x
        area_y = screen_y - area.y

        return area_x, area_y

    @staticmethod
    def region_to_gpu(region_x: int, region_y: int) -> Tuple[int, int]:

        return region_x, region_y

    @staticmethod
    def get_region_height() -> int:

        try:
            area = bpy.context.area
            return area.height if area else 0
        except:
            return 0
