from typing import Dict, Any, List, Optional, Generator

from ..base_table import BaseTable


class TablesTable(BaseTable):

    @property
    def name(self) -> str:
        return 'tables'

    @property
    def description(self) -> str:
        return 'Meta-table listing all available tables'

    def __init__(self, available_tables: Dict[str, BaseTable]):
        self.available_tables = available_tables

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for table_name, table_instance in self.available_tables.items():
            if limit and count >= limit:
                break

            table_data = {
                'name': table_name,
                'description': table_instance.description
            }

            if where and not self._matches_where(table_data, where):
                continue

            yield table_data
            count += 1
