from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable


class ImagesTable(BaseTable):

    @property
    def name(self) -> str:
        return 'images'

    @property
    def description(self) -> str:
        return 'Image data blocks'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for image in bpy.data.images:
            if limit and count >= limit:
                break

            if fields:
                image_data = self._extract_fields(image, fields)
            else:
                image_data = self._extract_all_fields(image)

            if where and not self._matches_where(image_data, where):
                continue

            yield image_data
            count += 1

    def _extract_fields(self, image, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = image.name
            elif field == 'filepath':
                data['filepath'] = image.filepath
            elif field == 'size':
                data['size'] = list(image.size)
            elif field == 'width':
                data['width'] = image.size[0]
            elif field == 'height':
                data['height'] = image.size[1]
            elif field == 'channels':
                data['channels'] = image.channels
            elif field == 'users':
                data['users'] = image.users

        return data

    def _extract_all_fields(self, image) -> Dict[str, Any]:
        return {
        :image.name,
        : image.filepath,
        :list(image.size),
        : image.size[0],
        :image.size[1],
        : image.channels,
        :image.users
        }
