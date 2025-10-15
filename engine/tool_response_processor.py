from typing import Dict, Any

from .tool_response import (
    ToolResponse,
    ToolCategory,
    ToolStatus,
    ToolDisplayHint
)


class ToolResponseProcessor:

    @staticmethod
    def create_execution_response(success: bool, console_output: str = "", error: str = "") -> ToolResponse:
        if success:
            if console_output.strip():
                display = "[Code executed]"
                data = f"Code executed successfully.\n\nConsole output:\n{console_output.strip()}"
            else:
                display = "[Code executed]"
                data = "Code executed successfully. (No console output)"

            return ToolResponse(
                tool_name="execute",
                category=ToolCategory.EXECUTION,
                status=ToolStatus.SUCCESS,
                display_message=display,
                display_hint=ToolDisplayHint.COMPACT,
                data={"result": data}
            )
        else:
            error_msg = error or console_output or "Code execution failed"
            return ToolResponse(
                tool_name="execute",
                category=ToolCategory.EXECUTION,
                status=ToolStatus.ERROR,
                display_message="[Code execution failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error_msg},
                error_message=error_msg
            )

    @staticmethod
    def create_query_response(success: bool, query_result: Dict = None, error: str = None) -> ToolResponse:
        if success and query_result:
            count = query_result.get("count", 0)
            display = f"[Found {count} results]" if count > 0 else "[Query completed]"

            return ToolResponse(
                tool_name="query",
                category=ToolCategory.QUERY,
                status=ToolStatus.SUCCESS,
                display_message=display,
                display_hint=ToolDisplayHint.COMPACT,
                data=query_result,
                metadata={"result_count": count}
            )
        else:
            return ToolResponse(
                tool_name="query",
                category=ToolCategory.QUERY,
                status=ToolStatus.ERROR,
                display_message="[Query failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or "Query execution failed"},
                error_message=error
            )

    @staticmethod
    def create_scene_context_response(success: bool, context_data: Dict = None, error: str = None) -> ToolResponse:
        if success and context_data:
            return ToolResponse(
                tool_name="scene_context",
                category=ToolCategory.SCENE_CONTEXT,
                status=ToolStatus.SUCCESS,
                display_message="[Scene analyzed]",
                display_hint=ToolDisplayHint.COMPACT,
                data={"result": context_data}
            )
        else:
            return ToolResponse(
                tool_name="scene_context",
                category=ToolCategory.SCENE_CONTEXT,
                status=ToolStatus.ERROR,
                display_message="[Scene analysis failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or "Scene context retrieval failed"},
                error_message=error
            )

    @staticmethod
    def create_viewport_response(success: bool, image_data: Dict = None, error: str = None) -> ToolResponse:
        if success and image_data:
            return ToolResponse(
                tool_name="viewport",
                category=ToolCategory.RENDER,
                status=ToolStatus.SUCCESS,
                display_message="[Viewport captured]",
                display_hint=ToolDisplayHint.COMPACT,
                data={"result": image_data},
                metadata={"has_image": True}
            )
        else:
            return ToolResponse(
                tool_name="viewport",
                category=ToolCategory.RENDER,
                status=ToolStatus.ERROR,
                display_message="[Viewport capture failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or "Viewport capture failed"},
                error_message=error
            )

    @staticmethod
    def create_render_sync_response(success: bool, render_data: Dict = None, error: str = None) -> ToolResponse:
        if success and render_data:
            return ToolResponse(
                tool_name="see_render",
                category=ToolCategory.RENDER,
                status=ToolStatus.SUCCESS,
                display_message="[Render captured]",
                display_hint=ToolDisplayHint.COMPACT,
                data={"result": render_data},
                metadata={"has_image": True}
            )
        else:
            return ToolResponse(
                tool_name="see_render",
                category=ToolCategory.RENDER,
                status=ToolStatus.ERROR,
                display_message="[Render failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or "Render failed"},
                error_message=error
            )

    @staticmethod
    def create_render_async_response(success: bool, render_data: Dict = None, error: str = None) -> ToolResponse:
        if success and render_data:
            render_id = render_data.get("render_id", "")
            used_existing = render_data.get("used_existing", False)
            status_str = render_data.get("status", "started")

            if status_str == "completed" or used_existing:
                display = "[Render completed]"
                status = ToolStatus.SUCCESS
            else:
                display = "[Render started]"
                status = ToolStatus.STARTED

            return ToolResponse(
                tool_name="render_async",
                category=ToolCategory.RENDER,
                status=status,
                display_message=display,
                display_hint=ToolDisplayHint.COMPACT,
                data={"result": render_data},
                metadata={"render_id": render_id, "used_existing": used_existing}
            )
        else:
            return ToolResponse(
                tool_name="render_async",
                category=ToolCategory.RENDER,
                status=ToolStatus.ERROR,
                display_message="[Render failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or "Async render failed"},
                error_message=error
            )

    @staticmethod
    def create_render_result_response(success: bool, result_data: Dict = None, error: str = None) -> ToolResponse:
        if success and result_data:
            status_str = result_data.get("status", "completed")

            if status_str == "rendering":
                display = "[Render in progress]"
                status = ToolStatus.IN_PROGRESS
            else:
                display = "[Render completed]"
                status = ToolStatus.SUCCESS

            return ToolResponse(
                tool_name="get_render_result",
                category=ToolCategory.RENDER,
                status=status,
                display_message=display,
                display_hint=ToolDisplayHint.COMPACT,
                data={"result": result_data}
            )
        else:
            return ToolResponse(
                tool_name="get_render_result",
                category=ToolCategory.RENDER,
                status=ToolStatus.ERROR,
                display_message="[Render result not found]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or "Render result retrieval failed"},
                error_message=error
            )

    @staticmethod
    def create_cancel_render_response(success: bool, render_id: str = "", error: str = None) -> ToolResponse:
        if success:
            return ToolResponse(
                tool_name="cancel_render",
                category=ToolCategory.RENDER,
                status=ToolStatus.CANCELLED,
                display_message="[Render cancelled]",
                display_hint=ToolDisplayHint.COMPACT,
                data={"result": f"Render {render_id} cancelled successfully"},
                metadata={"render_id": render_id}
            )
        else:
            return ToolResponse(
                tool_name="cancel_render",
                category=ToolCategory.RENDER,
                status=ToolStatus.ERROR,
                display_message="[Render cancellation failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or f"Failed to cancel render {render_id}"},
                error_message=error
            )

    @staticmethod
    def create_list_renders_response(success: bool, renders_data: Dict = None, error: str = None) -> ToolResponse:
        if success and renders_data:
            count = renders_data.get("count", 0)
            return ToolResponse(
                tool_name="list_active_renders",
                category=ToolCategory.RENDER,
                status=ToolStatus.SUCCESS,
                display_message="[Render status]",
                display_hint=ToolDisplayHint.COMPACT,
                data={"result": renders_data},
                metadata={"active_count": count}
            )
        else:
            return ToolResponse(
                tool_name="list_active_renders",
                category=ToolCategory.RENDER,
                status=ToolStatus.ERROR,
                display_message="[Render status failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or "Failed to list active renders"},
                error_message=error
            )

    @staticmethod
    def create_object_screenshot_response(success: bool, screenshot_data: Dict = None,
                                          error: str = None) -> ToolResponse:
        if success and screenshot_data:
            return ToolResponse(
                tool_name="screenshot_object",
                category=ToolCategory.ANALYSIS,
                status=ToolStatus.SUCCESS,
                display_message="[Object screenshot captured]",
                display_hint=ToolDisplayHint.COMPACT,
                data={"result": screenshot_data},
                metadata={"has_image": True}
            )
        else:
            return ToolResponse(
                tool_name="screenshot_object",
                category=ToolCategory.ANALYSIS,
                status=ToolStatus.ERROR,
                display_message="[Object screenshot failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or "Object screenshot failed"},
                error_message=error
            )

    @staticmethod
    def create_web_search_response(success: bool, result_count: int = 0, search_data: Any = None,
                                   error: str = None) -> ToolResponse:
        if success:
            display = f"[Found {result_count} results]" if result_count > 0 else "[Search completed]"
            return ToolResponse(
                tool_name="web_search",
                category=ToolCategory.WEB_SEARCH,
                status=ToolStatus.SUCCESS,
                display_message=display,
                display_hint=ToolDisplayHint.COMPACT,
                data=search_data,
                metadata={"result_count": result_count}
            )
        else:
            return ToolResponse(
                tool_name="web_search",
                category=ToolCategory.WEB_SEARCH,
                status=ToolStatus.ERROR,
                display_message="[Web search failed]",
                display_hint=ToolDisplayHint.ERROR_ALERT,
                data={"result": error or "Web search failed"},
                error_message=error
            )

    @staticmethod
    def create_error_response(tool_name: str, error: str,
                              category: ToolCategory = ToolCategory.EXECUTION) -> ToolResponse:
        return ToolResponse(
            tool_name=tool_name,
            category=category,
            status=ToolStatus.ERROR,
            display_message="[Tool failed]",
            display_hint=ToolDisplayHint.ERROR_ALERT,
            data={"result": error},
            error_message=error
        )
