"""Configure Ingress panels with native Home Assistant forms.

Home Assistant 2025.8 and newer let every panel own a config subentry, so each
ingress appears as its own row under *Settings -> Devices & services*. Older
cores have no subentry support, so the same forms are offered through the
integration's options flow and the panels are stored in the entry options.
Both paths share the schema builders and validators below.
"""

from copy import deepcopy
import re
from typing import Any

from homeassistant import config_entries
from homeassistant.components.frontend import DATA_PANELS
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

from . import CONFIG_SCHEMA, _active_panels, const
from .compat import SUPPORTS_SUBENTRIES, async_update_and_abort, object_selector
from .const import (
    DOMAIN,
    ConfMode,
    RewriteMode,
    TLSMode,
    UIMode,
    WorkMode,
)
from .panels import (
    get_panels,
    replace_panels,
    entry_snapshot,
    option_record,
    option_records,
)
from .tls import InvalidTLS, tls_context

CONNECT_TIMEOUT = 10
DEFAULT_URL = "ha-ingress:8080"
DEFAULT_TITLE = "Ingress"
TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")

# Cores without subentries cannot host a ConfigSubentryFlow subclass, so the
# panel flow falls back to a plain object there and is never registered.
_SubentryFlowBase = config_entries.ConfigSubentryFlow if SUPPORTS_SUBENTRIES else object


class InvalidPanel(ValueError):
    """A panel cannot be used safely by the runtime."""


def _select(values, **config):
    return selector.SelectSelector({"options": list(values), "mode": "dropdown", **config})


def _panel_schema(editing=False):
    text = selector.TextSelector()
    headers = object_selector(
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
    rewrite = object_selector(
        {
            "multiple": True,
            "label_field": const.CONF_MATCH,
            "fields": {
                "mode": {
                    "label": "Rewrite mode",
                    "required": True,
                    "selector": _select(RewriteMode).serialize()["selector"],
                },
                "path": {"label": "Request path pattern", "selector": {"text": {}}},
                "name": {"label": "Header or content type pattern", "selector": {"text": {}}},
                const.CONF_MATCH: {
                    "label": "Match pattern",
                    "required": True,
                    "selector": {"text": {}},
                },
                const.CONF_REPLACE: {"label": "Replacement", "selector": {"text": {}}},
            },
        }
    )
    fields = {} if editing else {vol.Required("slug"): text}
    fields.update(
        {
            vol.Required(const.CONF_TITLE): text,
            vol.Required(const.CONF_SHOW_IN_SIDEBAR, default=True): selector.BooleanSelector(),
            vol.Optional("icon"): selector.IconSelector(),
            vol.Required("url"): text,
            vol.Required("require_admin", default=False): selector.BooleanSelector(),
            vol.Optional("advanced"): section(
                vol.Schema(
                    {
                        vol.Optional(const.CONF_WORK_MODE): _select(WorkMode),
                        vol.Optional(const.CONF_UI_MODE): _select(UIMode),
                        vol.Optional(const.CONF_TLS_MODE, default=TLSMode.SYSTEM): _select(
                            TLSMode, translation_key="tls_mode"
                        ),
                        vol.Optional(const.CONF_TLS_CERTIFICATE): selector.TextSelector(
                            {"multiline": True}
                        ),
                        vol.Optional(const.CONF_INDEX): text,
                        vol.Optional(const.CONF_PARENT): text,
                        vol.Optional(const.CONF_COOKIE_NAME): text,
                        vol.Optional(const.CONF_STATIC_TOKEN): selector.TextSelector(
                            {"type": "password"}
                        ),
                        vol.Optional(const.CONF_EXPIRE_TIME): selector.NumberSelector(
                            {"min": 0, "step": 1, "mode": "box", "unit_of_measurement": "seconds"}
                        ),
                        vol.Optional(
                            const.CONF_ENABLE_COMPRESS, default=False
                        ): selector.BooleanSelector(),
                        vol.Optional("url_match"): text,
                        vol.Optional("url_replace"): text,
                        vol.Optional("headers"): headers,
                        vol.Optional(const.CONF_REWRITE): rewrite,
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
    basic = {
        key: panel.pop(key)
        for key in (const.CONF_TITLE, "icon", "url", "require_admin")
        if key in panel
    }
    if isinstance(basic["url"], dict):
        dynamic = basic["url"]
        basic["url"] = dynamic["default"]
        panel.update(url_match=dynamic[const.CONF_MATCH], url_replace=dynamic[const.CONF_REPLACE])
    if "headers" in panel:
        panel["headers"] = [
            {"name": name, "value": value} for name, value in panel["headers"].items()
        ]
    basic["advanced"] = panel
    return basic


def _panel_from_form(user_input):
    """Convert graphical rows to the integration's existing configuration."""
    panel = {
        key: value
        for key, value in user_input.items()
        if key not in ("slug", "advanced", const.CONF_SHOW_IN_SIDEBAR) and value != ""
    }
    panel.update(
        {
            key: value
            for key, value in user_input.get("advanced", {}).items()
            if value not in ("", None)
        }
    )
    if "headers" in panel:
        rows = panel["headers"]
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or set(row) != {"name", "value"}
            or not isinstance(row["name"], str)
            or not isinstance(row["value"], str)
            for row in rows
        ):
            raise InvalidPanel("invalid_headers")
        names = [row["name"].lower() for row in rows]
        if len(set(names)) != len(names):
            raise InvalidPanel("duplicate_headers")
        panel["headers"] = {row["name"]: row["value"] for row in rows}
    if const.CONF_REWRITE in panel:
        rows = panel[const.CONF_REWRITE]
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or not {"mode", const.CONF_MATCH} <= row.keys()
            or row.keys() - {"mode", "path", "name", const.CONF_MATCH, const.CONF_REPLACE}
            or any(not isinstance(value, str) for value in row.values())
            or row["mode"] not in RewriteMode
            for row in rows
        ):
            raise InvalidPanel("invalid_panel")
        panel[const.CONF_REWRITE] = [{const.CONF_REPLACE: "", **row} for row in rows]
    if (
        const.CONF_EXPIRE_TIME in panel
        and int(panel[const.CONF_EXPIRE_TIME]) != panel[const.CONF_EXPIRE_TIME]
    ):
        raise InvalidPanel("invalid_panel")
    match, replace = panel.pop("url_match", ""), panel.pop("url_replace", "")
    if match or replace:
        if not match:
            raise InvalidPanel("invalid_regex")
        panel["url"] = {
            "default": panel.get("url", ""),
            const.CONF_MATCH: match,
            const.CONF_REPLACE: replace,
        }
    if panel.get(const.CONF_TLS_MODE, TLSMode.SYSTEM) != TLSMode.CUSTOM:
        panel.pop(const.CONF_TLS_CERTIFICATE, None)
    return panel


def _validate_url(value, mode):
    if (
        not isinstance(value, str)
        or not value
        or any(char.isspace() or ord(char) < 32 for char in value)
    ):
        raise InvalidPanel("invalid_url")
    if mode == WorkMode.HASSIO:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise InvalidPanel("invalid_url")
        return
    if (
        mode in (WorkMode.IFRAME, WorkMode.CUSTOM)
        and value.startswith("/")
        and not value.startswith("//")
    ):
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
    foreign_routes = set(hass.data.get(DATA_PANELS, {})) - set(
        hass.data.get(DOMAIN, {}).get("panels", set())
    )
    for slug, panel in panels.items():
        mode = panel[const.CONF_WORK_MODE]
        url = panel["url"]
        _validate_url(url["default"] if isinstance(url, dict) else url, mode)
        try:
            tls_context(panel)
        except InvalidTLS as err:
            raise InvalidPanel(err.reason) from err
        if isinstance(url, dict) and not url[const.CONF_MATCH]:
            raise InvalidPanel("invalid_regex")
        headers = panel.get("headers", {})
        if len({key.lower() for key in headers}) != len(headers):
            raise InvalidPanel("duplicate_headers")
        if any(
            not TOKEN.fullmatch(key) or any(char in value for char in "\r\n\0")
            for key, value in headers.items()
        ):
            raise InvalidPanel("invalid_headers")
        for key in (const.CONF_COOKIE_NAME, const.CONF_STATIC_TOKEN):
            if key in panel and not TOKEN.fullmatch(panel[key]):
                raise InvalidPanel("invalid_token")
        if any(char in panel[const.CONF_INDEX] for char in "\r\n\0"):
            raise InvalidPanel("invalid_panel")
        for rule in panel.get(const.CONF_REWRITE, []):
            try:
                for field in ("path", "name"):
                    re.compile(rule.get(field, ""))
                if rule["mode"] == RewriteMode.BODY:
                    re.compile(rule[const.CONF_MATCH].encode()).sub(
                        rule[const.CONF_REPLACE].encode(), b""
                    )
                else:
                    re.compile(rule[const.CONF_MATCH]).sub(rule[const.CONF_REPLACE], "")
            except (re.error, ValueError) as err:
                raise InvalidPanel("invalid_regex") from err
        parent = panel.get(const.CONF_PARENT)
        seen = {slug}
        ancestor = parent
        while ancestor:
            if ancestor not in panels or ancestor in seen:
                raise InvalidPanel("invalid_parent")
            seen.add(ancestor)
            ancestor = panels[ancestor].get(const.CONF_PARENT)
        if mode == WorkMode.SUBAPP and (
            not parent or panels[parent][const.CONF_WORK_MODE] != WorkMode.INGRESS
        ):
            raise InvalidPanel("invalid_parent")
        if parent:
            child = slug.removeprefix(f"{parent}_")
            root = parent
            if grandparent := panels[parent].get(const.CONF_PARENT):
                if mode != WorkMode.SUBAPP or panels[grandparent].get(const.CONF_PARENT):
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


def _checked_panel(hass, panels, slug, user_input):
    """Validate one submitted panel form against the panels it will join."""
    panel = _panel_from_form(user_input)
    if not panel.get(const.CONF_TITLE, "").strip():
        raise InvalidPanel("invalid_panel")
    candidate, unavailable = _active_panels(panels | {slug: panel})
    if slug in unavailable:
        raise InvalidPanel("invalid_parent")
    return _validate_panels(hass, candidate)[slug]


class IngressPanelFlow(_SubentryFlowBase):
    """Configure a panel directly from its integration row (HA 2025.8+)."""

    def __init__(self):
        self._snapshot = None
        self._slug = None

    async def async_step_user(self, user_input=None):
        return await self._async_panel("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        if self._snapshot is None:
            self._slug = self._get_reconfigure_subentry().unique_id
        return await self._async_panel("reconfigure", user_input)

    async def _async_panel(self, step_id, user_input):
        entry = self._get_entry()
        if self._snapshot is None:
            self._snapshot = entry_snapshot(entry)
        elif self._snapshot != entry_snapshot(entry):
            return self.async_abort(reason="configuration_changed")
        if entry.data[const.CONF_MODE] != ConfMode.UI:
            return self.async_abort(
                reason=(
                    "agent_panels"
                    if entry.data[const.CONF_MODE] == ConfMode.AGENT
                    else "yaml_panels"
                )
            )
        panels = get_panels(entry)
        errors = {}
        if user_input is not None:
            slug = self._slug if step_id == "reconfigure" else user_input["slug"]
            if step_id == "user" and slug in panels:
                errors["slug"] = "duplicate_panel"
            else:
                try:
                    panel = _checked_panel(self.hass, panels, slug, user_input)
                except InvalidPanel as err:
                    errors["base"] = str(err)
                else:
                    title = panel.pop(const.CONF_TITLE)
                    panel[const.CONF_SHOW_IN_SIDEBAR] = user_input.get(
                        const.CONF_SHOW_IN_SIDEBAR, True
                    )
                    if step_id == "reconfigure":
                        return self.async_update_and_abort(
                            entry, self._get_reconfigure_subentry(), title=title, data=panel
                        )
                    return self.async_create_entry(title=title, data=panel, unique_id=slug)
        suggested = user_input
        if suggested is None and self._slug is not None:
            subentry = self._get_reconfigure_subentry()
            panel = deepcopy(dict(subentry.data))
            visible = panel.pop(const.CONF_SHOW_IN_SIDEBAR, True)
            suggested = _panel_form(panel | {const.CONF_TITLE: subentry.title}) | {
                const.CONF_SHOW_IN_SIDEBAR: visible
            }
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                _panel_schema(step_id == "reconfigure"), suggested
            ),
            errors=errors,
            description_placeholders={"slug": self._slug or ""},
        )


class IngressOptionsFlow(config_entries.OptionsFlow):
    """Manage panels through the entry options on cores without subentries.

    The forms, validation and stored fields are identical to the subentry flow;
    only the place the panels are kept and the way they are reached differ.
    """

    def __init__(self):
        self._snapshot = None
        self._slug = None

    async def async_step_init(self, user_input=None):
        entry = self.config_entry
        if entry.data[const.CONF_MODE] != ConfMode.UI:
            return self.async_abort(
                reason=(
                    "agent_panels"
                    if entry.data[const.CONF_MODE] == ConfMode.AGENT
                    else "yaml_panels"
                )
            )
        if not get_panels(entry):
            return await self.async_step_add()
        return self.async_show_menu(menu_options=["add", "edit", "delete"])

    async def async_step_add(self, user_input=None):
        return await self._async_panel("add", user_input)

    async def async_step_edit(self, user_input=None):
        if self._slug is None:
            # Picking the panel is its own step: the edit form's description needs
            # the slug, which is only known once a panel has been chosen.
            return self._select_panel("select_edit")
        return await self._async_panel("edit", user_input)

    async def async_step_select_edit(self, user_input=None):
        self._slug = user_input["slug"]
        return await self._async_panel("edit", None)

    async def async_step_delete(self, user_input=None):
        if user_input is not None:
            if (stale := self._stale_form()) is not None:
                return stale
            stored = option_records(self.config_entry)
            stored.pop(user_input["slug"], None)
            return self.async_create_entry(
                title="", data={**dict(self.config_entry.options), const.CONF_PANELS: stored}
            )
        return self._select_panel("delete")

    def _stale_form(self):
        """Reject a form that was filled in before the configuration changed."""
        entry = self.config_entry
        if self._snapshot is None:
            self._snapshot = entry_snapshot(entry)
        elif self._snapshot != entry_snapshot(entry):
            return self.async_abort(reason="configuration_changed")

    def _select_panel(self, step_id):
        if (stale := self._stale_form()) is not None:
            return stale
        panels = get_panels(self.config_entry)
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required("slug"): _select(panels)}),
        )

    async def _async_panel(self, step_id, user_input):
        entry = self.config_entry
        if (stale := self._stale_form()) is not None:
            return stale
        panels = get_panels(entry)
        errors = {}
        if user_input is not None:
            slug = self._slug if step_id == "edit" else user_input["slug"]
            if step_id == "add" and slug in panels:
                errors["slug"] = "duplicate_panel"
            else:
                try:
                    panel = _checked_panel(self.hass, panels, slug, user_input)
                except InvalidPanel as err:
                    errors["base"] = str(err)
                else:
                    title = panel.pop(const.CONF_TITLE)
                    stored = option_records(entry)
                    stored[slug] = option_record(
                        slug, panel, title, user_input.get(const.CONF_SHOW_IN_SIDEBAR, True)
                    )
                    return self.async_create_entry(
                        title="", data={**dict(entry.options), const.CONF_PANELS: stored}
                    )
        suggested = user_input
        if suggested is None and self._slug is not None:
            record = option_records(entry)[self._slug]
            visible = record.get(const.CONF_SHOW_IN_SIDEBAR, True)
            panel = {
                key: value for key, value in record.items() if key != const.CONF_SHOW_IN_SIDEBAR
            }
            suggested = _panel_form(panel) | {const.CONF_SHOW_IN_SIDEBAR: visible}
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(
                _panel_schema(step_id == "edit"), suggested
            ),
            errors=errors,
            description_placeholders={"slug": self._slug or ""},
        )


class IngressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Ingress config flow."""

    VERSION = 2

    def __init__(self) -> None:
        self._data = {}
        self._snapshot = None

    if SUPPORTS_SUBENTRIES:

        @classmethod
        @callback
        def async_get_supported_subentry_types(cls, config_entry):
            return {"panel": IngressPanelFlow}

    else:

        @staticmethod
        @callback
        def async_get_options_flow(config_entry):
            return IngressOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Select local UI, external agent, or YAML configuration."""
        if self.source == config_entries.SOURCE_USER and self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            self._data[const.CONF_MODE] = user_input[const.CONF_MODE]
            if self._data[const.CONF_MODE] == ConfMode.AGENT:
                return await self.async_step_my_agent()
            if self._data[const.CONF_MODE] == ConfMode.UI and self._snapshot is not None:
                entry = self._get_reconfigure_entry()
                if entry.data[const.CONF_MODE] == ConfMode.YAML and not entry.data.get(
                    const.CONF_UI_CONFIGURED
                ):
                    return await self.async_step_import_yaml()
            return await self.async_step_my_setup()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.CONF_MODE, default=self._data.get(const.CONF_MODE, ConfMode.UI)
                    ): _select(ConfMode, translation_key="configuration_mode")
                }
            ),
        )

    async def async_step_my_agent(self, user_input: dict[str, Any] | None = None):
        errors = {}
        url = self._data.get(const.CONF_URL, DEFAULT_URL)
        if user_input is not None:
            import asyncio
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            from .client import create_client
            from .client.exceptions import ClientException, InvalidAuth

            try:
                if not (url := user_input[const.CONF_URL].strip().rstrip("/")):
                    raise ClientException
                if "://" not in url:
                    url = f"http://{url}"
                client = create_client(None, url, async_get_clientsession(self.hass))
                try:
                    async with asyncio.timeout(CONNECT_TIMEOUT):
                        await client.connect()
                finally:
                    client.disconnect()
                self._data[const.CONF_URL] = url
                return await self.async_step_my_setup()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ClientException:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="my_agent",
            data_schema=vol.Schema(
                {vol.Required(const.CONF_URL, default=url): selector.TextSelector()}
            ),
            errors=errors,
        )

    async def async_step_my_setup(self, panels=None):
        if entries := self._async_current_entries():
            entry = entries[0]
            if self._snapshot != entry_snapshot(entry):
                return self.async_abort(reason="configuration_changed")
            if panels is not None:
                replace_panels(self.hass, entry, panels)
            if self._data[const.CONF_MODE] == ConfMode.UI:
                self._data[const.CONF_UI_CONFIGURED] = True
            result = async_update_and_abort(
                self, entry, data=self._data, reason="reconfigure_successful"
            )
            if not entry.update_listeners:
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
            return result
        if self._data[const.CONF_MODE] == ConfMode.UI:
            self._data[const.CONF_UI_CONFIGURED] = True
        return self.async_create_entry(title=DEFAULT_TITLE, data=self._data)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        entry = self._get_reconfigure_entry()
        self._data = deepcopy(dict(entry.data))
        self._snapshot = entry_snapshot(entry)
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
            data_schema=vol.Schema(
                {vol.Required("confirm", default=False): selector.BooleanSelector()}
            ),
            errors=errors,
        )

    async def async_step_import(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        self._data[const.CONF_MODE] = ConfMode.YAML
        return await self.async_step_my_setup()
