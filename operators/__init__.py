import bpy

from . import auth
from . import base
from . import execution
from . import history
from . import instructions
from . import keymap
from . import ui
from . import viewport_button

classes = []
classes.extend(base.classes)
classes.extend(auth.classes)
classes.extend(instructions.classes)
classes.extend(execution.classes)
classes.extend(history.classes)
classes.extend(ui.classes)
classes.extend(viewport_button.classes)

__all__ = ['classes']


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    keymap.register()


def unregister():
    keymap.unregister()

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
