import threading
import time

import bpy

from ..utils.logger import logger
from ..utils.storage import secure_storage


class InstructionManager:

    def __init__(self):
        self.is_initialized = False
        self._save_lock = threading.Lock()
        self._last_save_time = 0.0
        self._save_debounce_delay = 0.5
        self._pending_save_timer = None

    def initialize_instruction(self, context) -> bool:

        if self.is_initialized:
            return True

        try:

            saved_instruction = secure_storage.load_custom_instruction()

            if saved_instruction is None:
                self.is_initialized = True
                return True

            context.scene.vibe4d_custom_instruction = str(saved_instruction)

            self.is_initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize custom instruction: {str(e)}")
            self.is_initialized = True
            return False

    def save_instruction(self, context) -> bool:

        try:
            instruction = getattr(context.scene, 'vibe4d_custom_instruction', '')

            success = secure_storage.save_custom_instruction(instruction)

            if success:
                logger.debug(f"Successfully saved custom instruction ({len(instruction)} characters)")
            else:
                logger.error("Failed to save custom instruction")

            return success

        except Exception as e:
            logger.error(f"Failed to save custom instruction: {str(e)}")
            return False

    def clear_instruction(self, context) -> bool:

        try:

            context.scene.vibe4d_custom_instruction = ""

            secure_storage.clear_custom_instruction()

            logger.info("Custom instruction cleared")
            return True

        except Exception as e:
            logger.error(f"Failed to clear custom instruction: {str(e)}")
            return False

    def _debounced_save(self, context):

        try:
            with self._save_lock:
                current_time = time.time()

                if self._pending_save_timer:
                    self._pending_save_timer.cancel()
                    self._pending_save_timer = None

                if current_time - self._last_save_time >= self._save_debounce_delay:
                    self._execute_save(context)
                else:

                    delay = self._save_debounce_delay - (current_time - self._last_save_time)
                    self._pending_save_timer = threading.Timer(delay, self._execute_save, [context])
                    self._pending_save_timer.start()
                    logger.debug(f"Scheduled debounced save in {delay:.2f} seconds")

        except Exception as e:
            logger.error(f"Debounced save failed: {str(e)}")

    def _execute_save(self, context):
        max_retries = 3
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                with self._save_lock:
                    success = self.save_instruction(context)

                    if success:
                        self._last_save_time = time.time()
                        logger.debug(f"Auto-save successful on attempt {attempt + 1}")
                        return
                    else:
                        logger.warning(f"Auto-save attempt {attempt + 1} failed")

            except Exception as e:
                logger.warning(f"Auto-save attempt {attempt + 1} failed with exception: {str(e)}")

            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))

        logger.error(f"Auto-save failed after {max_retries} attempts")

    def auto_save_instruction(self, context):
        try:
            save_thread = threading.Thread(
                target=self._debounced_save,
                args=(context,),
                daemon=True
            )
            save_thread.start()

        except Exception as e:
            logger.error(f"Auto-save initialization failed: {str(e)}")

    def force_save_instruction(self, context) -> bool:
        try:
            with self._save_lock:

                if self._pending_save_timer:
                    self._pending_save_timer.cancel()
                    self._pending_save_timer = None

                success = self.save_instruction(context)

                if success:
                    self._last_save_time = time.time()
                else:
                    logger.error("Force save failed")

                return success

        except Exception as e:
            logger.error(f"Force save failed: {str(e)}")
            return False

    def force_reload_instruction(self, context) -> bool:
        try:
            saved_instruction = secure_storage.load_custom_instruction()

            if saved_instruction is None:
                context.scene.vibe4d_custom_instruction = ""
                return True

            context.scene.vibe4d_custom_instruction = str(saved_instruction)

            return True

        except Exception as e:
            logger.error(f"Failed to force reload custom instruction: {str(e)}")
            return False


instruction_manager = InstructionManager()
