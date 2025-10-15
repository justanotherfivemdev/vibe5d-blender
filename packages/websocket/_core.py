import socket
import struct
import threading
import time
from typing import Optional, Union

from ._abnf import ABNF, STATUS_NORMAL, continuous_frame, frame_buffer
from ._exceptions import WebSocketProtocolException, WebSocketConnectionClosedException
from ._handshake import SUPPORTED_REDIRECT_STATUSES, handshake
from ._http import connect, proxy_info
from ._logging import debug, error, trace, isEnabledForError, isEnabledForTrace
from ._socket import getdefaulttimeout, recv, send, sock_opt
from ._ssl_compat import ssl
from ._utils import NoLock

__all__ = ["WebSocket", "create_connection"]


class WebSocket:

    def __init__(
            self,
            get_mask_key=None,
            sockopt=None,
            sslopt=None,
            fire_cont_frame: bool = False,
            enable_multithread: bool = True,
            skip_utf8_validation: bool = False,
            **_,
    ):

        self.sock_opt = sock_opt(sockopt, sslopt)
        self.handshake_response = None
        self.sock: Optional[socket.socket] = None

        self.connected = False
        self.get_mask_key = get_mask_key

        self.frame_buffer = frame_buffer(self._recv, skip_utf8_validation)
        self.cont_frame = continuous_frame(fire_cont_frame, skip_utf8_validation)

        if enable_multithread:
            self.lock = threading.Lock()
            self.readlock = threading.Lock()
        else:
            self.lock = NoLock()
            self.readlock = NoLock()

    def __iter__(self):

        while True:
            yield self.recv()

    def __next__(self):
        return self.recv()

    def next(self):
        return self.__next__()

    def fileno(self):
        return self.sock.fileno()

    def set_mask_key(self, func):

        self.get_mask_key = func

    def gettimeout(self) -> Union[float, int, None]:

        return self.sock_opt.timeout

    def settimeout(self, timeout: Union[float, int, None]):

        self.sock_opt.timeout = timeout
        if self.sock:
            self.sock.settimeout(timeout)

    timeout = property(gettimeout, settimeout)

    def getsubprotocol(self):

        if self.handshake_response:
            return self.handshake_response.subprotocol
        else:
            return None

    subprotocol = property(getsubprotocol)

    def getstatus(self):

        if self.handshake_response:
            return self.handshake_response.status
        else:
            return None

    status = property(getstatus)

    def getheaders(self):

        if self.handshake_response:
            return self.handshake_response.headers
        else:
            return None

    def is_ssl(self):
        try:
            return isinstance(self.sock, ssl.SSLSocket)
        except:
            return False

    headers = property(getheaders)

    def connect(self, url, **options):

        self.sock_opt.timeout = options.get("timeout", self.sock_opt.timeout)
        self.sock, addrs = connect(
            url, self.sock_opt, proxy_info(**options), options.pop("socket", None)
        )

        try:
            self.handshake_response = handshake(self.sock, url, *addrs, **options)
            for _ in range(options.pop("redirect_limit", 3)):
                if self.handshake_response.status in SUPPORTED_REDIRECT_STATUSES:
                    url = self.handshake_response.headers["location"]
                    self.sock.close()
                    self.sock, addrs = connect(
                        url,
                        self.sock_opt,
                        proxy_info(**options),
                        options.pop("socket", None),
                    )
                    self.handshake_response = handshake(
                        self.sock, url, *addrs, **options
                    )
            self.connected = True
        except:
            if self.sock:
                self.sock.close()
                self.sock = None
            raise

    def send(self, payload: Union[bytes, str], opcode: int = ABNF.OPCODE_TEXT) -> int:

        frame = ABNF.create_frame(payload, opcode)
        return self.send_frame(frame)

    def send_text(self, text_data: str) -> int:

        return self.send(text_data, ABNF.OPCODE_TEXT)

    def send_bytes(self, data: Union[bytes, bytearray]) -> int:

        return self.send(data, ABNF.OPCODE_BINARY)

    def send_frame(self, frame) -> int:

        if self.get_mask_key:
            frame.get_mask_key = self.get_mask_key
        data = frame.format()
        length = len(data)
        if isEnabledForTrace():
            trace(f"++Sent raw: {repr(data)}")
            trace(f"++Sent decoded: {frame.__str__()}")
        with self.lock:
            while data:
                l = self._send(data)
                data = data[l:]

        return length

    def send_binary(self, payload: bytes) -> int:

        return self.send(payload, ABNF.OPCODE_BINARY)

    def ping(self, payload: Union[str, bytes] = ""):

        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self.send(payload, ABNF.OPCODE_PING)

    def pong(self, payload: Union[str, bytes] = ""):

        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self.send(payload, ABNF.OPCODE_PONG)

    def recv(self) -> Union[str, bytes]:

        with self.readlock:
            opcode, data = self.recv_data()
        if opcode == ABNF.OPCODE_TEXT:
            data_received: Union[bytes, str] = data
            if isinstance(data_received, bytes):
                return data_received.decode("utf-8")
            elif isinstance(data_received, str):
                return data_received
        elif opcode == ABNF.OPCODE_BINARY:
            data_binary: bytes = data
            return data_binary
        else:
            return ""

    def recv_data(self, control_frame: bool = False) -> tuple:

        opcode, frame = self.recv_data_frame(control_frame)
        return opcode, frame.data

    def recv_data_frame(self, control_frame: bool = False) -> tuple:

        while True:
            frame = self.recv_frame()
            if isEnabledForTrace():
                trace(f"++Rcv raw: {repr(frame.format())}")
                trace(f"++Rcv decoded: {frame.__str__()}")
            if not frame:

                raise WebSocketProtocolException(f"Not a valid frame {frame}")
            elif frame.opcode in (
                    ABNF.OPCODE_TEXT,
                    ABNF.OPCODE_BINARY,
                    ABNF.OPCODE_CONT,
            ):
                self.cont_frame.validate(frame)
                self.cont_frame.add(frame)

                if self.cont_frame.is_fire(frame):
                    return self.cont_frame.extract(frame)

            elif frame.opcode == ABNF.OPCODE_CLOSE:
                self.send_close()
                return frame.opcode, frame
            elif frame.opcode == ABNF.OPCODE_PING:
                if len(frame.data) < 126:
                    self.pong(frame.data)
                else:
                    raise WebSocketProtocolException("Ping message is too long")
                if control_frame:
                    return frame.opcode, frame
            elif frame.opcode == ABNF.OPCODE_PONG:
                if control_frame:
                    return frame.opcode, frame

    def recv_frame(self):

        return self.frame_buffer.recv_frame()

    def send_close(self, status: int = STATUS_NORMAL, reason: bytes = b""):

        if status < 0 or status >= ABNF.LENGTH_16:
            raise ValueError("code is invalid range")
        self.connected = False
        self.send(struct.pack("!H", status) + reason, ABNF.OPCODE_CLOSE)

    def close(self, status: int = STATUS_NORMAL, reason: bytes = b"", timeout: int = 3):

        if not self.connected:
            return
        if status < 0 or status >= ABNF.LENGTH_16:
            raise ValueError("code is invalid range")

        try:
            self.connected = False
            self.send(struct.pack("!H", status) + reason, ABNF.OPCODE_CLOSE)
            sock_timeout = self.sock.gettimeout()
            self.sock.settimeout(timeout)
            start_time = time.time()
            while timeout is None or time.time() - start_time < timeout:
                try:
                    frame = self.recv_frame()
                    if frame.opcode != ABNF.OPCODE_CLOSE:
                        continue
                    if isEnabledForError():
                        recv_status = struct.unpack("!H", frame.data[0:2])[0]
                        if recv_status >= 3000 and recv_status <= 4999:
                            debug(f"close status: {repr(recv_status)}")
                        elif recv_status != STATUS_NORMAL:
                            error(f"close status: {repr(recv_status)}")
                    break
                except:
                    break
            self.sock.settimeout(sock_timeout)
            self.sock.shutdown(socket.SHUT_RDWR)
        except:
            pass

        self.shutdown()

    def abort(self):

        if self.connected:
            self.sock.shutdown(socket.SHUT_RDWR)

    def shutdown(self):

        if self.sock:
            self.sock.close()
            self.sock = None
            self.connected = False

    def _send(self, data: Union[str, bytes]):
        return send(self.sock, data)

    def _recv(self, bufsize):
        try:
            return recv(self.sock, bufsize)
        except WebSocketConnectionClosedException:
            if self.sock:
                self.sock.close()
            self.sock = None
            self.connected = False
            raise


def create_connection(url: str, timeout=None, class_=WebSocket, **options):
    sockopt = options.pop("sockopt", [])
    sslopt = options.pop("sslopt", {})
    fire_cont_frame = options.pop("fire_cont_frame", False)
    enable_multithread = options.pop("enable_multithread", True)
    skip_utf8_validation = options.pop("skip_utf8_validation", False)
    websock = class_(
        sockopt=sockopt,
        sslopt=sslopt,
        fire_cont_frame=fire_cont_frame,
        enable_multithread=enable_multithread,
        skip_utf8_validation=skip_utf8_validation,
        **options,
    )
    websock.settimeout(timeout if timeout is not None else getdefaulttimeout())
    websock.connect(url, **options)
    return websock
