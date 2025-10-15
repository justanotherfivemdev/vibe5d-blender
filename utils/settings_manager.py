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

                context.scene.vibe4d_model = model

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

            current_model = getattr(context.scene, 'vibe4d_model', 'gpt-5-mini')

            settings_data = {
            :current_model,
            : current_model,
            :current_model,
            : "agent"
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

            context.scene.vibe4d_model = "gpt-5-mini"

            logger.info("Global settings cleared and reset to defaults")
            return True

        except Exception as e:
            logger.error(f"Failed to clear settings: {str(e)}")
            return False


settings_manager = SettingsManager()
