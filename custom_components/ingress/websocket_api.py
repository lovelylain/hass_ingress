"""WebSocket API for token generation and refresh."""

from homeassistant.components.websocket_api.const import (
    ERR_INVALID_FORMAT,
    ERR_UNAUTHORIZED,
    ERR_UNKNOWN_ERROR,
)
from typing import TYPE_CHECKING
import voluptuous as vol

from .config import IngressStore
from .const import DOMAIN, LOGGER as _LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.components.websocket_api.connection import ActiveConnection
    from typing import Any, Final


WS_API_PREFIX: "Final" = "ha-ingress"


def handle_generate_token(
    hass: "HomeAssistant", connection: "ActiveConnection", msg: dict[str, "Any"]
):
    """Handle generate token command."""
    try:
        # Get user_id from the authenticated WebSocket connection context
        user = connection.user
        if not user:
            connection.send_error(msg["id"], ERR_UNAUTHORIZED, "User not authenticated")
            return

        username = None
        for credential in user.credentials:
            if credential.auth_provider_type == "homeassistant":
                username = credential.data.get("username")
                break

        config: IngressStore = hass.data[DOMAIN]["config"]
        token = config.generate_user_token({"id": user.id, "name": user.name, "username": username})

        connection.send_result(msg["id"], {"session": token})
    except Exception as err:
        _LOGGER.error("Error generating token: %s", err)
        connection.send_error(msg["id"], ERR_UNKNOWN_ERROR, str(err))


def handle_refresh_token(
    hass: "HomeAssistant", connection: "ActiveConnection", msg: dict[str, "Any"]
):
    """Handle refresh token command."""
    try:
        token = msg.get("session")
        if not token:
            connection.send_error(msg["id"], ERR_INVALID_FORMAT, "Missing token")
            return

        config: IngressStore = hass.data[DOMAIN]["config"]
        user_info = config.check_user_token(token)
        if not user_info:
            raise ValueError("Invalid or expired token")

        connection.send_result(msg["id"], {"user_id": user_info["id"]})
    except Exception as err:
        _LOGGER.debug("Error refreshing token: %s", err)
        connection.send_error(msg["id"], ERR_UNKNOWN_ERROR, str(err))


async def async_register_websocket_api(hass: "HomeAssistant"):
    """Register WebSocket API."""
    from homeassistant.components.websocket_api import async_register_command
    from homeassistant.components.websocket_api.decorators import websocket_command

    define = websocket_command(
        {
            vol.Required("type"): "ha-ingress/session",
        }
    )
    async_register_command(hass, define(handle_generate_token))

    define = websocket_command(
        {
            vol.Required("type"): "ha-ingress/validate_session",
            vol.Required("session"): str,
        }
    )
    async_register_command(hass, define(handle_refresh_token))
