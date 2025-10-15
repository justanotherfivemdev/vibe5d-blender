from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable
from ....utils.json_utils import to_json_serializable


class MaterialsTable(BaseTable):

    @property
    def name(self) -> str:
        return 'materials'

    @property
    def description(self) -> str:
        return 'Material data including complete node trees'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for mat in bpy.data.materials:
            if limit and count >= limit:
                break

            if fields:
                mat_data = self._extract_fields(mat, fields)
            else:
                mat_data = self._extract_all_fields(mat)

            if where and not self._matches_where(mat_data, where):
                continue

            yield mat_data
            count += 1

    def _extract_fields(self, mat, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = mat.name
            elif field == 'use_nodes':
                data['use_nodes'] = mat.use_nodes
            elif field == 'users':
                data['users'] = mat.users
            elif field == 'diffuse_color':
                data['diffuse_color'] = to_json_serializable(mat.diffuse_color)
            elif field == 'metallic':
                data['metallic'] = mat.metallic
            elif field == 'roughness':
                data['roughness'] = mat.roughness
            elif field == 'blend_method':
                data['blend_method'] = mat.blend_method
            elif field == 'alpha':
                if hasattr(mat, 'alpha'):
                    data['alpha'] = mat.alpha
                elif mat.use_nodes and mat.node_tree:
                    for node in mat.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED' and 'Alpha' in node.inputs:
                            data['alpha'] = node.inputs['Alpha'].default_value
                            break
            elif field == 'node_graph':
                if mat.use_nodes and mat.node_tree:
                    data['node_graph'] = self._extract_node_graph(mat.node_tree)

        return data

    def _extract_all_fields(self, mat) -> Dict[str, Any]:
        mat_data = {
        :mat.name,
        : mat.use_nodes,
        :mat.users,
        : to_json_serializable(mat.diffuse_color),
        :mat.metallic,
        : mat.roughness,
        :mat.blend_method
        }

        if hasattr(mat, 'alpha'):
            mat_data["alpha"] = mat.alpha

        if mat.use_nodes and mat.node_tree:
            mat_data["node_graph"] = self._extract_node_graph(mat.node_tree)
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED' and 'Alpha' in node.inputs:
                    mat_data["alpha"] = node.inputs['Alpha'].default_value
                    break

        return mat_data

    def _extract_node_graph(self, node_tree) -> Dict[str, Any]:
        nodes = []
        connections = []

        for node in node_tree.nodes:
            node_data = {
            :node.name,
            : node.type,
            :[round(node.location.x, 2), round(node.location.y, 2)],
            }

            inputs = {}
            for socket in node.inputs:
                if not socket.is_linked and hasattr(socket, 'default_value'):
                    try:
                        default_val = socket.default_value
                        if hasattr(default_val, '__len__') and not isinstance(default_val, str):
                            inputs[socket.name] = to_json_serializable(default_val)
                        else:
                            inputs[socket.name] = default_val
                    except:
                        pass

            if inputs:
                node_data["inputs"] = inputs

            if node.type == 'TEX_IMAGE' and node.image:
                node_data["image"] = node.image.name
                node_data["image_filepath"] = node.image.filepath
            elif node.type == 'BSDF_PRINCIPLED':
                node_data["distribution"] = getattr(node, 'distribution', 'MULTISCATTER_GGX')

            nodes.append(node_data)

        for link in node_tree.links:
            if link.is_valid:
                connections.append({
                : link.from_node.name,
                :link.from_socket.name,
                : link.to_node.name,
                :link.to_socket.name,
                })

            return {
            :nodes,
            : connections
            }
