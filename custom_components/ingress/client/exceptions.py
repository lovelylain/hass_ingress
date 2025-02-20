"""Client-specific exceptions."""


class ClientException(Exception):
    """Generic exception."""

    def __init__(self, error: str | Exception | None = None):
        if error is not None:
            super().__init__(error if isinstance(error, str) else str(error))


class CannotConnect(ClientException):
    """Exception raised when failed to connect the client."""


class InvalidAuth(ClientException):
    """Exception raised when authenticate failed."""


class ConnectionLost(ClientException):
    """Exception raised when the connection is lost."""


class InvalidMessage(ClientException):
    """Exception raised when an invalid message is received."""


class ResultException(Exception):
    """Result exception."""

    def __init__(self, code: str, msg: str) -> None:
        self.code = code
        self.msg = msg
