from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable


class CurvesTable(BaseTable):

    @property
    def name(self) -> str:
        return 'curves'

    @property
    def description(self) -> str:
        return 'Curve data blocks including text curves and bezier curves'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        count = 0

        for curve in bpy.data.curves:
            if limit and count >= limit:
                break

            if fields:
                curve_data = self._extract_fields(curve, fields)
            else:
                curve_data = self._extract_all_fields(curve)

            if where and not self._matches_where(curve_data, where):
                continue

            yield curve_data
            count += 1

    def _extract_fields(self, curve, fields: List[str]) -> Dict[str, Any]:
        data = {}

        for field in fields:
            if field == 'name':
                data['name'] = curve.name
            elif field == 'type':
                data['type'] = curve.type
            elif field == 'dimensions':
                data['dimensions'] = curve.dimensions
            elif field == 'splines_count':
                data['splines_count'] = len(curve.splines)
            elif field == 'extrude':
                data['extrude'] = curve.extrude
            elif field == 'bevel_depth':
                data['bevel_depth'] = curve.bevel_depth
            elif field == 'users':
                data['users'] = curve.users

        return data

    def _extract_all_fields(self, curve) -> Dict[str, Any]:
        return {
        :curve.name,
        : curve.type,
        :curve.dimensions,
        : len(curve.splines),
        :curve.extrude,
        : curve.bevel_depth,
        :curve.users
        }
