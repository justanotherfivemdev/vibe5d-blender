import selectors
import socket
import threading
import time
from typing import Any, Callable, Optional, Union

from . import _logging
from ._abnf import ABNF
from ._core import WebSocket, getdefaulttimeout
from ._exceptions import (
    WebSocketConnectionClosedException,
    WebSocketException,
    WebSocketTimeoutException,
)
from ._ssl_compat import SSLEOFError
from ._url import parse_url

__all__ = ["WebSocketApp"]

RECONNECT = 0


def setReconnect(reconnectInterval: int) -> None:
    global RECONNECT
    RECONNECT = reconnectInterval


class DispatcherBase:

    def __init__(self, app: Any, ping_timeout: Union[float, int, None]) -> None:
        self.app = app
        self.ping_timeout = ping_timeout

    def timeout(self, seconds: Union[float, int, None], callback: Callable) -> None:
        time.sleep(seconds)
        callback()

    def reconnect(self, seconds: int, reconnector: Callable) -> None:
        try:
            _logging.info(

            )
            time.sleep(seconds)
            reconnector(reconnecting=True)
        except KeyboardInterrupt as e:
            _logging.info(f"User exited {e}")
            raise e


class Dispatcher(DispatcherBase):

    def read(
            self,
            sock: socket.socket,
            read_callback: Callable,
            check_callback: Callable,
    ) -> None:
        sel = selectors.DefaultSelector()
        sel.register(self.app.sock.sock, selectors.EVENT_READ)
        try:
            while self.app.keep_running:
                if sel.select(self.ping_timeout):
                    if not read_callback():
                        break
                check_callback()
        finally:
            sel.close()


class SSLDispatcher(DispatcherBase):

    def read(
            self,
            sock: socket.socket,
            read_callback: Callable,
            check_callback: Callable,
    ) -> None:
        sock = self.app.sock.sock
        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_READ)
        try:
            while self.app.keep_running:
                if self.select(sock, sel):
                    if not read_callback():
                        break
                check_callback()
        finally:
            sel.close()

    def select(self, sock, sel: selectors.DefaultSelector):
        sock = self.app.sock.sock
        if sock.pending():
            return [
                sock,
            ]

        r = sel.select(self.ping_timeout)

        if len(r) > 0:
            return r[0][0]


class WrappedDispatcher:

    def __init__(self, app, ping_timeout: Union[float, int, None], dispatcher) -> None:
        self.app = app
        self.ping_timeout = ping_timeout
        self.dispatcher = dispatcher
        dispatcher.signal(2, dispatcher.abort)

    def read(
            self,
            sock: socket.socket,
            read_callback: Callable,
            check_callback: Callable,
    ) -> None:
        self.dispatcher.read(sock, read_callback)
        self.ping_timeout and self.timeout(self.ping_timeout, check_callback)

    def timeout(self, seconds: float, callback: Callable) -> None:
        self.dispatcher.timeout(seconds, callback)

    def reconnect(self, seconds: int, reconnector: Callable) -> None:
        self.timeout(seconds, reconnector)


class WebSocketApp:

    def __init__(
            self,
            url: str,
            header: Union[list, dict, Callable, None] = None,
            on_open: Optional[Callable[[WebSocket], None]] = None,
            on_reconnect: Optional[Callable[[WebSocket], None]] = None,
            on_message: Optional[Callable[[WebSocket, Any], None]] = None,
            on_error: Optional[Callable[[WebSocket, Any], None]] = None,
            on_close: Optional[Callable[[WebSocket, Any, Any], None]] = None,
            on_ping: Optional[Callable] = None,
            on_pong: Optional[Callable] = None,
            on_cont_message: Optional[Callable] = None,
            keep_running: bool = True,
            get_mask_key: Optional[Callable] = None,
            cookie: Optional[str] = None,
            subprotocols: Optional[list] = None,
            on_data: Optional[Callable] = None,
            socket: Optional[socket.socket] = None,
    ) -> None:

        self.url = url
        self.header = header if header is not None else []
        self.cookie = cookie

        self.on_open = on_open
        self.on_reconnect = on_reconnect
        self.on_message = on_message
        self.on_data = on_data
        self.on_error = on_error
        self.on_close = on_close
        self.on_ping = on_ping
        self.on_pong = on_pong
        self.on_cont_message = on_cont_message
        self.keep_running = False
        self.get_mask_key = get_mask_key
        self.sock: Optional[WebSocket] = None
        self.last_ping_tm = float(0)
        self.last_pong_tm = float(0)
        self.ping_thread: Optional[threading.Thread] = None
        self.stop_ping: Optional[threading.Event] = None
        self.ping_interval = float(0)
        self.ping_timeout: Union[float, int, None] = None
        self.ping_payload = ""
        self.subprotocols = subprotocols
        self.prepared_socket = socket
        self.has_errored = False
        self.has_done_teardown = False
        self.has_done_teardown_lock = threading.Lock()

    def send(self, data: Union[bytes, str], opcode: int = ABNF.OPCODE_TEXT) -> None:

        if not self.sock or self.sock.send(data, opcode) == 0:
            raise WebSocketConnectionClosedException("Connection is already closed.")

    def send_text(self, text_data: str) -> None:

        if not self.sock or self.sock.send(text_data, ABNF.OPCODE_TEXT) == 0:
            raise WebSocketConnectionClosedException("Connection is already closed.")

    def send_bytes(self, data: Union[bytes, bytearray]) -> None:

        if not self.sock or self.sock.send(data, ABNF.OPCODE_BINARY) == 0:
            raise WebSocketConnectionClosedException("Connection is already closed.")

    def close(self, **kwargs) -> None:

        self.keep_running = False
        if self.sock:
            self.sock.close(**kwargs)
            self.sock = None

    def _start_ping_thread(self) -> None:
        self.last_ping_tm = self.last_pong_tm = float(0)
        self.stop_ping = threading.Event()
        self.ping_thread = threading.Thread(target=self._send_ping)
        self.ping_thread.daemon = True
        self.ping_thread.start()

    def _stop_ping_thread(self) -> None:
        if self.stop_ping:
            self.stop_ping.set()
        if self.ping_thread and self.ping_thread.is_alive():
            self.ping_thread.join(3)
        self.last_ping_tm = self.last_pong_tm = float(0)

    def _send_ping(self) -> None:
        if self.stop_ping.wait(self.ping_interval) or self.keep_running is False:
            return
        while not self.stop_ping.wait(self.ping_interval) and self.keep_running is True:
            if self.sock:
                self.last_ping_tm = time.time()
                try:
                    _logging.debug("Sending ping")
                    self.sock.ping(self.ping_payload)
                except Exception as e:
                    _logging.debug(f"Failed to send ping: {e}")

    def run_forever(
            self,
            sockopt: tuple = None,
            sslopt: dict = None,
            ping_interval: Union[float, int] = 0,
            ping_timeout: Union[float, int, None] = None,
            ping_payload: str = "",
            http_proxy_host: str = None,
            http_proxy_port: Union[int, str] = None,
            http_no_proxy: list = None,
            http_proxy_auth: tuple = None,
            http_proxy_timeout: Optional[float] = None,
            skip_utf8_validation: bool = False,
            host: str = None,
            origin: str = None,
            dispatcher=None,
            suppress_origin: bool = False,
            proxy_type: str = None,
            reconnect: int = None,
    ) -> bool:

        if reconnect is None:
            reconnect = RECONNECT

        if ping_timeout is not None and ping_timeout <= 0:
            raise WebSocketException("Ensure ping_timeout > 0")
        if ping_interval is not None and ping_interval < 0:
            raise WebSocketException("Ensure ping_interval >= 0")
        if ping_timeout and ping_interval and ping_interval <= ping_timeout:
            raise WebSocketException("Ensure ping_interval > ping_timeout")
        if not sockopt:
            sockopt = ()
        if not sslopt:
            sslopt = {}
        if self.sock:
            raise WebSocketException("socket is already opened")

        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.ping_payload = ping_payload
        self.has_done_teardown = False
        self.keep_running = True

        def teardown(close_frame: ABNF = None):

            with self.has_done_teardown_lock:
                if self.has_done_teardown:
                    return
                self.has_done_teardown = True

            self._stop_ping_thread()
            self.keep_running = False
            if self.sock:
                self.sock.close()
            close_status_code, close_reason = self._get_close_args(
                close_frame if close_frame else None
            )
            self.sock = None

            self._callback(self.on_close, close_status_code, close_reason)

        def setSock(reconnecting: bool = False) -> None:
            if reconnecting and self.sock:
                self.sock.shutdown()

            self.sock = WebSocket(
                self.get_mask_key,
                sockopt=sockopt,
                sslopt=sslopt,
                fire_cont_frame=self.on_cont_message is not None,
                skip_utf8_validation=skip_utf8_validation,
                enable_multithread=True,
            )

            self.sock.settimeout(getdefaulttimeout())
            try:
                header = self.header() if callable(self.header) else self.header

                self.sock.connect(
                    self.url,
                    header=header,
                    cookie=self.cookie,
                    http_proxy_host=http_proxy_host,
                    http_proxy_port=http_proxy_port,
                    http_no_proxy=http_no_proxy,
                    http_proxy_auth=http_proxy_auth,
                    http_proxy_timeout=http_proxy_timeout,
                    subprotocols=self.subprotocols,
                    host=host,
                    origin=origin,
                    suppress_origin=suppress_origin,
                    proxy_type=proxy_type,
                    socket=self.prepared_socket,
                )

                _logging.info("Websocket connected")

                if self.ping_interval:
                    self._start_ping_thread()

                if reconnecting and self.on_reconnect:
                    self._callback(self.on_reconnect)
                else:
                    self._callback(self.on_open)

                dispatcher.read(self.sock.sock, read, check)
            except (
                    WebSocketConnectionClosedException,
                    ConnectionRefusedError,
                    KeyboardInterrupt,
                    SystemExit,
                    Exception,
            ) as e:
                handleDisconnect(e, reconnecting)

        def read() -> bool:
            if not self.keep_running:
                return teardown()

            try:
                op_code, frame = self.sock.recv_data_frame(True)
            except (
                    WebSocketConnectionClosedException,
                    KeyboardInterrupt,
                    SSLEOFError,
            ) as e:
                if custom_dispatcher:
                    return handleDisconnect(e, bool(reconnect))
                else:
                    raise e

            if op_code == ABNF.OPCODE_CLOSE:
                return teardown(frame)
            elif op_code == ABNF.OPCODE_PING:
                self._callback(self.on_ping, frame.data)
            elif op_code == ABNF.OPCODE_PONG:
                self.last_pong_tm = time.time()
                self._callback(self.on_pong, frame.data)
            elif op_code == ABNF.OPCODE_CONT and self.on_cont_message:
                self._callback(self.on_data, frame.data, frame.opcode, frame.fin)
                self._callback(self.on_cont_message, frame.data, frame.fin)
            else:
                data = frame.data
                if op_code == ABNF.OPCODE_TEXT and not skip_utf8_validation:
                    data = data.decode("utf-8")
                self._callback(self.on_data, data, frame.opcode, True)
                self._callback(self.on_message, data)

            return True

        def check() -> bool:
            if self.ping_timeout:
                has_timeout_expired = (
                        time.time() - self.last_ping_tm > self.ping_timeout
                )
                has_pong_not_arrived_after_last_ping = (
                        self.last_pong_tm - self.last_ping_tm < 0
                )
                has_pong_arrived_too_late = (
                        self.last_pong_tm - self.last_ping_tm > self.ping_timeout
                )

                if (
                        self.last_ping_tm
                        and has_timeout_expired
                        and (
                        has_pong_not_arrived_after_last_ping
                        or has_pong_arrived_too_late
                )
                ):
                    raise WebSocketTimeoutException("ping/pong timed out")
            return True

        def handleDisconnect(
                e: Union[
                    WebSocketConnectionClosedException,
                    ConnectionRefusedError,
                    KeyboardInterrupt,
                    SystemExit,
                    Exception,
                ],
                reconnecting: bool = False,
        ) -> bool:
            self.has_errored = True
            self._stop_ping_thread()
            if not reconnecting:
                self._callback(self.on_error, e)

            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                teardown()

                raise

            if reconnect:
                _logging.info(f"{e} - reconnect")
                if custom_dispatcher:
                    _logging.debug(

                    )
                    dispatcher.reconnect(reconnect, setSock)
            else:
                _logging.error(f"{e} - goodbye")
                teardown()

        custom_dispatcher = bool(dispatcher)
        dispatcher = self.create_dispatcher(
            ping_timeout, dispatcher, parse_url(self.url)[3]
        )

        try:
            setSock()
            if not custom_dispatcher and reconnect:
                while self.keep_running:
                    _logging.debug(

                    )
                    dispatcher.reconnect(reconnect, setSock)
        except (KeyboardInterrupt, Exception) as e:
            _logging.info(f"tearing down on exception {e}")
            teardown()
        finally:
            if not custom_dispatcher:
                teardown()

        return self.has_errored

    def create_dispatcher(
            self,
            ping_timeout: Union[float, int, None],
            dispatcher: Optional[DispatcherBase] = None,
            is_ssl: bool = False,
    ) -> Union[Dispatcher, SSLDispatcher, WrappedDispatcher]:
        if dispatcher:
            return WrappedDispatcher(self, ping_timeout, dispatcher)
        timeout = ping_timeout or 10
        if is_ssl:
            return SSLDispatcher(self, timeout)
        return Dispatcher(self, timeout)

    def _get_close_args(self, close_frame: ABNF) -> list:

        if not self.on_close or not close_frame:
            return [None, None]

        if close_frame.data and len(close_frame.data) >= 2:
            close_status_code = 256 * int(close_frame.data[0]) + int(
                close_frame.data[1]
            )
            reason = close_frame.data[2:]
            if isinstance(reason, bytes):
                reason = reason.decode("utf-8")
            return [close_status_code, reason]
        else:

            return [None, None]

    def _callback(self, callback, *args) -> None:
        if callback:
            try:
                callback(self, *args)

            except Exception as e:
                _logging.error(f"error from callback {callback}: {e}")
                if self.on_error:
                    self.on_error(self, e)
