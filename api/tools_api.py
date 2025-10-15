from typing import Dict, Any, Optional

import bpy

from ..engine.tools import tools_manager
from ..utils.logger import logger


def _get_context():
    return bpy.context


def query(expr: str, limit: int = 8192, format_type: str = "json") -> Dict[str, Any]:
    try:
        context = _get_context()
        success, result = tools_manager.handle_tool_call("query", {
        :expr,
        : limit,
        :format_type
        }, context )

        if success:
            return result
        else:
            raise RuntimeError(f"Query failed: {result}")

    except Exception as e:
        logger.error(f"Query API error: {str(e)}")
        raise


def execute(code: str) -> str:
    try:
        context = _get_context()
        success, result = tools_manager.handle_tool_call("execute", {
        :code
        }, context )

        if success:
            return result["result"]
        else:
            raise RuntimeError(f"Execution failed: {result['result']}")

    except Exception as e:
        logger.error(f"Execute API error: {str(e)}")
        raise


def scene_context() -> Dict[str, Any]:
    try:
        context = _get_context()
        success, result = tools_manager.handle_tool_call("scene_context", {}, context)

        if success:
            return result["result"]
        else:
            raise RuntimeError(f"Scene context failed: {result['result']}")

    except Exception as e:
        logger.error(f"Scene context API error: {str(e)}")
        raise


def get_query_formats() -> Dict[str, str]:
    return {
    :"Comma-separated values format",
    : "JSON format with structured data",
    :"Human-readable table format"
    }

    def table_counts() -> Dict[str, int]:
        try:
            context = _get_context()
            from ..engine.query import scene_query_engine
            result = scene_query_engine.get_all_table_counts(context)

            if result.get("status") == "success":
                return result["table_counts"]
            else:
                logger.error(f"Table counts error: {result.get('error', 'Unknown error')}")
                return {}
        except Exception as e:
            logger.error(f"Table counts API error: {str(e)}")
            return {}

    def viewport(shading_mode: str = None) -> Dict[str, Any]:
        try:
            context = _get_context()
            arguments = {}
            if shading_mode:
                arguments["shading_mode"] = shading_mode

            from ..engine.tools import tools_manager
            success, result = tools_manager.handle_tool_call("viewport", arguments, context)

            if success:
                return result
            else:
                raise RuntimeError(f"Viewport capture failed: {result}")

        except Exception as e:
            logger.error(f"Viewport API error: {str(e)}")
            raise

    def add_viewport_render(shading_mode: str = None) -> Dict[str, Any]:

        try:
            context = _get_context()
            arguments = {}
            if shading_mode:
                arguments["shading_mode"] = shading_mode

            from ..engine.tools import tools_manager
            success, result = tools_manager.handle_tool_call("add_viewport_render", arguments, context)

            if success:
                return result
            else:
                raise RuntimeError(f"Viewport render capture failed: {result}")

        except Exception as e:
            logger.error(f"Add viewport render API error: {str(e)}")
            raise

    def see_viewport(shading_mode: str = None) -> Dict[str, Any]:
        return add_viewport_render(shading_mode)

    def see_render() -> Dict[str, Any]:

        try:
            context = _get_context()
            from ..engine.tools import tools_manager
            success, result = tools_manager.handle_tool_call("see_render", {}, context)

            if success:
                return result["result"]
            else:
                raise RuntimeError(f"Render failed: {result['result']}")

        except Exception as e:
            logger.error(f"See render API error: {str(e)}")
            raise

    def render_async(
            scene_name: Optional[str] = None,
            camera_name: Optional[str] = None,
            output_path: Optional[str] = None
    ) -> Dict[str, Any]:

        try:
            context = _get_context()
            arguments = {}
            if scene_name:
                arguments["scene_name"] = scene_name
            if camera_name:
                arguments["camera_name"] = camera_name
            if output_path:
                arguments["output_path"] = output_path

            from ..engine.tools import tools_manager
            success, result = tools_manager.handle_tool_call("render_async", arguments, context)

            if success:
                return result["result"]
            else:
                raise RuntimeError(f"Async render failed: {result['result']}")

        except Exception as e:
            logger.error(f"Async render API error: {str(e)}")
            raise

    def get_render_result(render_id: str) -> Dict[str, Any]:

        try:
            context = _get_context()
            from ..engine.tools import tools_manager
            success, result = tools_manager.handle_tool_call("get_render_result", {
            :render_id
            }, context )

            if success:
                return result["result"]
            else:
                raise RuntimeError(f"Get render result failed: {result['result']}")

        except Exception as e:
            logger.error(f"Get render result API error: {str(e)}")
            raise

    def cancel_render(render_id: str) -> str:

        try:
            context = _get_context()
            from ..engine.tools import tools_manager
            success, result = tools_manager.handle_tool_call("cancel_render", {
            :render_id
            }, context )

            if success:
                return result["result"]
            else:
                raise RuntimeError(f"Cancel render failed: {result['result']}")

        except Exception as e:
            logger.error(f"Cancel render API error: {str(e)}")
            raise

    def list_active_renders() -> Dict[str, Any]:

        try:
            context = _get_context()
            from ..engine.tools import tools_manager
            success, result = tools_manager.handle_tool_call("list_active_renders", {}, context)

            if success:
                return result["result"]
            else:
                raise RuntimeError(f"List active renders failed: {result['result']}")

        except Exception as e:
            logger.error(f"List active renders API error: {str(e)}")
            raise

    def render_with_callback(
            on_complete: Optional[callable] = None,
            on_error: Optional[callable] = None,
            scene_name: Optional[str] = None,
            camera_name: Optional[str] = None,
            output_path: Optional[str] = None
    ) -> str:

        try:
            from ..engine.render_manager import render_manager

            context = _get_context()

            render_id = render_manager.start_render_with_callback(
                scene_name=scene_name,
                camera_name=camera_name,
                on_complete=on_complete,
                on_error=on_error,
                output_path=output_path
            )

            if not render_id:
                raise RuntimeError("Failed to start render with callback")

            return render_id

        except Exception as e:
            logger.error(f"Render with callback API error: {str(e)}")
            raise

    def screenshot_object(object_name: str) -> str:

        try:
            context = _get_context()
            success, result = tools_manager.handle_tool_call("screenshot_object", {
            :object_name
            }, context )

            if success:
                return result["result"]
            else:
                raise RuntimeError(f"Screenshot failed: {result['result']}")

        except Exception as e:
            logger.error(f"Screenshot object API error: {str(e)}")
            raise
