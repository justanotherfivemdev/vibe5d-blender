class WebSocketException(Exception):
    pass


class WebSocketProtocolException(WebSocketException):
    pass


class WebSocketPayloadException(WebSocketException):
    pass


class WebSocketConnectionClosedException(WebSocketException):
    pass


class WebSocketTimeoutException(WebSocketException):
    pass


class WebSocketProxyException(WebSocketException):
    pass


class WebSocketBadStatusException(WebSocketException):

    def __init__(
            self,
            message: str,
            status_code: int,
            status_message=None,
            resp_headers=None,
            resp_body=None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.resp_headers = resp_headers
        self.resp_body = resp_body


class WebSocketAddressException(WebSocketException):
    pass
