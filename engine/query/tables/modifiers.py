from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable
from ....utils.json_utils import to_json_serializable


class ModifiersTable(BaseTable):

    @property
    def name(self) -> str:
        return 'modifiers'

    @property
    def description(self) -> str:
        return 'Object modifiers and their properties'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for obj in context.scene.objects:
            for mod in obj.modifiers:
                if limit and count >= limit:
                    return

                if fields:
                    mod_data = self._extract_fields(obj, mod, fields)
                else:
                    mod_data = self._extract_all_fields(obj, mod)

                if where and not self._matches_where(mod_data, where):
                    continue

                yield mod_data
                count += 1

    def _extract_fields(self, obj, mod, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'object_name':
                data['object_name'] = obj.name
            elif field == 'name':
                data['name'] = mod.name
            elif field == 'type':
                data['type'] = mod.type
            elif field == 'show_viewport':
                data['show_viewport'] = mod.show_viewport
            elif field == 'show_render':
                data['show_render'] = mod.show_render
            elif field == 'levels' and mod.type == 'SUBSURF':
                data['levels'] = mod.levels
            elif field == 'count' and mod.type == 'ARRAY':
                data['count'] = mod.count

        return data

    def _extract_all_fields(self, obj, mod) -> Dict[str, Any]:
        mod_data = {
        :obj.name,
        : mod.name,
        :mod.type,
        : mod.show_viewport,
        :mod.show_render,
        }

        if mod.type == 'SUBSURF':
            mod_data["levels"] = mod.levels
            mod_data["render_levels"] = mod.render_levels
        elif mod.type == 'ARRAY':
            mod_data["count"] = mod.count
            mod_data["relative_offset_displace"] = to_json_serializable(mod.relative_offset_displace)
        elif mod.type == 'MIRROR':
            mod_data["use_axis"] = [mod.use_axis[0], mod.use_axis[1], mod.use_axis[2]]
            mod_data["mirror_object"] = mod.mirror_object.name if mod.mirror_object else None
        elif mod.type == 'SOLIDIFY':
            mod_data["thickness"] = mod.thickness
            mod_data["offset"] = mod.offset
        elif mod.type == 'BEVEL':
            mod_data["width"] = mod.width
            mod_data["segments"] = mod.segments

        return mod_data
