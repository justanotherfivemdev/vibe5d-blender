"""
Snapshot optimization utilities for improved rollback performance.

This module provides optimized data structures and algorithms for efficient
state snapshotting and restoration in the Blender addon.
"""

import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import bpy

from ..utils.logger import logger


@dataclass
class SnapshotMetrics:
    """Tracks performance metrics for snapshot operations."""
    creation_time: float = 0.0
    rollback_time: float = 0.0
    objects_count: int = 0
    collections_count: int = 0
    materials_count: int = 0
    node_trees_count: int = 0
    total_data_size: int = 0
    memory_usage_mb: float = 0.0


class SmartSnapshotOptimizer:
    """Optimizes snapshot operations for better performance."""

    def __init__(self):
        self.metrics = SnapshotMetrics()
        self.last_snapshot_hash = None
        self.cached_signatures = {}
        self.performance_mode = 'auto'

    def should_use_lightweight_mode(self, context) -> bool:
        """Determine if lightweight mode should be used based on scene complexity."""
        try:

            object_count = len(bpy.data.objects)
            material_count = len(bpy.data.materials)
            node_group_count = len(bpy.data.node_groups)

            complexity_score = (
                    object_count * 1.0 +
                    material_count * 2.0 +
                    node_group_count * 3.0
            )

            lightweight_threshold = 500

            if self.performance_mode == 'fast':
                return True
            elif self.performance_mode == 'comprehensive':
                return False
            else:
                return complexity_score > lightweight_threshold

        except Exception as e:
            logger.warning(f"Error determining snapshot mode: {str(e)}")
            return False

    def get_scene_signature(self) -> str:
        """Get a quick signature of the current scene state."""
        try:

            import hashlib

            signature_data = []
            signature_data.append(str(len(bpy.data.objects)))
            signature_data.append(str(len(bpy.data.materials)))
            signature_data.append(str(len(bpy.data.collections)))

            signature_data.append(str(bpy.context.scene.frame_current))

            if bpy.context.active_object:
                signature_data.append(bpy.context.active_object.name)
                signature_data.append(str(bpy.context.active_object.location))

            signature_str = '|'.join(signature_data)
            return hashlib.md5(signature_str.encode()).hexdigest()

        except Exception as e:
            logger.warning(f"Error creating scene signature: {str(e)}")
            return str(time.time())

    def optimize_object_snapshot(self, objects_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize object snapshot data for memory efficiency."""
        try:
            optimized = {}

            for obj_name, obj_data in objects_snapshot.items():

                optimized_data = {

                    'location': obj_data['location'],
                    'rotation_euler': obj_data['rotation_euler'],
                    'scale': obj_data['scale'],
                    'hide_viewport': obj_data['hide_viewport'],
                    'hide_render': obj_data['hide_render'],
                }

                if obj_data.get('parent'):
                    optimized_data['parent'] = obj_data['parent']
                    optimized_data['parent_type'] = obj_data['parent_type']
                    optimized_data['matrix_parent_inverse'] = obj_data['matrix_parent_inverse']

                if obj_data.get('modifiers'):
                    optimized_data['modifier_names'] = [mod['name'] for mod in obj_data['modifiers']]

                if obj_data.get('custom_properties'):
                    optimized_data['custom_properties'] = obj_data['custom_properties']

                optimized[obj_name] = optimized_data

            return optimized

        except Exception as e:
            logger.warning(f"Error optimizing object snapshot: {str(e)}")
            return objects_snapshot

    def create_differential_snapshot(self, current_snapshot: Dict[str, Any],
                                     previous_snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a differential snapshot that only stores changes."""
        if not previous_snapshot:
            return current_snapshot

        try:
            differential = {}

            for key, current_value in current_snapshot.items():
                if key not in previous_snapshot or previous_snapshot[key] != current_value:
                    differential[key] = current_value

            differential['_is_differential'] = True
            differential['_base_snapshot_hash'] = self.last_snapshot_hash

            return differential

        except Exception as e:
            logger.warning(f"Error creating differential snapshot: {str(e)}")
            return current_snapshot

    def validate_snapshot_integrity(self, snapshot_data: Dict[str, Any]) -> bool:
        """Validate that snapshot data is complete and consistent."""
        try:
            required_keys = ['scene_snapshot', 'objects_snapshot', 'existing_data']

            for key in required_keys:
                if key not in snapshot_data:
                    logger.warning(f"Snapshot missing required key: {key}")
                    return False

            if 'objects_snapshot' in snapshot_data:
                objects_snapshot = snapshot_data['objects_snapshot']
                for obj_name, obj_data in objects_snapshot.items():
                    if 'location' not in obj_data or 'rotation_euler' not in obj_data:
                        logger.warning(f"Object {obj_name} missing essential transform data")
                        return False

            return True

        except Exception as e:
            logger.warning(f"Error validating snapshot integrity: {str(e)}")
            return False

    def estimate_snapshot_size(self, snapshot_data: Dict[str, Any]) -> int:
        """Estimate memory usage of snapshot data."""
        try:
            import sys

            def get_size(obj):
                size = sys.getsizeof(obj)
                if isinstance(obj, dict):
                    size += sum(get_size(k) + get_size(v) for k, v in obj.items())
                elif isinstance(obj, (list, tuple)):
                    size += sum(get_size(item) for item in obj)
                return size

            return get_size(snapshot_data)

        except Exception as e:
            logger.warning(f"Error estimating snapshot size: {str(e)}")
            return 0

    def cleanup_old_snapshots(self, max_age_seconds: float = 300):
        """Clean up old cached data to free memory."""
        try:
            current_time = time.time()
            keys_to_remove = []

            for key, (timestamp, data) in self.cached_signatures.items():
                if current_time - timestamp > max_age_seconds:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self.cached_signatures[key]

            if keys_to_remove:
                logger.debug(f"Cleaned up {len(keys_to_remove)} old cached snapshots")

        except Exception as e:
            logger.warning(f"Error cleaning up snapshots: {str(e)}")

    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations based on metrics."""
        recommendations = []

        try:
            if self.metrics.creation_time > 1.0:
                recommendations.append("Consider enabling lightweight mode for faster snapshots")

            if self.metrics.objects_count > 1000:
                recommendations.append("Scene has many objects - consider using collections to organize")

            if self.metrics.node_trees_count > 50:
                recommendations.append("Many node trees detected - consider consolidating node groups")

            if self.metrics.memory_usage_mb > 100:
                recommendations.append("High memory usage - consider enabling differential snapshots")

            if self.metrics.rollback_time > 2.0:
                recommendations.append("Slow rollback detected - consider reducing scene complexity")

        except Exception as e:
            logger.warning(f"Error generating recommendations: {str(e)}")

        return recommendations


snapshot_optimizer = SmartSnapshotOptimizer()
