from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable


class TextsTable(BaseTable):

    @property
    def name(self) -> str:
        return 'texts'

    @property
    def description(self) -> str:
        return 'Text data blocks (script texts and internal text files)'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for text in bpy.data.texts:
            if limit and count >= limit:
                break

            if fields:
                text_data = self._extract_fields(text, fields)
            else:
                text_data = self._extract_all_fields(text)

            if where and not self._matches_where(text_data, where):
                continue

            yield text_data
            count += 1

    def _extract_fields(self, text, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = text.name
            elif field == 'lines':
                data['lines'] = len(text.lines)
            elif field == 'is_modified':
                data['is_modified'] = text.is_modified
            elif field == 'is_in_memory':
                data['is_in_memory'] = text.is_in_memory
            elif field == 'filepath':
                data['filepath'] = text.filepath if text.filepath else None

        return data

    def _extract_all_fields(self, text) -> Dict[str, Any]:
        return {
        :text.name,
        : len(text.lines),
        :text.is_modified,
        : text.is_in_memory,
        :text.filepath if text.filepath else None
        }
