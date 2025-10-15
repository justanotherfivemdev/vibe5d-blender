from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Optional, TYPE_CHECKING

from ..style_types import Style
from ..types import EventType, UIEvent, Bounds, CursorType

if TYPE_CHECKING:
    from ..state import UIState
    from ..renderer import UIRenderer


class UIComponent(ABC):

    def __init__(self, x: int = 0, y: int = 0, width: int = 100, height: int = 30):
        self.bounds = Bounds(x, y, width, height)
        self.style = Style()
        self.visible = True
        self.focused = False
        self.ui_state: Optional['UIState'] = None
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.cursor_type = CursorType.DEFAULT

        self.apply_themed_style()

    def apply_themed_style(self, style_type: str = "default"):

        try:
            from ..component_theming import get_themed_component_style, apply_theme_to_component

            component_type = type(self).__name__.lower().replace('component', '')

            try:
                self.style = get_themed_component_style(component_type)
            except Exception:

                self.style = get_themed_component_style(style_type)

            apply_theme_to_component(self, component_type)

        except ImportError:
            try:
                from ..unified_styles import Styles
                from ..component_theming import get_themed_component_style

                self.style = get_themed_component_style(style_type)

                if not hasattr(self.style, 'text_color') or self.style.text_color == (1.0, 1.0, 1.0, 1.0):
                    self.style.text_color = Styles.Text
                if not hasattr(self.style, 'background_color') or self.style.background_color == (0.2, 0.2, 0.2, 0.8):
                    self.style.background_color = Styles.Primary
                if not hasattr(self.style, 'border_color') or self.style.border_color == (0.6, 0.6, 0.6, 1.0):
                    self.style.border_color = Styles.Border

            except ImportError:

                self.style.text_color = Styles.Text
                self.style.background_color = Styles.Primary
                self.style.border_color = Styles.Border

    def set_ui_state(self, ui_state: 'UIState'):

        self.ui_state = ui_state

    def set_position(self, x: int, y: int):

        self.bounds.x = x
        self.bounds.y = y

    def set_size(self, width: int, height: int):

        self.bounds.width = width
        self.bounds.height = height

    def get_bounds(self) -> Bounds:

        return self.bounds

    def is_visible(self) -> bool:

        return self.visible

    def set_visible(self, visible: bool):

        self.visible = visible

    def is_focused(self) -> bool:

        return self.focused

    def set_focused(self, focused: bool):

        self.focused = focused

    def add_event_handler(self, event_type: EventType, handler: Callable):

        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def handle_event(self, event: UIEvent) -> bool:

        if event.event_type in self.event_handlers:
            for handler in self.event_handlers[event.event_type]:
                try:
                    if handler(event):
                        return True
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in component event handler: {e}")
        return False

    def update_layout(self):

        pass

    def set_cursor_type(self, cursor_type: CursorType):

        self.cursor_type = cursor_type

    def get_cursor_type(self) -> CursorType:

        return self.cursor_type

    def refresh_theme(self):

        try:

            component_type = type(self).__name__.lower().replace('component', '')

            self.apply_themed_style(component_type)

            if hasattr(self, 'invalidate'):
                self.invalidate()

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Failed to refresh theme for {type(self).__name__}: {e}")

    def invalidate(self):

        pass

    @abstractmethod
    def render(self, renderer: 'UIRenderer'):

        pass
