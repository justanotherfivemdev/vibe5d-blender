import csv
import io
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class DataFormatter(ABC):
    @abstractmethod
    def format(self, data: List[Dict[str, Any]]) -> Any:
        pass


class JSONFormatter(DataFormatter):
    def format(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return data


class CSVFormatter(DataFormatter):
    FLOAT_PRECISION = 6

    def format(self, data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""

        fieldnames = self._collect_all_fieldnames(data)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()
        for row in data:
            csv_row = {}
            for field in fieldnames:
                value = row.get(field)
                if value is None:
                    csv_row[field] = "NULL"
                elif isinstance(value, (list, dict)):
                    csv_row[field] = json.dumps(value, separators=(',', ':'))
                elif isinstance(value, float):
                    csv_row[field] = round(value, self.FLOAT_PRECISION)
                elif isinstance(value, bool):
                    csv_row[field] = str(value).upper()
                else:
                    csv_row[field] = str(value)
            writer.writerow(csv_row)

        return output.getvalue()

    def _collect_all_fieldnames(self, data: List[Dict[str, Any]]) -> List[str]:
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())
        return sorted(all_keys)


class TableFormatter(DataFormatter):
    FLOAT_PRECISION = 6

    def format(self, data: List[Dict[str, Any]]) -> str:
        if not data:
            return "No data"

        fieldnames = self._collect_all_fieldnames(data)

        widths = {}
        for field in fieldnames:
            widths[field] = len(field)
            for row in data:
                value = row.get(field)
                if value is None:
                    value = "NULL"
                elif isinstance(value, (list, dict)):
                    value = json.dumps(value, separators=(',', ':'))
                elif isinstance(value, float):
                    value = round(value, self.FLOAT_PRECISION)
                elif isinstance(value, bool):
                    value = str(value).upper()
                widths[field] = max(widths[field], len(str(value)))

        lines = []
        header = " | ".join(field.ljust(widths[field]) for field in fieldnames)
        lines.append(header)
        lines.append("-" * len(header))

        for row in data:
            row_values = []
            for field in fieldnames:
                value = row.get(field)
                if value is None:
                    value = "NULL"
                elif isinstance(value, (list, dict)):
                    value = json.dumps(value, separators=(',', ':'))
                elif isinstance(value, float):
                    value = round(value, self.FLOAT_PRECISION)
                elif isinstance(value, bool):
                    value = str(value).upper()
                row_values.append(str(value).ljust(widths[field]))
            lines.append(" | ".join(row_values))

        return "\n".join(lines)

    def _collect_all_fieldnames(self, data: List[Dict[str, Any]]) -> List[str]:
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())
        return sorted(all_keys)


class CompactFormatter(DataFormatter):
    ABBREV = {
    :'loc',
    : 'rot',
    :'vis',
    : 'mats',
    :'res',
    : 'samp',
    :'metal',
    : 'rough',
    :'sel',
    : 'coll',
    :'mods',
    : 'cons',
    }

    def format(self, data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""

        lines = []
        for item in data:
            pairs = []
            for key, value in item.items():
                k = self.ABBREV.get(key, key)
                v = self._format_value(value)
                pairs.append(f"{k}={v}")
            lines.append(' '.join(pairs))

        return '\n'.join(lines)

    def _format_value(self, value) -> str:
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return '1' if value else '0'
        elif isinstance(value, float):
            return f"{value:.2g}"
        elif isinstance(value, list):
            if not value:
                return '[]'
            if all(isinstance(x, (int, float)) for x in value):
                formatted_items = [f"{x:.2g}" if isinstance(x, float) else str(x) for x in value]
                return '[' + ','.join(formatted_items) + ']'
            else:
                return '[' + ','.join(str(x) for x in value) + ']'
        elif isinstance(value, dict):
            if not value:
                return '{}'
            items = [f"{k}={self._format_value(v)}" for k, v in value.items()]
            return '{' + ' '.join(items) + '}'
        else:
            return str(value)


class ColumnarFormatter(DataFormatter):
    def format(self, data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""

        fieldnames = self._collect_all_fieldnames(data)

        widths = {}
        for field in fieldnames:
            widths[field] = len(field)

        formatted_rows = []
        for row in data:
            formatted_row = {}
            for field in fieldnames:
                value = row.get(field)
                formatted_value = self._format_value(value)
                formatted_row[field] = formatted_value
                widths[field] = max(widths[field], len(formatted_value))
            formatted_rows.append(formatted_row)

        lines = []
        header = ' '.join(field.ljust(widths[field]) for field in fieldnames)
        lines.append(header)

        for formatted_row in formatted_rows:
            row_values = [formatted_row[field].ljust(widths[field]) for field in fieldnames]
            lines.append(' '.join(row_values))

        return '\n'.join(lines)

    def _collect_all_fieldnames(self, data: List[Dict[str, Any]]) -> List[str]:
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())
        return sorted(all_keys)

    def _format_value(self, value) -> str:
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return '1' if value else '0'
        elif isinstance(value, float):
            return f"{value:.2g}"
        elif isinstance(value, list):
            if not value:
                return '[]'
            if all(isinstance(x, (int, float)) for x in value):
                formatted_items = [f"{x:.2g}" if isinstance(x, float) else str(x) for x in value]
                return '[' + ','.join(formatted_items) + ']'
            else:
                return '[' + ','.join(str(x) for x in value) + ']'
        elif isinstance(value, dict):
            return json.dumps(value, separators=(',', ':'))
        else:
            return str(value)


class GraphFormatter(DataFormatter):
    def format(self, data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""

        lines = []

        for item in data:
            if 'node_graph' not in item:
                continue

            name = item.get('name', 'Unknown')
            lines.append(f"GRAPH {name}")

            node_graph = item['node_graph']
            nodes = node_graph.get('nodes', [])
            connections = node_graph.get('connections', [])

            node_id_map = {}
            for i, node in enumerate(nodes, 1):
                node_id = f"N{i}"
                node_name = node.get('name', f'Node{i}')
                node_id_map[node_name] = node_id

                node_type = node.get('type', 'UNKNOWN').replace('_', '')

                props = []
                if 'inputs' in node and isinstance(node['inputs'], dict):
                    for inp_name, inp_val in node['inputs'].items():
                        if inp_val is not None:
                            short_name = inp_name[:4].lower().replace(' ', '')
                            if isinstance(inp_val, list):
                                formatted = '[' + ','.join(
                                    f'{x:.2g}' if isinstance(x, float) else str(x) for x in inp_val) + ']'
                                props.append(f"{short_name}={formatted}")
                            elif isinstance(inp_val, float):
                                props.append(f"{short_name}={inp_val:.2g}")
                            else:
                                props.append(f"{short_name}={inp_val}")

                props_str = ' '.join(props) if props else ''
                lines.append(f"{node_id}={node_type} {props_str}".strip())

            for conn in connections:
                from_node = conn.get('from_node', '')
                from_socket = conn.get('from_socket', '')[:4]
                to_node = conn.get('to_node', '')
                to_socket = conn.get('to_socket', '')[:4]

                from_id = node_id_map.get(from_node, from_node)
                to_id = node_id_map.get(to_node, to_node)

                lines.append(f"{from_id}:{from_socket}->{to_id}:{to_socket}")

            lines.append('')

        return '\n'.join(lines)


class FormatSelector:
    MAX_NESTING_DEPTH = 1
    MAX_FIELD_COUNT = 15

    @staticmethod
    def select_format(data: List[Dict[str, Any]]) -> str:
        if not data:
            return 'compact'

        if len(data) == 1:
            if 'node_graph' in data[0]:
                return 'graph'

        is_homogeneous = FormatSelector._is_homogeneous(data)

        if not is_homogeneous:
            return 'compact'

        max_depth = FormatSelector._get_max_nesting_depth(data)
        if max_depth > FormatSelector.MAX_NESTING_DEPTH:
            return 'compact'

        field_count = len(data[0].keys())
        if field_count > FormatSelector.MAX_FIELD_COUNT:
            return 'compact'

        return 'columnar'

    @staticmethod
    def _is_homogeneous(data: List[Dict[str, Any]]) -> bool:
        if not data:
            return True

        first_keys = set(data[0].keys())
        return all(set(row.keys()) == first_keys for row in data)

    @staticmethod
    def _get_max_nesting_depth(data: List[Dict[str, Any]]) -> int:
        if not data:
            return 0

        max_depth = 0
        for row in data:
            depth = FormatSelector._get_nesting_depth(row)
            max_depth = max(max_depth, depth)

        return max_depth

    @staticmethod
    def _get_nesting_depth(obj, current_depth=0) -> int:
        if not isinstance(obj, dict):
            return current_depth

        if not obj:
            return current_depth

        max_child_depth = current_depth
        for value in obj.values():
            if isinstance(value, dict):
                child_depth = FormatSelector._get_nesting_depth(value, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                child_depth = FormatSelector._get_nesting_depth(value[0], current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth


class FormatFactory:
    _formatters = {
    :JSONFormatter,
    : CSVFormatter,
    :TableFormatter,
    : CompactFormatter,
    :ColumnarFormatter,
    : GraphFormatter,
    }

    @classmethod
    def create_formatter(cls, format_type: str) -> DataFormatter:
        format_type = format_type.lower()
        if format_type not in cls._formatters:
            available = ', '.join(cls._formatters.keys())
            raise ValueError(f"Unknown format: {format_type}. Available formats: {available}")
        return cls._formatters[format_type]()

    @classmethod
    def get_available_formats(cls) -> List[str]:
        return list(cls._formatters.keys())
