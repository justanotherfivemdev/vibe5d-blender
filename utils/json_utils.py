import json
from typing import Any

import mathutils


class BlenderJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, (mathutils.Vector, mathutils.Euler, mathutils.Quaternion)):
            return list(obj)
        elif isinstance(obj, mathutils.Matrix):
            return [list(row) for row in obj]
        elif isinstance(obj, mathutils.Color):
            return list(obj)

        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            try:
                return list(obj)
            except (TypeError, ValueError):
                pass
        return super().default(obj)


def to_json_serializable(obj: Any) -> Any:
    if isinstance(obj, (mathutils.Vector, mathutils.Euler, mathutils.Quaternion)):
        return list(obj)
    elif isinstance(obj, mathutils.Matrix):
        return [list(row) for row in obj]
    elif isinstance(obj, mathutils.Color):
        return list(obj)
    elif isinstance(obj, (list, tuple)):
        return [to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: to_json_serializable(value) for key, value in obj.items()}
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        try:
            return [to_json_serializable(item) for item in obj]
        except (TypeError, ValueError):
            pass
    return obj


def safe_json_dumps(obj: Any, **kwargs) -> str:
    return json.dumps(obj, cls=BlenderJSONEncoder, **kwargs)
