from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable
from ....utils.json_utils import to_json_serializable


class CustomPropertiesTable(BaseTable):

    @property
    def name(self) -> str:
        return 'custom_properties'

    @property
    def description(self) -> str:
        return 'Custom properties from all data blocks'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for obj in context.scene.objects:
            for key in obj.keys():
                if key.startswith('_'):
                    continue

                if limit and count >= limit:
                    return

                prop_data = {
                    'object_name': obj.name,
                    'block_type': "OBJECT",
                    'property_name': key,
                    'value': to_json_serializable(obj[key])
                }

                if where and not self._matches_where(prop_data, where):
                    continue

                yield prop_data
                count += 1
