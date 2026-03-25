from typing import Dict, Any, List, Optional, Generator

import bpy

from ..base_table import BaseTable


class SceneTable(BaseTable):

    @property
    def name(self) -> str:
        return 'scene'

    @property
    def description(self) -> str:
        return 'Current scene configuration including render settings'

    def iterate(self, context, fields: Optional[List[str]] = None,
                where: Optional[Any] = None, limit: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:

        scene_data = self._extract_all_fields(context.scene) if not fields else self._extract_fields(context.scene,
                                                                                                     fields)

        if where and not self._matches_where(scene_data, where):
            return

        yield scene_data

    def _extract_fields(self, scene, fields: List[str]) -> Dict[str, Any]:
        data = {}
        render = scene.render

        for field in fields:
            if field == 'name':
                data['name'] = scene.name
            elif field == 'frame_current':
                data['frame_current'] = scene.frame_current
            elif field == 'frame_start':
                data['frame_start'] = scene.frame_start
            elif field == 'frame_end':
                data['frame_end'] = scene.frame_end
            elif field == 'fps':
                data['fps'] = render.fps
            elif field == 'render_engine':
                data['render_engine'] = render.engine
            elif field == 'resolution_x':
                data['resolution_x'] = render.resolution_x
            elif field == 'resolution_y':
                data['resolution_y'] = render.resolution_y
            elif field == 'resolution_percentage':
                data['resolution_percentage'] = render.resolution_percentage
            elif field == 'filepath':
                data['filepath'] = render.filepath
            elif field == 'image_format':
                data['image_format'] = render.image_settings.file_format
            elif field == 'color_mode':
                data['color_mode'] = render.image_settings.color_mode
            elif field == 'color_depth':
                data['color_depth'] = render.image_settings.color_depth
            elif field == 'samples':
                if render.engine == 'CYCLES':
                    data['samples'] = getattr(scene.cycles, 'samples', None)
            elif field == 'device':
                if render.engine == 'CYCLES':
                    data['device'] = getattr(scene.cycles, 'device', None)
            elif field == 'use_denoising':
                if render.engine == 'CYCLES':
                    data['use_denoising'] = getattr(scene.cycles, 'use_denoising', None)

        return data

    def _extract_all_fields(self, scene) -> Dict[str, Any]:
        render = scene.render

        scene_data = {
            'name': scene.name,
            'frame_current': scene.frame_current,
            'frame_start': scene.frame_start,
            'frame_end': scene.frame_end,
            'fps': render.fps,
            'render_engine': render.engine,
            'resolution_x': render.resolution_x,
            'resolution_y': render.resolution_y,
            'resolution_percentage': render.resolution_percentage,
            'filepath': render.filepath,
            'image_format': render.image_settings.file_format,
            'color_mode': render.image_settings.color_mode,
            'color_depth': render.image_settings.color_depth,
        }

        if render.engine == 'CYCLES':
            cycles = scene.cycles
            scene_data.update({
                'samples': getattr(cycles, 'samples', None),
                'preview_samples': getattr(cycles, 'preview_samples', None),
                'use_denoising': getattr(cycles, 'use_denoising', None),
                'device': getattr(cycles, 'device', None),
                'use_adaptive_sampling': getattr(cycles, 'use_adaptive_sampling', None)
            })
        elif render.engine in ['BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT']:
            eevee = scene.eevee
            scene_data.update({
                'taa_render_samples': getattr(eevee, 'taa_render_samples', None),
                'taa_samples': getattr(eevee, 'taa_samples', None),
                'use_bloom': getattr(eevee, 'use_bloom', None),
                'use_ssr': getattr(eevee, 'use_ssr', None),
                'use_motion_blur': getattr(eevee, 'use_motion_blur', None),
            })

        return scene_data
