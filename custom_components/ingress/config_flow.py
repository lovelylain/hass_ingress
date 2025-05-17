from homeassistant import config_entries
from homeassistant.const import CONF_MODE, CONF_URL
from typing import Any
import voluptuous as vol

from .const import DOMAIN, ConfMode


CONNECT_TIMEOUT = 10
DEFAULT_URL = "ha-ingress:8080"
DEFAULT_TITLE = "Ingress"


class IngressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Ingress config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._data = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self._data[CONF_MODE] = user_input[CONF_MODE]
            if self._data[CONF_MODE] == ConfMode.AGENT:
                return await self.async_step_my_agent()
            return await self.async_step_my_setup()

        conf_mode = self._data.get(CONF_MODE, ConfMode.AGENT)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_MODE, default=conf_mode): vol.In(list(ConfMode))}
            ),
        )

    async def async_step_my_agent(self, user_input: dict[str, Any] | None = None):
        errors = {}
        url = self._data.get(CONF_URL, DEFAULT_URL)
        if user_input is not None:
            import asyncio
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            from .client import create_client
            from .client.exceptions import ClientException, InvalidAuth

            try:
                # connect to validate the url
                if not (url := user_input[CONF_URL].strip().rstrip("/")):
                    raise ClientException
                if "://" not in url:
                    url = f"http://{url}"
                client = create_client(None, url, async_get_clientsession(self.hass))
                try:
                    async with asyncio.timeout(CONNECT_TIMEOUT):
                        await client.connect()
                finally:
                    client.disconnect()
                # url is valid
                self._data[CONF_URL] = url
                return await self.async_step_my_setup()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ClientException as err:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="my_agent",
            data_schema=vol.Schema({vol.Required(CONF_URL, default=url): str}),
            errors=errors,
        )

    async def async_step_my_setup(self):
        if entries := self._async_current_entries():
            entry = entries[0]
            self.hass.config_entries.async_update_entry(entry, data=self._data)
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reconfigure_successful")
        return self.async_create_entry(title=DEFAULT_TITLE, data=self._data)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle a reconfiguration flow initialized by the user."""
        self._data.update(self._get_reconfigure_entry().data)
        return await self.async_step_user()

    async def async_step_import(self, user_input: dict[str, Any] | None = None):
        self._data[CONF_MODE] = ConfMode.YAML
        return await self.async_step_my_setup()
