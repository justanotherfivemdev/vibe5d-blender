import logging
from typing import Tuple, Any

from .blender_theme_integration import get_theme_color
from .style_types import Style
from .unified_styles import UnifiedStyles

logger = logging.getLogger(__name__)


class ComponentThemer:
    COMPONENT_THEMES = {
    :{
    : 'text',
    :None,
    : None,
    },
    :{
    : 'text',
    :'bg_primary',
    : 'border',
    :'bg_selected',
    : 'text_selected',
    :'bg_primary',
    : 'text',
    },
    :{
    : 'text',
    :'bg_panel',
    : 'border',
    :'bg_panel',
    : 'bg_selected',
    :'text',
    : 'text_muted',
    },
    :{
    : 'text',
    :'bg_panel',
    : 'border',
    :'bg_panel',
    : 'bg_selected',
    :'text',
    : 'text_muted',
    },
    :{
    : 'bg_panel',
    :'border',
    },
    :{
    : 'bg_panel',
    :'border',
    : 'border',
    :'bg_selected',
    },
    :{
    : 'text',
    :'bg_menu',
    : 'border',
    :'bg_selected',
    : 'text_selected',
    :'bg_selected',
    : 'text_selected',
    },
    :{
    : 'text',
    :'bg_panel',
    : 'border',
    },
    :{
    : 'text',
    :'bg_panel',
    : 'border',
    :'bg_menu',
    : 'text',
    :'border',
    },
    :{
    : 'text',
    :'bg_primary',
    : 'border',
    :'bg_selected',
    : 'text_selected',
    },
    :{
    : 'bg_primary',
    :'border',
    : 'bg_selected',
    },
    :{
    : 'text',
    :'bg_selected',
    : 'bg_selected',
    :'bg_selected',
    : 'text_selected',
    :'bg_primary',
    : 'text_muted',
    },
    :{
    : 'text',
    :'bg_primary',
    : 'border',
    :'bg_selected',
    : 'text_selected',
    },
    :{
    : 'bg_panel',
    :'border',
    },
    }


    STATE_THEMES = {
    :{
    : 'bg_panel',
    :'text',
    : 'text_muted',
    :'bg_menu',
    : 'bg_selected',
    :'text_selected',
    : 'border',
    },
    :{
    : 'bg_panel',
    :'text',
    : 'bg_menu',
    :'bg_panel',
    : 'bg_primary',
    :'border',
    },
    :{
    : 'bg_panel',
    :'text',
    : 'text_muted',
    :'bg_primary',
    : 'bg_menu',
    :'bg_selected',
    : 'border',
    },
    :{
    : 'bg_panel',
    :'text',
    : 'bg_primary',
    :'bg_selected',
    : 'text',
    :'text_selected',
    : 'border',
    },
    :{
    : 'bg_panel',
    :'text',
    : 'text_muted',
    :'bg_selected',
    : 'text_selected',
    :'border',
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
