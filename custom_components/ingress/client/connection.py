import aiohttp
from aiohttp import WSMsgType
from typing import cast

from .exceptions import CannotConnect, ConnectionLost, InvalidMessage
from .helpers import LOGGER


class WebsocketConnection:
    """Websocket connection to server."""

    def __init__(self, server_url: str, websession: aiohttp.ClientSession):
        self._server_url = server_url
        self._websession = websession
        self._client: aiohttp.ClientWebSocketResponse | None = None

    @property
    def connected(self) -> bool:
        """Return if we're currently connected."""
        return self._client is not None and not self._client.closed

    async def connect(self) -> bool:
        """Connect to the websocket server."""
        if self.connected:
            return False

        LOGGER.debug("Trying to connect")
        try:
            self._client = await self._websession.ws_connect(
                self._server_url, heartbeat=55, compress=15, max_msg_size=0
            )
        except (aiohttp.WSServerHandshakeError, aiohttp.ClientError) as err:
            raise CannotConnect(err) from err
        return True

    async def disconnect(self) -> bool:
        """Disconnect the client."""
        LOGGER.debug("Closing client connection")
        if self._client is None:
            return False
        await self._client.close()
        self._client = None
        return True

    async def receive_message(self) -> str | bytes:
        """Receive the next message from the server (or raise on error)."""
        assert self._client
        ws_msg = await self._client.receive()

        if ws_msg.type == WSMsgType.TEXT:
            return cast(str, ws_msg.data)
        elif ws_msg.type == WSMsgType.BINARY:
            return cast(bytes, ws_msg.data)
        elif ws_msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            raise ConnectionLost
        elif ws_msg.type == WSMsgType.ERROR:
            raise ConnectionLost(ws_msg.data)
        else:
            raise InvalidMessage(f"Received unknown type message: {ws_msg.type}")

    async def send_message(self, msg: str | bytes, binary: bool = False) -> None:
        """Send a message to the server."""
        if not self.connected:
            raise ConnectionLost
        assert self._client

        await self._client.send_frame(
            msg.encode() if isinstance(msg, str) else msg,
            WSMsgType.BINARY if binary else WSMsgType.TEXT,
        )
