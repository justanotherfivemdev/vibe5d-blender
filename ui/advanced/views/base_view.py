import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable

from ..layout_manager import LayoutManager, layout_manager

logger = logging.getLogger(__name__)


class BaseView(ABC):

    def __init__(self, layout_mgr: LayoutManager = None):
        self.layout_manager = layout_mgr or layout_manager
        self.layouts: Dict[str, str] = {}
        self.components: Dict[str, Any] = {}
        self.callbacks: Dict[str, Callable] = {}
        self.view_id = self.__class__.__name__.lower().replace('view', '')

    def set_callbacks(self, **callbacks):
        self.callbacks.update(callbacks)

    @abstractmethod
    def create_layout(self, viewport_width: int, viewport_height: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_layout(self, viewport_width: int, viewport_height: int):
        pass

    def get_focused_component(self):
        return None

    def cleanup(self):
        self.layouts.clear()
        self.components.clear()

    def _create_layout_container(self, name: str, config) -> str:
        layout_name = f"{self.view_id}_{name}"
        return self.layout_manager.create_layout(layout_name, config)

    def _get_all_components(self) -> list:
        return list(self.components.values())
