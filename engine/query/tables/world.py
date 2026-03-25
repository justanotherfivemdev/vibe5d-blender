from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable
from ....utils.json_utils import to_json_serializable


class WorldTable(BaseTable):

    @property
    def name(self) -> str:
        return 'world'

    @property
    def description(self) -> str:
        return 'World shader and environment data with node tree'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for world in bpy.data.worlds:
            if limit and count >= limit:
                break

            if fields:
                world_data = self._extract_fields(world, fields)
            else:
                world_data = self._extract_all_fields(world)

            if where and not self._matches_where(world_data, where):
                continue

            yield world_data
            count += 1

    def _extract_fields(self, world, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = world.name
            elif field == 'use_nodes':
                data['use_nodes'] = world.use_nodes
            elif field == 'color':
                if hasattr(world, 'color'):
                    data['color'] = to_json_serializable(world.color)
            elif field == 'node_graph':
                if world.use_nodes and world.node_tree:
                    data['node_graph'] = self._extract_node_graph(world.node_tree)

        return data

    def _extract_all_fields(self, world) -> Dict[str, Any]:
        world_data = {
            'name': world.name,
            'use_nodes': world.use_nodes,
        }

        if hasattr(world, 'color'):
            world_data["color"] = to_json_serializable(world.color)

        if world.use_nodes and world.node_tree:
            world_data["node_graph"] = self._extract_node_graph(world.node_tree)

        return world_data

    def _extract_node_graph(self, node_tree) -> Dict[str, Any]:
        nodes = []
        connections = []

        for node in node_tree.nodes:
            node_data = {
                'name': node.name,
                'type': node.type,
                'location': [round(node.location.x, 2), round(node.location.y, 2)],
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
            elif node.type == 'BACKGROUND':
                node_data["shader_type"] = "background"

            nodes.append(node_data)

        for link in node_tree.links:
            if link.is_valid:
                connections.append({
                    'from_node': link.from_node.name,
                    'from_socket': link.from_socket.name,
                    'to_node': link.to_node.name,
                    'to_socket': link.to_socket.name,
                })

        return {
            'nodes': nodes,
            'connections': connections
        }
