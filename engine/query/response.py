from typing import Dict, Any, Union, List


class QueryResponse:
    def __init__(self, status: str, data: Union[Any, str, List] = None, error: str = None,
                 count: int = 0, format_type: str = "compact"):
        self.status = status
        self.data = data
        self.error = error
        self.count = count
        self.format_type = format_type

    def to_dict(self) -> Dict[str, Any]:
        response = {
            'status': self.status,
            'format': self.format_type,
            'count': self.count
        }

        if self.status == "success":
            response["data"] = self.data
        else:
            response["error"] = self.error

        return response
