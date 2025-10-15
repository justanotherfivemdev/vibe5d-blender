import logging
from typing import TYPE_CHECKING

import blf

from .markdown_message import MarkdownMessageComponent
from ..component_theming import get_themed_component_style
from ..coordinates import CoordinateSystem
from ..styles import FontSizes

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ErrorMessageComponent(MarkdownMessageComponent):

    def __init__(self, error_message: str, x: int = 0, y: int = 0, width: int = 400, height: int = 40):

        super().__init__(error_message, x, y, width, height)

        self.apply_error_styling()

        logger.debug(f"ErrorMessageComponent created with message: {error_message}")

    def apply_error_styling(self):

        self.style = get_themed_component_style("button")

        self.style.background_color = (0.0, 0.0, 0.0, 0.0)
        self.style.border_color = (0.0, 0.0, 0.0, 0.0)
        self.style.border_width = 0
        self.style.text_color = (1.0, 1.0, 1.0, 1.0)
        self.style.font_size = FontSizes.Default

        self.padding = CoordinateSystem.scale_int(8)

        self.corner_radius = CoordinateSystem.scale_int(8)

    def apply_themed_style(self, style_type: str = "error"):

        self.apply_error_styling()

    def auto_resize_to_content(self, max_width: int):

        try:
            from ..coordinates import CoordinateSystem

            required_width, required_height = self.calculate_required_size(max_width)

            min_width = max(CoordinateSystem.scale_int(150), required_width)

            min_height = max(CoordinateSystem.scale_int(30), required_height + CoordinateSystem.scale_int(10))

            final_width = min(min_width, max_width)

            self.set_size(final_width, min_height)

            logger.debug(f"ErrorMessageComponent auto-resized to: {final_width}x{min_height}")

        except Exception as e:
            logger.error(f"Error in ErrorMessageComponent auto_resize_to_content: {e}")

            from ..coordinates import CoordinateSystem
            fallback_width = min(CoordinateSystem.scale_int(200), max_width)
            fallback_height = CoordinateSystem.scale_int(40)
            self.set_size(fallback_width, fallback_height)

    def set_error_message(self, error_message: str):

        self.set_markdown(error_message)

    def get_error_message(self) -> str:

        return self.markdown_text
