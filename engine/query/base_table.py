from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Generator


class BaseTable(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        pass

    def count(self, context, where: Optional[Any] = None) -> int:
        count = 0
        for _ in self.iterate(context, fields=['name'], where=where, limit=None):
            count += 1
        return count

    def _matches_where(self, data: Dict[str, Any], where: Optional[Any]) -> bool:
        if where is None:
            return True
        return where.evaluate(data)

    def _get_field_value(self, obj: Any, field: str) -> Any:
        if '.' in field:
            field_parts = field.split('.')
            current_value = obj

            for part in field_parts:
                if hasattr(current_value, part):
                    current_value = getattr(current_value, part)
                elif isinstance(current_value, dict) and part in current_value:
                    current_value = current_value[part]
                else:
                    return None

            return current_value
        else:
            if hasattr(obj, field):
                return getattr(obj, field)
            elif isinstance(obj, dict) and field in obj:
                return obj[field]
            return None
