import logging
import sys


class AddonLogger:

    def __init__(self, name: str = "Vibe5D"):
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):

        if self.logger.handlers:
            return

        self.logger.setLevel(logging.DEBUG)

        self.logger.propagate = False

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter(

        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def _truncate_message(self, message: str, max_length: int = 4096) -> str:

        if len(message) <= max_length:
            return message

        truncated = message[:max_length]
        return f"{truncated}... [truncated, original length: {len(message)} chars]"

    def debug(self, message: str):

        truncated_message = self._truncate_message(message)
        self.logger.debug(truncated_message)

    def info(self, message: str):

        truncated_message = self._truncate_message(message)
        self.logger.info(truncated_message)

    def warning(self, message: str):

        truncated_message = self._truncate_message(message)
        self.logger.warning(truncated_message)

    def error(self, message: str):

        truncated_message = self._truncate_message(message)
        self.logger.error(truncated_message)

    def critical(self, message: str):

        truncated_message = self._truncate_message(message)
        self.logger.critical(truncated_message)


logger = AddonLogger()


def setup_vibe5d_logging():
    vibe5d_logger = logging.getLogger('vibe5d')

    vibe5d_logger.propagate = False

    if not vibe5d_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('[Vibe5D] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        vibe5d_logger.addHandler(handler)
        vibe5d_logger.setLevel(logging.DEBUG)


setup_vibe5d_logging()
