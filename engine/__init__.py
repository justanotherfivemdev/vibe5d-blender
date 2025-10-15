from .executor import code_executor
from .render_manager import render_manager
from .script_guard import script_guard
from .tools import tools_manager

classes = []

__all__ = ['classes', 'code_executor', 'script_guard', 'tools_manager', 'render_manager']


def register():
    render_manager.register_handlers()


def unregister():
    render_manager.cleanup()
