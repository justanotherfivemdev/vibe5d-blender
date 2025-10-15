import errno
import selectors
import socket
from typing import Union

from ._exceptions import (
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)
from ._ssl_compat import SSLError, SSLWantReadError, SSLWantWriteError
from ._utils import extract_error_code, extract_err_message

DEFAULT_SOCKET_OPTION = [(socket.SOL_TCP, socket.TCP_NODELAY, 1)]
if hasattr(socket, "SO_KEEPALIVE"):
    DEFAULT_SOCKET_OPTION.append((socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1))
if hasattr(socket, "TCP_KEEPIDLE"):
    DEFAULT_SOCKET_OPTION.append((socket.SOL_TCP, socket.TCP_KEEPIDLE, 30))
if hasattr(socket, "TCP_KEEPINTVL"):
    DEFAULT_SOCKET_OPTION.append((socket.SOL_TCP, socket.TCP_KEEPINTVL, 10))
if hasattr(socket, "TCP_KEEPCNT"):
    DEFAULT_SOCKET_OPTION.append((socket.SOL_TCP, socket.TCP_KEEPCNT, 3))

_default_timeout = None

__all__ = [
    ,
,
,
,
,
,
,
]

class sock_opt:
    def __init__(self, sockopt: list, sslopt: dict) -> None:
        if sockopt is None:
            sockopt = []
        if sslopt is None:
            sslopt = {}
        self.sockopt = sockopt
        self.sslopt = sslopt
        self.timeout = None


def setdefaulttimeout(timeout: Union[int, float, None]) -> None:
    global _default_timeout
    _default_timeout = timeout


def getdefaulttimeout() -> Union[int, float, None]:
    return _default_timeout


def recv(sock: socket.socket, bufsize: int) -> bytes:
    if not sock:
        raise WebSocketConnectionClosedException("socket is already closed.")

    def _recv():
        try:
            return sock.recv(bufsize)
        except SSLWantReadError:
            pass
        except socket.error as exc:
            error_code = extract_error_code(exc)
            if error_code not in [errno.EAGAIN, errno.EWOULDBLOCK]:
                raise

        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_READ)

        r = sel.select(sock.gettimeout())
        sel.close()

        if r:
            return sock.recv(bufsize)

    try:
        if sock.gettimeout() == 0:
            bytes_ = sock.recv(bufsize)
        else:
            bytes_ = _recv()
    except TimeoutError:
        raise WebSocketTimeoutException("Connection timed out")
    except socket.timeout as e:
        message = extract_err_message(e)
        raise WebSocketTimeoutException(message)
    except SSLError as e:
        message = extract_err_message(e)
        if isinstance(message, str) and "timed out" in message:
            raise WebSocketTimeoutException(message)
        else:
            raise

    if not bytes_:
        raise WebSocketConnectionClosedException("Connection to remote host was lost.")

    return bytes_


def recv_line(sock: socket.socket) -> bytes:
    line = []
    while True:
        c = recv(sock, 1)
        line.append(c)
        if c == b"\n":
            break
    return b"".join(line)


def send(sock: socket.socket, data: Union[bytes, str]) -> int:
    if isinstance(data, str):
        data = data.encode("utf-8")

    if not sock:
        raise WebSocketConnectionClosedException("socket is already closed.")

    def _send():
        try:
            return sock.send(data)
        except SSLWantWriteError:
            pass
        except socket.error as exc:
            error_code = extract_error_code(exc)
            if error_code is None:
                raise
            if error_code not in [errno.EAGAIN, errno.EWOULDBLOCK]:
                raise

        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_WRITE)

        w = sel.select(sock.gettimeout())
        sel.close()

        if w:
            return sock.send(data)

    try:
        if sock.gettimeout() == 0:
            return sock.send(data)
        else:
            return _send()
    except socket.timeout as e:
        message = extract_err_message(e)
        raise WebSocketTimeoutException(message)
    except Exception as e:
        message = extract_err_message(e)
        if isinstance(message, str) and "timed out" in message:
            raise WebSocketTimeoutException(message)
        else:
            raise
