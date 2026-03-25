import base64
import locale
import math
import os
import platform
import tempfile
import traceback
from typing import Dict, Any, Optional, Tuple

import bpy
from mathutils import Vector, Quaternion

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
    )


def _frame_camera_corner(cam: bpy.types.Object, obj: bpy.types.Object, /,
                         margin: float = 1.05) -> None:
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


POLY_COUNT_THRESHOLD_LOW = 10_000
POLY_COUNT_THRESHOLD_HIGH = 50_000
BASE_RESOLUTION_LOW = 512
BASE_RESOLUTION_MID = 768
BASE_RESOLUTION_HIGH = 1024
ASPECT_RATIO_WIDE_THRESHOLD = 1.10
ASPECT_RATIO_TALL_THRESHOLD = 0.90
MIN_RESOLUTION = 128
MAX_RESOLUTION = 2048
MIN_HEIGHT_EPSILON = 0.0001
VALID_SHADING_MODES = ['WIREFRAME', 'SOLID', 'MATERIAL', 'RENDERED']
ANALYSIS_SUN_ENERGY = 1.5
ANALYSIS_SUN_YAW_DEG = 35.0
ANALYSIS_SUN_PITCH_DEG = -15.0
TEMP_CAMERA_DATA_NAME = "_TMP_CAM_DATA"
TEMP_CAMERA_OBJECT_NAME = "_TMP_CAM"
TEMP_SUN_DATA_NAME = "_TMP_SUN_DATA"
TEMP_SUN_OBJECT_NAME = "_TMP_SUN"
TEMP_COLLECTION_NAME = "_TMP_COL"
TEMP_LAYER_NAME = "_TMP_LAYER"


def _pick_resolution(o: bpy.types.Object) -> tuple[int, int]:
    deps = bpy.context.evaluated_depsgraph_get()
    eval_obj = o.evaluated_get(deps)
    mesh = eval_obj.to_mesh()
    poly_cnt = len(mesh.polygons)
    eval_obj.to_mesh_clear()

    if poly_cnt < POLY_COUNT_THRESHOLD_LOW:
        base = BASE_RESOLUTION_LOW
    elif poly_cnt < POLY_COUNT_THRESHOLD_HIGH:
        base = BASE_RESOLUTION_MID
    else:
        base = BASE_RESOLUTION_HIGH

    world_bb = [eval_obj.matrix_world @ Vector(c) for c in o.bound_box]
    xs, ys, zs = zip(*[(v.x, v.y, v.z) for v in world_bb])

    width_xy = max(max(xs) - min(xs), max(ys) - min(ys))
    height_z = max(max(zs) - min(zs), MIN_HEIGHT_EPSILON)
    aspect = width_xy / height_z

    if aspect > ASPECT_RATIO_WIDE_THRESHOLD:
        res_x = base
        res_y = int(base / aspect)
    elif aspect < ASPECT_RATIO_TALL_THRESHOLD:
        res_y = base
        res_x = int(base * aspect)
    else:
        res_x = res_y = base

    res_x = max(MIN_RESOLUTION, min(res_x, MAX_RESOLUTION))
    res_y = max(MIN_RESOLUTION, min(res_y, MAX_RESOLUTION))
    return res_x, res_y


def _img_to_uri(filepath):
    with open(filepath, 'rb') as f:
        image_data = f.read()

    base64_data = base64.b64encode(image_data).decode('utf-8')
    return f"data:image/png;base64,{base64_data}"


def _upload_image_to_server(image_data_bytes: bytes, source_type: str, context) -> Optional[str]:
    try:
        from ..api.client import api_client
        from ..auth.manager import auth_manager

        if not auth_manager.is_authenticated(context):
            logger.warning("Not authenticated, cannot upload image")
            return None

        user_id = getattr(context.window_manager, 'vibe5d_user_id', '')
        token = getattr(context.window_manager, 'vibe5d_user_token', '')

        from ..utils.history_manager import history_manager
        chat_id = history_manager.get_current_chat_id(context)

        if not chat_id:
            logger.warning("No active chat session, cannot upload image")
            return None

        success, image_id = api_client.upload_image(chat_id, image_data_bytes, source_type, user_id, token)

        if success and image_id:
            logger.info(f"Successfully uploaded {source_type} image: {image_id}")
            return image_id
        else:
            logger.warning(f"Failed to upload {source_type} image")
            return None

    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return None


class ToolsManager:

    def __init__(self):
        self.tools = {
            'execute': self._execute_tool,
            'execute_code': self._execute_tool,
            'query': self._query_tool,
            'scene_query': self._query_tool,
            'scene_context': self._scene_context_tool,
            'see_viewport': self._viewport_tool,
            'viewport': self._viewport_tool,
            'screenshot_viewport': self._viewport_tool,
            'see_current_viewport': self._viewport_tool,
            'screenshot_camera_view': self._screenshot_camera_view_tool,
            'screenshot': self._screenshot_tool,
            'see_render': self._see_render_tool,
            'render_sync': self._see_render_tool,
            'render_async': self._render_async_tool,
            'get_render_result': self._get_render_result_tool,
            'cancel_render': self._cancel_render_tool,
            'list_active_renders': self._list_active_renders_tool,
            'screenshot_object': self._screenshot_object_tool,
            'import_image': self._import_image_tool,
        }

        render_manager.register_handlers()

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        if tool_name not in self.tools:
            return False, {"status": "error", "result": f"Unknown tool: {tool_name}"}

        try:
            success, result = self.tools[tool_name](arguments, context)
            status = "success" if success else "error"

            if isinstance(result, dict):
                result["status"] = status
                return success, result

            return success, {"status": status, "result": result}
        except Exception as e:
            logger.error(f"Error in tool '{tool_name}': {str(e)}")
            return False, {"status": "error", "result": str(e)}

    def _execute_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            code = arguments.get("code", "")
            if not code:
                return False, {"result": "No code provided"}

            prepare_success, prepare_error = code_executor.prepare_execution(code)
            if not prepare_success:
                return False, {"result": prepare_error or "Code preparation failed"}

            success, error = code_executor.execute_code(context)

            if success:
                console_output = getattr(context.scene, 'vibe5d_console_output', '')
                return True, {"result": "Success", "console_output": console_output}

            return False, {"result": error or "Code execution failed"}

        except Exception as e:
            logger.error(f"Execute tool error: {str(e)}")
            return False, {"result": f"Execution error: {str(e)}"}

    def _query_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            query = arguments.get("sql", arguments.get("expr", ""))
            if not query:
                return False, {"result": "No query provided"}

            limit = arguments.get("limit", 100)
            format_type = arguments.get("format", "csv")
            result = scene_query_engine.execute_query(query, limit, context, format_type)

            return True, {"result": result}

        except Exception as e:
            logger.error(f"Query tool error: {str(e)}")
            return False, {"result": f"Query error: {str(e)}"}

    def _scene_context_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            selected_objects = [obj.name for obj in context.selected_objects]
            active_object = context.active_object.name if context.active_object else None
            current_file_path = bpy.data.filepath if bpy.data.filepath else None
            current_language = locale.getdefaultlocale()[0] if locale.getdefaultlocale()[0] else None

            info = {
                'scene_name': context.scene.name,
                'frame_current': context.scene.frame_current,
                'frame_start': context.scene.frame_start,
                'frame_end': context.scene.frame_end,
                'render_engine': context.scene.render.engine,
                'blender_version': bpy.app.version_string,
                'file_path': current_file_path,
                'os': platform.system(),
                'window_size': {
                    'width': context.window.width,
                    'height': context.window.height
                },
                'dpi': context.preferences.system.dpi,
                'language': current_language,
                'selected_objects': selected_objects,
                'active_object': active_object,
            }

            return True, {"result": info}

        except Exception as e:
            logger.error(f"Scene context tool error: {str(e)}")
            return False, {"result": f"Scene context error: {str(e)}"}

    def _viewport_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            shading_mode = arguments.get("shading_mode", None)

            if not hasattr(context, 'screen') or not context.screen:
                return False, {"result": "No screen context available"}

            view3d_area = next((area for area in context.screen.areas if area.type == 'VIEW_3D'), None)
            if not view3d_area:
                return False, {"result": "No active 3D viewport found"}

            space_3d = next((space for space in view3d_area.spaces if space.type == 'VIEW_3D'), None)
            if not space_3d:
                return False, {"result": "No 3D viewport space found"}

            scene = context.scene
            original_filepath = scene.render.filepath
            original_res_x = scene.render.resolution_x
            original_res_y = scene.render.resolution_y
            original_res_percentage = scene.render.resolution_percentage
            original_file_format = scene.render.image_settings.file_format
            original_engine = scene.render.engine

            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_filepath = temp_file.name
            temp_file.close()

            try:
                scene.render.filepath = temp_filepath
                scene.render.image_settings.file_format = 'PNG'

                if shading_mode == 'WIREFRAME':
                    scene.render.engine = 'BLENDER_WORKBENCH'
                    scene.display.shading.light = 'FLAT'
                    scene.display.shading.color_type = 'SINGLE'
                    scene.display.shading.wireframe_color_type = 'OBJECT'
                elif shading_mode == 'SOLID':
                    scene.render.engine = 'BLENDER_WORKBENCH'
                    scene.display.shading.light = 'STUDIO'
                    scene.display.shading.color_type = 'MATERIAL'
                elif shading_mode == 'MATERIAL' or shading_mode == 'RENDERED':
                    if scene.render.engine == 'BLENDER_WORKBENCH':
                        scene.render.engine = 'BLENDER_EEVEE_NEXT'

                bpy.ops.render.opengl(write_still=True)

                if not os.path.exists(temp_filepath):
                    return False, {"result": "Viewport render was not created"}

                file_size = os.path.getsize(temp_filepath)

                with open(temp_filepath, 'rb') as f:
                    image_data = f.read()

                base64_data = base64.b64encode(image_data).decode('utf-8')
                data_uri = f"data:image/png;base64,{base64_data}"

                image_id = _upload_image_to_server(image_data, "viewport", context)

                result_data = {
                    'image_data': data_uri,
                    'width': original_res_x,
                    'height': original_res_y,
                    'file_size': file_size,
                    'format': "PNG",
                    'shading_mode': shading_mode
                }

                if image_id:
                    result_data["image_id"] = image_id

                try:
                    os.unlink(temp_filepath)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temporary file: {cleanup_error}")

                return True, {"result": result_data}

            finally:
                scene.render.filepath = original_filepath
                scene.render.resolution_x = original_res_x
                scene.render.resolution_y = original_res_y
                scene.render.resolution_percentage = original_res_percentage
                scene.render.image_settings.file_format = original_file_format
                scene.render.engine = original_engine

        except Exception as e:
            logger.error(f"Viewport capture failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False, {"result": f"Viewport capture failed: {str(e)}"}

    def _screenshot_camera_view_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            camera_name = arguments.get("camera_name", None)
            frame = arguments.get("frame", None)
            shading_mode = arguments.get("shading_mode", None)

            scene = context.scene
            camera = scene.camera

            if camera_name:
                camera = bpy.data.objects.get(camera_name)
                if not camera:
                    return False, {"result": f"Camera '{camera_name}' not found"}
                if camera.type != 'CAMERA':
                    return False, {"result": f"Object '{camera_name}' is not a camera (type: {camera.type})"}
            elif not camera:
                return False, {"result": "No active camera in scene and no camera_name provided"}

            original_camera = scene.camera
            original_frame = scene.frame_current
            original_filepath = scene.render.filepath
            original_res_x = scene.render.resolution_x
            original_res_y = scene.render.resolution_y
            original_res_percentage = scene.render.resolution_percentage
            original_file_format = scene.render.image_settings.file_format

            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_filepath = temp_file.name
            temp_file.close()

            try:
                scene.camera = camera

                if frame is not None:
                    scene.frame_set(frame)

                scene.render.filepath = temp_filepath
                scene.render.image_settings.file_format = 'PNG'

                if shading_mode == 'WIREFRAME':
                    scene.render.engine = 'BLENDER_WORKBENCH'
                    scene.display.shading.light = 'FLAT'
                    scene.display.shading.color_type = 'SINGLE'
                    scene.display.shading.wireframe_color_type = 'OBJECT'
                elif shading_mode == 'SOLID':
                    scene.render.engine = 'BLENDER_WORKBENCH'
                    scene.display.shading.light = 'STUDIO'
                    scene.display.shading.color_type = 'MATERIAL'
                elif shading_mode == 'MATERIAL' or shading_mode == 'RENDERED':
                    if scene.render.engine == 'BLENDER_WORKBENCH':
                        scene.render.engine = 'BLENDER_EEVEE_NEXT'

                bpy.ops.render.opengl(write_still=True)

                if not os.path.exists(temp_filepath):
                    return False, {"result": "Render was not created"}

                file_size = os.path.getsize(temp_filepath)

                with open(temp_filepath, 'rb') as f:
                    image_data = f.read()

                base64_data = base64.b64encode(image_data).decode('utf-8')
                data_uri = f"data:image/png;base64,{base64_data}"

                image_id = _upload_image_to_server(image_data, "camera_view", context)

                result_data = {
                    'image_data': data_uri,
                    'width': original_res_x,
                    'height': original_res_y,
                    'camera': camera.name,
                    'frame': frame if frame is not None else original_frame,
                    'file_size': file_size,
                    'format': "PNG",
                    'shading_mode': shading_mode
                }

                if image_id:
                    result_data["image_id"] = image_id

                try:
                    os.unlink(temp_filepath)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temporary file: {cleanup_error}")

                return True, {"result": result_data}

            finally:
                scene.camera = original_camera
                scene.render.filepath = original_filepath
                scene.render.resolution_x = original_res_x
                scene.render.resolution_y = original_res_y
                scene.render.resolution_percentage = original_res_percentage
                scene.render.image_settings.file_format = original_file_format
                if frame is not None:
                    scene.frame_set(original_frame)

        except Exception as e:
            logger.error(f"Camera view screenshot failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False, {"result": f"Camera view screenshot failed: {str(e)}"}

    def _screenshot_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_filepath = temp_file.name
            temp_file.close()

            try:
                bpy.ops.screen.screenshot(filepath=temp_filepath)

                if not os.path.exists(temp_filepath):
                    return False, {"result": "Screenshot was not created"}

                file_size = os.path.getsize(temp_filepath)

                with open(temp_filepath, 'rb') as f:
                    image_data = f.read()

                base64_data = base64.b64encode(image_data).decode('utf-8')
                data_uri = f"data:image/png;base64,{base64_data}"

                image_id = _upload_image_to_server(image_data, "screenshot", context)

                result_data = {
                    'image_data': data_uri,
                    'file_size': file_size,
                    'format': "PNG"
                }

                if context.window:
                    result_data["window_width"] = context.window.width
                    result_data["window_height"] = context.window.height

                if image_id:
                    result_data["image_id"] = image_id

                try:
                    os.unlink(temp_filepath)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temporary file: {cleanup_error}")

                return True, {"result": result_data}

            except Exception as screenshot_error:
                try:
                    os.unlink(temp_filepath)
                except:
                    pass
                raise screenshot_error

        except Exception as e:
            logger.error(f"Screenshot failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False, {"result": f"Screenshot failed: {str(e)}"}

    def _see_render_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            scene_name = arguments.get("scene_name", None)
            camera_name = arguments.get("camera_name", None)

            scene = bpy.data.scenes.get(scene_name) if scene_name else context.scene
            camera = scene.camera
            if camera_name:
                camera = bpy.data.objects.get(camera_name)

            existing_result = render_manager._get_existing_render_result(scene, camera)
            if existing_result:
                result_with_upload = self._add_image_id_to_render_result(existing_result, context)
                return True, {"result": result_with_upload}

            result_data = render_manager.render_sync(
                scene_name=scene_name,
                camera_name=camera_name,
                output_path=None
            )

            result_with_upload = self._add_image_id_to_render_result(result_data, context)
            return True, {"result": result_with_upload}

        except Exception as e:
            logger.error(f"Synchronous render failed: {str(e)}")
            logger.error(traceback.format_exc())
            return False, {"result": f"Render failed: {str(e)}"}

    def _render_async_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            scene_name = arguments.get("scene_name", None)
            camera_name = arguments.get("camera_name", None)
            output_path = arguments.get("output_path", None)

            completion_data = {}
            error_data = {}

            def on_complete(result_data):
                completion_data['result'] = result_data
                completion_data['completed'] = True

            def on_error(error_msg):
                error_data['error'] = error_msg
                error_data['failed'] = True

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
                    'result': {
                        **result_data,
                        'status': "completed",
                        'message': f"Used existing render result with ID: {render_id}",
                        'used_existing': True
                    }
                }

            result_data = {
                'render_id': render_id,
                'status': "started",
                'message': f"Async render started with ID: {render_id}",
                'scene_name': scene_name or context.scene.name,
                'camera_name': camera_name or (context.scene.camera.name if context.scene.camera else None),
                'used_existing': False
            }

            return True, {"result": result_data}

        except Exception as e:
            logger.error(f"Async render tool error: {str(e)}")
            return False, {"result": f"Async render error: {str(e)}"}

    def _get_render_result_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            render_id = arguments.get("render_id", "")
            if not render_id:
                return False, {"result": "No render ID provided"}

            result_data = render_manager.get_render_result(render_id)

            if result_data:
                return True, {"result": result_data}

            if render_manager.is_render_active(render_id):
                return True, {"result": {"status": "rendering", "render_id": render_id}}

            return False, {"result": f"Render result not found for ID: {render_id}"}

        except Exception as e:
            logger.error(f"Get render result tool error: {str(e)}")
            return False, {"result": f"Get render result error: {str(e)}"}

    def _cancel_render_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            render_id = arguments.get("render_id", "")
            if not render_id:
                return False, {"result": "No render ID provided"}

            success = render_manager.cancel_render(render_id)

            if success:
                return True, {"result": f"Render {render_id} cancelled successfully"}

            return False, {"result": f"Failed to cancel render {render_id}"}

        except Exception as e:
            logger.error(f"Cancel render tool error: {str(e)}")
            return False, {"result": f"Cancel render error: {str(e)}"}

    def _list_active_renders_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            active_renders = render_manager.get_active_renders()

            return True, {
                'result': {
                    'active_renders': active_renders,
                    'count': len(active_renders)
                }
            }

        except Exception as e:
            logger.error(f"List active renders tool error: {str(e)}")
            return False, {"result": f"List active renders error: {str(e)}"}

    def _screenshot_object_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:
        try:
            object_name = arguments.get("object_name")
            if not object_name:
                return False, {"result": "object_name is required"}

            target_object = bpy.data.objects.get(object_name)
            if not target_object:
                return False, {"result": f"Object '{object_name}' not found in scene"}

            if target_object.type != 'MESH':
                return False, {"result": f"Object '{object_name}' is not a mesh object (type: {target_object.type})"}

            image_data = self._render_object_isolated(target_object)
            if not image_data:
                return False, {"result": f"Failed to render object '{object_name}'"}

            data_uri_prefix = "data:image/png;base64,"
            if image_data.startswith(data_uri_prefix):
                base64_part = image_data[len(data_uri_prefix):]
                image_bytes = base64.b64decode(base64_part)
                image_id = _upload_image_to_server(image_bytes, "object_screenshot", context)

                result_data = {"image_data": image_data}
                if image_id:
                    result_data["image_id"] = image_id

                return True, {"result": result_data}
            else:
                return True, {"result": {"image_data": image_data}}

        except Exception as e:
            logger.error(f"Screenshot object tool error: {str(e)}")
            logger.error(traceback.format_exc())
            return False, {"result": f"Screenshot error: {str(e)}"}

    def _render_object_isolated(self, target) -> Optional[str]:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        filepath = tmp.name
        tmp.close()

        obj = _get_target_object(target)

        scn = bpy.context.scene
        win = bpy.context.window

        cache = {
            'view_layer': win.view_layer,
            'camera': scn.camera,
            'engine': scn.render.engine,
            'filepath': scn.render.filepath,
            'film_transparent': scn.render.film_transparent,
            'res_x': scn.render.resolution_x,
            'res_y': scn.render.resolution_y,
            'world_use_nodes': scn.world.use_nodes if scn.world else None,
            'objects_hide_render': {o: o.hide_render for o in bpy.data.objects},
        }

        cam_data = bpy.data.cameras.new(TEMP_CAMERA_DATA_NAME)
        cam_obj = bpy.data.objects.new(TEMP_CAMERA_OBJECT_NAME, cam_data)

        sun_data = bpy.data.lights.new(TEMP_SUN_DATA_NAME, type='SUN')
        sun_data.energy = ANALYSIS_SUN_ENERGY
        sun_obj = bpy.data.objects.new(TEMP_SUN_OBJECT_NAME, sun_data)

        iso_col = bpy.data.collections.new(TEMP_COLLECTION_NAME)
        scn.collection.children.link(iso_col)
        for o in (obj, cam_obj, sun_obj):
            iso_col.objects.link(o)

        iso_layer = scn.view_layers.new(name=TEMP_LAYER_NAME)

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
                    Quaternion((0, 0, 1), math.radians(ANALYSIS_SUN_YAW_DEG)) @
                    Quaternion((1, 0, 0), math.radians(ANALYSIS_SUN_PITCH_DEG)) @
                    cam_quat
            )
            sun_obj.location = cam_obj.location
            sun_obj.rotation_euler = sun_orient.to_euler()

            win.view_layer = iso_layer
            scn.camera = cam_obj

            for o in bpy.data.objects:
                if o not in (obj, cam_obj, sun_obj):
                    o.hide_render = True

            if scn.world:
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

    def _import_image_tool(self, arguments: Dict[str, Any], context) -> Tuple[bool, Any]:

        try:
            image_id = arguments.get("image_id", "")
            import_type = arguments.get("import_type", "texture")
            custom_name = arguments.get("name", "")

            if not image_id:
                return False, {"result": "image_id is required"}

            if import_type not in ["texture", "image_plane", "background"]:
                return False, {
                    "result": f"Invalid import_type: {import_type}. Must be texture, image_plane, or background"}

            from ..api.client import api_client
            from ..auth.manager import auth_manager

            if not auth_manager.is_authenticated(context):
                return False, {"result": "Not authenticated. Please log in first."}

            user_id = getattr(context.window_manager, 'vibe5d_user_id', '')
            token = getattr(context.window_manager, 'vibe5d_user_token', '')

            chat_id_prop = getattr(context.scene, 'vibe5d_current_chat_id', '')
            if not chat_id_prop:
                return False, {"result": "No active chat session"}

            logger.info(f"Downloading image {image_id} from chat {chat_id_prop}")
            success, image_data = api_client.download_image(chat_id_prop, image_id, user_id, token)

            if not success or not image_data:
                return False, {"result": f"Failed to download image {image_id}"}

            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            temp_path = temp_file.name
            temp_file.close()

            try:
                with open(temp_path, 'wb') as f:
                    f.write(image_data)

                logger.debug(f"Wrote {len(image_data)} bytes to temp file: {temp_path}")

                if not os.path.exists(temp_path):
                    logger.error(f"Temp file was not created: {temp_path}")
                    return False, {"result": "Failed to create temporary image file"}

                file_size = os.path.getsize(temp_path)
                if file_size != len(image_data):
                    logger.error(f"File size mismatch: expected {len(image_data)}, got {file_size}")
                    return False, {"result": "Image file size mismatch"}

                image_name = custom_name if custom_name else f"vibe5d_{image_id}"

                if import_type == "texture":
                    if image_name in bpy.data.images:
                        bpy.data.images.remove(bpy.data.images[image_name])

                    logger.debug(f"Loading image from {temp_path}")
                    try:
                        img = bpy.data.images.load(temp_path)
                    except Exception as load_error:
                        logger.error(f"Failed to load image from {temp_path}: {str(load_error)}")
                        return False, {"result": f"Blender failed to load image: {str(load_error)}"}

                    img.name = image_name
                    img.pack()

                    return True, {
                        'result': f"Image '{image_name}' loaded as texture data block",
                        'image_name': image_name,
                        'import_type': "texture"
                    }

                elif import_type == "image_plane":
                    if image_name in bpy.data.images:
                        bpy.data.images.remove(bpy.data.images[image_name])

                    logger.debug(f"Loading image from {temp_path}")
                    try:
                        img = bpy.data.images.load(temp_path)
                    except Exception as load_error:
                        logger.error(f"Failed to load image from {temp_path}: {str(load_error)}")
                        return False, {"result": f"Blender failed to load image: {str(load_error)}"}

                    img.name = image_name
                    img.pack()

                    aspect_ratio = img.size[0] / img.size[1] if img.size[1] > 0 else 1.0

                    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
                    plane = context.active_object
                    plane.name = f"{image_name}_plane"
                    plane.scale.x = aspect_ratio

                    mat = bpy.data.materials.new(name=f"{image_name}_mat")
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    nodes.clear()

                    node_tex = nodes.new(type='ShaderNodeTexImage')
                    node_tex.image = img
                    node_tex.location = (0, 0)

                    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                    node_bsdf.location = (300, 0)

                    node_output = nodes.new(type='ShaderNodeOutputMaterial')
                    node_output.location = (600, 0)

                    links = mat.node_tree.links
                    links.new(node_tex.outputs['Color'], node_bsdf.inputs['Base Color'])
                    links.new(node_tex.outputs['Alpha'], node_bsdf.inputs['Alpha'])
                    links.new(node_bsdf.outputs['BSDF'], node_output.inputs['Surface'])

                    mat.blend_method = 'BLEND'

                    plane.data.materials.append(mat)

                    return True, {
                        'result': f"Image plane '{plane.name}' created with image '{image_name}'",
                        'object_name': plane.name,
                        'image_name': image_name,
                        'import_type': "image_plane"
                    }

                elif import_type == "background":
                    if image_name in bpy.data.images:
                        bpy.data.images.remove(bpy.data.images[image_name])

                    logger.debug(f"Loading image from {temp_path}")
                    try:
                        img = bpy.data.images.load(temp_path)
                    except Exception as load_error:
                        logger.error(f"Failed to load image from {temp_path}: {str(load_error)}")
                        return False, {"result": f"Blender failed to load image: {str(load_error)}"}

                    img.name = image_name
                    img.pack()

                    world = context.scene.world
                    if world is None:
                        world = bpy.data.worlds.new("World")
                        context.scene.world = world

                    world.use_nodes = True
                    nodes = world.node_tree.nodes
                    nodes.clear()

                    node_tex = nodes.new(type='ShaderNodeTexEnvironment')
                    node_tex.image = img
                    node_tex.location = (0, 0)

                    node_background = nodes.new(type='ShaderNodeBackground')
                    node_background.location = (300, 0)

                    node_output = nodes.new(type='ShaderNodeOutputWorld')
                    node_output.location = (600, 0)

                    links = world.node_tree.links
                    links.new(node_tex.outputs['Color'], node_background.inputs['Color'])
                    links.new(node_background.outputs['Background'], node_output.inputs['Surface'])

                    return True, {
                        'result': f"Image '{image_name}' set as world background",
                        'image_name': image_name,
                        'import_type': "background"
                    }

            finally:
                if os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

        except Exception as e:
            logger.error(f"Import image tool error: {str(e)}")
            logger.error(traceback.format_exc())
            return False, {"result": f"Import error: {str(e)}"}

    def _add_image_id_to_render_result(self, result_data: Dict[str, Any], context) -> Dict[str, Any]:

        try:
            if not result_data or "image_data" not in result_data:
                return result_data

            image_data_uri = result_data["image_data"]
            data_uri_prefix = "data:image/png;base64,"

            if image_data_uri.startswith(data_uri_prefix):
                base64_part = image_data_uri[len(data_uri_prefix):]
                image_bytes = base64.b64decode(base64_part)
                image_id = _upload_image_to_server(image_bytes, "render", context)

                if image_id:
                    result_data["image_id"] = image_id
                    logger.debug(f"Added image_id {image_id} to render result")

            return result_data

        except Exception as e:
            logger.warning(f"Failed to add image_id to render result: {str(e)}")
            return result_data

    def cleanup(self):
        render_manager.cleanup()


tools_manager = ToolsManager()
