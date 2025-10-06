"""
Tools module for Vibe4D addon.

Implements backend tools that can be called by the AI assistant:
- execute: Code execution (existing)
- query: Scene data querying with SQL-like syntax
- custom_props: Custom properties access
- render_settings: Render configuration retrieval
- scene_graph: Scene hierarchy analysis  
- nodes_graph: Node tree information
- render_async: Asynchronous render with callback support
"""

import base64
import locale
import math
import os
import platform
import tempfile
from typing import Dict, Any, Optional, Tuple

import bpy
import gpu
from gpu.types import GPUTexture
from mathutils import Vector, Matrix, Euler, Quaternion, Color

from .executor import code_executor
from .query import scene_query_engine
from .render_manager import render_manager
from ..utils.logger import logger


def _get_target_object(target: bpy.types.ID) -> bpy.types.Object:
    if isinstance(target, bpy.types.Object):
        return target

    if isinstance(target, bpy.types.Mesh):
        for ob in bpy.data.objects:
            if ob.data is target:
                return ob
        raise ValueError("Mesh datablock is not used by any object in the scene")

    raise TypeError(
        f"Expected bpy.types.Object or bpy.types.Mesh, got {type(target).__name__}")


def _frame_camera_corner(cam: bpy.types.Object, obj: bpy.types.Object, /,
                         margin: float = 1.05) -> None:
    """Place *cam* on the (+X, –Y, +Z) diagonal so that *obj* fits entirely."""

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_obj = obj.evaluated_get(depsgraph)

    bpy.context.view_layer.update()
    corners_world = [evaluated_obj.matrix_world @ Vector(c) for c in evaluated_obj.bound_box]
    centre = sum(corners_world, Vector()) / 8.0
    radius = max((c - centre).length for c in corners_world)

    direction = Vector((1, -1, 1)).normalized()
    fov = max(cam.data.angle_x, cam.data.angle_y)
    distance = (radius * margin) / math.tan(fov * 0.5)

    cam.location = centre + direction * distance
    cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = distance / 50
    cam.data.clip_end = distance * 50


def _pick_resolution(o: bpy.types.Object) -> tuple[int, int]:
    deps = bpy.context.evaluated_depsgraph_get()
    eval_obj = o.evaluated_get(deps)
    mesh = eval_obj.to_mesh()
    poly_cnt = len(mesh.polygons)
    eval_obj.to_mesh_clear()

    base = (512 if poly_cnt < 10_000
            else 768 if poly_cnt < 50_000
    else 1024)

    world_bb = [eval_obj.matrix_world @ Vector(c) for c in o.bound_box]
    xs, ys, zs = zip(*[(v.x, v.y, v.z) for v in world_bb])

    width_xy = max(max(xs) - min(xs), max(ys) - min(ys))
    height_z = max(zs) - min(zs)
    height_z = max(height_z, 0.0001)

    aspect = width_xy / height_z

    WIDE_LIMIT = 1.10
    TALL_LIMIT = 0.90

    if aspect > WIDE_LIMIT:
        res_x = base
        res_y = int(base / aspect)
    elif aspect < TALL_LIMIT:
        res_y = base
        res_x = int(base * aspect)
    else:
        res_x = res_y = base

    res_x = max(128, min(res_x, 2048))
    res_y = max(128, min(res_y, 2048))
    return res_x, res_y


def _img_to_uri(filepath):
    with open(filepath, 'rb') as f:
        image_data = f.read()

    base64_data = base64.b64encode(image_data).decode('utf-8')
    return f"data:image/png;base64,{base64_data}"


class ToolsManager:
    """Manages and dispatches tool calls."""

    def __init__(self):
        self.tools = {
            'execute': self._execute_tool,
            'query': self._query_tool,
            'scene_context': self._scene_context_tool,
            'viewport': self._viewport_tool,
            'add_viewport_render': self._viewport_tool,
            'see_viewport': self._viewport_tool,
            'see_render': self._see_render_tool,
            'render_async': self._render_async_tool,
            'get_render_result': self._get_render_result_tool,
            'cancel_render': self._cancel_render_tool,
            'list_active_renders': self._list_active_renders_tool,
            'analyse_mesh_image': self._analyse_mesh_image_tool,
        }

        render_manager.register_handlers()

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        """Handle a tool call."""
        if tool_name not in self.tools:
            return False, {"status": "error", "result": f"Unknown tool: {tool_name}"}

        try:
            success, result = self.tools[tool_name](arguments, context)
            if success:

                if isinstance(result, dict):
                    result["status"] = "success"
                    return True, result
                else:
                    return True, {"status": "success", "result": result}
            else:

                if isinstance(result, dict):
                    result["status"] = "error"
                    return False, result
                else:
                    return False, {"status": "error", "result": result}
        except Exception as e:
            logger.error(f"Error in tool '{tool_name}': {str(e)}")
            return False, {"status": "error", "result": str(e)}

    def _execute_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        """Execute Python code."""
        try:
            code = arguments.get("code", "")
            if not code:
                return False, {"result": "No code provided"}

            prepare_success, prepare_error = code_executor.prepare_execution(code)
            if not prepare_success:
                return False, {"result": prepare_error or "Code preparation failed"}

            success, error = code_executor.execute_code(context)

            if success:

                console_output = getattr(context.scene, 'vibe4d_console_output', '')
                if console_output and console_output.strip():

                    result = f"Code executed successfully.\n\nConsole output:\n{console_output.strip()}"
                else:
                    result = "Code executed successfully. (No console output)"

                return True, {"result": result}
            else:
                return False, {"result": error or "Code execution failed"}

        except Exception as e:
            logger.error(f"Execute tool error: {str(e)}")
            return False, {"result": f"Execution error: {str(e)}"}

    def _query_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        """Query scene data."""
        try:
            query = arguments.get("expr", "")
            if not query:
                return False, {"result": "No query provided"}

            limit = arguments.get("limit", 8192)
            format_type = arguments.get("format", "json")

            result = scene_query_engine.execute_query(query, limit, context, format_type)

            return True, {"result": result}

        except Exception as e:
            logger.error(f"Query tool error: {str(e)}")
            return False, {"result": f"Query error: {str(e)}"}

    def _scene_context_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        """Get scene context information."""
        try:

            selected_objects = [obj.name for obj in context.selected_objects]
            active_object = context.active_object.name if context.active_object else None

            current_file_path = bpy.data.filepath if bpy.data.filepath else None

            current_language = locale.getdefaultlocale()[0] if locale.getdefaultlocale()[0] else None

            info = {
                "scene_name": context.scene.name,
                "frame_current": context.scene.frame_current,
                "frame_start": context.scene.frame_start,
                "frame_end": context.scene.frame_end,
                "render_engine": context.scene.render.engine,
                "blender_version": bpy.app.version_string,
                "current_file_path": current_file_path,
                "user_os": platform.system(),
                "window_resolution": {
                    "width": context.window.width,
                    "height": context.window.height
                },
                "dpi": context.preferences.system.dpi,
                "language": current_language,
                "selected_objects": selected_objects,
                "active_object": active_object,
            }

            return True, {"result": info}

        except Exception as e:
            logger.error(f"Scene context tool error: {str(e)}")
            return False, {"result": f"Scene context error: {str(e)}"}

    def _viewport_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            logger.info(f"Starting viewport capture with arguments: {arguments}")

            shading_mode = arguments.get("shading_mode", None)
            logger.info(f"Shading mode requested: {shading_mode}")

            view3d_area = None
            available_areas = []
            for area in context.screen.areas:
                available_areas.append(area.type)
                if area.type == 'VIEW_3D':
                    view3d_area = area
                    break

            logger.info(f"Available areas: {available_areas}")

            if not view3d_area:
                error_msg = f"No active 3D viewport found. Available areas: {available_areas}"
                logger.error(error_msg)
                return False, error_msg

            logger.info(f"Found 3D viewport area: {view3d_area}")

            space_3d = None
            available_spaces = []
            for space in view3d_area.spaces:
                available_spaces.append(space.type)
                if space.type == 'VIEW_3D':
                    space_3d = space
                    break

            logger.info(f"Available spaces in 3D area: {available_spaces}")

            if not space_3d:
                error_msg = f"No 3D viewport space found. Available spaces: {available_spaces}"
                logger.error(error_msg)
                return False, error_msg

            original_shading_type = space_3d.shading.type

            if shading_mode and shading_mode in ['WIREFRAME', 'SOLID', 'MATERIAL', 'RENDERED']:
                space_3d.shading.type = shading_mode
                logger.info(f"Changed shading mode to: {shading_mode}")

            view3d_area.tag_redraw()
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_filepath = temp_file.name
            temp_file.close()

            try:

                bpy.ops.screen.screenshot(filepath=temp_filepath)

                if not os.path.exists(temp_filepath):
                    return False, "Screenshot was not created"

                file_size = os.path.getsize(temp_filepath)
                logger.info(f"Screenshot captured, file size: {file_size} bytes")

                with open(temp_filepath, 'rb') as f:
                    image_data = f.read()

                import base64
                base64_data = base64.b64encode(image_data).decode('utf-8')
                data_uri = f"data:image/png;base64,{base64_data}"

                logger.info(f"Successfully encoded {len(base64_data)} characters of base64 data")

                return True, {
                    "result": {
                        "image_data": data_uri,
                        "width": view3d_area.width,
                        "height": view3d_area.height,
                        "original_viewport_size": [view3d_area.width, view3d_area.height],
                        "size_bytes": file_size,
                        "format": "PNG",
                        "shading_mode": shading_mode or original_shading_type
                    }
                }

            finally:

                if shading_mode and shading_mode in ['WIREFRAME', 'SOLID', 'MATERIAL', 'RENDERED']:
                    space_3d.shading.type = original_shading_type
                    logger.info(f"Restored shading mode to: {original_shading_type}")

                try:
                    os.unlink(temp_filepath)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temporary file: {cleanup_error}")

        except Exception as e:
            logger.error(f"Viewport capture failed with exception: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False, f"Viewport capture failed: {str(e)}"

    def _see_render_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            logger.info("Starting synchronous render with user control")

            scene_name = arguments.get("scene_name", None)
            camera_name = arguments.get("camera_name", None)

            scene = bpy.data.scenes.get(scene_name) if scene_name else context.scene
            camera = scene.camera
            if camera_name:
                camera = bpy.data.objects.get(camera_name)

            existing_result = render_manager._get_existing_render_result(scene, camera)
            if existing_result:
                return True, {"result": existing_result}

            result_data = render_manager.render_sync(
                scene_name=scene_name,
                camera_name=camera_name,
                output_path=None
            )

            logger.info(f"Synchronous render completed successfully")

            return True, {"result": result_data}

        except Exception as e:
            logger.error(f"Synchronous render tool failed: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            return False, {"result": f"Render failed: {str(e)}"}

    def _render_async_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        """Start an asynchronous render operation with callback support."""
        try:
            scene_name = arguments.get("scene_name", None)
            camera_name = arguments.get("camera_name", None)
            output_path = arguments.get("output_path", None)

            completion_data = {}
            error_data = {}

            def on_complete(result_data):
                """Callback for render completion."""
                completion_data['result'] = result_data
                completion_data['completed'] = True
                logger.info(f"Async render completed: {result_data.get('render_id', 'unknown')}")

            def on_error(error_msg):
                """Callback for render error."""
                error_data['error'] = error_msg
                error_data['failed'] = True
                logger.error(f"Async render failed: {error_msg}")

            render_id = render_manager.start_render_with_callback(
                scene_name=scene_name,
                camera_name=camera_name,
                on_complete=on_complete,
                on_error=on_error,
                output_path=output_path
            )

            if not render_id:
                return False, {"result": "Failed to start render"}

            if completion_data.get('completed'):
                result_data = completion_data['result']
                return True, {
                    "result": {
                        **result_data,
                        "status": "completed",
                        "message": f"Used existing render result with ID: {render_id}",
                        "used_existing": True
                    }
                }

            result_data = {
                "render_id": render_id,
                "status": "started",
                "message": f"Async render started with ID: {render_id}",
                "scene_name": scene_name or context.scene.name,
                "camera_name": camera_name or (context.scene.camera.name if context.scene.camera else None),
                "used_existing": False
            }

            return True, {"result": result_data}

        except Exception as e:
            logger.error(f"Async render tool error: {str(e)}")
            return False, {"result": f"Async render error: {str(e)}"}

    def _get_render_result_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        """Get the result of an async render operation."""
        try:
            render_id = arguments.get("render_id", "")
            if not render_id:
                return False, {"result": "No render ID provided"}

            result_data = render_manager.get_render_result(render_id)

            if result_data:
                return True, {"result": result_data}
            else:

                if render_manager.is_render_active(render_id):
                    return True, {"result": {"status": "rendering", "render_id": render_id}}
                else:
                    return False, {"result": f"Render result not found for ID: {render_id}"}

        except Exception as e:
            logger.error(f"Get render result tool error: {str(e)}")
            return False, {"result": f"Get render result error: {str(e)}"}

    def _cancel_render_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        """Cancel an active render operation."""
        try:
            render_id = arguments.get("render_id", "")
            if not render_id:
                return False, {"result": "No render ID provided"}

            success = render_manager.cancel_render(render_id)

            if success:
                return True, {"result": f"Render {render_id} cancelled successfully"}
            else:
                return False, {"result": f"Failed to cancel render {render_id}"}

        except Exception as e:
            logger.error(f"Cancel render tool error: {str(e)}")
            return False, {"result": f"Cancel render error: {str(e)}"}

    def _list_active_renders_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        """List all active render operations."""
        try:
            active_renders = render_manager.get_active_renders()

            result_data = {
                "active_renders": active_renders,
                "count": len(active_renders)
            }

            return True, {"result": result_data}

        except Exception as e:
            logger.error(f"List active renders tool error: {str(e)}")
            return False, {"result": f"List active renders error: {str(e)}"}

    def _analyse_mesh_image_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        """Analyze a mesh image by rendering a specific object and sending it for AI analysis."""
        try:
            object_name = arguments.get("object_name")
            if not object_name:
                return False, {"result": "object_name is required"}

            target_object = bpy.data.objects.get(object_name)
            if not target_object:
                return False, {"result": f"Object '{object_name}' not found in scene"}

            if target_object.type != 'MESH':
                return False, {"result": f"Object '{object_name}' is not a mesh object (type: {target_object.type})"}

            image_data = self._render_object_for_analysis(target_object)
            if not image_data:
                return False, {"result": f"Failed to render object '{object_name}'"}

            return True, {
                "result": {
                    "image_data": image_data,
                },
            }

        except Exception as e:
            logger.error(f"Analyse mesh image tool error: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            return False, {"result": f"Analysis error: {str(e)}"}

    def _render_object_for_analysis(self, target) -> Optional[str]:
        sun_energy = 1.5
        sun_yaw_deg = 35.0
        sun_pitch_deg = -15.0
        preserve_world_env = True
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        filepath = tmp.name
        tmp.close()

        obj = _get_target_object(target)

        scn = bpy.context.scene
        win = bpy.context.window

        cache = {
            "view_layer": win.view_layer,
            "camera": scn.camera,
            "engine": scn.render.engine,
            "filepath": scn.render.filepath,
            "film_transparent": scn.render.film_transparent,
            "res_x": scn.render.resolution_x,
            "res_y": scn.render.resolution_y,
            "world_use_nodes": scn.world.use_nodes if scn.world else None,
            "objects_hide_render": {o: o.hide_render for o in bpy.data.objects},
        }

        cam_data = bpy.data.cameras.new("_TMP_CAM_DATA")
        cam_obj = bpy.data.objects.new("_TMP_CAM", cam_data)

        sun_data = bpy.data.lights.new("_TMP_SUN_DATA", type='SUN')
        sun_data.energy = sun_energy
        sun_obj = bpy.data.objects.new("_TMP_SUN", sun_data)

        iso_col = bpy.data.collections.new("_TMP_COL")
        scn.collection.children.link(iso_col)
        for o in (obj, cam_obj, sun_obj):
            iso_col.objects.link(o)

        iso_layer = scn.view_layers.new(name="_TMP_LAYER")

        def _recursive_exclude(lc: bpy.types.LayerCollection, keep: bpy.types.Collection):
            lc.exclude = (lc.collection is not keep)
            for child in lc.children:
                _recursive_exclude(child, keep)

        _recursive_exclude(iso_layer.layer_collection, iso_col)

        res_x, res_y = _pick_resolution(obj)

        try:

            scn.render.engine = 'BLENDER_EEVEE_NEXT'
            scn.render.film_transparent = True
            scn.render.filepath = filepath
            scn.render.resolution_x, scn.render.resolution_y = res_x, res_y

            _frame_camera_corner(cam_obj, obj)

            cam_quat = cam_obj.rotation_euler.to_quaternion()
            sun_orient = (
                    Quaternion((0, 0, 1), math.radians(sun_yaw_deg)) @
                    Quaternion((1, 0, 0), math.radians(sun_pitch_deg)) @
                    cam_quat
            )
            sun_obj.location = cam_obj.location
            sun_obj.rotation_euler = sun_orient.to_euler()

            win.view_layer = iso_layer
            scn.camera = cam_obj

            for o in bpy.data.objects:
                if o not in (obj, cam_obj, sun_obj):
                    o.hide_render = True

            if not preserve_world_env and scn.world:
                scn.world.use_nodes = False

            bpy.ops.render.render(write_still=True, use_viewport=False)

            return _img_to_uri(filepath)

        finally:

            win.view_layer = cache["view_layer"]
            scn.camera = cache["camera"]
            scn.render.engine = cache["engine"]
            scn.render.filepath = cache["filepath"]
            scn.render.film_transparent = cache["film_transparent"]
            scn.render.resolution_x = cache["res_x"]
            scn.render.resolution_y = cache["res_y"]
            if scn.world and cache["world_use_nodes"] is not None:
                scn.world.use_nodes = cache["world_use_nodes"]
            for o, hidden in cache["objects_hide_render"].items():
                o.hide_render = hidden

            scn.view_layers.remove(iso_layer)
            scn.collection.children.unlink(iso_col)
            bpy.data.collections.remove(iso_col)

            for ob in (cam_obj, sun_obj):
                data = ob.data
                bpy.data.objects.remove(ob, do_unlink=True)
                if isinstance(data, bpy.types.Camera):
                    bpy.data.cameras.remove(data, do_unlink=True)
                elif isinstance(data, bpy.types.Light):
                    bpy.data.lights.remove(data, do_unlink=True)

            bpy.context.view_layer.update()

    def cleanup(self):
        render_manager.cleanup()


tools_manager = ToolsManager()
