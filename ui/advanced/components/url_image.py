"""
URL Image component for loading and displaying images from URLs asynchronously.
Extends the base ImageComponent with URL support, loading states, and error handling.
"""

import logging
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request
from enum import Enum
from typing import Optional, Callable, Dict, Any

import bpy

from .image import ImageComponent, ImageFit, ImagePosition
from ..colors import Colors
from ..coordinates import CoordinateSystem

logger = logging.getLogger(__name__)


class URLImageState(Enum):
    """States for URL image loading."""
    IDLE = "idle"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    RETRY = "retry"


class URLImageManager:
    """Manages URL image downloads and caching to prevent duplicate downloads."""

    def __init__(self):
        self._download_cache = {}
        self._download_lock = threading.Lock()
        self._active_downloads = set()

    def get_cached_state(self, url: str) -> Dict[str, Any]:
        """Get cached download state for a URL."""
        with self._download_lock:
            return self._download_cache.get(url, {'state': URLImageState.IDLE})

    def set_cached_state(self, url: str, state: URLImageState, temp_path: str = None, error: str = None):
        """Set cached download state for a URL."""
        with self._download_lock:
            self._download_cache[url] = {
                'state': state,
                'temp_path': temp_path,
                'error': error
            }

    def is_downloading(self, url: str) -> bool:
        """Check if URL is currently being downloaded."""
        with self._download_lock:
            return url in self._active_downloads

    def start_download(self, url: str):
        """Mark URL as being downloaded."""
        with self._download_lock:
            self._active_downloads.add(url)

    def finish_download(self, url: str):
        """Mark URL download as finished."""
        with self._download_lock:
            self._active_downloads.discard(url)

    def cleanup(self):
        """Clean up temporary files and cache."""
        with self._download_lock:
            for cache_data in self._download_cache.values():
                temp_path = cache_data.get('temp_path')
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except Exception as e:
                        logger.debug(f"Could not delete temp file {temp_path}: {e}")
            self._download_cache.clear()
            self._active_downloads.clear()


url_image_manager = URLImageManager()


class URLImageComponent(ImageComponent):
    """Image component that can load images from URLs asynchronously."""

    def __init__(self,
                 image_url: str,
                 x: int = 0,
                 y: int = 0,
                 width: int = 100,
                 height: int = 100,
                 fit: ImageFit = ImageFit.CONTAIN,
                 position: ImagePosition = ImagePosition.CENTER,
                 corner_radius: int = 8,
                 on_load: Optional[Callable] = None,
                 on_error: Optional[Callable] = None,
                 on_size_changed: Optional[Callable] = None,
                 show_loading_text: bool = True,
                 show_error_text: bool = True,
                 loading_text: str = "Loading image...",
                 error_text: str = "Failed to load image",
                 max_height: int = None,
                 **kwargs):
        """
        Initialize URLImageComponent.
        
        Args:
            image_url: URL of the image to load
            x, y, width, height: Component bounds
            fit: How image should fit within bounds
            position: How image should be positioned within bounds
            corner_radius: Radius for rounded corners
            on_load: Optional callback when image loads successfully
            on_error: Optional callback when image fails to load
            on_size_changed: Optional callback when component size changes after loading
            show_loading_text: Whether to show loading text
            show_error_text: Whether to show error text
            loading_text: Text to show while loading
            error_text: Text to show on error
            max_height: Maximum height in pixels (scaled by UI)
            **kwargs: Additional arguments passed to ImageComponent
        """

        super().__init__("", x, y, width, height, fit, position, corner_radius, **kwargs)

        self.image_url = image_url
        self.state = URLImageState.IDLE
        self.error_message = None
        self.temp_file_path = None

        self.on_load = on_load
        self.on_error = on_error
        self.on_size_changed = on_size_changed

        self.show_loading_text = show_loading_text
        self.show_error_text = show_error_text
        self.loading_text = loading_text
        self.error_text = error_text

        self.container_width = width
        self.max_height = CoordinateSystem.scale_int(max_height) if max_height else CoordinateSystem.scale_int(800)

        self.loading_animation_dots = 0
        self.loading_animation_time = 0

        cached_state = url_image_manager.get_cached_state(self.image_url)
        if cached_state['state'] == URLImageState.LOADED and cached_state.get('temp_path'):

            self.temp_file_path = cached_state['temp_path']
            self.state = URLImageState.LOADED
            self._update_image_path()
        elif cached_state['state'] == URLImageState.ERROR:

            self.state = URLImageState.ERROR
            self.error_message = cached_state.get('error', 'Unknown error')
        else:

            self._start_download()

    def _start_download(self):
        """Start downloading the image asynchronously."""
        if not self.image_url or self.image_url.startswith("data:"):
            logger.debug("Skipping download for data URL or empty URL")
            return

        if url_image_manager.is_downloading(self.image_url):
            self.state = URLImageState.LOADING
            return

        cached_state = url_image_manager.get_cached_state(self.image_url)
        if cached_state['state'] in [URLImageState.LOADED, URLImageState.ERROR]:
            return

        self.state = URLImageState.LOADING
        url_image_manager.set_cached_state(self.image_url, URLImageState.LOADING)
        url_image_manager.start_download(self.image_url)

        def download_worker():
            """Worker function that downloads the image in background thread."""
            temp_path = None
            try:
                logger.info(f"Starting download of image: {self.image_url}")

                request = urllib.request.Request(
                    self.image_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                )

                with urllib.request.urlopen(request, timeout=30) as response:
                    content_type = response.headers.get('content-type', '').lower()
                    data = response.read()

                if 'jpeg' in content_type or 'jpg' in content_type:
                    file_ext = '.jpg'
                elif 'png' in content_type:
                    file_ext = '.png'
                elif 'gif' in content_type:
                    file_ext = '.gif'
                elif 'webp' in content_type:
                    file_ext = '.webp'
                else:

                    if data.startswith(b'\x89PNG'):
                        file_ext = '.png'
                    elif data.startswith(b'\xff\xd8\xff'):
                        file_ext = '.jpg'
                    elif data.startswith(b'GIF'):
                        file_ext = '.gif'
                    elif data.startswith(b'RIFF') and b'WEBP' in data[:12]:
                        file_ext = '.webp'
                    else:
                        file_ext = '.png'

                temp_file = tempfile.NamedTemporaryFile(suffix=file_ext, delete=False)
                temp_path = temp_file.name

                temp_file.write(data)
                temp_file.close()

                if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                    raise Exception("Downloaded file is empty or does not exist")

                logger.info(f"Successfully downloaded image to: {temp_path} (detected format: {file_ext})")

                url_image_manager.set_cached_state(self.image_url, URLImageState.LOADED, temp_path)

                def on_download_success():
                    """Update UI on main thread after successful download."""
                    try:
                        if self.image_url:
                            self.temp_file_path = temp_path
                            self.state = URLImageState.LOADED
                            self.error_message = None
                            self._update_image_path()

                            if self.on_load:
                                try:
                                    self.on_load()
                                except Exception as e:
                                    logger.error(f"Error in on_load callback: {e}")

                    except Exception as e:
                        logger.error(f"Error updating UI after download success: {e}")
                    return None

                bpy.app.timers.register(on_download_success, first_interval=0.1)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to download image {self.image_url}: {error_msg}")

                try:
                    if temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass

                url_image_manager.set_cached_state(self.image_url, URLImageState.ERROR, error=error_msg)

                def on_download_error():
                    """Update UI on main thread after download error."""
                    try:
                        if self.image_url:
                            self.state = URLImageState.ERROR
                            self.error_message = error_msg

                            if self.on_error:
                                try:
                                    self.on_error(error_msg)
                                except Exception as e:
                                    logger.error(f"Error in on_error callback: {e}")

                    except Exception as e:
                        logger.error(f"Error updating UI after download error: {e}")
                    return None

                bpy.app.timers.register(on_download_error, first_interval=0.1)

            finally:

                url_image_manager.finish_download(self.image_url)

        download_thread = threading.Thread(target=download_worker, daemon=True)
        download_thread.start()

    def _calculate_optimal_size(self) -> tuple[int, int]:
        """Calculate optimal size based on image aspect ratio and constraints."""
        if not self.image_loaded or not self.image_width or not self.image_height:
            return self.container_width, min(self.max_height, CoordinateSystem.scale_int(300))

        aspect_ratio = self.image_width / self.image_height

        target_width = self.container_width
        target_height = int(target_width / aspect_ratio)

        if target_height > self.max_height:
            target_height = self.max_height
            target_width = int(target_height * aspect_ratio)

        logger.debug(f"Calculated optimal size: {target_width}x{target_height} "
                     f"(original: {self.image_width}x{self.image_height}, "
                     f"aspect: {aspect_ratio:.2f}, container_width: {self.container_width}, "
                     f"max_height: {self.max_height})")

        return target_width, target_height

    def set_container_width(self, width: int):
        """Update the container width and recalculate size if image is loaded."""
        old_width = self.container_width
        self.container_width = width

        logger.debug(f"URL image container width updated from {old_width} to {width}")

        if self.image_loaded and old_width != width:

            new_width, new_height = self._calculate_optimal_size()
            logger.debug(f"Recalculating size due to container width change: {new_width}x{new_height}")
            self.set_size(new_width, new_height)

            if self.on_size_changed:
                try:
                    self.on_size_changed()
                except Exception as e:
                    logger.error(f"Error in on_size_changed callback during container width update: {e}")
        elif not self.image_loaded:

            logger.debug(f"Container width updated but image not loaded yet - will recalculate when image loads")

    def _update_image_path(self):
        """Update the parent ImageComponent with the downloaded image path."""
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            logger.debug(f"Updating image path to: {self.temp_file_path}")

            old_image_loaded = self.image_loaded
            old_texture_attempted = self._texture_creation_attempted
            old_size = (self.bounds.width, self.bounds.height)

            self.set_image(self.temp_file_path)

            if self.image_data and not self.image_loaded:
                logger.debug("Image data loaded but texture not created, forcing GPU texture creation")
                self._texture_creation_attempted = False
                self._ensure_gpu_texture()

            if self.image_loaded:
                optimal_width, optimal_height = self._calculate_optimal_size()
                logger.debug(f"Setting optimal size: {optimal_width}x{optimal_height}")
                self.set_size(optimal_width, optimal_height)

                new_size = (optimal_width, optimal_height)
                if new_size != old_size and self.on_size_changed:
                    try:
                        self.on_size_changed()
                    except Exception as e:
                        logger.error(f"Error in on_size_changed callback: {e}")

            logger.debug(f"Image update result - loaded: {old_image_loaded} -> {self.image_loaded}, "
                         f"texture_attempted: {old_texture_attempted} -> {self._texture_creation_attempted}, "
                         f"size: {old_size} -> {(self.bounds.width, self.bounds.height)}")
        else:
            logger.error(f"Cannot update image path - temp file not found: {self.temp_file_path}")

    def _resolve_image_path(self) -> str:
        """Override parent method to properly handle temp file paths."""

        if os.path.isabs(self.image_path):
            if os.path.exists(self.image_path):
                logger.debug(f"Using absolute path: {self.image_path}")
                return self.image_path
            else:
                logger.error(f"Absolute path does not exist: {self.image_path}")
                return self.image_path

        return super()._resolve_image_path()

    def render(self, renderer):
        """Render the URL image component with state-specific UI."""
        if not self.visible:
            return

        if self.bounds.width <= 0 or self.bounds.height <= 0:
            logger.debug(f"Skipping render - invalid bounds: {self.bounds.width}x{self.bounds.height}")
            return

        if self.state == URLImageState.LOADED:
            logger.debug(f"Rendering URL image - state: {self.state}, image_loaded: {self.image_loaded}, "
                         f"has_texture: {self.image_texture is not None}, temp_path: {self.temp_file_path}")

        if self.background_color:
            if self.corner_radius > 0:
                renderer.draw_rounded_rect(self.bounds, self.background_color, self.corner_radius)
            else:
                renderer.draw_rect(self.bounds, self.background_color)

        if self.state == URLImageState.LOADED:

            if self.image_data and not self.image_loaded and not self._texture_creation_attempted:
                logger.debug("Image data exists but no GPU texture, creating texture...")
                self._ensure_gpu_texture()

            if self.image_loaded and self.image_texture:

                logger.debug("Rendering loaded image")
                super().render(renderer)
            else:

                logger.warning(
                    f"Image state is LOADED but rendering failed - image_loaded: {self.image_loaded}, texture: {self.image_texture is not None}")
                self._render_error_state(renderer)
        elif self.state == URLImageState.LOADING:

            self._render_loading_state(renderer)
        elif self.state == URLImageState.ERROR:

            self._render_error_state(renderer)
        else:

            self._render_placeholder(renderer)

        if self.border_width > 0:
            if self.corner_radius > 0:
                renderer.draw_rounded_rect_outline(
                    self.bounds, self.border_color, self.border_width, self.corner_radius
                )
            else:
                renderer.draw_rect_outline(self.bounds, self.border_color, self.border_width)

    def _render_loading_state(self, renderer):
        """Render loading state with animated text."""

        placeholder_color = Colors.lighten_color(Colors.Panel, 10)
        if self.corner_radius > 0:
            renderer.draw_rounded_rect(self.bounds, placeholder_color, self.corner_radius)
        else:
            renderer.draw_rect(self.bounds, placeholder_color)

        if self.show_loading_text:

            current_time = time.time()
            if current_time - self.loading_animation_time > 0.5:
                self.loading_animation_dots = (self.loading_animation_dots + 1) % 4
                self.loading_animation_time = current_time

            dots = "." * self.loading_animation_dots
            animated_text = self.loading_text + dots

            text_width, text_height = renderer.get_text_dimensions(animated_text, 16)

            text_x = self.bounds.x + (self.bounds.width - text_width) // 2
            text_y = self.bounds.y + (self.bounds.height - text_height) // 2

            renderer.draw_text(
                animated_text,
                text_x,
                text_y,
                16,
                Colors.Text,
                0
            )

    def _render_error_state(self, renderer):
        """Render error state."""

        error_bg_color = (0.8, 0.2, 0.2, 0.1)
        if self.corner_radius > 0:
            renderer.draw_rounded_rect(self.bounds, error_bg_color, self.corner_radius)
        else:
            renderer.draw_rect(self.bounds, error_bg_color)

        if self.show_error_text:
            text_width, text_height = renderer.get_text_dimensions(self.error_text, 16)

            text_x = self.bounds.x + (self.bounds.width - text_width) // 2
            text_y = self.bounds.y + (self.bounds.height - text_height) // 2

            error_text_color = (0.9, 0.3, 0.3, 1.0)
            renderer.draw_text(
                self.error_text,
                text_x,
                text_y,
                16,
                error_text_color,
                0
            )

    def _render_placeholder(self, renderer):
        """Render placeholder state."""

        placeholder_color = Colors.lighten_color(Colors.Panel, 5)
        if self.corner_radius > 0:
            renderer.draw_rounded_rect(self.bounds, placeholder_color, self.corner_radius)
        else:
            renderer.draw_rect(self.bounds, placeholder_color)

        placeholder_text = "Image"
        text_width, text_height = renderer.get_text_dimensions(placeholder_text, 16)

        text_x = self.bounds.x + (self.bounds.width - text_width) // 2
        text_y = self.bounds.y + (self.bounds.height - text_height) // 2

        renderer.draw_text(
            placeholder_text,
            text_x,
            text_y,
            16,
            Colors.Text,
            0
        )

    def set_url(self, new_url: str):
        """Change the image URL and start loading."""
        if self.image_url != new_url:

            self.cleanup()

            self.image_url = new_url
            self.state = URLImageState.IDLE
            self.error_message = None
            self.temp_file_path = None

            cached_state = url_image_manager.get_cached_state(self.image_url)
            if cached_state['state'] == URLImageState.LOADED and cached_state.get('temp_path'):
                self.temp_file_path = cached_state['temp_path']
                self.state = URLImageState.LOADED
                self._update_image_path()
            elif cached_state['state'] == URLImageState.ERROR:
                self.state = URLImageState.ERROR
                self.error_message = cached_state.get('error', 'Unknown error')
            else:
                self._start_download()

    def retry_download(self):
        """Retry downloading the image."""
        if self.state == URLImageState.ERROR:
            url_image_manager.set_cached_state(self.image_url, URLImageState.IDLE)
            self.state = URLImageState.IDLE
            self.error_message = None
            self._start_download()

    def _ensure_gpu_texture(self):
        """Override to add better error handling for temp files."""

        if hasattr(self, 'temp_file_path') and self.temp_file_path:
            if not os.path.exists(self.temp_file_path):
                logger.error(f"Temp file was cleaned up before GPU texture creation: {self.temp_file_path}")
                self.state = URLImageState.ERROR
                self.error_message = "Image file was cleaned up"
                return False

        result = super()._ensure_gpu_texture()

        if not result and self.state == URLImageState.LOADED:
            logger.error(f"GPU texture creation failed for loaded image: {self.image_path}")

        return result

    def cleanup(self):
        """Clean up resources."""

        super().cleanup()


def cleanup_url_image_manager():
    """Clean up the global URL image manager."""
    url_image_manager.cleanup()
