import logging
import math
import os
import re
import time
from typing import TYPE_CHECKING, List

import blf
import bpy
import gpu
from gpu.types import Buffer
from gpu_extras.batch import batch_for_shader

from .base import UIComponent
from .code_block import CodeBlockComponent
from .image import ImageComponent, ImageFit, ImagePosition
from .message import wrap_text_blf
from .url_image import URLImageComponent, URLImageState
from ..component_theming import get_themed_component_style
from ..coordinates import CoordinateSystem
from ..styles import FontSizes, MarkdownLayout
from ..types import EventType, UIEvent
from ..unified_styles import Styles

if TYPE_CHECKING:
    from ..renderer import UIRenderer

logger = logging.getLogger(__name__)

MARKDOWN_LINE_HEIGHT_MULTIPLIER = 1.75
MIN_LINE_HEIGHT = 8
FONT_BASELINE_OFFSET_RATIO = 0.3
FONT_REGULAR = 0
FONT_BOLD = None
FONT_ITALIC = None


def get_table_cell_padding():
    return CoordinateSystem.scale_int(8)


def get_table_border_width():
    return CoordinateSystem.scale_int(1)


def get_table_header_height_multiplier():
    return 1.4


def get_table_row_height_multiplier():
    return 1.2


def get_table_height_padding():
    return CoordinateSystem.scale_int(12)


def _get_consistent_line_height(font_size: int) -> int:
    line_height = math.ceil(font_size * MARKDOWN_LINE_HEIGHT_MULTIPLIER)
    return max(MIN_LINE_HEIGHT, line_height)


class FontManager:

    def __init__(self):
        self.fonts = {}
        self._font_paths = {
            'regular': 'fonts/regular.ttf',
            'bold': 'fonts/bold.ttf',
            'italic': 'fonts/italic.ttf',
            'medium': 'fonts/medium.ttf'
        }
        self._loaded_fonts = {}
        self._addon_path = None

    def _get_addon_path(self):

        if self._addon_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self._addon_path = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        return self._addon_path

    def get_font_id(self, font_type: str) -> int:

        if font_type in self._loaded_fonts:
            return self._loaded_fonts[font_type]

        if font_type == 'regular':
            self._loaded_fonts[font_type] = 0
            return 0

        if font_type not in self._font_paths:
            return self.get_font_id('regular')

        try:
            font_path = os.path.join(self._get_addon_path(), self._font_paths[font_type])
            if os.path.exists(font_path):
                font_id = blf.load(font_path)
                if font_id != -1:
                    self._loaded_fonts[font_type] = font_id
                    return font_id
                else:
                    logger.warning(f"Failed to load font {font_type} from {font_path}")
            else:
                logger.warning(f"Font file not found: {font_path}")
        except Exception as e:
            logger.error(f"Error loading font {font_type}: {e}")

        return self.get_font_id('regular')

    def cleanup(self):

        for font_type, font_id in self._loaded_fonts.items():
            if font_type != 'regular' and font_id != 0 and font_id != -1:
                try:
                    font_path = os.path.join(self._get_addon_path(), self._font_paths[font_type])
                    blf.unload(font_path)
                except Exception as e:
                    logger.debug(f"Could not unload font {font_type}: {e}")
        self._loaded_fonts.clear()


font_manager = FontManager()


class MarkdownElement:

    def __init__(self, text: str, element_type: str = 'text', level: int = 0):
        self.text = text
        self.element_type = element_type
        self.level = level
        self.font_size = FontSizes.Default
        self.font_id = FONT_REGULAR
        self.color = (0.9, 0.9, 0.9, 1.0)
        self.is_bold = False
        self.is_italic = False
        self.is_code = False
        self.block_type = None
        self.is_animated = False
        self.animation_start_time = None
        self.formatted_parts = []
        self.url = None
        self.alt_text = None
        self.image_component = None
        self.code_block_component = None
        self.code_language = None
        self.table_headers = []
        self.table_rows = []
        self.table_alignments = []

    def set_formatted_parts(self, parts):

        self.formatted_parts = parts

    def set_table_data(self, headers: List[str], rows: List[List[str]], alignments: List[str] = None):

        self.table_headers = headers
        self.table_rows = rows
        self.table_alignments = alignments or ['left'] * len(headers)

    def start_animation(self):

        self.is_animated = True
        self.animation_start_time = time.time()

    def stop_animation(self):

        self.is_animated = False
        self.animation_start_time = None

    def get_animation_progress(self) -> float:

        if not self.is_animated or self.animation_start_time is None:
            return 0.0

        cycle_duration = 0.8
        elapsed = time.time() - self.animation_start_time
        progress = (elapsed % cycle_duration) / cycle_duration
        return progress

    def apply_formatting(self, base_font_size: int, base_color: tuple):

        self.color = base_color

        if self.element_type == 'heading':
            self.font_size = int(base_font_size * MarkdownLayout.HEADING_SIZE_MULTIPLIERS.get(self.level, 1.0))
            self.is_bold = True
            self.font_id = font_manager.get_font_id('bold')
        elif self.element_type == 'code' or self.element_type == 'code_block':
            self.font_size = int(base_font_size)
            self.font_id = font_manager.get_font_id('monospace')
        elif self.element_type == 'bold':
            self.is_bold = True
            self.font_id = font_manager.get_font_id('bold')
        elif self.element_type == 'italic':
            self.is_italic = True
            self.font_id = font_manager.get_font_id('italic')
        elif self.element_type == 'list_item':
            self.font_size = base_font_size
            self.font_id = font_manager.get_font_id('regular')
            if not self.text.startswith('• ') and not self.text.startswith('- ') and not self.text.startswith('* '):
                if not (len(self.text) > 2 and self.text[0].isdigit() and self.text[1:3] == '. '):
                    self.text = "• " + self.text
        elif self.element_type == 'link':
            self.font_size = base_font_size
            self.color = (0.4, 0.6, 1.0, 1.0)
            self.font_id = font_manager.get_font_id('regular')
        elif self.element_type == 'table':
            self.font_size = base_font_size
            self.font_id = font_manager.get_font_id('regular')
        elif self.element_type == 'block':
            self.font_size = int(base_font_size * MarkdownLayout.CODE_FONT_SIZE_MULTIPLIER)
            self.color = (0.6, 0.6, 0.6, 1.0)
            self.font_id = font_manager.get_font_id('regular')
            if self._is_in_progress_block():
                self.start_animation()
        elif self.element_type == 'hr':
            pass
        elif self.element_type == 'image':
            pass
        else:
            self.font_size = base_font_size
            self.font_id = font_manager.get_font_id('regular')

    def _is_in_progress_block(self) -> bool:

        if not self.block_type:
            return False

        text_lower = self.text.lower()

        completed_indicators = [
            'code executed', 'execution complete', 'executed successfully',
            'scene read', 'scene analyzed', 'analysis complete',
            'web search complete', 'search completed', 'search finished',
            'image analyzed', 'image processing complete',
            'viewport captured', 'viewport capture complete', 'screenshot captured',
            'render completed', 'render complete', 'render finished', 'rendered successfully',
            'properties read', 'settings read',
            'tool executed', 'tool finished', 'execution done',
            'objects modified', 'scene updated', 'objects created',
            'update applied', 'modification complete', 'update complete',
            'code failed', 'execution failed', 'scene reading failed',
            'search failed', 'web search failed', 'image analysis failed',
            'capture failed', 'render failed', 'properties reading failed',
            'analysis failed', 'nodes analysis failed', 'tool failed'
        ]

        if any(indicator in text_lower for indicator in completed_indicators):
            return False

        in_progress_indicators = [
            'executing code', 'reading scene', 'analyzing scene', 'querying',
            'analyzing', 'thinking', 'processing', 'searching web', 'searching',
            'analyzing image', 'processing image', 'reading image',
            'capturing viewport', 'viewport capture', 'taking screenshot',
            'capturing render', 'render capture',
            'starting render', 'rendering', 'scene render',
            'generating code', 'generating text', 'finding', 'locating',
            'reading data', 'analyzing data', 'processing data',
            'modifying scene', 'updating scene', 'creating objects', 'adding objects'
        ]

        return any(indicator in text_lower for indicator in in_progress_indicators)


class BlockIconManager:

    def __init__(self):
        self.icon_components = {}

    def get_icon_component(self, icon_name: str):

        if icon_name not in self.icon_components:
            self.icon_components[icon_name] = ImageComponent(
                image_path=f"{icon_name}.png",
                x=0, y=0, width=MarkdownLayout.BLOCK_ICON_SIZE(), height=MarkdownLayout.BLOCK_ICON_SIZE(),
                fit=ImageFit.CONTAIN,
                position=ImagePosition.CENTER
            )
        return self.icon_components[icon_name]

    def get_block_icon_texture(self, block_type: str):

        if not block_type:
            return None

        icon_mapping = {
            'reading': 'scene',
            'planning': 'brain',
            'coding': 'code',
            'executing': 'code',
            'fixing': 'bug',
            'web_search': 'globe',
            'settings': 'settings',
            'processing': 'brain',
            'scene': 'scene',
            'image': 'image',
            'write': 'pen',
            'search': 'search',
            'viewport_capture': 'image',
            'render_capture': 'image',
            'tool': 'settings',
        }

        icon_name = icon_mapping.get(block_type)
        if not icon_name:
            return None

        try:
            icon_component = self.get_icon_component(icon_name)
            if not icon_component.image_loaded and not icon_component._texture_creation_attempted:
                icon_component._ensure_gpu_texture()
            return icon_component.image_texture if icon_component.image_loaded else None
        except Exception as e:
            logger.error(f"Failed to load icon {icon_name}: {str(e)}")
            return None

    def cleanup(self):

        for icon_component in self.icon_components.values():
            icon_component.cleanup()
        self.icon_components.clear()


block_icon_manager = BlockIconManager()


class ImprovedMarkdownRenderer:

    def __init__(self):
        self.elements = []
        self.patterns = {
            'header': re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE),
            'hr': re.compile(r'^(?:\*{3,}|-{3,}|_{3,})\s*$', re.MULTILINE),
            'code_block': re.compile(r'^```(?:\w+)?\n(.*?)\n```$', re.MULTILINE | re.DOTALL),
            'table': re.compile(r'^(\|.*\|)\s*$', re.MULTILINE),
            'link': re.compile(r'(?:\[([^\]]+)\]\(([^)]+)\)|<(https?://[^>]+)>)'),
            'image': re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),
            'bold': re.compile(r'(?:\*\*|__)([^*_]+)(?:\*\*|__)'),
            'italic': re.compile(r'(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)'),
            'inline_code': re.compile(r'`([^`]+)`'),
            'list_item': re.compile(r'^(?:\s*[-*+]|\s*\d+\.)\s+(.+)$', re.MULTILINE),
            'block': re.compile(r'^\[([^\]]+)\](?:\s*[.!?]*)?\s*(.*)$', re.MULTILINE),
        }

    def parse_markdown(self, markdown_text: str) -> List[MarkdownElement]:

        self.elements = []

        try:
            self._parse_advanced_markdown(markdown_text)
            if not self.elements and markdown_text.strip():
                self.elements = [MarkdownElement(markdown_text.strip(), 'text')]
        except Exception as e:
            logger.error(f"Error parsing markdown: {e}")
            self.elements = [MarkdownElement(markdown_text, 'text')]

        return self.elements

    def _parse_advanced_markdown(self, text: str):

        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].rstrip()

            if not line.strip():
                i += 1
                continue

            if line.strip().startswith('```'):
                i = self._parse_code_block(lines, i)
                continue

            if self.patterns['table'].match(line):
                i = self._parse_table(lines, i)
                continue

            header_match = self.patterns['header'].match(line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2).strip()
                self.elements.append(MarkdownElement(text, 'heading', level))
                i += 1
                continue

            if self.patterns['hr'].match(line):
                self.elements.append(MarkdownElement('', 'hr'))
                i += 1
                continue

            block_match = self.patterns['block'].match(line)
            if block_match:
                block_text = block_match.group(1).strip()
                remaining_text = block_match.group(2).strip() if block_match.group(2) else ''

                block_type = self._get_block_type(block_text)
                if block_type:
                    element = MarkdownElement(block_text, 'block')
                    element.block_type = block_type
                    self.elements.append(element)

                    if remaining_text:
                        remaining_text = remaining_text.lstrip('.!?;,: ')
                        if remaining_text:
                            self._parse_inline_formatting(remaining_text)
                    i += 1
                    continue

            list_match = self.patterns['list_item'].match(line)
            if list_match:
                list_text = list_match.group(1).strip()
                self._parse_inline_formatting_for_element(line, 'list_item')
                i += 1
                continue

            self._parse_inline_formatting(line)
            i += 1

    def _parse_table(self, lines: List[str], start_index: int) -> int:

        table_lines = []
        i = start_index

        while i < len(lines):
            line = lines[i].rstrip()
            if self.patterns['table'].match(line):
                table_lines.append(line)
                i += 1
            else:
                break

        if len(table_lines) < 2:
            for line in table_lines:
                self._parse_inline_formatting(line)
            return i

        headers = []
        alignments = []
        rows = []

        header_line = table_lines[0]
        header_cells = [cell.strip() for cell in header_line.split('|')[1:-1]]
        headers = [self._parse_table_cell_content(cell) for cell in header_cells]

        if len(table_lines) > 1:
            alignment_line = table_lines[1]
            alignment_cells = [cell.strip() for cell in alignment_line.split('|')[1:-1]]

            is_alignment_row = all(
                self._is_alignment_cell(cell) for cell in alignment_cells
            )

            if is_alignment_row:
                alignments = [self._parse_alignment(cell) for cell in alignment_cells]
                data_start = 2
            else:
                alignments = ['left'] * len(headers)
                data_start = 1
        else:
            alignments = ['left'] * len(headers)
            data_start = 1

        for row_line in table_lines[data_start:]:
            row_cells = [cell.strip() for cell in row_line.split('|')[1:-1]]
            row_data = [self._parse_table_cell_content(cell) for cell in row_cells]

            while len(row_data) < len(headers):
                row_data.append('')

            rows.append(row_data)

        table_element = MarkdownElement('', 'table')
        table_element.set_table_data(headers, rows, alignments)
        self.elements.append(table_element)

        return i

    def _is_alignment_cell(self, cell: str) -> bool:

        cell = cell.strip()
        if not cell or '-' not in cell:
            return False
        allowed_chars = set('-:')
        return all(c in allowed_chars for c in cell)

    def _parse_alignment(self, cell: str) -> str:

        cell = cell.strip()
        if cell.startswith(':') and cell.endswith(':'):
            return 'center'
        elif cell.endswith(':'):
            return 'right'
        else:
            return 'left'

    def _parse_table_cell_content(self, cell: str) -> str:

        return cell.strip()

    def _parse_code_block(self, lines: List[str], start_index: int) -> int:

        opening_line = lines[start_index].strip()
        language = opening_line[3:].strip() if len(opening_line) > 3 else ""

        i = start_index + 1
        code_lines = []

        while i < len(lines):
            if lines[i].strip().startswith('```'):
                code_text = '\n'.join(code_lines)
                element = MarkdownElement(code_text, 'code_block')
                element.code_language = language
                self.elements.append(element)
                return i + 1
            code_lines.append(lines[i])
            i += 1

        for line in [lines[start_index]] + code_lines:
            if line.strip():
                self._parse_inline_formatting(line)
        return i

    def _parse_inline_formatting(self, text: str):

        if not text.strip():
            return

        image_matches = list(self.patterns['image'].finditer(text))
        if image_matches:
            for match in image_matches:
                alt_text = match.group(1) if match.group(1) else ''
                url = match.group(2)
                element = MarkdownElement(url, 'image')
                element.url = url
                element.alt_text = alt_text
                self.elements.append(element)
                text = text.replace(match.group(0), '')

        link_matches = list(self.patterns['link'].finditer(text))
        if link_matches:
            last_end = 0
            for match in link_matches:
                before_text = text[last_end:match.start()]
                if before_text.strip():
                    self._parse_text_formatting(before_text)

                if match.group(3):
                    url = match.group(3)
                    display_text = url
                else:
                    display_text = match.group(2)
                    url = match.group(2)

                element = MarkdownElement(display_text, 'link')
                element.url = url
                self.elements.append(element)
                last_end = match.end()

            remaining_text = text[last_end:]
            if remaining_text.strip():
                self._parse_text_formatting(remaining_text)
        else:
            self._parse_text_formatting(text)

    def _parse_text_formatting(self, text: str):

        parts = self._extract_formatting_parts(text)

        if len(parts) == 1 and parts[0][1] == 'text':
            element = MarkdownElement(parts[0][0], 'text')
            self.elements.append(element)
        else:
            element = MarkdownElement(text, 'text')
            element.set_formatted_parts(parts)
            self.elements.append(element)

    def _parse_inline_formatting_for_element(self, text: str, base_element_type: str):

        if not text:
            if base_element_type == 'list_item':
                self.elements.append(MarkdownElement("", 'list_item'))
            return

        parts = self._extract_formatting_parts(text)
        element = MarkdownElement(text, base_element_type)
        element.set_formatted_parts(parts)
        self.elements.append(element)

    def _extract_formatting_parts(self, text: str):

        parts = []
        current_text = ""
        i = 0

        while i < len(text):
            char = text[i]

            if char == '`':
                if current_text:
                    parts.append((current_text, 'text'))
                    current_text = ""

                i += 1
                code_text = ""
                found_closing = False

                while i < len(text):
                    if text[i] == '`':
                        parts.append((code_text, 'code'))
                        i += 1
                        found_closing = True
                        break
                    else:
                        code_text += text[i]
                        i += 1

                if not found_closing:
                    current_text += '`' + code_text

            elif (char == '*' and i + 1 < len(text) and text[i + 1] == '*') or (
                    char == '_' and i + 1 < len(text) and text[i + 1] == '_'):
                if current_text:
                    parts.append((current_text, 'text'))
                    current_text = ""

                delimiter = char
                i += 2
                bold_text = ""
                found_closing = False

                while i + 1 < len(text):
                    if text[i] == delimiter and text[i + 1] == delimiter:
                        parts.append((bold_text, 'bold'))
                        i += 2
                        found_closing = True
                        break
                    else:
                        bold_text += text[i]
                        i += 1

                if not found_closing:
                    current_text += delimiter + delimiter + bold_text

            elif (char == '*' and not (i > 0 and text[i - 1] == '*') and not (
                    i + 1 < len(text) and text[i + 1] == '*')) or (
                    char == '_' and not (i > 0 and text[i - 1] == '_') and not (
                    i + 1 < len(text) and text[i + 1] == '_')):
                if current_text:
                    parts.append((current_text, 'text'))
                    current_text = ""

                delimiter = char
                i += 1
                italic_text = ""
                found_closing = False

                while i < len(text):
                    if text[i] == delimiter and not (i + 1 < len(text) and text[i + 1] == delimiter):
                        parts.append((italic_text, 'italic'))
                        i += 1
                        found_closing = True
                        break
                    else:
                        italic_text += text[i]
                        i += 1

                if not found_closing:
                    current_text += delimiter + italic_text

            else:
                current_text += char
                i += 1

        if current_text:
            parts.append((current_text, 'text'))

        return parts

    def _get_block_type(self, block_text: str) -> str:

        block_text_lower = block_text.lower()

        if 'rendering scene' in block_text_lower or 'render captured' in block_text_lower:
            return 'render_capture'
        elif 'render failed' in block_text_lower or 'render error' in block_text_lower:
            return 'render_capture'
        if 'reading scene' in block_text_lower or 'scene read' in block_text_lower:
            return 'reading'
        elif 'analyzing scene' in block_text_lower or 'scene analyzed' in block_text_lower:
            return 'reading'
        elif 'querying' in block_text_lower or 'query' in block_text_lower:
            return 'reading'
        elif 'reading' in block_text_lower and ('properties' in block_text_lower or 'settings' in block_text_lower):
            return 'reading'
        elif 'planning' in block_text_lower or 'analyzing' in block_text_lower:
            return 'planning'
        elif 'thinking' in block_text_lower or 'processing' in block_text_lower:
            return 'processing'
        elif 'writing code' in block_text_lower or 'coding' in block_text_lower:
            return 'coding'
        elif 'executing code' in block_text_lower or 'executing' in block_text_lower:
            return 'executing'
        elif 'code executed' in block_text_lower or 'execution' in block_text_lower:
            return 'executing'
        elif 'fixing code' in block_text_lower or 'fixing' in block_text_lower:
            return 'fixing'
        elif 'debugging' in block_text_lower or 'debug' in block_text_lower:
            return 'fixing'
        elif 'executed' in block_text_lower or 'complete' in block_text_lower or 'done' in block_text_lower:
            return 'coding'
        elif 'searching web' in block_text_lower or 'web search' in block_text_lower:
            return 'web_search'
        elif 'searching' in block_text_lower and ('internet' in block_text_lower or 'online' in block_text_lower):
            return 'web_search'
        elif 'finding information' in block_text_lower or 'looking up' in block_text_lower:
            return 'web_search'
        elif 'found' in block_text_lower and 'results' in block_text_lower:
            return 'web_search'
        elif 'capturing viewport' in block_text_lower or 'viewport capturing' in block_text_lower:
            return 'viewport_capture'
        elif 'capturing render' in block_text_lower or 'render capturing' in block_text_lower:
            return 'render_capture'
        elif 'viewport captured' in block_text_lower or 'viewport capture' in block_text_lower:
            return 'viewport_capture'
        elif 'render captured' in block_text_lower or 'render capture' in block_text_lower:
            return 'render_capture'
        elif 'analyzing image' in block_text_lower or 'image analysis' in block_text_lower:
            return 'image'
        elif 'processing image' in block_text_lower or 'image processing' in block_text_lower:
            return 'image'
        elif 'reading image' in block_text_lower or 'image read' in block_text_lower:
            return 'image'
        elif 'image analysed' in block_text_lower or 'image analyzed' in block_text_lower:
            return 'image'
        elif 'writing' in block_text_lower and 'code' not in block_text_lower:
            return 'write'
        elif 'generating text' in block_text_lower or 'text generation' in block_text_lower:
            return 'write'
        elif 'searching' in block_text_lower and 'web' not in block_text_lower:
            return 'search'
        elif 'finding' in block_text_lower or 'locating' in block_text_lower:
            return 'search'
        elif 'using tool' in block_text_lower or 'tool' in block_text_lower:
            return 'tool'
        elif 'analyzing data' in block_text_lower or 'processing data' in block_text_lower:
            return 'processing'
        elif 'modifying scene' in block_text_lower or 'updating scene' in block_text_lower:
            return 'scene'
        elif 'creating objects' in block_text_lower or 'adding objects' in block_text_lower:
            return 'scene'
        elif 'scene' in block_text_lower and ('modified' in block_text_lower or 'updated' in block_text_lower):
            return 'scene'

        return None

class MarkdownMessageComponent(UIComponent):

    def __init__(self, markdown_text: str, x: int = 0, y: int = 0, width: int = 400, height: int = 40):
        super().__init__(x, y, width, height)

        self.markdown_text = markdown_text
        self.corner_radius = MarkdownLayout.CORNER_RADIUS()
        self.padding = 0
        self.padding_vertical = 0
        self.renderer = ImprovedMarkdownRenderer()
        self.elements = []
        self._cached_wrapped_elements = None
        self._cached_width = None
        self._cached_markdown = None
        self._text_dimension_cache = {}
        self._selection_active = False
        self._selection_start_pos = None
        self._selection_end_pos = None
        self._selecting = False
        self._rendered_text_positions = []
        self.on_height_changed = None

        self.apply_themed_style("message")
        self._parse_markdown()

    def apply_themed_style(self, style_type: str = "message"):

        try:
            from ..unified_styles import Styles

            self.style = get_themed_component_style("button")
            self.style.background_color = (0.0, 0.0, 0.0, 0.0)
            self.style.border_color = Styles.Selected
            self.style.border_width = 0
            self.style.text_color = Styles.Text
            self.style.font_size = FontSizes.Default
        except Exception as e:
            logger.warning(f"Could not apply themed style: {e}")
            from ..unified_styles import Styles
            self.style.background_color = (0.0, 0.0, 0.0, 0.0)
            self.style.border_color = Styles.Selected
            self.style.border_width = 0
            self.style.text_color = Styles.Text
            self.style.font_size = FontSizes.Default

    def set_markdown(self, markdown_text: str):

        if self.markdown_text != markdown_text:
            old_width = self.bounds.width
            self.markdown_text = markdown_text
            self._parse_markdown()
            self._update_animation_states()
            self._invalidate_text_cache()

            max_width = 800
            required_width, _ = self.calculate_required_size(max_width)
            if required_width != old_width:
                self.set_size(required_width, self.bounds.height)

    def _update_animation_states(self):

        try:
            for element in self.elements:
                if element.element_type == 'block':
                    if element._is_in_progress_block():
                        if not element.is_animated:
                            element.start_animation()
                    else:
                        if element.is_animated:
                            element.stop_animation()
        except Exception as e:
            logger.error(f"Error updating animation states: {e}")

    def get_message(self) -> str:

        return self.markdown_text

    def _parse_markdown(self):

        self.elements = self.renderer.parse_markdown(self.markdown_text)

        for element in self.elements:
            element.apply_formatting(self.style.font_size, self.style.text_color)

            if element.element_type == 'image' and element.url:
                try:
                    is_url = (element.url.startswith('http://') or
                              element.url.startswith('https://') or
                              element.url.startswith('data:'))

                    if is_url:
                        available_width = max(
                            self.bounds.width - (self.padding * 2) - (self.style.border_width * 2), 400)

                        element.image_component = URLImageComponent(
                            image_url=element.url,
                            x=0, y=0,
                            width=available_width,
                            height=CoordinateSystem.scale_int(300),
                            fit=ImageFit.CONTAIN,
                            position=ImagePosition.CENTER,
                            corner_radius=8,
                            loading_text="Loading image...",
                            error_text="Failed to load image",
                            max_height=800,
                            on_load=self._on_image_loaded,
                            on_error=self._on_image_error,
                            on_size_changed=self._on_image_size_changed
                        )
                        element.image_component.set_container_width(available_width)
                    else:
                        element.image_component = ImageComponent(
                            image_path=element.url,
                            x=0, y=0,
                            width=self.bounds.width if self.bounds.width > 0 else 800,
                            height=200,
                            fit=ImageFit.CONTAIN,
                            position=ImagePosition.CENTER
                        )
                except Exception as e:
                    logger.error(f"Failed to create image component for {element.url}: {e}")

            elif element.element_type == 'code_block' and element.text:
                try:
                    available_width = max(self.bounds.width - (self.padding * 2) - (self.style.border_width * 2),
                                          400)
                    element.code_block_component = CodeBlockComponent(
                        code=element.text,
                        language=element.code_language or "",
                        x=0, y=0,
                        width=available_width
                    )
                except Exception as e:
                    logger.error(f"Failed to create code block component: {e}")

    def _on_image_loaded(self):

        try:
            old_height = self.bounds.height
            self._invalidate_cache()
            current_width = self.bounds.width
            new_width, new_height = self.calculate_required_size(current_width)
            self.set_size(new_width, new_height)

            if self.on_height_changed and old_height != new_height:
                try:
                    self.on_height_changed(old_height, new_height)
                except Exception as e:
                    logger.error(f"Error in on_height_changed callback: {e}")

            if hasattr(self, 'ui_state') and self.ui_state and hasattr(self.ui_state, 'target_area'):
                self.ui_state.target_area.tag_redraw()
        except Exception as e:
            logger.error(f"Error handling image load: {e}")

    def _on_image_size_changed(self):

        try:
            old_height = self.bounds.height
            self._invalidate_cache()
            current_width = self.bounds.width
            new_width, new_height = self.calculate_required_size(current_width)
            self.set_size(new_width, new_height)

            if self.on_height_changed and old_height != new_height:
                try:
                    self.on_height_changed(old_height, new_height)
                except Exception as e:
                    logger.error(f"Error in on_height_changed callback: {e}")

            if hasattr(self, 'ui_state') and self.ui_state and hasattr(self.ui_state, 'target_area'):
                self.ui_state.target_area.tag_redraw()
        except Exception as e:
            logger.error(f"Error handling image size change: {e}")

    def _on_image_error(self, error_message: str):

        logger.warning(f"Image failed to load: {error_message}")
        try:
            if hasattr(self, 'ui_state') and self.ui_state and hasattr(self.ui_state, 'target_area'):
                self.ui_state.target_area.tag_redraw()
        except Exception as e:
            pass

    def _invalidate_text_cache(self):

        try:
            self._text_dimension_cache.clear()
            self._invalidate_cache()
        except Exception as e:
            logger.debug(f"Error invalidating text cache: {e}")

    def _get_text_height_blf(self, text: str, font_size: int) -> int:

        if not text:
            return font_size

        cache_key = (text, font_size)
        if cache_key not in self._text_dimension_cache:
            try:
                blf.size(0, font_size)
                dimensions = blf.dimensions(0, text)
                self._text_dimension_cache[cache_key] = dimensions[1] if len(dimensions) > 1 else font_size
            except Exception as e:
                logger.debug(f"Error measuring text height: {e}")
                self._text_dimension_cache[cache_key] = font_size

        return self._text_dimension_cache[cache_key]

    def _get_fs_for_type(self, typ: str, base_fs: int) -> int:

        if typ == 'bold':
            return int(base_fs * MarkdownLayout.BOLD_FONT_SIZE_MULTIPLIER)
        elif typ == 'code':
            return int(base_fs * MarkdownLayout.CODE_FONT_SIZE_MULTIPLIER)
        else:
            return base_fs

    def _calculate_line_height(self, element) -> int:

        if element.element_type == 'block':
            return MarkdownLayout.BLOCK_HEIGHT()
        elif element.element_type == 'hr':
            return CoordinateSystem.scale_int(20)
        elif element.element_type == 'code_block':
            if element.code_block_component:
                return element.code_block_component.bounds.height + CoordinateSystem.scale_int(10)
            else:
                lines = element.text.split('\n') if element.text else [""]
                line_height = int(FontSizes.Default * MarkdownLayout.CODE_FONT_SIZE_MULTIPLIER * 1.4)
                return len(lines) * line_height + CoordinateSystem.scale_int(60)
        elif element.element_type == 'image':
            if element.image_component:
                if element.image_component.bounds.height <= 0:
                    return CoordinateSystem.scale_int(300)

                if hasattr(element.image_component, 'state'):
                    if element.image_component.state == URLImageState.LOADED:
                        return element.image_component.bounds.height + CoordinateSystem.scale_int(10)
                    elif element.image_component.state == URLImageState.LOADING:
                        container_width = element.image_component.container_width
                        max_height = element.image_component.max_height
                        estimated_height = int(container_width * 9 / 16)
                        loading_height = min(estimated_height, max_height)
                        loading_height = max(loading_height, CoordinateSystem.scale_int(150))
                        return loading_height + CoordinateSystem.scale_int(10)
                    elif element.image_component.state == URLImageState.ERROR:
                        return CoordinateSystem.scale_int(80)
                    else:
                        container_width = getattr(element.image_component, 'container_width',
                                                  CoordinateSystem.scale_int(400))
                        max_height = getattr(element.image_component, 'max_height', CoordinateSystem.scale_int(800))
                        estimated_height = int(container_width * 9 / 16)
                        default_height = min(estimated_height, max_height)
                        default_height = max(default_height, CoordinateSystem.scale_int(200))
                        return default_height + CoordinateSystem.scale_int(10)
                else:
                    return element.image_component.bounds.height + CoordinateSystem.scale_int(10)
            else:
                return CoordinateSystem.scale_int(300)
        elif element.element_type == 'table':
            return self._calculate_table_height(element)

        if element.formatted_parts:
            max_font_size = element.font_size
            for part_text, part_type in element.formatted_parts:
                fs = self._get_fs_for_type(part_type, element.font_size)
                max_font_size = max(max_font_size, fs)
            return _get_consistent_line_height(max_font_size)
        else:
            return _get_consistent_line_height(element.font_size)

    def _calculate_table_height(self, table_element) -> int:

        if not table_element.table_headers:
            return CoordinateSystem.scale_int(40)

        header_height = int(
            table_element.font_size * get_table_header_height_multiplier() * get_table_row_height_multiplier()) + get_table_cell_padding() * 2
        row_height = int(table_element.font_size * get_table_row_height_multiplier()) + get_table_cell_padding() * 2

        total_height = header_height + (len(table_element.table_rows) * row_height)
        total_height += get_table_border_width() * (len(table_element.table_rows) + 1)

        return total_height

    def _invalidate_cache(self):

        self._cached_wrapped_elements = None
        self._cached_width = None
        self._cached_markdown = None
        self._rendered_text_positions = []

    def _get_wrapped_elements(self, available_width: int) -> List[tuple]:

        if (self._cached_wrapped_elements is not None and
                self._cached_width == available_width and
                self._cached_markdown == self.markdown_text):
            return self._cached_wrapped_elements

        wrapped_elements = []

        for element in self.elements:
            if element.element_type == 'block':
                wrapped_elements.append((element.text, element))
            elif element.element_type == 'hr':
                wrapped_elements.append(('', element))
            elif element.element_type == 'image':
                wrapped_elements.append((element.alt_text or '', element))
            elif element.element_type == 'table':
                wrapped_elements.append(('', element))
            elif element.element_type == 'code_block':
                wrapped_elements.append(('', element))
            elif element.text.strip():
                if element.formatted_parts:
                    wrapped_with_formatting = self._wrap_formatted_text(element, available_width)
                    wrapped_elements.extend(wrapped_with_formatting)
                else:
                    wrapped_lines = wrap_text_blf(element.text, available_width, element.font_size)
                    for line in wrapped_lines:
                        if line.strip():
                            wrapped_elements.append((line, element))

        self._cached_wrapped_elements = wrapped_elements
        self._cached_width = available_width
        self._cached_markdown = self.markdown_text

        return wrapped_elements

    def _wrap_formatted_text(self, element, available_width: int) -> List[tuple]:

        formatted_spans = []
        for p_text, p_type in element.formatted_parts:
            fs = self._get_fs_for_type(p_type, element.font_size)
            color = (0.8, 1.0, 0.8, 1.0) if p_type in ['bold', 'code'] else element.color

            if p_type == 'bold':
                font_id = font_manager.get_font_id('bold')
            elif p_type == 'italic':
                font_id = font_manager.get_font_id('italic')
            elif p_type == 'code':
                font_id = font_manager.get_font_id('regular')
            else:
                font_id = font_manager.get_font_id('regular')

            formatted_spans.append({
                'text': p_text,
                'type': p_type,
                'fs': fs,
                'color': color,
                'font_id': font_id
            })


            mini_spans = []
            for span in formatted_spans:

                lines = span['text'].split('\n')
                for line_idx, line in enumerate(lines):

                    if line_idx > 0:
                        newline_mini = {
                            'text': '\n',
                            'type': span['type'],
                            'fs': span['fs'],
                            'color': span['color'],
                            'font_id': span['font_id']
                        }
                        mini_spans.append(newline_mini)

                    leading_whitespace = ''
                    content_start = 0
                    for i, char in enumerate(line):
                        if char.isspace():
                            leading_whitespace += char
                            content_start = i + 1
                        else:
                            break

                    if leading_whitespace:
                        whitespace_mini = {
                            'text': leading_whitespace,
                            'type': span['type'],
                            'fs': span['fs'],
                            'color': span['color'],
                            'font_id': span['font_id']
                        }
                        mini_spans.append(whitespace_mini)

                    content = line[content_start:]

                    words = []
                    current_word = ""
                    for char in content:
                        if char.isspace():
                            if current_word:
                                words.append(current_word)
                                current_word = ""
                            words.append(char)
                        else:
                            current_word += char
                    if current_word:
                        words.append(current_word)

                    for word in words:
                        word_mini = {
                            'text': word,
                            'type': span['type'],
                            'fs': span['fs'],
                            'color': span['color'],
                            'font_id': span['font_id']
                        }
                        mini_spans.append(word_mini)

            lines = []
            current_line = []
            current_width = 0
            for mini in mini_spans:

                if mini['text'] == '\n':
                    if current_line:
                        lines.append(current_line)
                        current_line = []
                        current_width = 0
                    continue

                w = self._measure_text_width(mini['text'], mini['fs'], mini['font_id'])
                if current_width + w > available_width and current_line:
                    lines.append(current_line)
                    current_line = []
                    current_width = 0

                    if mini['text'].isspace() and not any(
                            c.isspace() for c in ''.join(m['text'] for m in current_line)):
                        continue

                current_line.append(mini)
                current_width += w
            if current_line:
                lines.append(current_line)

            result = []
            for line_spans in lines:
                merged_parts = []
                current_part = None
                for mini in line_spans:
                    if current_part and current_part['type'] == mini['type'] and current_part['fs'] == mini[
                        'fs'] and current_part['color'] == mini['color'] and current_part['font_id'] == mini[
                        'font_id']:
                        current_part['text'] += mini['text']
                    else:
                        if current_part:
                            merged_parts.append(current_part)
                        current_part = mini.copy()
                if current_part:
                    merged_parts.append(current_part)

                line_text = ''.join(p['text'] for p in merged_parts)
                if not line_text.strip():
                    continue
                line_parts = [(p['text'], p['type']) for p in merged_parts]

                line_element = MarkdownElement(line_text, element.element_type, element.level)
                line_element.set_formatted_parts(line_parts)
                line_element.color = element.color
                line_element.font_size = element.font_size

                result.append((line_text, line_element))

            return result

    def _measure_text_width(self, text: str, font_size: int, font_id: int = 0) -> float:

        dimensions = self._get_cached_text_dimensions(text, font_size, font_id)
        return dimensions[0]

    def _get_cached_text_dimensions(self, text: str, font_size: int, font_id: int = 0) -> tuple:

        if not text:
            return (0, font_size)

        cache_key = (text, font_size, font_id)
        if cache_key not in self._text_dimension_cache:
            try:
                blf.size(font_id, font_size)
                dimensions = blf.dimensions(font_id, text)
                self._text_dimension_cache[cache_key] = dimensions if dimensions else (
                    len(text) * (font_size * 0.6), font_size)
            except Exception as e:
                logger.debug(f"Error measuring text dimensions: {e}")
                self._text_dimension_cache[cache_key] = (len(text) * (font_size * 0.6), font_size)
        return self._text_dimension_cache[cache_key]

    def calculate_required_size(self, max_width: int) -> tuple[int, int]:

        if not self.elements:
            return (MarkdownLayout.MIN_COMPONENT_WIDTH(), MarkdownLayout.MIN_COMPONENT_HEIGHT())

        border_and_padding = (self.padding * 2) + (self.style.border_width * 2)
        available_width = max_width - border_and_padding

        wrapped_elements = self._get_wrapped_elements(available_width)

        max_line_width = 0
        total_height = 0
        first_block = True

        try:
            for line_text, element in wrapped_elements:
                if element.element_type == 'block':

                    icon_size = MarkdownLayout.BLOCK_ICON_SIZE()
                    padding = MarkdownLayout.BLOCK_PADDING()
                    text_padding = MarkdownLayout.BLOCK_TEXT_PADDING()

                    blf.size(element.font_id, element.font_size)

                    try:
                        text_dimensions = self._get_cached_text_dimensions(element.text, element.font_size,
                                                                           element.font_id)
                        text_width = text_dimensions[0] if text_dimensions else len(element.text) * (
                                element.font_size * MarkdownLayout.TEXT_ESTIMATION_FACTOR)
                    except:
                        text_width = len(element.text) * (
                                    element.font_size * MarkdownLayout.TEXT_ESTIMATION_FACTOR)

                    content_width = padding + icon_size + text_padding + text_width + padding
                    block_width = min(max(content_width, MarkdownLayout.BLOCK_MIN_WIDTH()), available_width)

                    block_height = MarkdownLayout.BLOCK_HEIGHT()

                    if first_block:
                        total_height += block_height
                        first_block = False
                    else:
                        total_height += block_height + MarkdownLayout.BLOCK_MARGIN()

                    max_line_width = max(max_line_width, block_width)
                elif element.element_type == 'hr':

                    max_line_width = max(max_line_width, available_width)
                    total_height += self._calculate_line_height(element)
                    first_block = False
                elif element.element_type == 'image':

                    max_line_width = max(max_line_width, available_width)
                    total_height += self._calculate_line_height(element)
                    first_block = False
                elif element.element_type == 'table':

                    max_line_width = max(max_line_width, available_width)
                    total_height += self._calculate_line_height(element)
                    first_block = False
                elif element.element_type == 'code_block':

                    max_line_width = max(max_line_width, available_width)
                    total_height += self._calculate_line_height(element)
                    first_block = False
                else:

                    if element.formatted_parts:
                        line_width = 0
                        for p_text, p_type in element.formatted_parts:
                            fs = self._get_fs_for_type(p_type, element.font_size)

                            if p_type == 'bold':
                                font_id = font_manager.get_font_id('bold')
                            elif p_type == 'italic':
                                font_id = font_manager.get_font_id('italic')
                            elif p_type == 'code':
                                font_id = font_manager.get_font_id('regular')
                            else:
                                font_id = font_manager.get_font_id('regular')

                            part_dimensions = self._get_cached_text_dimensions(p_text, fs, font_id)
                            line_width += part_dimensions[0]
                    else:
                        line_dimensions = self._get_cached_text_dimensions(line_text, element.font_size,
                                                                           element.font_id)
                        line_width = line_dimensions[0]

                    max_line_width = max(max_line_width, line_width)

                    line_height = self._calculate_line_height(element)
                    total_height += line_height
                    first_block = False

        except Exception as e:
            logger.error(f"Error calculating markdown size: {e}")

            estimated_lines = len(wrapped_elements)
            base_font_size = self.style.font_size
            estimated_line_height = _get_consistent_line_height(base_font_size)
            total_height = estimated_lines * estimated_line_height
            max_line_width = available_width

        content_width = min(max_line_width + border_and_padding, max_width)
        content_height = total_height + (self.padding_vertical * 2) + (self.style.border_width * 2)

        return (max(MarkdownLayout.MIN_COMPONENT_WIDTH(), content_width),
                max(MarkdownLayout.MIN_COMPONENT_HEIGHT(), content_height))

    def set_size(self, width: int, height: int):

        old_width = self.bounds.width
        old_height = self.bounds.height

        super().set_size(width, height)

        if old_width != width:
            self._invalidate_text_cache()

            available_width = max(width - (self.padding * 2) - (self.style.border_width * 2), 400)

            for element in self.elements:
                if element.element_type == 'image' and element.image_component:

                    if hasattr(element.image_component, 'set_container_width'):

                        logger.debug(
                        )
                        element.image_component.set_container_width(available_width)
                    else:

                        element.image_component.set_size(available_width, element.image_component.bounds.height)
                elif element.element_type == 'code_block' and element.code_block_component:

                    element.code_block_component.set_size(available_width,
                                                          element.code_block_component.bounds.height)

        if self.on_height_changed and old_height != height:
            try:
                logger.debug(
                )
                self.on_height_changed(old_height, height)
            except Exception as e:
                logger.error(f"Error in on_height_changed callback during set_size: {e}")

    def trigger_layout_update(self):

        try:
            old_height = self.bounds.height

            self._invalidate_cache()
            current_width = self.bounds.width
            new_width, new_height = self.calculate_required_size(current_width)

            if new_height != old_height:
                self.set_size(new_width, new_height)
                logger.debug(f"Manual layout update triggered height change: {old_height} -> {new_height}")

        except Exception as e:
            logger.error(f"Error during manual layout update: {e}")

    def render(self, renderer: 'UIRenderer'):

        if not self.visible:
            return

        if not self.elements:
            renderer.draw_rounded_rect(self.bounds, self.style.background_color, self.corner_radius)
            return

        renderer.draw_rounded_rect(self.bounds, self.style.background_color, self.corner_radius)

        if self.style.border_width > 0:
            renderer.draw_rounded_rect_outline(
                self.bounds,
                self.style.border_color,
                self.style.border_width,
                self.corner_radius
            )

        text_x = self.bounds.x + self.padding + self.style.border_width
        text_y = self.bounds.y + self.padding_vertical + self.style.border_width + CoordinateSystem.scale_int(2)
        text_width = self.bounds.width - (self.padding * 2) - (self.style.border_width * 2)
        text_height = self.bounds.height - (self.padding_vertical * 2) - (self.style.border_width * 2)

        self._rendered_text_positions = []

        if self._selection_active:
            self._render_selection_highlights(renderer, text_x, text_y, text_width, text_height)

        self._render_markdown_text(renderer, text_x, text_y, text_width, text_height)

    def _render_markdown_text(self, renderer: 'UIRenderer', x: int, y: int, width: int, height: int):

        wrapped_elements = self._get_wrapped_elements(width)

        current_y = y + height
        first_block = True
        element_index = 0

        for line_text, element in wrapped_elements:
            if element.element_type == 'block':

                block_height = MarkdownLayout.BLOCK_HEIGHT()

                if first_block:
                    current_y -= block_height
                    first_block = False
                else:
                    current_y -= block_height + MarkdownLayout.BLOCK_MARGIN()

                if current_y >= y:
                    self._render_special_block(renderer, element, x, current_y, width, block_height)

                    self._store_text_position(element_index, element.text, x, current_y, width, block_height)
                element_index += 1
            elif element.element_type == 'hr':

                line_height = self._calculate_line_height(element)
                current_y -= line_height
                first_block = False

                if current_y >= y:
                    self._render_horizontal_rule(renderer, x, current_y + line_height // 2, width)

            elif element.element_type == 'image':

                line_height = self._calculate_line_height(element)
                current_y -= line_height
                first_block = False

                if current_y >= y and element.image_component:

                    element.image_component.set_position(x, current_y)

                    if not hasattr(element.image_component, 'state'):

                        element.image_component.set_size(width, element.image_component.bounds.height)
                    else:

                        logger.debug(
                        )

                    element.image_component.render(renderer)

                    self._store_text_position(element_index, element.alt_text or element.url, x, current_y,
                                              width,
                                              line_height)
                element_index += 1
            elif element.element_type == 'table':

                line_height = self._calculate_line_height(element)

                if not first_block:
                    current_y -= CoordinateSystem.scale_int(8)

                current_y -= line_height
                first_block = False

                if current_y >= y:
                    self._render_table(renderer, element, x, current_y, width, line_height)

                    table_text = ' | '.join(element.table_headers)
                    for row in element.table_rows:
                        table_text += '\n' + ' | '.join(row)
                    self._store_text_position(element_index, table_text, x, current_y, width, line_height)

                current_y -= CoordinateSystem.scale_int(8)
                element_index += 1
            elif element.element_type == 'code_block':

                line_height = self._calculate_line_height(element)

                if not first_block:
                    current_y -= CoordinateSystem.scale_int(8)

                current_y -= line_height
                first_block = False

                if current_y >= y and element.code_block_component:
                    element.code_block_component.set_position(x, current_y)

                    element.code_block_component.set_size(width, element.code_block_component.bounds.height)

                    element.code_block_component.render(renderer)

                    self._store_text_position(element_index, element.text, x, current_y, width, line_height)

                current_y -= CoordinateSystem.scale_int(8)
                element_index += 1
            else:

                line_height = self._calculate_line_height(element)
                current_y -= line_height
                first_block = False

                if current_y >= y:

                    self._store_text_position(element_index, line_text, x, current_y, width, line_height)

                    if element.formatted_parts:
                        self._render_mixed_formatting_line(renderer, line_text, element, x, current_y)
                    else:

                        renderer.draw_text(
                            line_text,
                            x,
                            current_y,
                            element.font_size,
                            element.color,
                            element.font_id
                        )
                element_index += 1

            if current_y < y:
                break

    def _render_horizontal_rule(self, renderer: 'UIRenderer', x: int, y: int, width: int):

        from ..types import Bounds

        line_color = (0.5, 0.5, 0.5, 1.0)
        line_height = 1
        line_bounds = Bounds(x, y, width, line_height)

        renderer.draw_rounded_rect(line_bounds, line_color, 0)

    def _render_special_block(self, renderer: 'UIRenderer', element, x: int, y: int, width: int, height: int):

        from ..types import Bounds

        icon_size = MarkdownLayout.BLOCK_ICON_SIZE()
        padding = MarkdownLayout.BLOCK_PADDING()
        text_padding = MarkdownLayout.BLOCK_TEXT_PADDING()

        blf.size(element.font_id, element.font_size)

        try:
            text_dimensions = self._get_cached_text_dimensions(element.text, element.font_size, element.font_id)
            text_width = text_dimensions[0] if text_dimensions else len(element.text) * (
                    element.font_size * MarkdownLayout.TEXT_ESTIMATION_FACTOR)
        except:
            text_width = len(element.text) * (element.font_size * MarkdownLayout.TEXT_ESTIMATION_FACTOR)

        content_width = padding + icon_size + text_padding + text_width + padding + CoordinateSystem.scale_int(
            8)

        block_width = min(max(content_width, MarkdownLayout.BLOCK_MIN_WIDTH()), width)

        block_x = x

        block_bounds = Bounds(block_x, y, block_width, height)

        block_bg_color = Styles.lighten_color(Styles.Panel, 5)

        renderer.draw_rounded_rect(block_bounds, block_bg_color, MarkdownLayout.BLOCK_CORNER_RADIUS())

        if element.is_animated:
            self._render_animated_gradient(renderer, block_bounds, element.get_animation_progress())

        icon_map = {
            'reading': 'scene',
            'planning': 'brain',
            'coding': 'code',
            'executing': 'code',
            'fixing': 'bug',
            'web_search': 'globe',
            'settings': 'settings',
            'processing': 'brain',
            'scene': 'scene',
            'image': 'image',
            'write': 'pen',
            'search': 'search',
            'viewport_capture': 'image',
            'render_capture': 'image',
            'tool': 'settings',
        }
        icon_name = icon_map.get(element.block_type)

        text_start_x = block_x + padding
        icon_texture = None

        if icon_name:
            block_icon_manager.get_icon_component(icon_name)

            icon_texture = block_icon_manager.get_block_icon_texture(element.block_type)

        if icon_texture:

            icon_x = text_start_x
            icon_y = y + (height - icon_size) // 2

            try:
                renderer.draw_image(icon_texture, icon_x, icon_y, icon_size, icon_size)
                text_start_x += icon_size + text_padding
            except Exception as e:
                logger.warning(f"Could not render icon for block {element.block_type}: {e}")

        text_x = text_start_x

        block_center_y = y + (height // 2)
        baseline_offset = element.font_size * FONT_BASELINE_OFFSET_RATIO
        text_y = block_center_y - baseline_offset - CoordinateSystem.scale_int(2)

        blf.size(element.font_id, element.font_size)
        renderer.draw_text(
            element.text,
            text_x,
            text_y,
            element.font_size,
            element.color,
            element.font_id
        )

    def _render_animated_gradient(self, renderer: 'UIRenderer', block_bounds, progress: float):

        try:
            gradient_width = block_bounds.width * 0.5
            gradient_center_opacity = 0.06
            corner_radius = MarkdownLayout.BLOCK_CORNER_RADIUS()

            eased_progress = -(math.cos(math.pi * progress) - 1) / 2

            gradient_center_x = block_bounds.x + (
                        block_bounds.width + gradient_width) * eased_progress - gradient_width / 2

            segments = 15

            for i in range(segments):
                segment_start = gradient_center_x - gradient_width / 2 + (i / segments) * gradient_width
                segment_end = gradient_center_x - gradient_width / 2 + ((i + 1) / segments) * gradient_width

                clipped_start = max(segment_start, block_bounds.x)
                clipped_end = min(segment_end, block_bounds.x + block_bounds.width)

                if clipped_start >= clipped_end:
                    continue

                segment_center = (segment_start + segment_end) / 2
                distance_from_gradient_center = abs(segment_center - gradient_center_x) / (gradient_width / 2)

                falloff_factor = math.cos(distance_from_gradient_center * math.pi / 2)
                falloff_factor = max(0.0, falloff_factor) ** 1.5

                opacity = gradient_center_opacity * falloff_factor

                if opacity < 0.005:
                    continue

                vertices = self._create_gradient_segment_vertices(
                    clipped_start, clipped_end, block_bounds, corner_radius
                )

                if len(vertices) < 3:
                    continue

                indices = []
                center_vertex = len(vertices) // 2
                for j in range(len(vertices) - 1):
                    indices.append((center_vertex, j, j + 1))
                indices.append((center_vertex, len(vertices) - 1, 0))

                batch = batch_for_shader(
                    renderer.shader,
                    'TRIS',
                    {"pos": vertices},
                    indices=indices
                )

                gpu.state.blend_set('ALPHA')
                renderer.shader.bind()
                renderer.shader.uniform_float("color", (1.0, 1.0, 1.0, opacity))
                batch.draw(renderer.shader)
                gpu.state.blend_set('NONE')

        except Exception as e:
            logger.debug(f"Could not render animated gradient: {e}")

    def _create_gradient_segment_vertices(self, segment_start_x: float, segment_end_x: float,
                                          block_bounds, corner_radius: float) -> list:

        vertices = []

        left_corner_center_x = block_bounds.x + corner_radius
        right_corner_center_x = block_bounds.x + block_bounds.width - corner_radius

        sample_count = 6

        def calc_y_offset(sample_x):
            y_offset = 0.0
            if sample_x < left_corner_center_x:
                dx = left_corner_center_x - sample_x
                if dx <= corner_radius:
                    dy = corner_radius - (corner_radius ** 2 - dx ** 2) ** 0.5
                    y_offset = max(y_offset, dy)
            elif sample_x > right_corner_center_x:
                dx = sample_x - right_corner_center_x
                if dx <= corner_radius:
                    dy = corner_radius - (corner_radius ** 2 - dx ** 2) ** 0.5
                    y_offset = max(y_offset, dy)
            return y_offset + 0.5

        bottom_vertices = []
        for k in range(sample_count):
            sample_x = segment_start_x + (k / (sample_count - 1)) * (segment_end_x - segment_start_x)
            y_offset = calc_y_offset(sample_x)
            bottom_y = block_bounds.y + y_offset
            bottom_vertices.append((sample_x, bottom_y))

        top_vertices = []
        for k in range(sample_count):
            sample_x = segment_start_x + (k / (sample_count - 1)) * (segment_end_x - segment_start_x)
            y_offset = calc_y_offset(sample_x)
            top_y = block_bounds.y + block_bounds.height - y_offset
            top_vertices.append((sample_x, top_y))

        vertices = bottom_vertices + list(reversed(top_vertices))
        return vertices

    def _render_mixed_formatting_line(self, renderer: 'UIRenderer', line_text: str, element, x: int, y: int):

        current_x = x

        for part_text, part_type in element.formatted_parts:
            if not part_text:
                continue

            if part_type == 'bold':
                color = element.color
                font_size = self._get_fs_for_type('bold', element.font_size)
                font_id = font_manager.get_font_id('bold')
            elif part_type == 'italic':
                color = element.color
                font_size = element.font_size
                font_id = font_manager.get_font_id('italic')
            elif part_type == 'code':
                color = element.color
                font_size = self._get_fs_for_type('code', element.font_size)
                font_id = font_manager.get_font_id('regular')
            else:
                color = element.color
                font_size = element.font_size
                font_id = font_manager.get_font_id('regular')

            blf.size(font_id, font_size)
            renderer.draw_text(
                part_text,
                current_x,
                y,
                font_size,
                color,
                font_id
            )

            try:
                text_dimensions = self._get_cached_text_dimensions(part_text, font_size, font_id)
                text_width = text_dimensions[0]
                current_x += text_width
            except:

                current_x += len(part_text) * (font_size * MarkdownLayout.TEXT_ESTIMATION_FACTOR)

    def auto_resize_to_content(self, max_width: int):

        required_width, required_height = self.calculate_required_size(max_width)

        has_loading_images = any(
            element.element_type == 'image' and
            element.image_component and
            hasattr(element.image_component, 'state') and
            element.image_component.state in [URLImageState.IDLE, URLImageState.LOADING]
            for element in self.elements
        )

        if has_loading_images:
            logger.debug("Component has loading URL images, may need re-layout after loading")

        self.set_size(required_width, required_height)

    def cleanup(self):

        for element in self.elements:
            if element.element_type == 'image' and element.image_component:
                element.image_component.cleanup()
            elif element.element_type == 'code_block' and element.code_block_component:
                element.code_block_component.cleanup()

        try:
            block_icon_manager.cleanup()
            font_manager.cleanup()
        except:
            pass

        super().cleanup()

    def _render_table(self, renderer: 'UIRenderer', table_element, x: int, y: int, width: int, height: int):

        from ..types import Bounds

        if not table_element.table_headers or len(table_element.table_headers) == 0:
            logger.debug("Skipping table render: no headers")
            return

        try:
            column_widths = self._calculate_table_column_widths(table_element, width)
            if not column_widths or len(column_widths) == 0:
                logger.debug("Skipping table render: could not calculate column widths")
                return
        except Exception as e:
            logger.error(f"Error calculating table column widths: {e}")
            return

        table_width = width

        header_height = int(
            table_element.font_size * get_table_header_height_multiplier() * get_table_row_height_multiplier()) + get_table_cell_padding() * 2
        row_height = int(
            table_element.font_size * get_table_row_height_multiplier()) + get_table_cell_padding() * 2

        border_color = Styles.Border
        header_bg_color = Styles.lighten_color(Styles.Panel, 20)
        row_bg_color = Styles.Transparent
        alt_row_bg_color = Styles.Transparent

        current_y = y + height

        current_y -= header_height
        self._render_table_row(
            renderer, table_element.table_headers, column_widths,
            x, current_y, header_height, header_bg_color, border_color,
            table_element.font_size, table_element.color, table_element.font_id,
            table_element.table_alignments, is_header=True,
            row_index=-1, total_rows=len(table_element.table_rows), is_last_row=False
        )

        for row_index, row_data in enumerate(table_element.table_rows):
            current_y -= row_height

            bg_color = alt_row_bg_color if row_index % 2 == 1 else row_bg_color

            self._render_table_row(
                renderer, row_data, column_widths,
                x, current_y, row_height, bg_color, border_color,
                table_element.font_size, table_element.color, table_element.font_id,
                table_element.table_alignments, is_header=False,
                row_index=row_index, total_rows=len(table_element.table_rows),
                is_last_row=(row_index == len(table_element.table_rows) - 1)
            )

        table_bottom_y = current_y
        table_bottom_border_bounds = Bounds(x, table_bottom_y, table_width, get_table_border_width())
        renderer.draw_rounded_rect(table_bottom_border_bounds, border_color, 0)

    def _calculate_table_column_widths(self, table_element, available_width: int) -> List[int]:

        if not table_element.table_headers or len(table_element.table_headers) == 0:
            return []

        num_columns = len(table_element.table_headers)
        if num_columns == 0:
            return []

        min_widths = []
        for col_index in range(num_columns):
            max_width = 0

            if col_index < len(table_element.table_headers):
                header_text = str(table_element.table_headers[col_index])
                if header_text:
                    header_width = self._get_cached_text_dimensions(
                        header_text, table_element.font_size, table_element.font_id
                    )[0]
                    max_width = max(max_width, header_width)

            for row_data in table_element.table_rows:
                if col_index < len(row_data):
                    cell_text = str(row_data[col_index])
                    if cell_text:
                        cell_width = self._get_cached_text_dimensions(
                            cell_text, table_element.font_size, table_element.font_id
                        )[0]
                        max_width = max(max_width, cell_width)

            min_widths.append(max(max_width + (get_table_cell_padding() * 2), 50))

        if not min_widths:
            return []

        total_min_width = sum(min_widths) + (get_table_border_width() * (num_columns + 1))

        if total_min_width <= available_width:
            extra_space = available_width - total_min_width
            total_min_content = sum(min_widths)

            final_widths = []
            for min_width in min_widths:
                if total_min_content > 0:
                    proportion = min_width / total_min_content
                    final_widths.append(min_width + int(extra_space * proportion))
                else:
                    final_widths.append(min_width)
        else:
            scale_factor = available_width / total_min_width if total_min_width > 0 else 1.0
            final_widths = [max(50, int(w * scale_factor)) for w in min_widths]

        return final_widths

    def _render_table_row(self, renderer: 'UIRenderer', row_data: List[str], column_widths: List[int],
                          x: int, y: int, row_height: int, bg_color: tuple, border_color: tuple,
                          font_size: int, text_color: tuple, font_id: int, alignments: List[str],
                          is_header: bool = False,
                          row_index: int = 0, total_rows: int = 0, is_last_row: bool = False):

        from ..types import Bounds

        if not row_data or not column_widths:
            return

        table_width = sum(column_widths) + (get_table_border_width() * (len(column_widths) + 1))

        row_bounds = Bounds(x, y, table_width, row_height)
        renderer.draw_rounded_rect(row_bounds, bg_color, 0)

        if is_header:
            top_border_bounds = Bounds(x, y, table_width, get_table_border_width())
            renderer.draw_rounded_rect(top_border_bounds, border_color, 0)

        bottom_border_bounds = Bounds(x, y + row_height - get_table_border_width(), table_width,
                                      get_table_border_width())
        renderer.draw_rounded_rect(bottom_border_bounds, border_color, 0)

        left_border_bounds = Bounds(x, y, get_table_border_width(), row_height)
        renderer.draw_rounded_rect(left_border_bounds, border_color, 0)

        right_border_bounds = Bounds(x + table_width - get_table_border_width(), y, get_table_border_width(),
                                     row_height)
        renderer.draw_rounded_rect(right_border_bounds, border_color, 0)

        current_x = x + get_table_border_width()
        for col_index, col_width in enumerate(column_widths[:-1]):
            current_x += col_width
            separator_bounds = Bounds(current_x, y, get_table_border_width(), row_height)
            renderer.draw_rounded_rect(separator_bounds, border_color, 0)
            current_x += get_table_border_width()

        current_x = x + get_table_border_width()

        for col_index, (cell_text, col_width) in enumerate(zip(row_data, column_widths)):
            if col_index >= len(row_data):
                break

            cell_text = str(cell_text) if cell_text else ""
            alignment = alignments[col_index] if col_index < len(alignments) else 'left'
            text_x = current_x + get_table_cell_padding()

            if cell_text:
                if alignment == 'center':
                    text_width = self._get_cached_text_dimensions(cell_text, font_size, font_id)[0]
                    text_x = current_x + (col_width - text_width) // 2
                elif alignment == 'right':
                    text_width = self._get_cached_text_dimensions(cell_text, font_size, font_id)[0]
                    text_x = current_x + col_width - text_width - get_table_cell_padding()

                text_y = y + (row_height - font_size) // 2

                actual_font_id = font_manager.get_font_id('bold') if is_header else font_id
                actual_font_size = font_size

                renderer.draw_text(
                    cell_text,
                    text_x,
                    text_y,
                    actual_font_size,
                    text_color,
                    actual_font_id
                )

            current_x += col_width + get_table_border_width()

    def set_height_changed_callback(self, callback):

        self.on_height_changed = callback

    def handle_event(self, event) -> bool:

        if not self.bounds.contains_point(event.mouse_x, event.mouse_y):

            if self._selecting:
                self._selection_end_pos = self._get_character_position_at_coords(event.mouse_x, event.mouse_y)
                return True
            return False

        if event.event_type == EventType.MOUSE_PRESS:
            if event.data.get('button') == 'LEFT':
                self._selection_start_pos = self._get_character_position_at_coords(event.mouse_x, event.mouse_y)
                self._selection_end_pos = self._selection_start_pos
                self._selecting = True
                self._selection_active = True
                logger.info(f"Started text selection at position {self._selection_start_pos}")
                return True

        elif event.event_type == EventType.MOUSE_DRAG:
            if self._selecting:
                self._selection_end_pos = self._get_character_position_at_coords(event.mouse_x, event.mouse_y)
                logger.debug(f"Updated selection to {self._selection_start_pos} - {self._selection_end_pos}")
                return True

        elif event.event_type == EventType.MOUSE_RELEASE:
            if self._selecting:

                self._selecting = False
                self._selection_end_pos = self._get_character_position_at_coords(event.mouse_x, event.mouse_y)

                if (self._selection_start_pos == self._selection_end_pos):

                    self._selection_active = False
                    self._selection_start_pos = None
                    self._selection_end_pos = None
                    logger.info("Cleared selection (no text selected)")
                else:
                    logger.info(f"Completed selection: {self._selection_start_pos} - {self._selection_end_pos}")
                return True

        elif event.event_type == EventType.KEY_PRESS:

            if event.data.get('ctrl', False):
                if event.key == 'C':

                    if self._selection_active:
                        if self._copy_selection_to_clipboard():
                            logger.info("Copied selection to clipboard")
                        else:
                            logger.warning("No text selected for copying")
                        return True
                elif event.key == 'A':

                    if self._rendered_text_positions:
                        self._selection_start_pos = (0, 0)
                        last_pos = self._rendered_text_positions[-1]
                        self._selection_end_pos = (last_pos['element_index'], last_pos['char_count'])
                        self._selection_active = True
                        logger.info("Selected all text")
                        return True

            elif event.key == 'ESCAPE':

                if self._selection_active:
                    self._selection_active = False
                    self._selection_start_pos = None
                    self._selection_end_pos = None
                    self._selecting = False
                    logger.info("Cleared selection")
                    return True

        for element in self.elements:
            if element.element_type == 'code_block' and element.code_block_component:
                code_block = element.code_block_component

                local_x = event.mouse_x - self.bounds.x
                local_y = event.mouse_y - self.bounds.y

                if code_block.bounds.contains_point(local_x, local_y):
                    logger.info(f"MarkdownMessage: Event within code block bounds - forwarding to code block")

                    adjusted_event = UIEvent(
                        event.event_type,
                        local_x,
                        local_y,
                        event.key,
                        event.unicode,
                        event.data.copy() if hasattr(event, 'data') else {}
                    )
                    if code_block.handle_event(adjusted_event):
                        logger.info(f"MarkdownMessage: Code block handled event")
                        return True
                    else:
                        logger.info(f"MarkdownMessage: Code block did not handle event")

        return super().handle_event(event)

    def _store_text_position(self, element_index: int, text: str, x: int, y: int, width: int, height: int):

        if text:
            self._rendered_text_positions.append({
                'element_index': element_index,
                'text': text,
                'x': x,
                'y': y,
                'width': width,
                'height': height,
                'char_count': len(text)
            })

    def _render_selection_highlights(self, renderer: 'UIRenderer', x: int, y: int, width: int, height: int):

        if not self._selection_start_pos or not self._selection_end_pos:
            return

        try:

            start_pos = self._selection_start_pos
            end_pos = self._selection_end_pos

            if (start_pos[0] > end_pos[0] or
                    (start_pos[0] == end_pos[0] and start_pos[1] > end_pos[1])):
                start_pos, end_pos = end_pos, start_pos

            selection_color = (0.3, 0.5, 0.8, 0.3)

            for text_pos in self._rendered_text_positions:
                element_idx = text_pos['element_index']

                if element_idx < start_pos[0] or element_idx > end_pos[0]:
                    continue

                start_char = 0 if element_idx > start_pos[0] else start_pos[1]
                end_char = text_pos['char_count'] if element_idx < end_pos[0] else end_pos[1]

                if start_char >= end_char:
                    continue

                char_width = text_pos['width'] / max(1, text_pos['char_count'])
                highlight_x = text_pos['x'] + (start_char * char_width)
                highlight_width = (end_char - start_char) * char_width

                from ..types import Bounds
                highlight_bounds = Bounds(
                    int(highlight_x),
                    text_pos['y'],
                    int(highlight_width),
                    text_pos['height']
                )

                renderer.draw_rounded_rect(highlight_bounds, selection_color, 2)

        except Exception as e:
            logger.warning(f"Error rendering selection highlights: {e}")

    def _get_character_position_at_coords(self, mouse_x: int, mouse_y: int) -> tuple:

        try:
            if not self._rendered_text_positions:
                return (0, 0)

            local_x = mouse_x - self.bounds.x
            local_y = mouse_y - self.bounds.y

            for text_pos in self._rendered_text_positions:
                if text_pos['y'] <= local_y <= text_pos['y'] + text_pos['height']:
                    if text_pos['char_count'] > 0 and text_pos['width'] > 0:
                        char_width = text_pos['width'] / text_pos['char_count']
                        char_offset = max(0, local_x - text_pos['x'])
                        char_index = min(text_pos['char_count'], int(char_offset / char_width))
                    else:
                        char_index = 0

                    return (text_pos['element_index'], char_index)

            if self._rendered_text_positions:
                last_pos = self._rendered_text_positions[-1]
                return (last_pos['element_index'], last_pos['char_count'])

            return (0, 0)

        except Exception as e:
            logger.debug(f"Error getting character position: {e}")
            return (0, 0)

    def _get_selected_text(self) -> str:

        if not self._selection_start_pos or not self._selection_end_pos:
            return ""

        try:
            if not self._rendered_text_positions:
                return ""

            start_pos = self._selection_start_pos
            end_pos = self._selection_end_pos

            if (start_pos[0] > end_pos[0] or
                    (start_pos[0] == end_pos[0] and start_pos[1] > end_pos[1])):
                start_pos, end_pos = end_pos, start_pos

            selected_text = ""

            for text_pos in self._rendered_text_positions:
                element_idx = text_pos.get('element_index', -1)
                if element_idx < 0:
                    continue

                if element_idx < start_pos[0] or element_idx > end_pos[0]:
                    continue

                start_char = 0 if element_idx > start_pos[0] else start_pos[1]
                end_char = text_pos['char_count'] if element_idx < end_pos[0] else end_pos[1]

                if start_char >= end_char:
                    continue

                text_content = text_pos.get('text', '')
                if not text_content:
                    continue

                element_text = text_content[start_char:end_char] if start_char < len(text_content) else ""

                if selected_text and element_text:
                    selected_text += "\n"

                selected_text += element_text

            return selected_text

        except Exception as e:
            logger.debug(f"Error extracting selected text: {e}")
            return ""

    def _copy_selection_to_clipboard(self):

        try:
            selected_text = self._get_selected_text()
            if selected_text:
                bpy.context.window_manager.clipboard = selected_text
                logger.info(f"Copied to clipboard: {len(selected_text)} characters")
                return True
            return False
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            return False
