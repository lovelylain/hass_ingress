"""Configure Ingress panels with native Home Assistant forms."""

from copy import deepcopy
import re
from typing import Any

from homeassistant import config_entries
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.const import CONF_MODE, CONF_URL
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
from homeassistant.helpers.reload import async_integration_yaml_config
from yarl import URL
import voluptuous as schema_vol

try:
    import probatio as vol
except ImportError:
    import voluptuous as vol

from . import CONFIG_SCHEMA
from .const import CONF_PANELS, DOMAIN, ConfMode, RewriteMode, UIMode, WorkMode

CONNECT_TIMEOUT = 10
DEFAULT_URL = "ha-ingress:8080"
DEFAULT_TITLE = "Ingress"
TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")


class InvalidPanel(ValueError):
    """A panel cannot be used safely by the runtime."""


def _select(values, **config):
    return selector.SelectSelector({"options": list(values), "mode": "dropdown", **config})


def _panel_schema(editing=False):
    text = selector.TextSelector()
    headers = selector.ObjectSelector(
        {
            "multiple": True,
            "label_field": "name",
            "fields": {
                "name": {"label": "Header name", "required": True, "selector": {"text": {}}},
                "value": {
                    "label": "Header value",
                    "required": True,
                    "selector": {"text": {"type": "password"}},
                },
            },
        }
    )
    rewrite = selector.ObjectSelector(
        {
            "multiple": True,
            "label_field": "match",
            "fields": {
                "mode": {
                    "label": "Rewrite mode",
                    "required": True,
                    "selector": _select(RewriteMode).serialize()["selector"],
                },
                "path": {"label": "Request path pattern", "selector": {"text": {}}},
                "name": {"label": "Header or content type pattern", "selector": {"text": {}}},
                "match": {"label": "Match pattern", "required": True, "selector": {"text": {}}},
                "replace": {"label": "Replacement", "selector": {"text": {}}},
            },
        }
    )
    fields = {} if editing else {vol.Required("slug"): text}
    fields.update(
        {
            vol.Optional("title"): text,
            vol.Optional("icon"): selector.IconSelector(),
            vol.Required("url"): text,
            vol.Required("require_admin", default=False): selector.BooleanSelector(),
            vol.Optional("advanced"): section(
                vol.Schema(
                    {
                        vol.Optional("work_mode"): _select(WorkMode),
                        vol.Optional("ui_mode"): _select(UIMode),
                        vol.Optional("index"): text,
                        vol.Optional("parent"): text,
                        vol.Optional("cookie_name"): text,
                        vol.Optional("static_token"): selector.TextSelector({"type": "password"}),
                        vol.Optional("expire_time"): selector.NumberSelector(
                            {"min": 0, "step": 1, "mode": "box", "unit_of_measurement": "seconds"}
                        ),
                        vol.Optional("url_match"): text,
                        vol.Optional("url_replace"): text,
                        vol.Optional("headers"): headers,
                        vol.Optional("rewrite"): rewrite,
                    }
                ),
                {"collapsed": True},
            ),
        }
    )
    return vol.Schema(fields)


def _panel_form(panel):
    """Represent every persisted field in the editable form."""
    panel = deepcopy(panel)
    basic = {key: panel.pop(key) for key in ("title", "icon", "url", "require_admin") if key in panel}
    if isinstance(basic["url"], dict):
        dynamic = basic["url"]
        basic["url"] = dynamic["default"]
        panel.update(url_match=dynamic["match"], url_replace=dynamic["replace"])
    if "headers" in panel:
        panel["headers"] = [{"name": name, "value": value} for name, value in panel["headers"].items()]
    basic["advanced"] = panel
    return basic


def _panel_from_form(user_input):
    """Convert graphical rows to the integration's existing configuration."""
    panel = {key: value for key, value in user_input.items() if key not in ("slug", "advanced") and value != ""}
    panel.update({key: value for key, value in user_input.get("advanced", {}).items() if value not in ("", None)})
    if "headers" in panel:
        rows = panel["headers"]
        if not isinstance(rows, list) or any(
            not isinstance(row, dict) or set(row) != {"name", "value"}
            or not isinstance(row["name"], str) or not isinstance(row["value"], str)
            for row in rows
        ):
            raise InvalidPanel("invalid_headers")
        names = [row["name"].lower() for row in rows]
        if len(set(names)) != len(names):
            raise InvalidPanel("duplicate_headers")
        panel["headers"] = {row["name"]: row["value"] for row in rows}
    if "rewrite" in panel:
        rows = panel["rewrite"]
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or not {"mode", "match"} <= row.keys()
            or row.keys() - {"mode", "path", "name", "match", "replace"}
            or any(not isinstance(value, str) for value in row.values())
            or row["mode"] not in RewriteMode
            for row in rows
        ):
            raise InvalidPanel("invalid_panel")
        panel["rewrite"] = [{"replace": "", **row} for row in rows]
    if "expire_time" in panel and int(panel["expire_time"]) != panel["expire_time"]:
        raise InvalidPanel("invalid_panel")
    match, replace = panel.pop("url_match", ""), panel.pop("url_replace", "")
    if match or replace:
        if not match:
            raise InvalidPanel("invalid_regex")
        panel["url"] = {"default": panel.get("url", ""), "match": match, "replace": replace}
    return panel


def _validate_url(value, mode):
    if not isinstance(value, str) or not value or any(char.isspace() or ord(char) < 32 for char in value):
        raise InvalidPanel("invalid_url")
    if mode == WorkMode.HASSIO:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise InvalidPanel("invalid_url")
        return
    if mode in (WorkMode.IFRAME, WorkMode.CUSTOM) and value.startswith("/") and not value.startswith("//"):
        return
    if mode in (WorkMode.IFRAME, WorkMode.CUSTOM) and "://" not in value:
        raise InvalidPanel("invalid_url")
    try:
        url = URL(value if "://" in value else f"http://{value}")
        if url.scheme not in ("http", "https") or not url.host or url.port is None:
            raise ValueError
    except ValueError as err:
        raise InvalidPanel("invalid_url") from err


def _validate_panels(hass, panels):
    """Use the runtime schema, then check values it cannot safely interpret."""
    try:
        panels = CONFIG_SCHEMA({DOMAIN: deepcopy(panels)})[DOMAIN]
    except (schema_vol.Invalid, vol.Invalid, TypeError, ValueError) as err:
        raise InvalidPanel("invalid_panel") from err
    routes = set()
    foreign_routes = set(hass.data.get(DATA_PANELS, {})) - set(hass.data.get(DOMAIN, {}).get("panels", set()))
    for slug, panel in panels.items():
        mode = panel["work_mode"]
        url = panel["url"]
        _validate_url(url["default"] if isinstance(url, dict) else url, mode)
        if isinstance(url, dict) and not url["match"]:
            raise InvalidPanel("invalid_regex")
        headers = panel.get("headers", {})
        if len({key.lower() for key in headers}) != len(headers):
            raise InvalidPanel("duplicate_headers")
        if any(not TOKEN.fullmatch(key) or any(char in value for char in "\r\n\0") for key, value in headers.items()):
            raise InvalidPanel("invalid_headers")
        for key in ("cookie_name", "static_token"):
            if key in panel and not TOKEN.fullmatch(panel[key]):
                raise InvalidPanel("invalid_token")
        if any(char in panel["index"] for char in "\r\n\0"):
            raise InvalidPanel("invalid_panel")
        for rule in panel.get("rewrite", []):
            try:
                for field in ("path", "name"):
                    re.compile(rule.get(field, ""))
                if rule["mode"] == RewriteMode.BODY:
                    re.compile(rule["match"].encode()).sub(rule["replace"].encode(), b"")
                else:
                    re.compile(rule["match"]).sub(rule["replace"], "")
            except (re.error, ValueError) as err:
                raise InvalidPanel("invalid_regex") from err
        parent = panel.get("parent")
        seen = {slug}
        ancestor = parent
        while ancestor:
            if ancestor not in panels or ancestor in seen:
                raise InvalidPanel("invalid_parent")
            seen.add(ancestor)
            ancestor = panels[ancestor].get("parent")
        if mode == WorkMode.SUBAPP and (not parent or panels[parent]["work_mode"] != WorkMode.INGRESS):
            raise InvalidPanel("invalid_parent")
        if parent:
            child = slug.removeprefix(f"{parent}_")
            root = parent
            if grandparent := panels[parent].get("parent"):
                if mode != WorkMode.SUBAPP or panels[grandparent].get("parent"):
                    raise InvalidPanel("invalid_parent")
                root = grandparent
                child = f"{parent.removeprefix(f'{grandparent}_')}-{child}"
            route = f"{root}/{child}"
        else:
            route = slug
            if route in foreign_routes:
                raise InvalidPanel("route_conflict")
        if route in routes:
            raise InvalidPanel("route_conflict")
        routes.add(route)
    return panels


class IngressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Ingress config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._data = {}
        self._snapshot = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return IngressOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Select local UI, external agent, or YAML configuration."""
        if self.source == config_entries.SOURCE_USER and self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            self._data[CONF_MODE] = user_input[CONF_MODE]
            if self._data[CONF_MODE] == ConfMode.AGENT:
                return await self.async_step_my_agent()
            if self._data[CONF_MODE] == ConfMode.UI and self._snapshot is not None:
                entry = self._get_reconfigure_entry()
                if entry.data[CONF_MODE] == ConfMode.YAML and CONF_PANELS not in entry.options:
                    return await self.async_step_import_yaml()
            return await self.async_step_my_setup()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_MODE, default=self._data.get(CONF_MODE, ConfMode.UI)): _select(ConfMode, translation_key="configuration_mode")}),
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
                self._data[CONF_URL] = url
                return await self.async_step_my_setup()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ClientException:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="my_agent",
            data_schema=vol.Schema({vol.Required(CONF_URL, default=url): selector.TextSelector()}),
            errors=errors,
        )

    async def async_step_my_setup(self, panels=None):
        if entries := self._async_current_entries():
            entry = entries[0]
            if self._snapshot != (dict(entry.data), dict(entry.options)):
                return self.async_abort(reason="configuration_changed")
            options = dict(entry.options)
            if panels is not None:
                options[CONF_PANELS] = panels
            elif self._data[CONF_MODE] == ConfMode.UI:
                options.setdefault(CONF_PANELS, {})
            return self.async_update_reload_and_abort(entry, data=self._data, options=options, reason="reconfigure_successful")
        options = {CONF_PANELS: {}} if self._data[CONF_MODE] == ConfMode.UI else {}
        return self.async_create_entry(title=DEFAULT_TITLE, data=self._data, options=options)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        entry = self._get_reconfigure_entry()
        self._data = deepcopy(dict(entry.data))
        self._snapshot = deepcopy((dict(entry.data), dict(entry.options)))
        return await self.async_step_user(user_input)

    async def async_step_import_yaml(self, user_input=None):
        errors = {}
        if user_input is not None:
            if not user_input["confirm"]:
                return self.async_abort(reason="import_cancelled")
            try:
                config = await async_integration_yaml_config(self.hass, DOMAIN)
                if config is None:
                    raise ValueError("YAML configuration could not be loaded")
            except Exception:
                errors["base"] = "yaml_load_failed"
            else:
                try:
                    panels = _validate_panels(self.hass, config.get(DOMAIN, {}))
                except InvalidPanel as err:
                    errors["base"] = str(err)
                else:
                    return await self.async_step_my_setup(panels)
        return self.async_show_form(
            step_id="import_yaml",
            data_schema=vol.Schema({vol.Required("confirm", default=False): selector.BooleanSelector()}),
            errors=errors,
        )

    async def async_step_import(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        self._data[CONF_MODE] = ConfMode.YAML
        return await self.async_step_my_setup()


class IngressOptionsFlow(config_entries.OptionsFlowWithReload):
    """Add, edit, or remove one panel per options flow."""

    async def async_step_init(self, user_input=None):
        mode = self.config_entry.data[CONF_MODE]
        if mode != ConfMode.UI:
            return self.async_abort(reason="agent_options" if mode == ConfMode.AGENT else "yaml_options")
        self._snapshot = deepcopy((dict(self.config_entry.data), dict(self.config_entry.options)))
        self._options = deepcopy(dict(self.config_entry.options))
        self._panels = self._options.setdefault(CONF_PANELS, {})
        self._slug = None
        return self.async_show_menu(step_id="init", menu_options=["add", "edit", "remove"] if self._panels else ["add"])

    async def async_step_add(self, user_input=None):
        return await self._async_panel("add", user_input)

    async def async_step_edit(self, user_input=None):
        if self._slug is None:
            if user_input is None:
                return self._select_panel("edit")
            self._slug = user_input["panel"]
            user_input = None
        return await self._async_panel("edit", user_input)

    def _select_panel(self, step_id):
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required("panel"): _select([{"value": slug, "label": f"{panel.get('title', slug)} ({slug})"} for slug, panel in self._panels.items()])}),
        )

    async def _async_panel(self, step_id, user_input):
        errors = {}
        if user_input is not None:
            slug = self._slug if step_id == "edit" else user_input["slug"]
            if step_id == "add" and slug in self._panels:
                errors["slug"] = "duplicate_panel"
            else:
                try:
                    panel = _panel_from_form(user_input)
                    panels = _validate_panels(self.hass, self._panels | {slug: panel})
                except InvalidPanel as err:
                    errors["base"] = str(err)
                else:
                    self._panels.clear()
                    self._panels.update(panels)
                    return self._save()
        suggested = user_input
        if suggested is None and self._slug is not None:
            suggested = _panel_form(self._panels[self._slug])
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(_panel_schema(step_id == "edit"), suggested),
            errors=errors,
            description_placeholders={"slug": self._slug or ""},
        )

    async def async_step_remove(self, user_input=None):
        if user_input is None:
            return self._select_panel("remove")
        self._slug = user_input["panel"]
        return await self.async_step_remove_confirm()

    async def async_step_remove_confirm(self, user_input=None):
        errors = {}
        if any(panel.get("parent") == self._slug for panel in self._panels.values()):
            errors["base"] = "parent_has_children"
        elif user_input is not None:
            if not user_input["confirm"]:
                return self.async_abort(reason="remove_cancelled")
            del self._panels[self._slug]
            return self._save()
        return self.async_show_form(
            step_id="remove_confirm",
            data_schema=vol.Schema({vol.Required("confirm", default=False): selector.BooleanSelector()}),
            description_placeholders={"slug": self._slug},
            errors=errors,
        )

    def _save(self):
        if self._snapshot != (dict(self.config_entry.data), dict(self.config_entry.options)):
            return self.async_abort(reason="configuration_changed")
        return self.async_create_entry(title="", data=self._options)
