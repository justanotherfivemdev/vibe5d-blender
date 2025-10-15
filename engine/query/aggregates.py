from typing import Dict, Any, List


class AggregateFunction:
    @staticmethod
    def apply(func_name: str, field: str, data: List[Dict[str, Any]]) -> Any:
        func_name = func_name.upper()

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
            else:
                return item.get(field, None)

        if func_name == 'COUNT':
            if field == '*':
                return len(data)
            else:
                return len([item for item in data if get_field_value(item, field) is not None])

        values = []
        for item in data:
            value = get_field_value(item, field)
            if value is not None:
                try:
                    if isinstance(value, (int, float)):
                        values.append(float(value))
                    elif isinstance(value, str):
                        try:
                            if '.' in value or 'e' in value.lower():
                                values.append(float(value))
                            else:
                                values.append(float(int(value)))
                        except ValueError:
                            continue
                    elif isinstance(value, bool):
                        values.append(float(value))
                except (ValueError, TypeError):
                    continue

        if not values:
            return None

        try:
            if func_name == 'SUM':
                return sum(values)
            elif func_name == 'AVG':
                return sum(values) / len(values)
            elif func_name == 'MIN':
                return min(values)
            elif func_name == 'MAX':
                return max(values)
            elif func_name == 'STDDEV':
                if len(values) < 2:
                    return 0.0
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
                return variance ** 0.5
            elif func_name == 'VARIANCE':
                if len(values) < 2:
                    return 0.0
                mean = sum(values) / len(values)
                return sum((x - mean) ** 2 for x in values) / (len(values) - 1)
            else:
                raise ValueError(f"Unsupported aggregate function: {func_name}")

        except Exception as e:
            raise ValueError(f"Error calculating {func_name}: {str(e)}")

        return None
