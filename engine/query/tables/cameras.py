from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable


class CamerasTable(BaseTable):

    @property
    def name(self) -> str:
        return 'cameras'

    @property
    def description(self) -> str:
        return 'Camera objects and settings'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for camera in bpy.data.cameras:
            if limit and count >= limit:
                break

            if fields:
                camera_data = self._extract_fields(camera, fields)
            else:
                camera_data = self._extract_all_fields(camera)

            if where and not self._matches_where(camera_data, where):
                continue

            yield camera_data
            count += 1

    def _extract_fields(self, camera, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = camera.name
            elif field == 'type':
                data['type'] = camera.type
            elif field == 'focal_length':
                data['focal_length'] = camera.lens
            elif field == 'sensor_width':
                data['sensor_width'] = camera.sensor_width
            elif field == 'sensor_height':
                data['sensor_height'] = camera.sensor_height
            elif field == 'clip_start':
                data['clip_start'] = camera.clip_start
            elif field == 'clip_end':
                data['clip_end'] = camera.clip_end
            elif field == 'users':
                data['users'] = camera.users

        return data

    def _extract_all_fields(self, camera) -> Dict[str, Any]:
        return {
            'name': camera.name,
            'type': camera.type,
            'focal_length': camera.lens,
            'sensor_width': camera.sensor_width,
            'sensor_height': camera.sensor_height,
            'clip_start': camera.clip_start,
            'clip_end': camera.clip_end,
            'users': camera.users
        }
