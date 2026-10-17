import aiohttp
import asyncio
from copy import deepcopy
from homeassistant.components import frontend, http, panel_custom
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession, async_get_clientsession
import homeassistant.helpers.config_validation as cv
import inspect
import os
import re
import time
from typing import TYPE_CHECKING, cast
import voluptuous as vol
from yarl import URL

from . import const
from .const import (
    DOMAIN,
    LOGGER as _LOGGER,
    API_BASE,
    URL_BASE,
    WorkMode,
    UIMode,
    RewriteMode,
    ConfMode,
    TLSMode,
)
from . import compat
from .config import IngressStore, IngressCfg, RewriteCfg
from .ingress import IngressView, std_header_name
from .panels import (
    get_panels,
    replace_panels,
)
from .tls import tls_context
from .websocket_api import async_register_websocket_api

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.config_entries import ConfigEntry
    from typing import Any, Final, TypedDict
    from .client import IngressClient

    class DomainData(TypedDict):
        client: IngressClient
        config: IngressStore
        panels: set[str]


VERSION = ""
CONNECT_TIMEOUT = 20


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: cv.schema_with_slug_keys(
            vol.Schema(
                {
                    vol.Optional(panel_custom.CONF_REQUIRE_ADMIN, default=False): cv.boolean,
                    vol.Optional(const.CONF_TITLE): cv.string,
                    vol.Optional(const.CONF_ICON): cv.icon,
                    vol.Required(const.CONF_URL): vol.Any(
                        cv.string,
                        vol.Schema(
                            {
                                vol.Required(const.CONF_MATCH): cv.string,
                                vol.Required(const.CONF_REPLACE): cv.string,
                                vol.Required(const.CONF_DEFAULT): cv.string,
                            }
                        ),
                    ),
                    vol.Optional(const.CONF_INDEX, default=""): cv.string,
                    vol.Optional(const.CONF_PARENT): cv.string,
                    vol.Optional(const.CONF_WORK_MODE, default=WorkMode.INGRESS): vol.In(
                        list(WorkMode)
                    ),
                    vol.Optional(const.CONF_UI_MODE, default=UIMode.NORMAL): vol.In(list(UIMode)),
                    vol.Optional(const.CONF_HEADERS): vol.Schema({str: cv.string}),
                    vol.Optional(const.CONF_REWRITE): [
                        vol.Schema(
                            {
                                vol.Required(const.CONF_MODE): vol.In(list(RewriteMode)),
                                vol.Optional(const.CONF_PATH): cv.string,
                                vol.Optional(const.CONF_NAME): cv.string,
                                vol.Required(const.CONF_MATCH): cv.string,
                                vol.Required(const.CONF_REPLACE): cv.string,
                            }
                        )
                    ],
                    vol.Optional(const.CONF_COOKIE_NAME): cv.string,
                    vol.Optional(const.CONF_STATIC_TOKEN): cv.string,
                    vol.Optional(const.CONF_EXPIRE_TIME): cv.positive_int,
                    vol.Optional(const.CONF_ENABLE_COMPRESS): cv.boolean,
                    vol.Optional(const.CONF_TLS_MODE, default=TLSMode.SYSTEM): vol.In(
                        list(TLSMode)
                    ),
                    vol.Optional(const.CONF_TLS_CERTIFICATE): cv.string,
                    vol.Optional(const.CONF_SHOW_IN_SIDEBAR): cv.boolean,
                }
            )
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: "HomeAssistant", config) -> bool:
    # init once
    await _async_init(hass)

    # init config entry
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries and DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(DOMAIN, context={"source": "import"})
        )

    return True


async def async_setup_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> bool:
    data = await _async_init(hass)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    if entry.data[const.CONF_MODE] == ConfMode.UI:
        config = _ui_config(hass, entry)
        await setup_domain(hass, data, config)
        return True
    if entry.data[const.CONF_MODE] == ConfMode.YAML:
        from homeassistant.helpers.reload import async_integration_yaml_config

        config = await async_integration_yaml_config(hass, DOMAIN)
        await setup_domain(hass, data, config or {})
        return True
    if entry.data[const.CONF_MODE] != ConfMode.AGENT:
        return True

    from homeassistant.const import EVENT_HOMEASSISTANT_STOP
    from .client import create_client
    from .client.exceptions import ClientException

    # init client
    client = create_client(hass, entry.data[const.CONF_URL], async_get_clientsession(hass))
    client.on_client_event("ready", on_remote_ready)

    # get config
    config = None
    try:
        async with asyncio.timeout(CONNECT_TIMEOUT):
            await client.connect()
            config = await get_remote_config(hass, client)
    except ClientException as err:
        raise ConfigEntryNotReady("Failed to connect to ingress agent") from err
    except Exception as err:
        _LOGGER.exception("Failed to connect to ingress agent")
        raise ConfigEntryNotReady("Unknown error connecting to the ingress agent") from err
    finally:
        if config is None:
            client.disconnect()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lambda e: client.disconnect())
    )

    # setup config
    data: DomainData = hass.data[DOMAIN]
    data["client"] = client
    await setup_domain(hass, data, config)
    return True


async def async_reload_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _active_panels(panels):
    """Exclude broken parent chains before creating any routes or tokens."""
    unavailable = {}
    for slug, panel in panels.items():
        seen = {slug}
        parent = panel.get(const.CONF_PARENT)
        while parent:
            if parent not in panels or parent in seen:
                unavailable[slug] = parent
                break
            seen.add(parent)
            parent = panels[parent].get(const.CONF_PARENT)
    return {slug: panel for slug, panel in panels.items() if slug not in unavailable}, unavailable


def _ui_config(hass, entry):
    from homeassistant.helpers import issue_registry as ir

    panels, unavailable = _active_panels(get_panels(entry))
    issue_id = f"missing_parent_{entry.entry_id}"
    if unavailable:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="missing_parent",
            translation_placeholders={
                "panels": ", ".join(unavailable),
                "parents": ", ".join(sorted(set(unavailable.values()))),
            },
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
    return CONFIG_SCHEMA({DOMAIN: panels})


async def async_migrate_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> bool:
    if entry.version > 2:
        return False
    if entry.version == 1:
        # Version 1 kept the panels in the entry options, with the sidebar title
        # inside the panel itself. Subentry-aware cores move them into subentries;
        # the others keep them in place, normalised to the same shape.
        had_panels = const.CONF_PANELS in entry.options
        replace_panels(hass, entry, entry.options.get(const.CONF_PANELS, {}))
        options = dict(entry.options)
        if compat.SUPPORTS_SUBENTRIES:
            options.pop(const.CONF_PANELS, None)
        data = dict(entry.data)
        if had_panels or data[const.CONF_MODE] == ConfMode.UI:
            data[const.CONF_UI_CONFIGURED] = True
        hass.config_entries.async_update_entry(entry, version=2, data=data, options=options)
    return True


async def async_remove_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> None:
    from homeassistant.helpers import issue_registry as ir

    ir.async_delete_issue(hass, DOMAIN, f"missing_parent_{entry.entry_id}")


async def on_remote_ready(hass: "HomeAssistant", client: "IngressClient", _: "Any"):
    await client.send_command({"type": "subscribe"})


async def get_remote_config(hass: "HomeAssistant", client: "IngressClient") -> dict[str, "Any"]:
    # TODO
    return {DOMAIN: {}}


async def async_unload_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> bool:
    from homeassistant.helpers import issue_registry as ir

    ir.async_delete_issue(hass, DOMAIN, f"missing_parent_{entry.entry_id}")
    client: IngressClient
    if client := hass.data[DOMAIN].pop("client", None):
        client.disconnect()
    data: DomainData = hass.data[DOMAIN]
    for name in data["panels"]:
        frontend.async_remove_panel(hass, name)
    data["panels"].clear()
    data["config"].clear()
    return True


async def setup_domain(hass: "HomeAssistant", data: "DomainData", config) -> None:
    # Parsing expands placeholders; keep the saved configuration unchanged.
    config, panels = _parse_config(hass, {DOMAIN: deepcopy(config.get(DOMAIN, {}))})

    # clean
    for name in data["panels"]:
        frontend.async_remove_panel(hass, name)
    data["panels"].clear()
    data["config"].clear()

    # add ingress
    now = int(time.time())
    for cfg in config:
        data["config"].add_ingress(cfg, now)

    # add panels
    data["panels"].update(panels)
    await asyncio.gather(*(_async_register_panel(hass, v) for v in panels.values()))


async def _async_init(hass: "HomeAssistant") -> "DomainData":
    """Init DomainData and service once."""
    data: DomainData = hass.data.setdefault(DOMAIN, {})
    if "config" not in cast(dict, data):
        from homeassistant.const import SERVICE_RELOAD
        from homeassistant.helpers.reload import async_integration_yaml_config
        from homeassistant.helpers.service import async_register_admin_service

        # get version
        global VERSION
        VERSION = await get_version(hass, DOMAIN)

        # register static url
        static_dir = os.path.join(os.path.dirname(__file__), "www")
        await _async_register_static_paths(hass.http, [(URL_BASE, static_dir, False)])

        # register ingress view
        config = IngressStore()
        # Backend cookies belong to each browser, never to the shared proxy session.
        websession = async_create_clientsession(hass, cookie_jar=aiohttp.DummyCookieJar())
        hass.http.register_view(IngressView(hass, config, websession))

        # register websocket api
        await async_register_websocket_api(hass)

        # register reload config
        async def reload_config(call: "ServiceCall"):
            data: DomainData = hass.data[DOMAIN]
            entries = hass.config_entries.async_entries(DOMAIN)
            if entries and entries[0].data[const.CONF_MODE] == ConfMode.UI:
                config = _ui_config(hass, entries[0])
            elif client := data.get("client"):
                config = await get_remote_config(hass, client)
            else:
                config = await async_integration_yaml_config(hass, DOMAIN)
            await setup_domain(hass, data, config or {})
            hass.bus.async_fire(f"event_{DOMAIN}_reloaded", context=call.context)

        async_register_admin_service(hass, DOMAIN, SERVICE_RELOAD, reload_config)

        # init data
        data.update(config=config, panels=set())
    return data


async def get_version(hass: "HomeAssistant", domain: str) -> str:
    version = "unknown"
    try:
        from homeassistant.loader import async_get_integration

        integration = await async_get_integration(hass, domain)
        version = integration.version or version
    except Exception:
        pass
    return version


async def _async_register_panel(hass: "HomeAssistant", panel: dict[str, "Any"]) -> None:
    """Register a custom panel, dropping keywords this core does not accept.

    ``handle_safe_area`` only exists on newer cores; older ones reject it.
    """
    supported = inspect.signature(panel_custom.async_register_panel).parameters
    if "handle_safe_area" not in supported:
        panel = {key: value for key, value in panel.items() if key != "handle_safe_area"}
    return await panel_custom.async_register_panel(hass, **panel)


async def _async_register_static_paths(hass_http: "http.HomeAssistantHTTP", configs):
    if hasattr(hass_http, "async_register_static_paths"):
        await hass_http.async_register_static_paths([http.StaticPathConfig(*c) for c in configs])
    else:
        for c in configs:
            hass_http.register_static_path(*c)


def _parse_config(
    hass: "HomeAssistant", config
) -> tuple[list[IngressCfg], dict[str, dict[str, "Any"]]]:
    cfgs: list[IngressCfg] = []
    panels: dict[str, dict[str, Any]] = {}
    ingresses, children = {}, []
    placeholder = "$http_x_ingress_path"
    entrypoint = f"{URL_BASE}/entrypoint.js?v={VERSION}"
    for name, data in config.get(DOMAIN, {}).items():
        ssl_policy = tls_context(data)
        cfg: dict[str, Any]
        ingress_cfg = None
        work_mode = data[const.CONF_WORK_MODE]
        url, front_url = data[const.CONF_URL], {}
        if isinstance(url, dict):
            url, front_url = url[const.CONF_DEFAULT], url
        if work_mode not in (WorkMode.IFRAME, WorkMode.CUSTOM):
            # init backend config
            ingress_cfg = dict(mode=work_mode, name=name, entry=name, ssl=ssl_policy)
            ingress_path, sub_path = f"{API_BASE}/{name}", ""
            if work_mode != WorkMode.HASSIO:
                url = url.replace(placeholder, ingress_path).rstrip("/")
                if "://" not in url:
                    url = f"http://{url}"
                pos = url.find("/", url.index("://") + 3)
                if pos > 0:
                    url, sub_path = url[:pos], url[pos:]
                headers = {}
                for k, v in data.get(const.CONF_HEADERS, {}).items():
                    headers[std_header_name(k)] = v.replace(placeholder, ingress_path)
                ingress_cfg.update(
                    origin=URL(url),
                    sub_path=sub_path,
                    headers=headers,
                    cookie_name=data.get(const.CONF_COOKIE_NAME),
                    expire_time=data.get(const.CONF_EXPIRE_TIME),
                    static_token=data.get(const.CONF_STATIC_TOKEN),
                    enable_compress=data.get(const.CONF_ENABLE_COMPRESS),
                )
                url += sub_path
                if work_mode in (WorkMode.INGRESS, WorkMode.SUBAPP):
                    rewrites: list[RewriteCfg] = []
                    if rewrite := data.get(const.CONF_REWRITE):
                        ingress_path = re.escape(ingress_path)
                        for item in rewrite:
                            item[const.CONF_REPLACE] = item[const.CONF_REPLACE].replace(
                                placeholder, ingress_path
                            )
                            rewrites.append(RewriteCfg(**item))
                    ingress_cfg.update(rewrites=rewrites)
            ingress_cfg = IngressCfg(**ingress_cfg)
            cfgs.append(ingress_cfg)
            # init frontend config
            cfg = {"token": ingress_cfg.token, "index": data[const.CONF_INDEX].lstrip("/")}
            if work_mode == WorkMode.AUTH:
                cfg["url"] = front_url
                cfg["field"] = ingress_cfg.cookie_name
            elif work_mode == WorkMode.HASSIO:
                cfg["addon"] = url
            elif work_mode == WorkMode.INGRESS:
                ingresses[name] = ingress_cfg
        else:
            cfg = {"url": front_url}
            if data[const.CONF_INDEX]:
                url = url.rstrip("/")
                cfg["index"] = data[const.CONF_INDEX].lstrip("/")
        if front_url.get(const.CONF_MATCH):
            front_url[const.CONF_DEFAULT] = url
        elif "url" in cfg:
            cfg["url"] = url

        cfg["ui_mode"] = work_mode if work_mode == WorkMode.CUSTOM else data[const.CONF_UI_MODE]
        title, icon = data.get(const.CONF_TITLE), data.get(const.CONF_ICON)
        if parent := data.get(const.CONF_PARENT):
            if name.startswith(parent) and name[len(parent) : len(parent) + 1] == "_":
                name = name[len(parent) + 1 :]
            if ingress_cfg:
                ingress_cfg.entry = f"{parent}/{name}"
            if title:
                cfg["title"] = title
            if icon:
                cfg["icon"] = icon
            children.append((name, parent, cfg, ingress_cfg))
            continue

        if not data.get(const.CONF_SHOW_IN_SIDEBAR, True):
            # Keep the name inside the panel so it still has a header, but register
            # it without a sidebar entry.
            if title:
                cfg["title"] = title
            title = None

        panels[name] = dict(
            webcomponent_name="ha-panel-ingress",
            js_url=entrypoint,
            frontend_url_path=name,
            sidebar_title=title,
            sidebar_icon=icon,
            require_admin=data[panel_custom.CONF_REQUIRE_ADMIN],
            embed_iframe=False,
            handle_safe_area=True,
            config=cfg,
        )

    for child, parent, cfg, ingress_cfg in children:
        if ingress_cfg and ingress_cfg.mode == WorkMode.SUBAPP:
            if parent not in ingresses:
                _LOGGER.error(
                    "parent ingress[%s] not found, skip subapp[%s]!", parent, ingress_cfg.name
                )
                continue
            # ingress: add subapp to parent's sub_apps
            pi_cfg = ingresses[parent]
            if not pi_cfg.sub_apps:
                pi_cfg.sub_apps = []
            pi_cfg.sub_apps.append(ingress_cfg)
            # panel: use parent's parent if parent is a child panel
            if parent not in panels:
                parent = pi_cfg.entry.partition("/")
                parent, child = parent[0], f"{parent[2]}-{child}"
                ingress_cfg.entry = f"{parent}/{child}"
        if parent not in panels:
            _LOGGER.error("parent panel[%s] not found, skip child panel[%s]!", parent, child)
            continue
        # panel: add child to parent's children
        panels[parent]["config"].setdefault("children", {})[child] = cfg

    return cfgs, panels
