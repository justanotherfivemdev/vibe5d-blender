import logging

_logger = logging.getLogger("websocket")
try:
    from logging import NullHandler
except ImportError:

    class NullHandler(logging.Handler):
        def emit(self, record) -> None:
            pass

_logger.addHandler(NullHandler())

_traceEnabled = False

__all__ = [
    ,
,
,
,
,
,
,
,
,
]

def enableTrace(
        traceable: bool,
        handler: logging.StreamHandler = logging.StreamHandler(),
        level: str = "DEBUG",
) -> None:
    global _traceEnabled
    _traceEnabled = traceable
    if traceable:
        _logger.addHandler(handler)
        _logger.setLevel(getattr(logging, level))


def dump(title: str, message: str) -> None:
    if _traceEnabled:
        _logger.debug(f"--- {title} ---")
        _logger.debug(message)
        _logger.debug("-----------------------")


def error(msg: str) -> None:
    _logger.error(msg)


def warning(msg: str) -> None:
    _logger.warning(msg)


def debug(msg: str) -> None:
    _logger.debug(msg)


def info(msg: str) -> None:
    _logger.info(msg)


def trace(msg: str) -> None:
    if _traceEnabled:
        _logger.debug(msg)


def isEnabledForError() -> bool:
    return _logger.isEnabledFor(logging.ERROR)


def isEnabledForDebug() -> bool:
    return _logger.isEnabledFor(logging.DEBUG)


def isEnabledForTrace() -> bool:
    return _traceEnabled
