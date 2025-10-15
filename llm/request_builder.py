import sys
from typing import Dict, Any, Optional, List, Tuple

import bpy

from ..utils.logger import logger


class LLMRequestBuilder:
    DEFAULT_MODEL = "gpt-5-mini"
    SOFTWARE_NAME = "blender"
    DEFAULT_HISTORY_MESSAGE_LIMIT = 10

    FALLBACK_ADDON_INFO = {
    :"Vibe4D",
    : "1.0.0",
    :"Vibe4D Team",
    : "AI-powered Blender addon",
    :"Development"
    }

    @staticmethod
    def _find_addon_module_by_package() -> Optional[Any]:
        current_package = __name__.split('.')[0]
        addon_module = sys.modules.get(current_package)

        if addon_module and hasattr(addon_module, 'bl_info'):
            logger.debug(f"Found addon module via package name: {current_package}")
            return addon_module
        return None

    @staticmethod
    def _find_addon_module_by_name() -> Optional[Any]:
        for module_name, module in sys.modules.items():
            if (hasattr(module, 'bl_info') and
                    isinstance(module.bl_info, dict) and
                    module.bl_info.get('name') == 'Vibe4D'):
                logger.debug(f"Found addon module via name search: {module_name}")
                return module
        return None

    @staticmethod
    def _find_addon_module_by_pattern() -> Optional[Any]:
        for module_name, module in sys.modules.items():
            if ('vibe4d' in module_name.lower() and
                    hasattr(module, 'bl_info') and
                    isinstance(module.bl_info, dict)):
                logger.debug(f"Found addon module via name pattern: {module_name}")
                return module
        return None

    @staticmethod
    def _extract_addon_info_from_module(addon_module: Any) -> Dict[str, Any]:
        bl_info = addon_module.bl_info
        version_tuple = bl_info.get('version', (0, 0, 0))
        version_str = '.'.join(map(str, version_tuple))

        return {
        :bl_info.get('name', 'Unknown Addon'),
        : version_str,
        :bl_info.get('author', 'Unknown'),
        : bl_info.get('description', ''),
        :bl_info.get('category', 'Unknown')
        }

        @staticmethod
        def _get_addon_info() -> Dict[str, Any]:
            try:
                addon_module = (
                        LLMRequestBuilder._find_addon_module_by_package() or
                        LLMRequestBuilder._find_addon_module_by_name() or
                        LLMRequestBuilder._find_addon_module_by_pattern()
                )

                if addon_module and hasattr(addon_module, 'bl_info'):
                    return LLMRequestBuilder._extract_addon_info_from_module(addon_module)

                logger.warning("Could not find bl_info, using fallback addon information")
                return LLMRequestBuilder.FALLBACK_ADDON_INFO

            except Exception as e:
                logger.error(f"Failed to extract addon info: {str(e)}")
                return LLMRequestBuilder.FALLBACK_ADDON_INFO

        @staticmethod
        def _get_model_and_instruction(context) -> Tuple[str, str]:
            model = getattr(context.scene, 'vibe4d_model', LLMRequestBuilder.DEFAULT_MODEL)
            instruction = getattr(context.scene, 'vibe4d_custom_instruction', '')
            return model, instruction

        @staticmethod
        def build_chat_request(
                context,
                prompt: str,
                user_id: str,
                token: str,
                model: Optional[str] = None,
                include_history: bool = True
        ) -> Dict[str, Any]:
            selected_model, instruction = LLMRequestBuilder._get_model_and_instruction(context)
            selected_model = model or selected_model

            instructions = LLMRequestBuilder._to_instruction_array(instruction)
            addon_info = LLMRequestBuilder._get_addon_info()

            messages = []
            if include_history:
                recent_messages = LLMRequestBuilder._get_chat_messages_from_history(
                    context,
                    limit=LLMRequestBuilder.DEFAULT_HISTORY_MESSAGE_LIMIT
                )
                messages.extend(recent_messages)

            messages.append({
            : "user",
            :prompt.strip()
            })

            schema_summary = LLMRequestBuilder._get_schema_summary(context)

            from ..utils.history_manager import history_manager
            chat_id = history_manager.get_current_chat_id(context)

            request = {
            :user_id,
            : token,
            :chat_id,
            : messages,
            :selected_model,
            : instructions,
            :schema_summary,
            : {
            :LLMRequestBuilder.SOFTWARE_NAME,
            : LLMRequestBuilder._get_blender_version()
            },
            :{
            : addon_info["version"],
            :addon_info["name"]
            }
            }

            logger.debug(
                f"Built chat request with chat_id={chat_id}, {len(messages)} messages and {len(instructions)} instructions")
            return request

        @staticmethod
        def _get_schema_summary(context) -> str:
            try:
                from ..engine.query import scene_query_engine
                return scene_query_engine.get_llm_friendly_schema_summary(context)
            except Exception as e:
                logger.warning(f"Failed to get schema summary: {str(e)}")
                return ""

        @staticmethod
        def _get_chat_messages_from_history(context, limit: int) -> List[Dict[str, Any]]:
            try:
                from ..utils.history_manager import history_manager
                messages = history_manager.get_chat_messages(context)
                return messages[-limit:] if len(messages) > limit else messages
            except Exception as e:
                logger.error(f"Failed to get chat messages from history: {str(e)}")
                return []

        @staticmethod
        def _get_blender_version() -> str:
            try:
                version = bpy.app.version
                return f"{version[0]}.{version[1]}"
            except Exception as e:
                logger.error(f"Failed to get Blender version: {str(e)}")
                return "4.4"

        @staticmethod
        def _to_instruction_array(instruction_text: str) -> List[str]:
            if instruction_text and instruction_text.strip():
                return [instruction_text.strip()]
            return []
