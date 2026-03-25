import bpy

from .logger import logger
from .storage import secure_storage


class SettingsManager:

    def __init__(self):
        self.is_initialized = False

    def initialize_settings(self, context) -> bool:

        if self.is_initialized:
            return True

        try:

            saved_settings = secure_storage.load_settings()

            if saved_settings:

                model = saved_settings.get("model", "gpt-5-mini")
                context.scene.vibe5d_model = model

                # Load provider settings
                provider = saved_settings.get("provider", "openai")
                if hasattr(context.scene, 'vibe5d_provider'):
                    context.scene.vibe5d_provider = provider

                provider_api_key = saved_settings.get("provider_api_key", "")
                if hasattr(context.scene, 'vibe5d_provider_api_key'):
                    context.scene.vibe5d_provider_api_key = provider_api_key

                provider_base_url = saved_settings.get("provider_base_url", "")
                if hasattr(context.scene, 'vibe5d_provider_base_url'):
                    context.scene.vibe5d_provider_base_url = provider_base_url

                provider_model = saved_settings.get("provider_model", "")
                if hasattr(context.scene, 'vibe5d_provider_model'):
                    context.scene.vibe5d_provider_model = provider_model

            else:
                logger.info("No saved settings found, using defaults")

            self.is_initialized = True
            return True

        except Exception as e:
            logger.error(f"Settings initialization failed: {str(e)}")
            self.is_initialized = True
            return False

    def save_settings(self, context) -> bool:

        try:

            current_model = getattr(context.scene, 'vibe5d_model', 'gpt-5-mini')
            current_provider = getattr(context.scene, 'vibe5d_provider', 'openai')
            current_api_key = getattr(context.scene, 'vibe5d_provider_api_key', '')
            current_base_url = getattr(context.scene, 'vibe5d_provider_base_url', '')
            current_provider_model = getattr(context.scene, 'vibe5d_provider_model', '')

            settings_data = {
                "agent_model": current_model,
                "ask_model": current_model,
                "model": current_model,
                "mode": "agent",
                "provider": current_provider,
                "provider_api_key": current_api_key,
                "provider_base_url": current_base_url,
                "provider_model": current_provider_model
            }

            return secure_storage.save_settings(settings_data)

        except Exception as e:
            logger.error(f"Failed to save settings: {str(e)}")
            return False

    def auto_save_settings(self, context):

        try:

            import threading

            def save_in_background():
                try:
                    self.save_settings(context)
                except Exception as e:
                    logger.debug(f"Background settings save failed: {str(e)}")

            thread = threading.Thread(target=save_in_background)
            thread.daemon = True
            thread.start()

        except Exception as e:
            logger.debug(f"Auto-save settings failed: {str(e)}")

    def clear_settings(self, context) -> bool:

        try:

            secure_storage.clear_settings()

            context.scene.vibe5d_model = "gpt-5-mini"

            if hasattr(context.scene, 'vibe5d_provider'):
                context.scene.vibe5d_provider = 'openai'
            if hasattr(context.scene, 'vibe5d_provider_api_key'):
                context.scene.vibe5d_provider_api_key = ''
            if hasattr(context.scene, 'vibe5d_provider_base_url'):
                context.scene.vibe5d_provider_base_url = ''
            if hasattr(context.scene, 'vibe5d_provider_model'):
                context.scene.vibe5d_provider_model = ''

            logger.info("Global settings cleared and reset to defaults")
            return True

        except Exception as e:
            logger.error(f"Failed to clear settings: {str(e)}")
            return False


settings_manager = SettingsManager()
