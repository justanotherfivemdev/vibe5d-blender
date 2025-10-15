import re
from typing import Dict, Any, List

import bpy

from .aggregates import AggregateFunction
from .formatters import FormatFactory, FormatSelector
from .parser import QueryParser
from .response import QueryResponse
from .tables import (
    ObjectsTable, MaterialsTable, LightsTable, CamerasTable,
    CollectionsTable, SceneTable, WorldTable, MeshesTable,
    ImagesTable, ModifiersTable, ConstraintsTable,
    CustomPropertiesTable, TextsTable, CurvesTable, TablesTable
)


class SceneQueryEngine:
    def __init__(self):
        self.tables = self._register_tables()

    def _register_tables(self) -> Dict[str, Any]:
        tables = {}

        table_classes = [
            ObjectsTable(), MaterialsTable(), LightsTable(), CamerasTable(),
            CollectionsTable(), SceneTable(), WorldTable(), MeshesTable(),
            ImagesTable(), ModifiersTable(), ConstraintsTable(),
            CustomPropertiesTable(), TextsTable(), CurvesTable()
        ]

        for table in table_classes:
            tables[table.name] = table

        tables['tables'] = TablesTable(tables)

        return tables

    def get_llm_friendly_schema_summary(self, context) -> str:

        summaries = []
        for table_name, table_instance in sorted(self.tables.items()):
            summaries.append(f"{table_name}: {table_instance.description}")
        return "\n".join(summaries)

    def execute_query(self, expr: str, limit: int, context, format_type: str = None) -> Dict[str, Any]:
        try:
            is_valid, validation_error = QueryParser.validate_query_syntax(expr)
            if not is_valid:
                return QueryResponse(
                    status="error",
                    error=f"Query syntax error: {validation_error}",
                    format_type="compact"
                ).to_dict()

            from_match = re.search(r'FROM\s+(\w+)', expr, re.IGNORECASE)
            if not from_match:
                return QueryResponse(
                    status="error",
                    error="Invalid query format. Expected: SELECT fields FROM table [WHERE conditions] [ORDER BY field] [LIMIT n]",
                    format_type="compact"
                ).to_dict()

            table_name = from_match.group(1).strip().lower()

            if table_name not in self.tables:
                available = ', '.join(sorted(self.tables.keys()))
                return QueryResponse(
                    status="error",
                    error=f"Unknown table: '{table_name}'. Available tables: {available}",
                    format_type="compact"
                ).to_dict()

            try:
                fields, distinct, aggregates, aliases = QueryParser.parse_select(expr)
            except Exception as e:
                return QueryResponse(
                    status="error",
                    error=f"SELECT clause error: {str(e)}",
                    format_type="compact"
                ).to_dict()

            where_expression = None
            where_match = re.search(r'WHERE\s+(.*?)(?:\s+GROUP|\s+ORDER|\s+LIMIT|\s*$)', expr, re.IGNORECASE)
            if where_match:
                try:
                    where_clause = where_match.group(1).strip().rstrip(';')
                    where_expression = QueryParser.parse_where(where_clause)
                except Exception as e:
                    return QueryResponse(
                        status="error",
                        error=f"WHERE clause error: {str(e)}",
                        format_type="compact"
                    ).to_dict()

            try:
                order_by_fields = QueryParser.parse_order_by(expr)
            except Exception as e:
                return QueryResponse(
                    status="error",
                    error=f"ORDER BY clause error: {str(e)}",
                    format_type="compact"
                ).to_dict()

            table = self.tables[table_name]

            if aggregates:
                try:
                    data = self._execute_aggregate_query(table, context, aggregates, aliases, where_expression)
                except Exception as e:
                    return QueryResponse(
                        status="error",
                        error=f"Error executing aggregate query: {str(e)}",
                        format_type="compact"
                    ).to_dict()
            else:
                try:
                    query_fields = None if fields == ['*'] else fields
                    data = list(table.iterate(context, fields=query_fields, where=where_expression, limit=limit))
                except Exception as e:
                    return QueryResponse(
                        status="error",
                        error=f"Error loading data from table '{table_name}': {str(e)}",
                        format_type="compact"
                    ).to_dict()

                if distinct:
                    data = self._apply_distinct(data, fields)

                if order_by_fields:
                    data = self._apply_order_by(data, order_by_fields)

                if fields != ["*"]:
                    data = self._select_fields(data, fields)

            selected_format = format_type if format_type else FormatSelector.select_format(data)

            try:
                formatter = FormatFactory.create_formatter(selected_format)
                formatted_data = formatter.format(data)
            except Exception as e:
                return QueryResponse(
                    status="error",
                    error=f"Error formatting output: {str(e)}",
                    format_type=selected_format
                ).to_dict()

            return QueryResponse(
                status="success",
                data=formatted_data,
                count=len(data),
                format_type=selected_format
            ).to_dict()

        except Exception as e:
            return QueryResponse(
                status="error",
                error=f"Query execution error: {str(e)}",
                format_type="compact"
            ).to_dict()

    def _execute_aggregate_query(self, table, context, aggregates, aliases, where_expression):
        result = {}

        for alias, (func, field) in aggregates.items():
            if func == 'COUNT' and field == '*':
                result[alias] = table.count(context, where_expression)
            else:
                data = list(table.iterate(context, fields=[field] if field != '*' else None, where=where_expression,
                                          limit=None))
                result[alias] = AggregateFunction.apply(func, field, data)

        return [result]

    def _apply_distinct(self, data: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
        seen = set()
        distinct_data = []

        for item in data:
            if fields == ['*']:
                key = tuple(sorted((k, str(v)) for k, v in item.items()))
            else:
                key = tuple(str(item.get(f)) for f in fields)

            if key not in seen:
                seen.add(key)
                distinct_data.append(item)

        return distinct_data

    def _apply_order_by(self, data: List[Dict[str, Any]], order_fields: List[tuple]) -> List[Dict[str, Any]]:
        def get_field_value(item, field):
            if '.' in field:
                field_parts = field.split('.')
                current_value = item
                for part in field_parts:
                    if isinstance(current_value, dict) and part in current_value:
                        current_value = current_value[part]
                    else:
                        return None
                return current_value
            return item.get(field)

        def make_sort_key(item):
            keys = []
            for field, direction in order_fields:
                value = get_field_value(item, field)
                if value is None:
                    keys.append((1, ""))
                else:
                    keys.append((0, value))
            return keys

        reverse = any(direction == 'DESC' for _, direction in order_fields)

        try:
            data.sort(key=make_sort_key, reverse=reverse)
        except:
            pass

        return data

    def _select_fields(self, data: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
        selected_data = []

        for item in data:
            selected_item = {}
            for field in fields:
                if '.' in field:
                    field_parts = field.split('.')
                    current_value = item
                    for part in field_parts:
                        if isinstance(current_value, dict) and part in current_value:
                            current_value = current_value[part]
                        else:
                            current_value = None
                            break
                    selected_item[field] = current_value
                else:
                    selected_item[field] = item.get(field)
            selected_data.append(selected_item)

        return selected_data


scene_query_engine = SceneQueryEngine()
