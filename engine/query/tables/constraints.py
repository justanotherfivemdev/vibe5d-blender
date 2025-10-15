from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable


class ConstraintsTable(BaseTable):

    @property
    def name(self) -> str:
        return 'constraints'

    @property
    def description(self) -> str:
        return 'Object and bone constraints'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for obj in context.scene.objects:
            for con in obj.constraints:
                if limit and count >= limit:
                    return

                if fields:
                    con_data = self._extract_fields(obj, con, fields)
                else:
                    con_data = self._extract_all_fields(obj, con)

                if where and not self._matches_where(con_data, where):
                    continue

                yield con_data
                count += 1

    def _extract_fields(self, obj, con, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'object_name':
                data['object_name'] = obj.name
            elif field == 'name':
                data['name'] = con.name
            elif field == 'type':
                data['type'] = con.type
            elif field == 'enabled':
                data['enabled'] = not con.mute
            elif field == 'influence':
                data['influence'] = con.influence
            elif field == 'target':
                if hasattr(con, 'target'):
                    data['target'] = con.target.name if con.target else None

        return data

    def _extract_all_fields(self, obj, con) -> Dict[str, Any]:
        con_data = {
        :obj.name,
        : con.name,
        :con.type,
        : not con.mute,
        :con.influence,
        }

        if hasattr(con, 'target'):
            con_data["target"] = con.target.name if con.target else None

        if con.type == 'TRACK_TO':
            con_data["track_axis"] = con.track_axis
            con_data["up_axis"] = con.up_axis
        elif con.type == 'COPY_LOCATION':
            con_data["use_x"] = con.use_x
            con_data["use_y"] = con.use_y
            con_data["use_z"] = con.use_z
        elif con.type == 'COPY_ROTATION':
            con_data["use_x"] = con.use_x
            con_data["use_y"] = con.use_y
            con_data["use_z"] = con.use_z

        return con_data
