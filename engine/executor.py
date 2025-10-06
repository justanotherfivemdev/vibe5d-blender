"""
Code execution engine for Vibe4D addon.

Handles safe code execution with comprehensive rollback capabilities and error reporting.
"""

import sys
import time
import traceback
from typing import Dict, Any, Optional, Tuple

import bpy
from mathutils import Vector, Euler, Quaternion, Matrix

from .script_guard import script_guard
from .snapshot_optimizer import snapshot_optimizer
from ..utils.logger import logger


class ComprehensiveExecutionState:
    """Tracks comprehensive execution state for robust rollback functionality."""

    def __init__(self):
        self.is_executing = False
        self.execution_id = None
        self.execution_content = ""
        self.error_info = None

        self.scene_snapshot = None
        self.objects_snapshot = None
        self.collections_snapshot = None
        self.materials_snapshot = None
        self.node_trees_snapshot = None
        self.world_snapshot = None
        self.render_settings_snapshot = None
        self.view_layer_snapshot = None

        self.existing_data = None

        self.snapshot_timestamp = None
        self.lightweight_mode = False
        self.snapshot_hash = None

    def clear(self):
        """Clear execution state."""
        self.is_executing = False
        self.execution_id = None
        self.execution_content = ""
        self.error_info = None
        self.scene_snapshot = None
        self.objects_snapshot = None
        self.collections_snapshot = None
        self.materials_snapshot = None
        self.node_trees_snapshot = None
        self.world_snapshot = None
        self.render_settings_snapshot = None
        self.view_layer_snapshot = None
        self.existing_data = None
        self.snapshot_timestamp = None
        self.lightweight_mode = False
        self.snapshot_hash = None


class PrintCapture:
    """Captures print statements and stores them for UI display."""

    def __init__(self, context):
        self.context = context
        self.outputs = []
        self.original_stdout = sys.stdout

    def write(self, text):
        """Capture written text."""
        if text.strip():
            self.outputs.append(text.strip())

            try:
                current_output = getattr(self.context.scene, 'vibe4d_console_output', '')
                if current_output:
                    new_output = current_output + '\n' + text.strip()
                else:
                    new_output = text.strip()
                self.context.scene.vibe4d_console_output = new_output
            except Exception as e:
                logger.error(f"Failed to update console output: {str(e)}")

    def flush(self):
        """Required for stdout compatibility."""
        pass

    def get_output(self):
        """Get captured output as string."""
        return '\n'.join(self.outputs)


class CodeExecutor:
    """Handles safe code execution with comprehensive rollback capabilities."""

    def __init__(self):
        self.execution_state = ComprehensiveExecutionState()
        self.restricted_globals = self._create_restricted_globals()

    def _create_restricted_globals(self) -> Dict[str, Any]:
        """Create restricted globals for safe execution."""

        import builtins
        safe_builtins = {}

        excluded_builtins = {'eval', 'exec', 'compile', 'open', 'input', '__import__'}

        for name in dir(builtins):
            if not name.startswith('_') or name in ['__name__', '__doc__']:
                if name not in excluded_builtins:
                    safe_builtins[name] = getattr(builtins, name)

        return {
            '__builtins__': safe_builtins,
            'bpy': bpy,
            'bmesh': None,
            'mathutils': None,
        }

    def prepare_execution(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Prepare code for execution with safety checks.
        
        Args:
            code: Raw code content (may include markdown)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:

            python_code = script_guard.extract_python_code(code)

            if not python_code.strip():
                return False, "No Python code found to execute"

            is_safe, error_msg = script_guard.validate_code(python_code)
            if not is_safe:
                return False, f"Security check failed: {error_msg}"

            self._create_comprehensive_snapshot()

            self.execution_state.execution_content = python_code
            self.execution_state.is_executing = True
            self.execution_state.execution_id = self._generate_execution_id()

            logger.info(f"Code prepared for execution (ID: {self.execution_state.execution_id})")
            return True, None

        except Exception as e:
            error_msg = f"Failed to prepare code execution: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def execute_code(self, context) -> Tuple[bool, Optional[str]]:
        """
        Execute prepared code in safe environment.
        
        Args:
            context: Blender context
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.execution_state.is_executing:
            return False, "No code prepared for execution"

        try:
            logger.info(f"Executing code (ID: {self.execution_state.execution_id})")

            context.scene.vibe4d_console_output = ""

            safe_globals = self._prepare_safe_globals()

            print_capture = PrintCapture(context)
            original_stdout = sys.stdout

            try:

                sys.stdout = print_capture

                exec(self.execution_state.execution_content, safe_globals, safe_globals)

            finally:

                sys.stdout = original_stdout

            context.view_layer.update()
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

            logger.info("Code executed successfully")
            return True, None

        except Exception as e:

            sys.stdout = original_stdout

            error_msg = str(e)
            error_traceback = traceback.format_exc()

            self.execution_state.error_info = {
                'error': error_msg,
                'traceback': error_traceback,
                'execution_id': self.execution_state.execution_id
            }

            logger.error(f"Code execution failed: {error_msg}")
            logger.debug(f"Full traceback: {error_traceback}")

            return self._handle_execution_error(context, error_msg, error_traceback)

    def _create_comprehensive_snapshot(self):
        """Create comprehensive snapshot of current Blender state."""
        start_time = time.time()
        try:
            logger.debug("Creating comprehensive execution snapshot")
            self.execution_state.snapshot_timestamp = start_time

            self.execution_state.lightweight_mode = snapshot_optimizer.should_use_lightweight_mode(bpy.context)

            if self.execution_state.lightweight_mode:
                logger.debug("Using lightweight snapshot mode for better performance")

            self._snapshot_scene_state()

            self._snapshot_objects_state()

            self._snapshot_collections_state()

            self._snapshot_materials_state()

            self._snapshot_node_trees_state()

            self._snapshot_world_state()

            self._snapshot_render_settings()

            self._snapshot_view_layer_state()

            self._snapshot_existing_data()

            self.execution_state.snapshot_hash = snapshot_optimizer.get_scene_signature()
            snapshot_optimizer.last_snapshot_hash = self.execution_state.snapshot_hash

            elapsed = time.time() - start_time
            snapshot_optimizer.metrics.creation_time = elapsed
            snapshot_optimizer.metrics.objects_count = len(bpy.data.objects)
            snapshot_optimizer.metrics.collections_count = len(bpy.data.collections)
            snapshot_optimizer.metrics.materials_count = len(bpy.data.materials)
            snapshot_optimizer.metrics.node_trees_count = len(bpy.data.node_groups)

            snapshot_data = {
                'scene_snapshot': self.execution_state.scene_snapshot,
                'objects_snapshot': self.execution_state.objects_snapshot,
                'collections_snapshot': self.execution_state.collections_snapshot,
                'materials_snapshot': self.execution_state.materials_snapshot,
                'node_trees_snapshot': self.execution_state.node_trees_snapshot,
                'world_snapshot': self.execution_state.world_snapshot,
                'render_settings_snapshot': self.execution_state.render_settings_snapshot,
                'view_layer_snapshot': self.execution_state.view_layer_snapshot,
                'existing_data': self.execution_state.existing_data,
            }

            snapshot_size = snapshot_optimizer.estimate_snapshot_size(snapshot_data)
            snapshot_optimizer.metrics.total_data_size = snapshot_size
            snapshot_optimizer.metrics.memory_usage_mb = snapshot_size / (1024 * 1024)

            logger.debug(f"Comprehensive snapshot created in {elapsed:.3f}s "
                         f"({snapshot_optimizer.metrics.memory_usage_mb:.1f}MB, "
                         f"{snapshot_optimizer.metrics.objects_count} objects)")

            if elapsed > 0.5:
                snapshot_optimizer.cleanup_old_snapshots()

        except Exception as e:
            logger.error(f"Failed to create comprehensive snapshot: {str(e)}")
            raise

    def _snapshot_scene_state(self):
        """Snapshot basic scene state."""
        scene = bpy.context.scene
        self.execution_state.scene_snapshot = {
            'active_object': bpy.context.active_object.name if bpy.context.active_object else None,
            'selected_objects': [obj.name for obj in bpy.context.selected_objects],
            'cursor_location': scene.cursor.location.copy(),
            'frame_current': scene.frame_current,
            'frame_start': scene.frame_start,
            'frame_end': scene.frame_end,
            'active_camera': scene.camera.name if scene.camera else None,
            'tool_settings': {
                'use_keyframe_insert_auto': scene.tool_settings.use_keyframe_insert_auto,
                'transform_pivot_point': scene.tool_settings.transform_pivot_point,
                'use_snap': scene.tool_settings.use_snap,
                'snap_elements': set(scene.tool_settings.snap_elements),
            }
        }

    def _snapshot_objects_state(self):
        """Snapshot comprehensive object states."""
        self.execution_state.objects_snapshot = {}

        use_lightweight = self.execution_state.lightweight_mode

        for obj in bpy.data.objects:

            obj_state = {
                'location': obj.location.copy(),
                'rotation_euler': obj.rotation_euler.copy(),
                'rotation_mode': obj.rotation_mode,
                'scale': obj.scale.copy(),
                'hide_viewport': obj.hide_viewport,
                'hide_render': obj.hide_render,
                'data_name': obj.data.name if obj.data else None,
            }

            if not use_lightweight:
                obj_state.update({
                    'rotation_quaternion': obj.rotation_quaternion.copy(),
                    'hide_select': obj.hide_select,

                    'parent': obj.parent.name if obj.parent else None,
                    'parent_type': obj.parent_type,
                    'parent_bone': obj.parent_bone,
                    'matrix_parent_inverse': obj.matrix_parent_inverse.copy(),

                    'display_type': obj.display_type,
                    'show_wire': obj.show_wire,
                    'show_all_edges': obj.show_all_edges,
                    'show_transparent': obj.show_transparent,
                    'show_in_front': obj.show_in_front,

                    'animation_data_exists': obj.animation_data is not None,

                    'collections': [coll.name for coll in obj.users_collection],

                    'custom_properties': dict(obj.items()) if hasattr(obj, 'items') else {},

                    'modifiers': [{'name': mod.name, 'type': mod.type, 'show_viewport': mod.show_viewport,
                                   'show_render': mod.show_render} for mod in obj.modifiers],

                    'constraints': [{'name': const.name, 'type': const.type, 'mute': const.mute}
                                    for const in obj.constraints],
                })

                if obj.type == 'MESH' and obj.data:
                    obj_state['mesh_data'] = {
                        'vertices_count': len(obj.data.vertices),
                        'edges_count': len(obj.data.edges),
                        'polygons_count': len(obj.data.polygons),
                        'materials_count': len(obj.data.materials),
                    }
            else:

                obj_state.update({
                    'hide_select': obj.hide_select,
                    'parent': obj.parent.name if obj.parent else None,

                    'has_modifiers': len(obj.modifiers) > 0,
                    'has_constraints': len(obj.constraints) > 0,
                })

            self.execution_state.objects_snapshot[obj.name] = obj_state

        if not use_lightweight:
            self.execution_state.objects_snapshot = snapshot_optimizer.optimize_object_snapshot(
                self.execution_state.objects_snapshot
            )

    def _snapshot_collections_state(self):
        """Snapshot collections and their hierarchy."""
        self.execution_state.collections_snapshot = {}
        for coll in bpy.data.collections:
            coll_state = {
                'objects': [obj.name for obj in coll.objects],
                'children': [child.name for child in coll.children],
                'hide_viewport': coll.hide_viewport,
                'hide_render': coll.hide_render,
                'hide_select': coll.hide_select,
                'custom_properties': dict(coll.items()) if hasattr(coll, 'items') else {},
            }
            self.execution_state.collections_snapshot[coll.name] = coll_state

    def _snapshot_materials_state(self):
        """Snapshot materials and their essential properties."""
        self.execution_state.materials_snapshot = {}
        for mat in bpy.data.materials:
            mat_state = {
                'use_nodes': mat.use_nodes,
                'diffuse_color': mat.diffuse_color[:] if hasattr(mat, 'diffuse_color') else None,
                'metallic': getattr(mat, 'metallic', None),
                'roughness': getattr(mat, 'roughness', None),
                'use_backface_culling': mat.use_backface_culling,
                'blend_method': mat.blend_method,
                'custom_properties': dict(mat.items()) if hasattr(mat, 'items') else {},
                'node_tree_exists': mat.node_tree is not None if mat.use_nodes else False,
            }
            self.execution_state.materials_snapshot[mat.name] = mat_state

    def _snapshot_node_trees_state(self):
        """Snapshot node trees (lightweight approach for performance)."""
        self.execution_state.node_trees_snapshot = {}

        for mat in bpy.data.materials:
            if mat.use_nodes and mat.node_tree:
                tree_state = self._get_node_tree_signature(mat.node_tree)
                self.execution_state.node_trees_snapshot[f"material_{mat.name}"] = tree_state

        for world in bpy.data.worlds:
            if world.use_nodes and world.node_tree:
                tree_state = self._get_node_tree_signature(world.node_tree)
                self.execution_state.node_trees_snapshot[f"world_{world.name}"] = tree_state

        for scene in bpy.data.scenes:
            if scene.use_nodes and scene.node_tree:
                tree_state = self._get_node_tree_signature(scene.node_tree)
                self.execution_state.node_trees_snapshot[f"compositor_{scene.name}"] = tree_state

        for node_group in bpy.data.node_groups:
            if node_group.type == 'GEOMETRY':
                tree_state = self._get_node_tree_signature(node_group)
                self.execution_state.node_trees_snapshot[f"geometry_group_{node_group.name}"] = tree_state

    def _get_node_tree_signature(self, node_tree):
        """Get a lightweight signature of a node tree for change detection."""
        if not node_tree:
            return None

        return {
            'nodes_count': len(node_tree.nodes),
            'links_count': len(node_tree.links),
            'node_types': [node.type for node in node_tree.nodes],
            'node_names': [node.name for node in node_tree.nodes],

            'output_nodes': [
                {
                    'name': node.name,
                    'type': node.type,
                    'is_active': getattr(node, 'is_active_output', True)
                }
                for node in node_tree.nodes
                if node.type in ['OUTPUT_MATERIAL', 'OUTPUT_WORLD', 'GROUP_OUTPUT', 'COMPOSITE']
            ]
        }

    def _snapshot_world_state(self):
        """Snapshot world settings."""
        self.execution_state.world_snapshot = {}
        for world in bpy.data.worlds:
            world_state = {
                'use_nodes': world.use_nodes,
                'color': world.color[:] if hasattr(world, 'color') else None,
                'custom_properties': dict(world.items()) if hasattr(world, 'items') else {},
                'node_tree_exists': world.node_tree is not None if world.use_nodes else False,
            }
            self.execution_state.world_snapshot[world.name] = world_state

    def _snapshot_render_settings(self):
        """Snapshot render and scene settings."""
        scene = bpy.context.scene
        render = scene.render

        self.execution_state.render_settings_snapshot = {
            'engine': render.engine,
            'resolution_x': render.resolution_x,
            'resolution_y': render.resolution_y,
            'resolution_percentage': render.resolution_percentage,
            'fps': render.fps,
            'filepath': render.filepath,
            'image_format': render.image_settings.file_format,
            'color_mode': render.image_settings.color_mode,
            'color_depth': render.image_settings.color_depth,
            'use_compositing': scene.render.use_compositing,
            'use_sequencer': scene.render.use_sequencer,
        }

        if render.engine == 'CYCLES':
            cycles = scene.cycles
            self.execution_state.render_settings_snapshot['cycles'] = {
                'samples': getattr(cycles, 'samples', 128),
                'preview_samples': getattr(cycles, 'preview_samples', 32),
                'use_denoising': getattr(cycles, 'use_denoising', True),
                'device': getattr(cycles, 'device', 'CPU'),
            }
        elif render.engine in ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
            eevee = scene.eevee
            self.execution_state.render_settings_snapshot['eevee'] = {
                'taa_render_samples': getattr(eevee, 'taa_render_samples', 64),
                'taa_samples': getattr(eevee, 'taa_samples', 16),
                'use_bloom': getattr(eevee, 'use_bloom', False),
                'use_ssr': getattr(eevee, 'use_ssr', False),
            }

    def _snapshot_view_layer_state(self):
        """Snapshot view layer settings."""
        view_layer = bpy.context.view_layer
        self.execution_state.view_layer_snapshot = {
            'name': view_layer.name,
            'use_pass_combined': view_layer.use_pass_combined,
            'use_pass_z': view_layer.use_pass_z,
            'use_pass_normal': view_layer.use_pass_normal,
            'use_pass_diffuse_direct': view_layer.use_pass_diffuse_direct,
            'use_pass_diffuse_indirect': view_layer.use_pass_diffuse_indirect,
        }

    def _snapshot_existing_data(self):
        """Snapshot existing data for new item detection."""
        self.execution_state.existing_data = {
            'objects': set(obj.name for obj in bpy.data.objects),
            'collections': set(coll.name for coll in bpy.data.collections),
            'meshes': set(mesh.name for mesh in bpy.data.meshes),
            'materials': set(mat.name for mat in bpy.data.materials),
            'textures': set(tex.name for tex in bpy.data.textures),
            'images': set(img.name for img in bpy.data.images),
            'curves': set(curve.name for curve in bpy.data.curves),
            'lights': set(light.name for light in bpy.data.lights),
            'cameras': set(cam.name for cam in bpy.data.cameras),
            'worlds': set(world.name for world in bpy.data.worlds),
            'node_groups': set(ng.name for ng in bpy.data.node_groups),
            'actions': set(action.name for action in bpy.data.actions),
        }

    def _rollback_changes(self, context) -> bool:
        """Comprehensive rollback of changes to snapshot state."""
        start_time = time.time()
        try:
            logger.debug("Starting comprehensive rollback")

            if not self._has_valid_snapshot():
                logger.warning("No valid snapshot available for rollback")
                return False

            snapshot_data = {
                'scene_snapshot': self.execution_state.scene_snapshot,
                'objects_snapshot': self.execution_state.objects_snapshot,
                'existing_data': self.execution_state.existing_data
            }

            if not snapshot_optimizer.validate_snapshot_integrity(snapshot_data):
                logger.error("Snapshot integrity validation failed")
                return False

            success = True
            rollback_start = time.time()

            success &= self._rollback_new_data_blocks()
            success &= self._rollback_collections()
            success &= self._rollback_objects()
            success &= self._rollback_materials()
            success &= self._rollback_node_trees()
            success &= self._rollback_world_settings()
            success &= self._rollback_render_settings()
            success &= self._rollback_view_layer()
            success &= self._rollback_scene_state()

            context.view_layer.update()
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

            try:
                bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
                logger.debug("Orphaned data blocks purged")
            except Exception as e:
                logger.warning(f"Failed to purge orphaned data: {str(e)}")

            elapsed = time.time() - start_time
            rollback_time = time.time() - rollback_start
            snapshot_optimizer.metrics.rollback_time = rollback_time

            logger.debug(f"Comprehensive rollback completed in {elapsed:.3f}s "
                         f"(rollback: {rollback_time:.3f}s), success: {success}")

            if elapsed > 1.0:
                recommendations = snapshot_optimizer.get_optimization_recommendations()
                if recommendations:
                    logger.info("Performance recommendations:")
                    for rec in recommendations:
                        logger.info(f"  - {rec}")

            return success

        except Exception as e:
            logger.error(f"Comprehensive rollback failed: {str(e)}")
            return False

    def _has_valid_snapshot(self) -> bool:
        """Check if we have a valid snapshot to rollback to."""
        return (self.execution_state.scene_snapshot is not None and
                self.execution_state.existing_data is not None)

    def _rollback_new_data_blocks(self) -> bool:
        """Remove newly created data blocks."""
        try:
            existing_data = self.execution_state.existing_data

            objects_to_remove = [obj for obj in bpy.data.objects
                                 if obj.name not in existing_data['objects']]
            for obj in objects_to_remove:
                try:
                    logger.debug(f"Removing new object: {obj.name}")
                    bpy.data.objects.remove(obj, do_unlink=True)
                except Exception as e:
                    logger.warning(f"Failed to remove object {obj.name}: {str(e)}")

            collections_to_remove = [coll for coll in bpy.data.collections
                                     if coll.name not in existing_data['collections']]
            for coll in collections_to_remove:
                try:
                    logger.debug(f"Removing new collection: {coll.name}")
                    bpy.data.collections.remove(coll)
                except Exception as e:
                    logger.warning(f"Failed to remove collection {coll.name}: {str(e)}")

            materials_to_remove = [mat for mat in bpy.data.materials
                                   if mat.name not in existing_data['materials'] and mat.users == 0]
            for mat in materials_to_remove:
                try:
                    logger.debug(f"Removing new material: {mat.name}")
                    bpy.data.materials.remove(mat)
                except Exception as e:
                    logger.warning(f"Failed to remove material {mat.name}: {str(e)}")

            node_groups_to_remove = [ng for ng in bpy.data.node_groups
                                     if ng.name not in existing_data['node_groups'] and ng.users == 0]
            for ng in node_groups_to_remove:
                try:
                    logger.debug(f"Removing new node group: {ng.name}")
                    bpy.data.node_groups.remove(ng)
                except Exception as e:
                    logger.warning(f"Failed to remove node group {ng.name}: {str(e)}")

            self._remove_new_data_blocks_by_type('meshes', bpy.data.meshes)
            self._remove_new_data_blocks_by_type('curves', bpy.data.curves)
            self._remove_new_data_blocks_by_type('lights', bpy.data.lights)
            self._remove_new_data_blocks_by_type('cameras', bpy.data.cameras)
            self._remove_new_data_blocks_by_type('images', bpy.data.images)
            self._remove_new_data_blocks_by_type('textures', bpy.data.textures)
            self._remove_new_data_blocks_by_type('worlds', bpy.data.worlds)
            self._remove_new_data_blocks_by_type('actions', bpy.data.actions)

            return True

        except Exception as e:
            logger.error(f"Failed to remove new data blocks: {str(e)}")
            return False

    def _remove_new_data_blocks_by_type(self, data_type: str, data_collection):
        """Remove new data blocks of a specific type."""
        existing_names = self.execution_state.existing_data[data_type]
        items_to_remove = [item for item in data_collection
                           if item.name not in existing_names and item.users == 0]

        for item in items_to_remove:
            try:
                logger.debug(f"Removing new {data_type[:-1]}: {item.name}")
                data_collection.remove(item)
            except Exception as e:
                logger.warning(f"Failed to remove {data_type[:-1]} {item.name}: {str(e)}")

    def _rollback_objects(self) -> bool:
        """Rollback object states."""
        try:
            use_lightweight = self.execution_state.lightweight_mode

            for obj_name, obj_state in self.execution_state.objects_snapshot.items():
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]

                    obj.location = obj_state['location']
                    obj.rotation_euler = obj_state['rotation_euler']
                    obj.rotation_mode = obj_state['rotation_mode']
                    obj.scale = obj_state['scale']

                    obj.hide_viewport = obj_state['hide_viewport']
                    obj.hide_render = obj_state['hide_render']
                    obj.hide_select = obj_state['hide_select']

                    if not use_lightweight and 'rotation_quaternion' in obj_state:
                        obj.rotation_quaternion = obj_state['rotation_quaternion']

                        if 'display_type' in obj_state:
                            obj.display_type = obj_state['display_type']
                            obj.show_wire = obj_state['show_wire']
                            obj.show_all_edges = obj_state['show_all_edges']
                            obj.show_transparent = obj_state['show_transparent']
                            obj.show_in_front = obj_state['show_in_front']

                        if obj_state.get('parent'):
                            if obj_state['parent'] in bpy.data.objects:
                                obj.parent = bpy.data.objects[obj_state['parent']]
                                obj.parent_type = obj_state['parent_type']
                                obj.parent_bone = obj_state['parent_bone']
                                obj.matrix_parent_inverse = obj_state['matrix_parent_inverse']
                        else:
                            obj.parent = None

                        if 'custom_properties' in obj_state:
                            self._restore_custom_properties(obj, obj_state['custom_properties'])

                    elif use_lightweight:

                        if obj_state.get('parent'):
                            if obj_state['parent'] in bpy.data.objects:
                                obj.parent = bpy.data.objects[obj_state['parent']]
                        else:
                            obj.parent = None

            return True

        except Exception as e:
            logger.error(f"Failed to rollback objects: {str(e)}")
            return False

    def _rollback_collections(self) -> bool:
        """Rollback collection states."""
        try:
            for coll_name, coll_state in self.execution_state.collections_snapshot.items():
                if coll_name in bpy.data.collections:
                    coll = bpy.data.collections[coll_name]

                    coll.hide_viewport = coll_state['hide_viewport']
                    coll.hide_render = coll_state['hide_render']
                    coll.hide_select = coll_state['hide_select']

                    self._restore_custom_properties(coll, coll_state['custom_properties'])

            return True

        except Exception as e:
            logger.error(f"Failed to rollback collections: {str(e)}")
            return False

    def _rollback_materials(self) -> bool:
        """Rollback material states."""
        try:
            for mat_name, mat_state in self.execution_state.materials_snapshot.items():
                if mat_name in bpy.data.materials:
                    mat = bpy.data.materials[mat_name]

                    mat.use_nodes = mat_state['use_nodes']
                    if mat_state['diffuse_color']:
                        mat.diffuse_color = mat_state['diffuse_color']
                    if mat_state['metallic'] is not None:
                        mat.metallic = mat_state['metallic']
                    if mat_state['roughness'] is not None:
                        mat.roughness = mat_state['roughness']
                    mat.use_backface_culling = mat_state['use_backface_culling']
                    mat.blend_method = mat_state['blend_method']

                    self._restore_custom_properties(mat, mat_state['custom_properties'])

            return True

        except Exception as e:
            logger.error(f"Failed to rollback materials: {str(e)}")
            return False

    def _rollback_node_trees(self) -> bool:
        """Rollback node tree states (lightweight verification)."""
        try:

            changes_detected = False

            for mat in bpy.data.materials:
                if mat.use_nodes and mat.node_tree:
                    key = f"material_{mat.name}"
                    if key in self.execution_state.node_trees_snapshot:
                        original_sig = self.execution_state.node_trees_snapshot[key]
                        current_sig = self._get_node_tree_signature(mat.node_tree)
                        if original_sig != current_sig:
                            logger.debug(f"Node tree changes detected in material: {mat.name}")
                            changes_detected = True

            if changes_detected:
                logger.warning("Node tree changes detected but not fully restored (performance optimization)")

            return True

        except Exception as e:
            logger.error(f"Failed to verify node trees: {str(e)}")
            return False

    def _rollback_world_settings(self) -> bool:
        """Rollback world settings."""
        try:
            for world_name, world_state in self.execution_state.world_snapshot.items():
                if world_name in bpy.data.worlds:
                    world = bpy.data.worlds[world_name]

                    world.use_nodes = world_state['use_nodes']
                    if world_state['color']:
                        world.color = world_state['color']

                    self._restore_custom_properties(world, world_state['custom_properties'])

            return True

        except Exception as e:
            logger.error(f"Failed to rollback world settings: {str(e)}")
            return False

    def _rollback_render_settings(self) -> bool:
        """Rollback render settings."""
        try:
            scene = bpy.context.scene
            render = scene.render
            settings = self.execution_state.render_settings_snapshot

            render.engine = settings['engine']
            render.resolution_x = settings['resolution_x']
            render.resolution_y = settings['resolution_y']
            render.resolution_percentage = settings['resolution_percentage']
            render.fps = settings['fps']
            render.filepath = settings['filepath']
            render.image_settings.file_format = settings['image_format']
            render.image_settings.color_mode = settings['color_mode']
            render.image_settings.color_depth = settings['color_depth']
            scene.render.use_compositing = settings['use_compositing']
            scene.render.use_sequencer = settings['use_sequencer']

            if 'cycles' in settings and render.engine == 'CYCLES':
                cycles = scene.cycles
                cycles_settings = settings['cycles']
                cycles.samples = cycles_settings['samples']
                cycles.preview_samples = cycles_settings['preview_samples']
                cycles.use_denoising = cycles_settings['use_denoising']
                cycles.device = cycles_settings['device']

            elif 'eevee' in settings and render.engine in ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
                eevee = scene.eevee
                eevee_settings = settings['eevee']
                eevee.taa_render_samples = eevee_settings['taa_render_samples']
                eevee.taa_samples = eevee_settings['taa_samples']
                eevee.use_bloom = eevee_settings['use_bloom']
                eevee.use_ssr = eevee_settings['use_ssr']

            return True

        except Exception as e:
            logger.error(f"Failed to rollback render settings: {str(e)}")
            return False

    def _rollback_view_layer(self) -> bool:
        """Rollback view layer settings."""
        try:
            view_layer = bpy.context.view_layer
            settings = self.execution_state.view_layer_snapshot

            view_layer.use_pass_combined = settings['use_pass_combined']
            view_layer.use_pass_z = settings['use_pass_z']
            view_layer.use_pass_normal = settings['use_pass_normal']
            view_layer.use_pass_diffuse_direct = settings['use_pass_diffuse_direct']
            view_layer.use_pass_diffuse_indirect = settings['use_pass_diffuse_indirect']

            return True

        except Exception as e:
            logger.error(f"Failed to rollback view layer: {str(e)}")
            return False

    def _rollback_scene_state(self) -> bool:
        """Rollback basic scene state."""
        try:
            scene = bpy.context.scene
            scene_state = self.execution_state.scene_snapshot

            scene.cursor.location = scene_state['cursor_location']
            scene.frame_current = scene_state['frame_current']
            scene.frame_start = scene_state['frame_start']
            scene.frame_end = scene_state['frame_end']

            if scene_state['active_camera'] and scene_state['active_camera'] in bpy.data.objects:
                scene.camera = bpy.data.objects[scene_state['active_camera']]

            tool_settings = scene_state['tool_settings']
            scene.tool_settings.use_keyframe_insert_auto = tool_settings['use_keyframe_insert_auto']
            scene.tool_settings.transform_pivot_point = tool_settings['transform_pivot_point']
            scene.tool_settings.use_snap = tool_settings['use_snap']
            scene.tool_settings.snap_elements = tool_settings['snap_elements']

            bpy.ops.object.select_all(action='DESELECT')
            for obj_name in scene_state['selected_objects']:
                if obj_name in bpy.data.objects:
                    bpy.data.objects[obj_name].select_set(True)

            if scene_state['active_object'] and scene_state['active_object'] in bpy.data.objects:
                bpy.context.view_layer.objects.active = bpy.data.objects[scene_state['active_object']]

            return True

        except Exception as e:
            logger.error(f"Failed to rollback scene state: {str(e)}")
            return False

    def _restore_custom_properties(self, data_block, custom_props: dict):
        """Restore custom properties to a data block."""
        try:

            keys_to_remove = [key for key in data_block.keys() if not key.startswith('_')]
            for key in keys_to_remove:
                del data_block[key]

            for key, value in custom_props.items():
                if not key.startswith('_'):
                    data_block[key] = value

        except Exception as e:
            logger.warning(f"Failed to restore custom properties: {str(e)}")

    def _prepare_safe_globals(self) -> Dict[str, Any]:
        """Prepare safe globals for code execution."""
        safe_globals = self.restricted_globals.copy()

        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            """Custom import function that blocks dangerous imports."""
            try:

                base_module = name.split('.')[0]
                if base_module in script_guard.dangerous_imports:
                    logger.warning(f"Blocked dangerous import attempt: {name}")
                    raise ImportError(f"Import of '{name}' is not allowed for security reasons")

                logger.debug(f"Allowing safe import: {name}")

                return __import__(name, globals, locals, fromlist, level)

            except ImportError as e:

                raise
            except Exception as e:

                logger.error(f"Unexpected error during import of '{name}': {str(e)}")
                raise ImportError(f"Failed to import '{name}': {str(e)}")

        if isinstance(safe_globals['__builtins__'], dict):
            safe_globals['__builtins__'] = safe_globals['__builtins__'].copy()
            safe_globals['__builtins__']['__import__'] = safe_import
        else:

            import builtins
            safe_builtins_dict = {}
            for attr in dir(builtins):
                if not attr.startswith('_') or attr in ['__name__', '__doc__']:
                    if attr == '__import__':
                        safe_builtins_dict[attr] = safe_import
                    elif attr not in {'eval', 'exec', 'compile', 'open', 'input'}:
                        safe_builtins_dict[attr] = getattr(builtins, attr)
            safe_globals['__builtins__'] = safe_builtins_dict

        try:
            import bmesh
            safe_globals['bmesh'] = bmesh
        except ImportError:
            pass

        try:
            import mathutils
            safe_globals['mathutils'] = mathutils
        except ImportError:
            pass

        safe_modules = ['math', 'random', 'time', 'datetime', 'json', 're', 'collections',
                        'itertools', 'functools', 'operator', 'copy', 'string', 'textwrap',
                        'struct', 'array', 'heapq', 'bisect', 'weakref', 'types']

        for module_name in safe_modules:
            if module_name not in script_guard.dangerous_imports:
                try:
                    module = __import__(module_name)
                    safe_globals[module_name] = module
                except ImportError:
                    pass

        return safe_globals

    def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        import time
        return f"exec_{int(time.time() * 1000)}"

    def _handle_execution_error(self, context, error_msg: str, traceback_str: str) -> Tuple[bool, Optional[str]]:
        """
        Handle execution error by rolling back changes and reporting the error.
        
        Args:
            context: Blender context
            error_msg: Error message
            traceback_str: Full traceback string
            
        Returns:
            Tuple of (success, error_message)
        """
        try:

            clean_error_msg = self._extract_clean_error_message(error_msg)

            logger.info("Rolling back changes due to execution error")
            rollback_success = self._rollback_changes(context)

            context.scene.vibe4d_console_output = ""

            self.execution_state.clear()

            if not rollback_success:
                logger.error("Rollback failed")
                return False, f"Execution failed and rollback unsuccessful: {clean_error_msg}"

            logger.info("Changes rolled back successfully")
            return False, clean_error_msg

        except Exception as e:
            logger.error(f"Error in _handle_execution_error: {str(e)}")
            return False, f"Error handling failed: {str(e)}"

    def _extract_clean_error_message(self, error_msg: str) -> str:
        """
        Extract a clean, user-friendly error message from the raw error.
        
        Args:
            error_msg: Raw error message
            
        Returns:
            Clean error message with helpful suggestions
        """
        try:

            clean_msg = error_msg

            import re
            clean_msg = re.sub(r'File "[^"]*", line \d+, in [^\n]*\n', '', clean_msg)
            clean_msg = re.sub(r'^\s*File "[^"]*", line \d+', '', clean_msg, flags=re.MULTILINE)

            lines = clean_msg.strip().split('\n')
            if lines:

                for line in reversed(lines):
                    if line.strip():
                        clean_msg = line.strip()
                        break

            return "ERROR: " + clean_msg

        except Exception as e:
            logger.error(f"Failed to extract clean error message: {str(e)}")
            return error_msg

    def accept_execution(self, context) -> bool:
        """
        Accept the execution results and clear state.
        
        Args:
            context: Blender context
            
        Returns:
            True if accepted successfully
        """
        try:
            if not self.execution_state.is_executing:
                logger.warning("No execution to accept")
                return False

            logger.info(f"Accepting execution (ID: {self.execution_state.execution_id})")

            self.execution_state.clear()

            context.scene.vibe4d_final_code = ""
            context.scene.vibe4d_last_error = ""
            context.scene.vibe4d_console_output = ""
            context.scene.vibe4d_prompt = ""

            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            logger.info("Execution accepted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to accept execution: {str(e)}")
            return False

    def reject_execution(self, context) -> bool:
        """
        Reject the execution and rollback changes.
        
        Args:
            context: Blender context
            
        Returns:
            True if rollback successful
        """
        try:
            if not self.execution_state.is_executing:
                logger.warning("No execution to reject")
                return False

            logger.info(f"Rejecting execution (ID: {self.execution_state.execution_id})")

            rollback_success = self._rollback_changes(context)

            if not rollback_success:
                logger.error("Rollback failed during rejection")
                return False

            self.execution_state.clear()

            context.scene.vibe4d_final_code = ""
            context.scene.vibe4d_last_error = ""
            context.scene.vibe4d_console_output = ""
            context.scene.vibe4d_execution_pending = False
            context.scene.vibe4d_prompt = ""

            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            logger.info("Execution rejected and changes rolled back successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to reject execution: {str(e)}")
            return False

    def get_rollback_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of rollback system performance and recommendations."""
        try:
            metrics = snapshot_optimizer.metrics
            summary = {
                'snapshot_creation_time': metrics.creation_time,
                'rollback_time': metrics.rollback_time,
                'objects_count': metrics.objects_count,
                'collections_count': metrics.collections_count,
                'materials_count': metrics.materials_count,
                'node_trees_count': metrics.node_trees_count,
                'memory_usage_mb': metrics.memory_usage_mb,
                'lightweight_mode_enabled': self.execution_state.lightweight_mode,
                'snapshot_hash': self.execution_state.snapshot_hash,
                'total_execution_time': metrics.creation_time + metrics.rollback_time,
                'performance_grade': self._calculate_performance_grade(),
                'recommendations': snapshot_optimizer.get_optimization_recommendations(),
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to generate performance summary: {str(e)}")
            return {'error': str(e)}

    def _calculate_performance_grade(self) -> str:
        """Calculate a performance grade based on timing metrics."""
        try:
            metrics = snapshot_optimizer.metrics
            total_time = metrics.creation_time + metrics.rollback_time

            complexity_factor = (
                    metrics.objects_count * 0.001 +
                    metrics.materials_count * 0.002 +
                    metrics.node_trees_count * 0.003
            )

            normalized_time = total_time / max(complexity_factor, 0.1)

            if normalized_time < 0.5:
                return "A"
            elif normalized_time < 1.0:
                return "B"
            elif normalized_time < 2.0:
                return "C"
            elif normalized_time < 4.0:
                return "D"
            else:
                return "F"

        except Exception as e:
            logger.warning(f"Failed to calculate performance grade: {str(e)}")
            return "Unknown"


code_executor = CodeExecutor()
