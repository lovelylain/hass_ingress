import asyncio
from typing import Any, Generic, TypeVar, TYPE_CHECKING, cast

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

    type ClientEventListener[T] = Callable[[T, "IngressClient", Any], Awaitable[None] | None]
    type BinaryHandler[T] = Callable[[T, "IngressClient", bytes], Awaitable[None] | None]
    type EventHandler[T] = Callable[[T, "IngressClient", dict[str, Any]], Awaitable[None] | None]
    type EventSubscriber[T] = tuple[EventHandler[T], tuple[str] | None, tuple[str] | None]


MSG_TYPE_AUTH = "auth"
MSG_TYPE_AUTH_OK = "auth_ok"
MSG_TYPE_AUTH_INVALID = "auth_invalid"
MSG_TYPE_RESULT = "result"
MSG_TYPE_EVENT = "event"

T = TypeVar("T")


class IngressClient(Generic[T]):
    """Manage an Ingress server remotely."""

    def __init__(self, ctx: T, auth: "IngressAuth"):
        self._ctx = ctx
        self.auth = auth
        self._conn = WebsocketConnection(auth.ws_url, auth.websession)
        self._event_listeners: dict[str, list[ClientEventListener[T]]] = {}
        self._binary_handlers: dict[int, BinaryHandler[T]] = {}
        self._subscribers: list[EventSubscriber[T]] = []
        self._result_futures: dict[int | None, asyncio.Future[Any]] = {}
        self._receive_task: asyncio.Task | None = None

    def on_client_event(
        self, event_type: str, callback: "ClientEventListener[T]"
    ) -> "Callable[[], None]":
        listeners = self._event_listeners.setdefault(event_type, [])
        listeners.append(callback)
        return lambda: listeners.remove(callback)

    def _fire_event(self, event_type: str, event_data: Any = None) -> None:
        async def fire_event():
            for callback in self._event_listeners.get(event_type, []):
                if asyncio.iscoroutinefunction(callback):
                    await callback(self._ctx, self, event_data)
                else:
                    callback(self._ctx, self, event_data)

        self._loop.create_task(fire_event())

    def register_binary(self, id: int, handler: "BinaryHandler[T]"):
        if handler:
            self._binary_handlers[id] = handler
        else:
            self._binary_handlers.pop(id, None)

    def subscribe(
        self,
        cb_func: "EventHandler[T]",
        ev_type: str | tuple[str] | None = None,
        ev_id: str | tuple[str] | None = None,
    ) -> "Callable[[], None]":
        """Add callback to event listeners. Returns function to remove the listener."""
        subscriber: EventSubscriber[T] = (
            cb_func,
            ((ev_type,) if isinstance(ev_type, str) else ev_type),
            ((ev_id,) if isinstance(ev_id, str) else ev_id),
        )
        self._subscribers.append(subscriber)
        return lambda: self._subscribers.remove(subscriber)

    def _handle_event(self, msg: dict[str, Any]) -> None:
        async def handle_event():
            ev_type, ev_id = msg.get("ev_type"), msg.get("ev_id")
            for cb_func, ev_types, ev_ids in self._subscribers:
                if ev_types is not None and ev_type not in ev_types:
                    continue
                if ev_ids is not None and ev_id not in ev_ids:
                    continue
                if asyncio.iscoroutinefunction(cb_func):
                    await cb_func(self._ctx, self, msg)
                else:
                    cb_func(self._ctx, self, msg)

        self._loop.create_task(handle_event())

    async def receive_message(self) -> "AsyncGenerator[dict[str, Any]]":
        """Receive the next message from the server."""
        try:
            while True:
                if not (data := await self._conn.receive_message()):
                    continue
                if not isinstance(data, bytes):
                    break
                if not (handler := self._binary_handlers.get(data[0])):
                    if data[0] in b"[{":
                        break
                    raise InvalidMessage(f"Received invalid binary: {data[0]}")
                handler(self._ctx, self, data[1:])
            msg = json_loads(data)
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
            await self.send_message({"type": MSG_TYPE_AUTH, "token": self.auth.access_token})
            while not self._stop_called and server_info is None:
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

        self._binary_handlers.clear()
        self._msg_id = 0
        return True

    async def reconnect(self) -> None:
        for future in self._result_futures.values():
            future.set_exception(ConnectionLost)
        self._result_futures.clear()
        self._fire_event("disconnected")

        while not self._stop_called:
            await self._conn.disconnect()
            try:
                await self._connect()
                self._fire_event("ready")
                break
            except InvalidAuth as err:
                raise
            except ClientException:
                await asyncio.sleep(5)

    async def connect(self) -> bool:
        async def receive_task():
            client_event = None
            try:
                while not self._stop_called:
                    try:
                        async for msg in self.receive_message():
                            await self._handle_message(msg)
                    except InvalidMessage as err:
                        LOGGER.warning(err)
                    except ConnectionLost:
                        await self.reconnect()
            except InvalidAuth as err:
                client_event = ("reconnect-error", err)
            finally:
                await self._conn.disconnect()
                self._receive_task = None
                if client_event:
                    self._fire_event(*client_event)

        if self._receive_task is not None:
            return False
        self._stop_called = False
        await self._connect()
        self._loop = asyncio.get_running_loop()
        self._receive_task = self._loop.create_task(receive_task())
        self._fire_event("ready")
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
            self._handle_event(msg)
