import re
from typing import Dict, Any, List, Tuple

from .conditions import WhereCondition, WhereExpression


class QueryParser:
    OPERATORS = {
        'OR': 1,
        'AND': 2,
        'NOT': 3,
        'IN': 4, 'NOT IN': 4,
        'LIKE': 4, 'NOT LIKE': 4, 'ILIKE': 4, 'NOT ILIKE': 4,
        'IS': 4, 'IS NOT': 4,
        'BETWEEN': 4, 'NOT BETWEEN': 4,
        '=': 5, '!=': 5, '<>': 5,
        '<': 5, '<=': 5, '>': 5, '>=': 5
    }

    NULL_OPERATORS = {'IS', 'IS NOT'}

    @staticmethod
    def parse_select(query: str) -> Tuple[List[str], bool, Dict[str, str], Dict[str, str]]:
        try:
            select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
            if not select_match:
                raise ValueError("Invalid SELECT clause. Expected format: SELECT fields FROM table")

            select_clause = select_match.group(1).strip()
            if not select_clause:
                raise ValueError("Empty SELECT clause")

            distinct = select_clause.upper().startswith('DISTINCT')

            if distinct:
                select_clause = select_clause[8:].strip()
                if not select_clause:
                    raise ValueError("Empty field list after DISTINCT")

            aggregates = {}
            aliases = {}
            fields = []

            field_parts = QueryParser._split_select_fields(select_clause)

            for field in field_parts:
                field = field.strip()
                if not field:
                    continue

                alias_match = re.search(r'(.+?)\s+AS\s+([a-zA-Z_][a-zA-Z0-9_]*)', field, re.IGNORECASE)
                if alias_match:
                    original_field = alias_match.group(1).strip()
                    alias_name = alias_match.group(2).strip()

                    agg_match = re.match(r'(COUNT|SUM|AVG|MIN|MAX|STDDEV|VARIANCE)\s*\(\s*(.*?)\s*\)', original_field,
                                         re.IGNORECASE)
                    if agg_match:
                        func_name = agg_match.group(1).upper()
                        field_name = agg_match.group(2).strip()
                        if field_name == '*' and func_name != 'COUNT':
                            raise ValueError(f"Function {func_name} cannot be used with *")
                        aggregates[alias_name] = (func_name, field_name)
                        aliases[alias_name] = f"{func_name}({field_name})"
                    else:
                        aliases[alias_name] = original_field

                    fields.append(alias_name)
                else:
                    agg_match = re.match(r'(COUNT|SUM|AVG|MIN|MAX|STDDEV|VARIANCE)\s*\(\s*(.*?)\s*\)', field,
                                         re.IGNORECASE)
                    if agg_match:
                        func_name = agg_match.group(1).upper()
                        field_name = agg_match.group(2).strip()
                        if field_name == '*' and func_name != 'COUNT':
                            raise ValueError(f"Function {func_name} cannot be used with *")
                        alias = f"{func_name}({field_name})"
                        aggregates[alias] = (func_name, field_name)
                        fields.append(alias)
                    else:
                        if not QueryParser._is_valid_field_name(field):
                            raise ValueError(f"Invalid field name: {field}")
                        fields.append(field)

            if not fields:
                raise ValueError("No valid fields found in SELECT clause")

            return fields, distinct, aggregates, aliases

        except Exception as e:
            raise ValueError(f"Error parsing SELECT clause: {str(e)}")

    @staticmethod
    def _split_select_fields(select_clause: str) -> List[str]:
        fields = []
        current_field = ""
        paren_depth = 0
        in_quotes = False
        quote_char = None

        i = 0
        while i < len(select_clause):
            char = select_clause[i]

            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current_field += char
            elif char == quote_char and in_quotes:
                if i + 1 < len(select_clause) and select_clause[i + 1] == quote_char:
                    current_field += char * 2
                    i += 1
                else:
                    in_quotes = False
                    quote_char = None
                    current_field += char
            elif not in_quotes:
                if char == '(':
                    paren_depth += 1
                    current_field += char
                elif char == ')':
                    paren_depth -= 1
                    current_field += char
                elif char == ',' and paren_depth == 0:
                    fields.append(current_field.strip())
                    current_field = ""
                else:
                    current_field += char
            else:
                current_field += char

            i += 1

        if current_field.strip():
            fields.append(current_field.strip())

        if paren_depth != 0:
            raise ValueError("Mismatched parentheses in SELECT clause")

        if in_quotes:
            raise ValueError(f"Unclosed quote in SELECT clause")

        return fields

    @staticmethod
    def _is_valid_field_name(field: str) -> bool:
        if not field or field == '*':
            return field == '*'

        if (field.startswith('"') and field.endswith('"')) or (field.startswith("'") and field.endswith("'")):
            inner = field[1:-1]
            return len(inner) > 0 and not inner.count(field[0]) > 0

        return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*$', field) is not None

    @staticmethod
    def parse_where(where_str: str) -> 'WhereExpression':
        if not where_str or not where_str.strip():
            return WhereExpression()

        where_str = where_str.strip()
        expression = WhereExpression()

        conditions_with_ops = QueryParser._split_where_conditions(where_str)

        for i, (condition_str, operator) in enumerate(conditions_with_ops):
            condition_str = condition_str.strip()
            if condition_str:
                try:
                    condition = QueryParser._parse_condition(condition_str)
                    expression.conditions.append(condition)
                    if operator and i < len(conditions_with_ops) - 1:
                        expression.operators.append(operator)
                except Exception as e:
                    raise ValueError(f"Error parsing condition '{condition_str}': {str(e)}")

        return expression

    @staticmethod
    def _split_where_conditions(where_str: str) -> List[Tuple[str, str]]:
        conditions_with_ops = []
        current_condition = ""
        i = 0

        while i < len(where_str):
            char = where_str[i]

            if char in ('"', "'"):
                quote_char = char
                current_condition += char
                i += 1

                while i < len(where_str):
                    char = where_str[i]
                    current_condition += char
                    if char == quote_char:
                        if i + 1 < len(where_str) and where_str[i + 1] == quote_char:
                            i += 2
                            current_condition += quote_char
                        else:
                            i += 1
                            break
                    else:
                        i += 1
                continue

            if i + 3 <= len(where_str) and where_str[i:i + 3].upper() == 'AND':
                if (i == 0 or where_str[i - 1].isspace()) and (i + 3 >= len(where_str) or where_str[i + 3].isspace()):
                    conditions_with_ops.append((current_condition.strip(), 'AND'))
                    current_condition = ""
                    i += 3
                    while i < len(where_str) and where_str[i].isspace():
                        i += 1
                    continue
            elif i + 2 <= len(where_str) and where_str[i:i + 2].upper() == 'OR':
                if (i == 0 or where_str[i - 1].isspace()) and (i + 2 >= len(where_str) or where_str[i + 2].isspace()):
                    conditions_with_ops.append((current_condition.strip(), 'OR'))
                    current_condition = ""
                    i += 2
                    while i < len(where_str) and where_str[i].isspace():
                        i += 1
                    continue

            current_condition += char
            i += 1

        if current_condition.strip():
            conditions_with_ops.append((current_condition.strip(), None))

        return conditions_with_ops

    @staticmethod
    def parse_order_by(query: str) -> List[Tuple[str, str]]:
        order_match = re.search(r'ORDER\s+BY\s+(.*?)(?:\s+LIMIT|\s*$)', query, re.IGNORECASE)
        if not order_match:
            return []

        try:
            order_clause = order_match.group(1).strip()
            if not order_clause:
                raise ValueError("Empty ORDER BY clause")

            order_fields = []
            field_parts = QueryParser._split_order_fields(order_clause)

            for field_spec in field_parts:
                field_spec = field_spec.strip()
                if not field_spec:
                    continue

                parts = field_spec.split()

                if len(parts) == 1:
                    field_name = parts[0]
                    direction = 'ASC'
                elif len(parts) == 2:
                    field_name = parts[0]
                    direction = parts[1].upper()
                    if direction not in ('ASC', 'DESC'):
                        raise ValueError(f"Invalid sort direction: {direction}. Use ASC or DESC")
                else:
                    raise ValueError(f"Invalid ORDER BY specification: {field_spec}")

                if not QueryParser._is_valid_field_name(field_name) and field_name != '*':
                    raise ValueError(f"Invalid field name in ORDER BY: {field_name}")

                order_fields.append((field_name, direction))

            return order_fields

        except Exception as e:
            raise ValueError(f"Error parsing ORDER BY clause: {str(e)}")

    @staticmethod
    def _split_order_fields(order_clause: str) -> List[str]:
        fields = []
        current_field = ""
        paren_depth = 0
        in_quotes = False
        quote_char = None

        for char in order_clause:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current_field += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current_field += char
            elif not in_quotes:
                if char == '(':
                    paren_depth += 1
                    current_field += char
                elif char == ')':
                    paren_depth -= 1
                    current_field += char
                elif char == ',' and paren_depth == 0:
                    fields.append(current_field.strip())
                    current_field = ""
                else:
                    current_field += char
            else:
                current_field += char

        if current_field.strip():
            fields.append(current_field.strip())

        return fields

    @staticmethod
    def parse_group_by(query: str) -> List[str]:
        group_match = re.search(r'GROUP\s+BY\s+(.*?)(?:\s+HAVING|\s+ORDER|\s+LIMIT|\s*$)', query, re.IGNORECASE)
        if not group_match:
            return []

        try:
            group_clause = group_match.group(1).strip()
            if not group_clause:
                raise ValueError("Empty GROUP BY clause")

            fields = [field.strip() for field in group_clause.split(',')]

            for field in fields:
                if not field:
                    raise ValueError("Empty field name in GROUP BY")
                if not QueryParser._is_valid_field_name(field):
                    raise ValueError(f"Invalid field name in GROUP BY: {field}")

            return fields

        except Exception as e:
            raise ValueError(f"Error parsing GROUP BY clause: {str(e)}")

    @staticmethod
    def validate_query_syntax(query: str) -> Tuple[bool, str]:
        try:
            query = query.strip()
            if not query:
                return False, "Empty query"

            if not re.search(r'SELECT\s+.+\s+FROM\s+\w+', query, re.IGNORECASE):
                return False, "Query must have SELECT ... FROM ... structure"

            if not QueryParser._check_balanced_parentheses(query):
                return False, "Unbalanced parentheses in query"

            if not QueryParser._check_balanced_quotes(query):
                return False, "Unbalanced quotes in query"

            try:
                QueryParser.parse_select(query)
            except Exception as e:
                return False, f"SELECT clause error: {str(e)}"

            where_match = re.search(r'WHERE\s+(.*?)(?:\s+GROUP|\s+ORDER|\s+LIMIT|\s*$)', query, re.IGNORECASE)
            if where_match:
                try:
                    QueryParser.parse_where(where_match.group(1))
                except Exception as e:
                    return False, f"WHERE clause error: {str(e)}"

            try:
                QueryParser.parse_order_by(query)
            except Exception as e:
                return False, f"ORDER BY clause error: {str(e)}"

            try:
                QueryParser.parse_group_by(query)
            except Exception as e:
                return False, f"GROUP BY clause error: {str(e)}"

            return True, ""

        except Exception as e:
            return False, f"Query validation error: {str(e)}"

    @staticmethod
    def _check_balanced_parentheses(text: str) -> bool:
        count = 0
        in_quotes = False
        quote_char = None

        for char in text:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif not in_quotes:
                if char == '(':
                    count += 1
                elif char == ')':
                    count -= 1
                    if count < 0:
                        return False

        return count == 0

    @staticmethod
    def _check_balanced_quotes(text: str) -> bool:
        single_quote_count = 0
        double_quote_count = 0
        i = 0

        while i < len(text):
            char = text[i]
            if char == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    i += 1
                else:
                    single_quote_count += 1
            elif char == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    i += 1
                else:
                    double_quote_count += 1
            i += 1

        return single_quote_count % 2 == 0 and double_quote_count % 2 == 0

    @staticmethod
    def _parse_condition(condition_str: str) -> 'WhereCondition':
        condition_str = condition_str.strip()
        if not condition_str:
            raise ValueError("Empty condition")

        try:
            is_null_match = re.match(r'(\w+(?:\.\w+)?)\s+IS\s+NOT\s+NULL', condition_str, re.IGNORECASE)
            if is_null_match:
                field = is_null_match.group(1).strip()
                return WhereCondition(field, 'IS NOT', None)

            is_null_match = re.match(r'(\w+(?:\.\w+)?)\s+IS\s+NULL', condition_str, re.IGNORECASE)
            if is_null_match:
                field = is_null_match.group(1).strip()
                return WhereCondition(field, 'IS', None)

            between_match = re.match(r'(\w+(?:\.\w+)?)\s+(?:NOT\s+)?BETWEEN\s+(.+?)\s+AND\s+(.+)', condition_str,
                                     re.IGNORECASE)
            if between_match:
                field = between_match.group(1).strip()
                value1 = QueryParser._parse_value(between_match.group(2).strip())
                value2 = QueryParser._parse_value(between_match.group(3).strip())
                operator = 'NOT BETWEEN' if 'NOT BETWEEN' in condition_str.upper() else 'BETWEEN'
                return WhereCondition(field, operator, (value1, value2))

            in_match = re.match(r'(\w+(?:\.\w+)?)\s+(NOT\s+)?IN\s*\((.*?)\)', condition_str, re.IGNORECASE)
            if in_match:
                field = in_match.group(1).strip()
                is_not = bool(in_match.group(2))
                values_str = in_match.group(3).strip()

                values = QueryParser._parse_in_values(values_str)
                operator = 'NOT IN' if is_not else 'IN'
                return WhereCondition(field, operator, values)

            operators = ['>=', '<=', '!=', '<>', '>', '<', '=', 'NOT LIKE', 'NOT ILIKE', 'LIKE', 'ILIKE']

            for op in operators:
                pattern = f'\\s*{re.escape(op)}\\s*'
                if re.search(pattern, condition_str, re.IGNORECASE):
                    parts = re.split(pattern, condition_str, flags=re.IGNORECASE)
                    if len(parts) == 2:
                        field = parts[0].strip()
                        value_str = parts[1].strip()

                        if not field:
                            raise ValueError(f"Missing field name in condition: {condition_str}")

                        value = QueryParser._parse_value(value_str)
                        return WhereCondition(field, op.upper(), value)

            raise ValueError(f"No valid operator found in condition: {condition_str}")

        except Exception as e:
            raise ValueError(f"Error parsing condition '{condition_str}': {str(e)}")

    @staticmethod
    def _parse_value(value_str: str) -> Any:
        value_str = value_str.strip()
        if not value_str:
            return ""

        if value_str.upper() == 'NULL':
            return None

        if value_str.upper() in ('TRUE', 'FALSE'):
            return value_str.upper() == 'TRUE'

        if (value_str.startswith('"') and value_str.endswith('"')) or (
                value_str.startswith("'") and value_str.endswith("'")):
            return QueryParser._unescape_string(value_str[1:-1])

        try:
            if '.' in value_str or 'e' in value_str.lower():
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass

        return value_str

    @staticmethod
    def _unescape_string(s: str) -> str:
        s = s.replace("''", "'").replace('""', '"')
        s = s.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
        s = s.replace('\\\\', '\\')
        return s

    @staticmethod
    def _parse_in_values(values_str: str) -> List[Any]:
        if not values_str.strip():
            return []

        values = []
        current_value = ""
        in_quotes = False
        quote_char = None
        paren_depth = 0

        i = 0
        while i < len(values_str):
            char = values_str[i]

            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current_value += char
            elif char == quote_char and in_quotes:
                if i + 1 < len(values_str) and values_str[i + 1] == quote_char:
                    current_value += char * 2
                    i += 1
                else:
                    in_quotes = False
                    quote_char = None
                    current_value += char
            elif not in_quotes:
                if char == '(':
                    paren_depth += 1
                    current_value += char
                elif char == ')':
                    paren_depth -= 1
                    current_value += char
                elif char == ',' and paren_depth == 0:
                    if current_value.strip():
                        values.append(QueryParser._parse_value(current_value.strip()))
                    current_value = ""
                else:
                    current_value += char
            else:
                current_value += char

            i += 1

        if current_value.strip():
            values.append(QueryParser._parse_value(current_value.strip()))

        return values
