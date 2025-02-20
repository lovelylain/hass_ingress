import asyncio
from typing import Any, TYPE_CHECKING, cast

from .connection import WebsocketConnection
from .exceptions import (
    InvalidMessage,
    InvalidAuth,
    ConnectionLost,
    ClientException,
    ResultException,
)
from .helpers import LOGGER, json_loads, json_dumps, to_dict

if TYPE_CHECKING:
    from collections.abc import Callable, Awaitable, AsyncGenerator

    from .auth import IngressAuth

    type ClientEventListener = Callable[["IngressClient", Any], Awaitable[None] | None]
    type CommandHandler = Callable[["IngressClient", dict[str, Any]], Awaitable[None] | None]
    type EventSubscriber = tuple[CommandHandler, tuple[str] | None, tuple[str] | None]


MSG_TYPE_AUTH = "auth"
MSG_TYPE_AUTH_OK = "auth_ok"
MSG_TYPE_AUTH_INVALID = "auth_invalid"
MSG_TYPE_RESULT = "result"
MSG_TYPE_EVENT = "event"


class IngressClient:
    """Manage an Ingress server remotely."""

    def __init__(self, auth: "IngressAuth"):
        self._auth = auth
        self._conn = WebsocketConnection(auth.ws_url, auth.websession)
        self._event_listeners: dict[str, list[ClientEventListener]] = {}
        self._command_handlers: dict[str, CommandHandler] = {}
        self._subscribers: list[EventSubscriber] = []
        self._result_futures: dict[int | None, asyncio.Future[Any]] = {}
        self._receive_task: asyncio.Task | None = None

    def on_client_event(
        self, event_type: str, callback: "ClientEventListener"
    ) -> "Callable[[], None]":
        listeners = self._event_listeners.setdefault(event_type, [])
        listeners.append(callback)
        return lambda: listeners.remove(callback)

    async def _fire_event(self, event_type: str, event_data: Any = None) -> None:
        for callback in self._event_listeners.get(event_type, []):
            if asyncio.iscoroutinefunction(callback):
                await callback(self, event_data)
            else:
                callback(self, event_data)

    def register_command(self, msg_type: str, handler: "CommandHandler") -> None:
        """Register a websocket command."""
        self._command_handlers[msg_type] = handler

    async def _handle_command(self, callback: "CommandHandler", msg: dict[str, Any]) -> None:
        if asyncio.iscoroutinefunction(callback):
            await callback(self, msg)
        else:
            callback(self, msg)

    def subscribe(
        self,
        cb_func: "CommandHandler",
        ev_type: str | tuple[str] | None = None,
        ev_id: str | tuple[str] | None = None,
    ) -> "Callable[[], None]":
        """Add callback to event listeners. Returns function to remove the listener."""
        subscriber: EventSubscriber = (
            cb_func,
            ((ev_type,) if isinstance(ev_type, str) else ev_type),
            ((ev_id,) if isinstance(ev_id, str) else ev_id),
        )
        self._subscribers.append(subscriber)
        return lambda: self._subscribers.remove(subscriber)

    async def _handle_event(self, msg: dict[str, Any]) -> None:
        ev_type, ev_id = msg.get("ev_type"), msg.get("ev_id")
        for cb_func, ev_types, ev_ids in self._subscribers:
            if ev_types is not None and ev_type not in ev_types:
                continue
            if ev_ids is not None and ev_id not in ev_ids:
                continue
            await self._handle_command(cb_func, msg)

    async def receive_message(self) -> "AsyncGenerator[dict[str, Any]]":
        """Receive the next message from the server."""
        try:
            msg = json_loads(await self._conn.receive_message())
        except (TypeError, ValueError) as err:
            raise InvalidMessage(f"Received invalid json: {err}") from err

        for msg in msg if isinstance(msg, list) else [msg]:
            if not isinstance(msg, dict) or not msg.get("type"):
                LOGGER.warning("Received invalid msg: %s", msg)
                continue
            LOGGER.debug("Received message: %s", msg)
            yield cast(dict[str, Any], msg)

    async def send_message(self, obj: Any) -> None:
        """Send a message to the server."""
        msg = json_dumps(obj)
        LOGGER.debug("Publishing message: %s", msg)
        await self._conn.send_message(msg)

    async def _connect(self) -> bool:
        """Connect to the server."""
        if not (await self._conn.connect()):
            return False
        server_info = None

        try:
            await self.send_message({"type": MSG_TYPE_AUTH, "token": self._auth.access_token})
            while not self._stop_called:
                async for msg in self.receive_message():
                    msg_type = msg["type"]
                    if msg_type == MSG_TYPE_AUTH_OK:
                        server_info = msg
                        break
                    elif msg_type == MSG_TYPE_AUTH_INVALID:
                        raise InvalidAuth
        finally:
            if server_info is None:
                await self._conn.disconnect()

        await self._fire_event("ready")
        self._msg_id = 0
        return True

    async def reconnect(self) -> None:
        await self._fire_event("disconnected")
        for future in self._result_futures.values():
            future.set_exception(ConnectionLost)
        self._result_futures.clear()

        while not self._stop_called:
            await self._conn.disconnect()
            try:
                await self._connect()
            except InvalidAuth as err:
                await self._fire_event("reconnect-error", err)
                raise
            except ClientException:
                await asyncio.sleep(5)

    async def connect(self) -> bool:
        async def receive_task():
            try:
                while not self._stop_called:
                    try:
                        async for msg in self.receive_message():
                            await self._handle_message(msg)
                    except InvalidMessage as err:
                        LOGGER.warning(err)
                    except ConnectionLost:
                        await self.reconnect()
            finally:
                await self._conn.disconnect()
                self._receive_task = None

        if self._receive_task is not None:
            return False
        self._stop_called = False
        await self._connect()
        self._loop = asyncio.get_running_loop()
        self._receive_task = self._loop.create_task(receive_task())
        return True

    def disconnect(self):
        """Disconnect the client."""
        self._stop_called = True
        for future in self._result_futures.values():
            future.cancel()
        self._result_futures.clear()

    async def send_command(
        self, cmd: Any, wait: bool = True, return_exceptions: bool = False
    ) -> Any | list[Any] | None:
        is_list = isinstance(cmd, (list, tuple))
        msgs = [to_dict(i) for i in cmd] if is_list else [to_dict(cmd)]
        futures: list[asyncio.Future[Any]] = []
        for msg in msgs:
            if msg.get("type") in (MSG_TYPE_RESULT, MSG_TYPE_EVENT):
                continue
            self._msg_id += 1
            msg["id"] = self._msg_id
            if wait:
                futures.append(self._loop.create_future())
                self._result_futures[msg["id"]] = futures[-1]

        await self.send_message(msgs[0] if len(msgs) == 1 else msgs)
        if wait:
            result = await asyncio.gather(*futures, return_exceptions=return_exceptions)
            return result if is_list else result[0]

    async def _handle_message(self, msg: dict[str, Any]):
        msg_type = msg["type"]
        if msg_type == MSG_TYPE_RESULT:
            future = self._result_futures.pop(msg.get("id"), None)
            if future is None:
                pass
            elif not msg.get("fail"):
                future.set_result(msg.get("result"))
            else:
                err = msg.get("error", {})
                future.set_exception(ResultException(err.get("code"), err.get("msg")))
        elif msg_type == MSG_TYPE_EVENT:
            await self._handle_event(msg)
        elif handler := self._command_handlers.get(msg_type):
            await self._handle_command(handler, msg)
