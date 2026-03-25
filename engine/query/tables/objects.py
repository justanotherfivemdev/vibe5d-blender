from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable
from ....utils.json_utils import to_json_serializable


class ObjectsTable(BaseTable):

    @property
    def name(self) -> str:
        return 'objects'

    @property
    def description(self) -> str:
        return 'Scene objects with transform, type-specific data, modifiers, and constraints'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for obj in context.scene.objects:
            if limit and count >= limit:
                break

            if fields:
                obj_data = self._extract_fields(obj, context, fields)
            else:
                obj_data = self._extract_all_fields(obj, context)

            if where and not self._matches_where(obj_data, where):
                continue

            yield obj_data
            count += 1

    def _extract_fields(self, obj, context, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = obj.name
            elif field == 'type':
                data['type'] = obj.type
            elif field == 'location':
                data['location'] = to_json_serializable(obj.location)
            elif field == 'rotation':
                data['rotation'] = to_json_serializable(obj.rotation_euler)
            elif field == 'scale':
                data['scale'] = to_json_serializable(obj.scale)
            elif field == 'visible':
                data['visible'] = obj.visible_get()
            elif field == 'selected':
                data['selected'] = obj.select_get()
            elif field == 'active':
                data['active'] = obj == context.active_object
            elif field == 'data_name':
                data['data_name'] = obj.data.name if obj.data else None
            elif field == 'parent':
                data['parent'] = obj.parent.name if obj.parent else None
            elif field == 'collection':
                data['collection'] = obj.users_collection[0].name if obj.users_collection else None
            elif field == 'modifiers':
                data['modifiers'] = self._extract_modifiers(obj)
            elif field == 'constraints':
                data['constraints'] = self._extract_constraints(obj)
            elif field == 'children':
                data['children'] = [child.name for child in obj.children]
            elif field in ['vertices', 'faces', 'materials'] and obj.type == 'MESH' and obj.data:
                if field == 'vertices':
                    data['vertices'] = len(obj.data.vertices)
                elif field == 'faces':
                    data['faces'] = len(obj.data.polygons)
                elif field == 'materials':
                    data['materials'] = [mat.name for mat in obj.data.materials if mat]
            elif field in ['light_type', 'energy', 'color'] and obj.type == 'LIGHT' and obj.data:
                if field == 'light_type':
                    data['light_type'] = obj.data.type
                elif field == 'energy':
                    data['energy'] = obj.data.energy
                elif field == 'color':
                    data['color'] = to_json_serializable(obj.data.color)
            elif field in ['focal_length', 'sensor_width'] and obj.type == 'CAMERA' and obj.data:
                if field == 'focal_length':
                    data['focal_length'] = obj.data.lens
                elif field == 'sensor_width':
                    data['sensor_width'] = obj.data.sensor_width

        return data

    def _extract_all_fields(self, obj, context) -> Dict[str, Any]:
        obj_data = {
            'name': obj.name,
            'type': obj.type,
            'location': to_json_serializable(obj.location),
            'rotation': to_json_serializable(obj.rotation_euler),
            'scale': to_json_serializable(obj.scale),
            'visible': obj.visible_get(),
            'selected': obj.select_get(),
            'active': obj == context.active_object,
            'data_name': obj.data.name if obj.data else None,
            'parent': obj.parent.name if obj.parent else None,
            'collection': obj.users_collection[0].name if obj.users_collection else None,
            'children': [child.name for child in obj.children],
        }

        if obj.type == 'MESH' and obj.data:
            obj_data["vertices"] = len(obj.data.vertices)
            obj_data["faces"] = len(obj.data.polygons)
            obj_data["materials"] = [mat.name for mat in obj.data.materials if mat]
        elif obj.type == 'LIGHT' and obj.data:
            obj_data["light_type"] = obj.data.type
            obj_data["energy"] = obj.data.energy
            obj_data["color"] = to_json_serializable(obj.data.color)
        elif obj.type == 'CAMERA' and obj.data:
            obj_data["focal_length"] = obj.data.lens
            obj_data["sensor_width"] = obj.data.sensor_width
        elif obj.type == 'FONT' and obj.data:
            obj_data["text_body"] = obj.data.body
            obj_data["font_size"] = obj.data.size
            obj_data["extrude"] = obj.data.extrude
            obj_data["bevel_depth"] = obj.data.bevel_depth
            obj_data["font_name"] = obj.data.font.name if obj.data.font else None
            obj_data["align_x"] = obj.data.align_x
            obj_data["align_y"] = obj.data.align_y
            obj_data["text_on_curve"] = obj.data.follow_curve.name if obj.data.follow_curve else None
        elif obj.type == 'CURVE' and obj.data:
            obj_data["curve_type"] = obj.data.type
            obj_data["splines_count"] = len(obj.data.splines)
            obj_data["dimensions"] = obj.data.dimensions
            obj_data["extrude"] = obj.data.extrude
            obj_data["bevel_depth"] = obj.data.bevel_depth

        obj_data["modifiers"] = self._extract_modifiers(obj)
        obj_data["constraints"] = self._extract_constraints(obj)

        return obj_data

    def _extract_modifiers(self, obj) -> List[Dict[str, Any]]:
        modifiers = []
        for mod in obj.modifiers:
            mod_data = {
                'name': mod.name,
                'type': mod.type,
                'show_viewport': mod.show_viewport,
                'show_render': mod.show_render,
            }

            if mod.type == 'SUBSURF':
                mod_data["levels"] = mod.levels
                mod_data["render_levels"] = mod.render_levels
            elif mod.type == 'ARRAY':
                mod_data["count"] = mod.count
                mod_data["use_relative_offset"] = mod.use_relative_offset
                mod_data["relative_offset_displace"] = to_json_serializable(mod.relative_offset_displace)
            elif mod.type == 'MIRROR':
                mod_data["use_axis"] = [mod.use_axis[0], mod.use_axis[1], mod.use_axis[2]]
                mod_data["mirror_object"] = mod.mirror_object.name if mod.mirror_object else None
            elif mod.type == 'SOLIDIFY':
                mod_data["thickness"] = mod.thickness
                mod_data["offset"] = mod.offset
            elif mod.type == 'BEVEL':
                mod_data["width"] = mod.width
                mod_data["segments"] = mod.segments

            modifiers.append(mod_data)

        return modifiers

    def _extract_constraints(self, obj) -> List[Dict[str, Any]]:
        constraints = []
        for con in obj.constraints:
            con_data = {
                'name': con.name,
                'type': con.type,
                'enabled': not con.mute,
                'influence': con.influence,
            }

            if hasattr(con, 'target'):
                con_data["target"] = con.target.name if con.target else None

            if con.type == 'TRACK_TO':
                con_data["track_axis"] = con.track_axis
                con_data["up_axis"] = con.up_axis
            elif con.type == 'COPY_LOCATION':
                con_data["use_x"] = con.use_x
                con_data["use_y"] = con.use_y
                con_data["use_z"] = con.use_z
            elif con.type == 'COPY_ROTATION':
                con_data["use_x"] = con.use_x
                con_data["use_y"] = con.use_y
                con_data["use_z"] = con.use_z

            constraints.append(con_data)

        return constraints
