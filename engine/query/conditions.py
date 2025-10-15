import re
from typing import Dict, Any


class WhereCondition:
    def __init__(self, field: str, operator: str, value: Any):
        self.field = field
        self.operator = operator.upper()
        self.value = value
        self.negated = False

    def evaluate(self, item: Dict[str, Any]) -> bool:
        if '.' in self.field:
            field_parts = self.field.split('.')
            current_value = item

            for part in field_parts:
                if isinstance(current_value, dict) and part in current_value:
                    current_value = current_value[part]
                else:
                    if self.operator in ('IS', 'IS NOT'):
                        current_value = None
                        break
                    else:
                        result = False
                        return not result if self.negated else result

            item_value = current_value
        else:
            if self.field not in item:
                if self.operator in ('IS', 'IS NOT'):
                    item_value = None
                else:
                    result = False
                    return not result if self.negated else result
            else:
                item_value = item[self.field]

        try:
            if self.operator not in ('IS', 'IS NOT', 'IN', 'NOT IN', 'BETWEEN', 'NOT BETWEEN'):
                if isinstance(item_value, (int, float)) and isinstance(self.value, str):
                    try:
                        if '.' in str(self.value) or 'e' in str(self.value).lower():
                            self.value = float(self.value)
                        else:
                            self.value = int(self.value)
                    except ValueError:
                        pass
                elif isinstance(item_value, bool) and isinstance(self.value, str):
                    self.value = self.value.lower() in ['true', '1', 'yes', 'on']
                elif isinstance(item_value, str) and isinstance(self.value, (int, float)):
                    item_value = str(item_value)
        except Exception:
            pass

        result = False

        if self.operator == '=':
            result = item_value == self.value
        elif self.operator in ('!=', '<>'):
            result = item_value != self.value
        elif self.operator == '>':
            try:
                result = item_value > self.value
            except TypeError:
                result = str(item_value) > str(self.value)
        elif self.operator == '<':
            try:
                result = item_value < self.value
            except TypeError:
                result = str(item_value) < str(self.value)
        elif self.operator == '>=':
            try:
                result = item_value >= self.value
            except TypeError:
                result = str(item_value) >= str(self.value)
        elif self.operator == '<=':
            try:
                result = item_value <= self.value
            except TypeError:
                result = str(item_value) <= str(self.value)
        elif self.operator == 'LIKE':
            pattern = str(self.value).replace('%', '.*').replace('_', '.')
            result = bool(re.search(pattern, str(item_value), re.IGNORECASE))
        elif self.operator == 'NOT LIKE':
            pattern = str(self.value).replace('%', '.*').replace('_', '.')
            result = not bool(re.search(pattern, str(item_value), re.IGNORECASE))
        elif self.operator == 'ILIKE':
            pattern = str(self.value).replace('%', '.*').replace('_', '.')
            result = bool(re.search(pattern, str(item_value), re.IGNORECASE))
        elif self.operator == 'NOT ILIKE':
            pattern = str(self.value).replace('%', '.*').replace('_', '.')
            result = not bool(re.search(pattern, str(item_value), re.IGNORECASE))
        elif self.operator == 'IN':
            if isinstance(self.value, (list, tuple)):
                result = item_value in self.value
            else:
                result = False
        elif self.operator == 'NOT IN':
            if isinstance(self.value, (list, tuple)):
                result = item_value not in self.value
            else:
                result = True
        elif self.operator == 'IS':
            if self.value is None:
                result = item_value is None
            else:
                result = item_value == self.value
        elif self.operator == 'IS NOT':
            if self.value is None:
                result = item_value is not None
            else:
                result = item_value != self.value
        elif self.operator == 'BETWEEN':
            if isinstance(self.value, (list, tuple)) and len(self.value) == 2:
                try:
                    result = self.value[0] <= item_value <= self.value[1]
                except TypeError:
                    result = str(self.value[0]) <= str(item_value) <= str(self.value[1])
            else:
                result = False
        elif self.operator == 'NOT BETWEEN':
            if isinstance(self.value, (list, tuple)) and len(self.value) == 2:
                try:
                    result = not (self.value[0] <= item_value <= self.value[1])
                except TypeError:
                    result = not (str(self.value[0]) <= str(item_value) <= str(self.value[1]))
            else:
                result = True

        return not result if self.negated else result


class WhereExpression:
    def __init__(self):
        self.conditions = []
        self.operators = []
        self.negated = False

    def add_condition(self, condition: WhereCondition, operator: str = None):
        self.conditions.append(condition)
        if operator:
            self.operators.append(operator.upper())

    def evaluate(self, item: Dict[str, Any]) -> bool:
        if not self.conditions:
            result = True
        else:
            result = self.conditions[0].evaluate(item)

            for i, operator in enumerate(self.operators):
                next_result = self.conditions[i + 1].evaluate(item)
                if operator == 'AND':
                    result = result and next_result
                elif operator == 'OR':
                    result = result or next_result

        return not result if self.negated else result
