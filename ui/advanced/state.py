import logging
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING

from .types import EventType, UIEvent

if TYPE_CHECKING:
    from .components.base import UIComponent

logger = logging.getLogger(__name__)


class UIState:

    def __init__(self):
        self.is_enabled: bool = False
        self.target_area: Optional[Any] = None
        self.focused_component: Optional['UIComponent'] = None
        self.mouse_x: int = 0
        self.mouse_y: int = 0
        self.viewport_width: int = 0
        self.viewport_height: int = 0
        self.components: List['UIComponent'] = []
        self.event_listeners: Dict[EventType, List[Callable]] = {}

    def add_event_listener(self, event_type: EventType, callback: Callable):

        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(callback)

    def remove_event_listener(self, event_type: EventType, callback: Callable):

        if event_type in self.event_listeners:
            self.event_listeners[event_type].remove(callback)

    def emit_event(self, event: UIEvent):

        if event.event_type in self.event_listeners:
            for callback in self.event_listeners[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")

    def set_focus(self, component: Optional['UIComponent']):

        if self.focused_component == component:
            return

        if self.focused_component:
            self.focused_component.set_focused(False)
            self.emit_event(UIEvent(EventType.FOCUS_LOST))

        self.focused_component = component
        if component:
            component.set_focused(True)
            self.emit_event(UIEvent(EventType.FOCUS_GAINED))

    def add_component(self, component: 'UIComponent'):

        self.components.append(component)
        component.set_ui_state(self)

    def remove_component(self, component: 'UIComponent'):

        if component in self.components:
            self.components.remove(component)
            if self.focused_component == component:
                self.set_focus(None)

    def get_component_at_point(self, x: int, y: int) -> Optional['UIComponent']:

        for i, component in enumerate(reversed(self.components)):
            bounds = component.get_bounds()
            contains = bounds.contains_point(x, y)

            if component.is_visible() and contains:
                return component

        return None

    def update_viewport_size(self, width: int, height: int):

        self.viewport_width = width
        self.viewport_height = height

        for component in self.components:
            component.update_layout()

    def reset(self):

        self.is_enabled = False
        self.target_area = None
        self.focused_component = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.viewport_width = 0
        self.viewport_height = 0
        self.components.clear()
        self.event_listeners.clear()
