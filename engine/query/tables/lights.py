from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable
from ....utils.json_utils import to_json_serializable


class LightsTable(BaseTable):

    @property
    def name(self) -> str:
        return 'lights'

    @property
    def description(self) -> str:
        return 'Light objects and properties'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for light in bpy.data.lights:
            if limit and count >= limit:
                break

            if fields:
                light_data = self._extract_fields(light, fields)
            else:
                light_data = self._extract_all_fields(light)

            if where and not self._matches_where(light_data, where):
                continue

            yield light_data
            count += 1

    def _extract_fields(self, light, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = light.name
            elif field == 'type':
                data['type'] = light.type
            elif field == 'energy':
                data['energy'] = light.energy
            elif field == 'color':
                data['color'] = to_json_serializable(light.color)
            elif field == 'users':
                data['users'] = light.users
            elif field == 'angle' and light.type in ['SUN', 'SPOT']:
                if light.type == 'SUN':
                    data['angle'] = light.angle
                elif light.type == 'SPOT':
                    data['angle'] = light.spot_size
            elif field == 'spot_blend' and light.type == 'SPOT':
                data['spot_blend'] = light.spot_blend
            elif field == 'size' and light.type in ['POINT', 'AREA']:
                data['size'] = light.size if light.type == 'POINT' else light.size
            elif field == 'shape' and light.type == 'AREA':
                data['shape'] = light.shape

        return data

    def _extract_all_fields(self, light) -> Dict[str, Any]:
        light_data = {
            'name': light.name,
            'type': light.type,
            'energy': light.energy,
            'color': to_json_serializable(light.color),
            'users': light.users
        }

        if light.type == 'SUN':
            light_data["angle"] = light.angle
        elif light.type == 'SPOT':
            light_data["angle"] = light.spot_size
            light_data["spot_blend"] = light.spot_blend
        elif light.type in ['POINT', 'AREA']:
            light_data["size"] = light.size
            if light.type == 'AREA':
                light_data["shape"] = light.shape

        return light_data
