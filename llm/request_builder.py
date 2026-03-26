import sys
from typing import Dict, Any, Optional, List, Tuple

import bpy

from ..utils.logger import logger


class LLMRequestBuilder:
    DEFAULT_MODEL = "gpt-4o-mini"
    SOFTWARE_NAME = "blender"
    DEFAULT_HISTORY_MESSAGE_LIMIT = 10

    # Context size limits to prevent freezing with large scenes.
    # These are character counts (not tokens). With ~4 chars/token average,
    # 120K chars ≈ 30K tokens which fits within most model context windows.
    # Local models with smaller contexts will naturally truncate via max_tokens.
    MAX_SCHEMA_SUMMARY_CHARS = 50000
    MAX_MESSAGE_CONTENT_CHARS = 30000
    MAX_TOTAL_CONTEXT_CHARS = 120000

    FALLBACK_ADDON_INFO = {
        "name": "Vibe5D",
        "version": "0.4.0",
        "author": "Vibe5D Community",
        "description": "Open-source AI-powered Blender addon",
        "category": "Development"
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
                    module.bl_info.get('name') == 'Vibe5D'):
                logger.debug(f"Found addon module via name search: {module_name}")
                return module
        return None

    @staticmethod
    def _find_addon_module_by_pattern() -> Optional[Any]:
        for module_name, module in sys.modules.items():
            if ('vibe5d' in module_name.lower() and
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
            "name": bl_info.get('name', 'Unknown Addon'),
            "version": version_str,
            "author": bl_info.get('author', 'Unknown'),
            "description": bl_info.get('description', ''),
            "category": bl_info.get('category', 'Unknown')
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
        model = getattr(context.scene, 'vibe5d_model', LLMRequestBuilder.DEFAULT_MODEL)
        instruction = getattr(context.scene, 'vibe5d_custom_instruction', '')
        return model, instruction

    @staticmethod
    def _truncate_content(content: str, max_chars: int, label: str = "content") -> str:
        """Truncate content to max_chars with a warning if truncated."""
        if len(content) <= max_chars:
            return content
        logger.warning(f"Truncating {label} from {len(content)} to {max_chars} chars to prevent freezing")
        return content[:max_chars] + f"\n\n[{label} truncated due to size limit]"

    @staticmethod
    def build_openai_chat_request(
            context,
            prompt: str,
            api_key: str = "",
            base_url: str = "",
            model: Optional[str] = None,
            include_history: bool = True,
            image_data_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a request formatted for the OpenAI-compatible client."""
        selected_model, instruction = LLMRequestBuilder._get_model_and_instruction(context)
        selected_model = model or selected_model

        instructions = LLMRequestBuilder._to_instruction_array(instruction)

        messages = []
        if include_history:
            recent_messages = LLMRequestBuilder._get_chat_messages_from_history(
                context,
                limit=LLMRequestBuilder.DEFAULT_HISTORY_MESSAGE_LIMIT
            )
            messages.extend(recent_messages)

        if image_data_uri:
            user_content = [
                {"type": "text", "text": prompt.strip()},
                {"type": "image_url", "image_url": {"url": image_data_uri, "detail": "auto"}},
            ]
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": prompt.strip()})

        # Truncate individual message contents (skip multimodal content arrays)
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                continue
            if len(content) > LLMRequestBuilder.MAX_MESSAGE_CONTENT_CHARS:
                msg["content"] = LLMRequestBuilder._truncate_content(
                    content, LLMRequestBuilder.MAX_MESSAGE_CONTENT_CHARS, "message"
                )

        schema_summary = LLMRequestBuilder._get_schema_summary(context)

        if len(schema_summary) > LLMRequestBuilder.MAX_SCHEMA_SUMMARY_CHARS:
            schema_summary = LLMRequestBuilder._truncate_content(
                schema_summary, LLMRequestBuilder.MAX_SCHEMA_SUMMARY_CHARS, "schema summary"
            )

        # Get provider settings from scene properties
        if not base_url:
            base_url = getattr(context.scene, 'vibe5d_provider_base_url', '')
        if not api_key:
            api_key = getattr(context.scene, 'vibe5d_provider_api_key', '')

        request = {
            "api_key": api_key,
            "base_url": base_url,
            "model": selected_model,
            "messages": messages,
            "instructions": instructions,
            "schema_summary": schema_summary,
            "tools": LLMRequestBuilder._get_tool_definitions(),
        }

        logger.debug(
            f"Built OpenAI chat request with {len(messages)} messages, "
            f"model={selected_model}, base_url={base_url}"
        )
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

    @staticmethod
    def _get_tool_definitions() -> List[Dict[str, Any]]:
        """Return OpenAI-format tool definitions for the Blender assistant.

        These are passed in the request so that models which support tool
        calling know they can execute code, query the scene, and inspect
        the current context.
        """
        try:
            from ..api.openai_client import OpenAIClient
            return list(OpenAIClient.TOOL_DEFINITIONS)
        except Exception:
            return []
