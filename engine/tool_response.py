import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Dict


class ToolCategory(Enum):
    EXECUTION = "execution"
    QUERY = "query"
    RENDER = "render"
    ANALYSIS = "analysis"
    WEB_SEARCH = "web_search"
    PROPERTIES = "properties"
    SCENE_CONTEXT = "scene_context"


class ToolStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"


class ToolDisplayHint(Enum):
    HIDE = "hide"
    COMPACT = "compact"
    DETAILED = "detailed"
    ERROR_ALERT = "error_alert"


@dataclass
class ToolResponse:
    tool_name: str
    category: ToolCategory
    status: ToolStatus
    display_message: str
    display_hint: ToolDisplayHint
    data: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_llm_format(self) -> Dict[str, Any]:
        result = {
            'status': self.status.value,
        }

        if self.data is not None:
            result["result"] = self.data
        elif self.error_message:
            result["result"] = self.error_message
        else:
            result["result"] = self.display_message

        if self.metadata:
            result["metadata"] = self.metadata

        return result

    def to_ui_format(self) -> str:
        return self.display_message

    def to_storage_format(self) -> str:
        return json.dumps({
            'tool_name': self.tool_name,
            'category': self.category.value,
            'status': self.status.value,
            'display_message': self.display_message,
            'display_hint': self.display_hint.value,
            'data': self.data,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'metadata': self.metadata or {}
        })

    @classmethod
    def from_storage_format(cls, json_str: str) -> 'ToolResponse':
        data = json.loads(json_str)
        return cls(
            tool_name=data["tool_name"],
            category=ToolCategory(data["category"]),
            status=ToolStatus(data["status"]),
            display_message=data["display_message"],
            display_hint=ToolDisplayHint(data.get("display_hint", "compact")),
            data=data.get("data"),
            error_message=data.get("error_message"),
            execution_time_ms=data.get("execution_time_ms"),
            metadata=data.get("metadata", {})
        )

    @classmethod
    def from_legacy_format(cls, legacy_result: Dict[str, Any], tool_name: str = "unknown") -> 'ToolResponse':

            status_str = legacy_result.get("status", "success")
            status = ToolStatus.SUCCESS if status_str == "success" else ToolStatus.ERROR

            result_data = legacy_result.get("result", "")

            if isinstance(result_data, str):
                display_message = result_data if len(result_data) < 50 else "[Tool completed]"
            else:
                display_message = "[Tool completed]"

            return cls(
                tool_name=tool_name,
                category=ToolCategory.EXECUTION,
                status=status,
                display_message=display_message,
                display_hint=ToolDisplayHint.COMPACT,
                data=result_data,
                error_message=result_data if status == ToolStatus.ERROR else None
            )
