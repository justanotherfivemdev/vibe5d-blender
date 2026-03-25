from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable


class MeshesTable(BaseTable):

    @property
    def name(self) -> str:
        return 'meshes'

    @property
    def description(self) -> str:
        return 'Mesh geometry data blocks'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for mesh in bpy.data.meshes:
            if limit and count >= limit:
                break

            if fields:
                mesh_data = self._extract_fields(mesh, fields)
            else:
                mesh_data = self._extract_all_fields(mesh)

            if where and not self._matches_where(mesh_data, where):
                continue

            yield mesh_data
            count += 1

    def _extract_fields(self, mesh, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = mesh.name
            elif field == 'vertices':
                data['vertices'] = len(mesh.vertices)
            elif field == 'edges':
                data['edges'] = len(mesh.edges)
            elif field == 'faces':
                data['faces'] = len(mesh.polygons)
            elif field == 'users':
                data['users'] = mesh.users
            elif field == 'materials':
                data['materials'] = [mat.name for mat in mesh.materials if mat]

        return data

    def _extract_all_fields(self, mesh) -> Dict[str, Any]:
        return {
            'name': mesh.name,
            'vertices': len(mesh.vertices),
            'edges': len(mesh.edges),
            'faces': len(mesh.polygons),
            'users': mesh.users,
            'materials': [mat.name for mat in mesh.materials if mat]
        }
