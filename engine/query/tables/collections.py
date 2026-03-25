from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable


class CollectionsTable(BaseTable):

    @property
    def name(self) -> str:
        return 'collections'

    @property
    def description(self) -> str:
        return 'Collection hierarchy and contents'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for collection in bpy.data.collections:
            if limit and count >= limit:
                break

            if fields:
                coll_data = self._extract_fields(collection, fields)
            else:
                coll_data = self._extract_all_fields(collection)

            if where and not self._matches_where(coll_data, where):
                continue

            yield coll_data
            count += 1

    def _extract_fields(self, collection, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = collection.name
            elif field == 'objects':
                data['objects'] = [obj.name for obj in collection.objects]
            elif field == 'objects_count':
                data['objects_count'] = len(collection.objects)
            elif field == 'children':
                data['children'] = [child.name for child in collection.children]
            elif field == 'hide_viewport':
                data['hide_viewport'] = collection.hide_viewport
            elif field == 'hide_render':
                data['hide_render'] = collection.hide_render

        return data

    def _extract_all_fields(self, collection) -> Dict[str, Any]:
        return {
            'name': collection.name,
            'objects': [obj.name for obj in collection.objects],
            'objects_count': len(collection.objects),
            'children': [child.name for child in collection.children],
            'hide_viewport': collection.hide_viewport,
            'hide_render': collection.hide_render
        }
