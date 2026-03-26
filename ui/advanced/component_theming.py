import logging
from typing import Tuple, Any

from .blender_theme_integration import get_theme_color
from .style_types import Style
from .unified_styles import UnifiedStyles

logger = logging.getLogger(__name__)


class ComponentThemer:
    COMPONENT_THEMES = {
        'text': {
            'text_color': 'text',
            'background_color': None,
            'border_color': None,
        },
        'button': {
            'text_color': 'text',
            'background_color': 'bg_primary',
            'border_color': 'border',
            'focus_background_color': 'bg_selected',
            'focus_border_color': 'text_selected',
            'pressed_background_color': 'bg_primary',
            'pressed_border_color': 'text',
        },
        'text_input': {
            'text_color': 'text',
            'background_color': 'bg_panel',
            'border_color': 'border',
            'focus_background_color': 'bg_panel',
            'focus_border_color': 'bg_selected',
            'pressed_background_color': 'text',
            'pressed_border_color': 'text_muted',
        },
        'input': {
            'text_color': 'text',
            'background_color': 'bg_panel',
            'border_color': 'border',
            'focus_background_color': 'bg_panel',
            'focus_border_color': 'bg_selected',
            'pressed_background_color': 'text',
            'pressed_border_color': 'text_muted',
        },
        'panel': {
            'background_color': 'bg_panel',
            'border_color': 'border',
        },
        'container': {
            'background_color': 'bg_panel',
            'border_color': 'border',
            'focus_background_color': 'border',
            'focus_border_color': 'bg_selected',
        },
        'dropdown': {
            'text_color': 'text',
            'background_color': 'bg_menu',
            'border_color': 'border',
            'focus_background_color': 'bg_selected',
            'focus_border_color': 'text_selected',
            'pressed_background_color': 'bg_selected',
            'pressed_border_color': 'text_selected',
        },
        'label': {
            'text_color': 'text',
            'background_color': 'bg_panel',
            'border_color': 'border',
        },
        'scrollview': {
            'text_color': 'text',
            'background_color': 'bg_panel',
            'border_color': 'border',
            'focus_background_color': 'bg_menu',
            'focus_border_color': 'text',
            'pressed_background_color': 'border',
        },
        'icon_button': {
            'text_color': 'text',
            'background_color': 'bg_primary',
            'border_color': 'border',
            'focus_background_color': 'bg_selected',
            'focus_border_color': 'text_selected',
        },
        'toggle_button': {
            'background_color': 'bg_primary',
            'border_color': 'border',
            'focus_background_color': 'bg_selected',
        },
        'send_button': {
            'text_color': 'text',
            'background_color': 'bg_selected',
            'border_color': 'bg_selected',
            'focus_background_color': 'bg_selected',
            'focus_border_color': 'text_selected',
            'pressed_background_color': 'bg_primary',
            'pressed_border_color': 'text_muted',
        },
        'title': {
            'text_color': 'text',
            'background_color': 'bg_primary',
            'border_color': 'border',
            'focus_background_color': 'bg_selected',
            'focus_border_color': 'text_selected',
        },
        'default': {
            'background_color': 'bg_panel',
            'border_color': 'border',
        },
    }


    STATE_THEMES = {
        'normal': {
            'background_color': 'bg_panel',
            'text_color': 'text',
            'muted_text_color': 'text_muted',
            'surface_color': 'bg_menu',
            'highlight_color': 'bg_selected',
            'accent_color': 'text_selected',
            'border_color': 'border',
        },
        'hover': {
            'background_color': 'bg_panel',
            'text_color': 'text',
            'surface_color': 'bg_menu',
            'highlight_color': 'bg_panel',
            'accent_color': 'bg_primary',
            'border_color': 'border',
        },
        'active': {
            'background_color': 'bg_panel',
            'text_color': 'text',
            'muted_text_color': 'text_muted',
            'surface_color': 'bg_primary',
            'highlight_color': 'bg_menu',
            'accent_color': 'bg_selected',
            'border_color': 'border',
        },
        'focused': {
            'background_color': 'bg_panel',
            'text_color': 'text',
            'surface_color': 'bg_primary',
            'highlight_color': 'bg_selected',
            'accent_color': 'text',
            'accent_text_color': 'text_selected',
            'border_color': 'border',
        },
        'disabled': {
            'background_color': 'bg_panel',
            'text_color': 'text',
            'muted_text_color': 'text_muted',
            'highlight_color': 'bg_selected',
            'accent_color': 'text_selected',
            'border_color': 'border',
        },
    }

    def get_component_style(self, component_type: str, style_property: str) -> Tuple[float, float, float, float]:

        theme_config = self.COMPONENT_THEMES.get(component_type, {})
        token = theme_config.get(style_property)

        if token:
            return get_theme_color(token)

        return (0.0, 0.0, 0.0, 0.0)

    def get_state_style(self, state_name: str, style_property: str) -> Tuple[float, float, float, float]:

        theme_config = self.STATE_THEMES.get(state_name, {})
        token = theme_config.get(style_property)

        if token:
            return get_theme_color(token)

        return get_theme_color('text')

    def apply_theme_to_component(self, component: Any, component_type: str) -> bool:

        try:

            theme_config = self.COMPONENT_THEMES.get(component_type, {})

            for style_property, token in theme_config.items():
                if token and hasattr(component, style_property):
                    color = get_theme_color(token)
                    setattr(component, style_property, color)
                    logger.debug(f"Applied {style_property} = {color} to {component_type}")

            if hasattr(component, 'invalidate'):
                try:
                    component.invalidate()
                except AttributeError as e:

                    logger.debug(f"Skipping invalidate for {component_type} during initialization: {e}")
                except Exception as e:
                    logger.warning(f"Error calling invalidate on {component_type}: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to apply theme to {component_type}: {e}")
            return False

    def get_themed_style(self, component_type: str) -> Style:

        style = Style()

        try:

            theme_config = self.COMPONENT_THEMES.get(component_type, {})

            for style_property, token in theme_config.items():
                if token and hasattr(style, style_property):
                    color = get_theme_color(token)
                    setattr(style, style_property, color)

            style.font_size = UnifiedStyles.get_font_size()
            style.padding = UnifiedStyles.get_container_padding()
            style.border_width = UnifiedStyles.get_thin_border()

            return style

        except Exception as e:
            logger.error(f"Failed to create themed style for {component_type}: {e}")
            return style


component_themer = ComponentThemer()


def get_component_color(component_type: str, style_property: str) -> Tuple[float, float, float, float]:
    return component_themer.get_component_style(component_type, style_property)


def get_state_color(state_name: str, style_property: str) -> Tuple[float, float, float, float]:
    return component_themer.get_state_style(state_name, style_property)


def apply_theme_to_component(component: Any, component_type: str) -> bool:
    return component_themer.apply_theme_to_component(component, component_type)


def get_themed_component_style(component_type: str) -> Style:
    return component_themer.get_themed_style(component_type)
