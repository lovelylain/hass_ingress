import asyncio
from homeassistant.components import frontend, http, panel_custom
from homeassistant.const import (
    CONF_DEFAULT,
    CONF_HEADERS,
    CONF_ICON,
    CONF_MODE,
    CONF_NAME,
    CONF_PATH,
    CONF_URL,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
import os
import re
import time
from typing import TYPE_CHECKING, cast
import voluptuous as vol
from yarl import URL

from .const import (
    DOMAIN,
    LOGGER as _LOGGER,
    API_BASE,
    URL_BASE,
    WorkMode,
    UIMode,
    RewriteMode,
    ConfMode,
)
from .config import IngressStore, IngressCfg, RewriteCfg
from .ingress import IngressView, std_header_name

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

CONF_TITLE: "Final" = "title"
CONF_MATCH: "Final" = "match"
CONF_REPLACE: "Final" = "replace"
CONF_INDEX: "Final" = "index"
CONF_PARENT: "Final" = "parent"
CONF_WORK_MODE: "Final" = "work_mode"
CONF_UI_MODE: "Final" = "ui_mode"
CONF_REWRITE: "Final" = "rewrite"
CONF_COOKIE_NAME: "Final" = "cookie_name"
CONF_EXPIRE_TIME: "Final" = "expire_time"
CONF_STATIC_TOKEN: "Final" = "static_token"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: cv.schema_with_slug_keys(
            vol.Schema(
                {
                    vol.Optional(panel_custom.CONF_REQUIRE_ADMIN, default=False): cv.boolean,
                    vol.Optional(CONF_TITLE): cv.string,
                    vol.Optional(CONF_ICON): cv.icon,
                    vol.Required(CONF_URL): vol.Any(
                        cv.string,
                        vol.Schema(
                            {
                                vol.Required(CONF_MATCH): cv.string,
                                vol.Required(CONF_REPLACE): cv.string,
                                vol.Required(CONF_DEFAULT): cv.string,
                            }
                        ),
                    ),
                    vol.Optional(CONF_INDEX, default=""): cv.string,
                    vol.Optional(CONF_PARENT): cv.string,
                    vol.Optional(CONF_WORK_MODE, default=WorkMode.INGRESS): vol.In(list(WorkMode)),
                    vol.Optional(CONF_UI_MODE, default=UIMode.NORMAL): vol.In(list(UIMode)),
                    vol.Optional(CONF_HEADERS): vol.Schema({str: cv.string}),
                    vol.Optional(CONF_REWRITE): [
                        vol.Schema(
                            {
                                vol.Required(CONF_MODE): vol.In(list(RewriteMode)),
                                vol.Optional(CONF_PATH): cv.string,
                                vol.Optional(CONF_NAME): cv.string,
                                vol.Required(CONF_MATCH): cv.string,
                                vol.Required(CONF_REPLACE): cv.string,
                            }
                        )
                    ],
                    vol.Optional(CONF_COOKIE_NAME): cv.string,
                    vol.Optional(CONF_STATIC_TOKEN): cv.string,
                    vol.Optional(CONF_EXPIRE_TIME): cv.positive_int,
                }
            )
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: "HomeAssistant", config) -> bool:
    # init once
    data = await _async_init(hass)

    # init config entry
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        hass.async_create_task(
            hass.config_entries.flow.async_init(DOMAIN, context={"source": "import"})
        )

    # init yaml mode
    if not entries or entries[0].data[CONF_MODE] == ConfMode.YAML:
        await setup_domain(hass, data, config)

    return True


async def async_setup_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> bool:
    if entry.data[CONF_MODE] != ConfMode.AGENT:
        return True

    from homeassistant.const import EVENT_HOMEASSISTANT_STOP
    from .client import create_client
    from .client.exceptions import ClientException

    # init client
    client = create_client(hass, entry.data[CONF_URL], async_get_clientsession(hass))
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


async def on_remote_ready(hass: "HomeAssistant", client: "IngressClient", _: "Any"):
    await client.send_command({"type": "subscribe"})


async def get_remote_config(hass: "HomeAssistant", client: "IngressClient") -> dict[str, "Any"]:
    # TODO
    return {DOMAIN: {}}


async def async_unload_entry(hass: "HomeAssistant", entry: "ConfigEntry") -> bool:
    client: IngressClient
    if client := hass.data[DOMAIN].pop("client", None):
        client.disconnect()
    return True


async def setup_domain(hass: "HomeAssistant", data: "DomainData", config) -> None:
    # clean
    for name in data["panels"]:
        frontend.async_remove_panel(hass, name)
    data["panels"].clear()
    data["config"].clear()

    # parse config
    config, panels = _parse_config(hass, config)

    # add ingress
    now = int(time.time())
    for cfg in config:
        data["config"].add_ingress(cfg, now)

    # add panels
    data["panels"].update(panels)
    await asyncio.gather(*(panel_custom.async_register_panel(hass, **v) for v in panels.values()))


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
        hass.http.register_view(IngressView(hass, config, async_get_clientsession(hass)))

        # register reload config
        async def reload_config(call: "ServiceCall"):
            data: DomainData = hass.data[DOMAIN]
            if client := data.get("client"):
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
        cfg: dict[str, Any]
        ingress_cfg = None
        work_mode = data[CONF_WORK_MODE]
        url, front_url = data[CONF_URL], {}
        if isinstance(url, dict):
            url, front_url = url[CONF_DEFAULT], url
        if work_mode not in (WorkMode.IFRAME, WorkMode.CUSTOM):
            # init backend config
            ingress_cfg = dict(mode=work_mode, name=name, entry=name)
            ingress_path, sub_path = f"{API_BASE}/{name}", ""
            if work_mode != WorkMode.HASSIO:
                url = url.replace(placeholder, ingress_path).rstrip("/")
                if "://" not in url:
                    url = f"http://{url}"
                pos = url.find("/", url.index("://") + 3)
                if pos > 0:
                    url, sub_path = url[:pos], url[pos:]
                headers = {}
                for k, v in data.get(CONF_HEADERS, {}).items():
                    headers[std_header_name(k)] = v.replace(placeholder, ingress_path)
                ingress_cfg.update(
                    origin=URL(url),
                    sub_path=sub_path,
                    headers=headers,
                    cookie_name=data.get(CONF_COOKIE_NAME),
                    expire_time=data.get(CONF_EXPIRE_TIME),
                    static_token=data.get(CONF_STATIC_TOKEN),
                )
                url += sub_path
                if work_mode in (WorkMode.INGRESS, WorkMode.SUBAPP):
                    rewrites: list[RewriteCfg] = []
                    if rewrite := data.get(CONF_REWRITE):
                        ingress_path = re.escape(ingress_path)
                        for item in rewrite:
                            item[CONF_REPLACE] = item[CONF_REPLACE].replace(
                                placeholder, ingress_path
                            )
                            rewrites.append(RewriteCfg(**item))
                    ingress_cfg.update(rewrites=rewrites)
            ingress_cfg = IngressCfg(**ingress_cfg)
            cfgs.append(ingress_cfg)
            # init frontend config
            cfg = {"token": ingress_cfg.token, "index": data[CONF_INDEX].lstrip("/")}
            if work_mode == WorkMode.AUTH:
                cfg["url"] = front_url
                cfg["field"] = ingress_cfg.cookie_name
            elif work_mode == WorkMode.HASSIO:
                cfg["addon"] = url
            elif work_mode == WorkMode.INGRESS:
                ingresses[name] = ingress_cfg
        else:
            cfg = {"url": front_url}
            if data[CONF_INDEX]:
                url = url.rstrip("/")
                cfg["index"] = data[CONF_INDEX].lstrip("/")
        if front_url.get(CONF_MATCH):
            front_url[CONF_DEFAULT] = url
        elif "url" in cfg:
            cfg["url"] = url

        cfg["ui_mode"] = work_mode if work_mode == WorkMode.CUSTOM else data[CONF_UI_MODE]
        title, icon = data.get(CONF_TITLE), data.get(CONF_ICON)
        if parent := data.get(CONF_PARENT):
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

        panels[name] = dict(
            webcomponent_name="ha-panel-ingress",
            js_url=entrypoint,
            frontend_url_path=name,
            sidebar_title=title,
            sidebar_icon=icon,
            require_admin=data[panel_custom.CONF_REQUIRE_ADMIN],
            embed_iframe=False,
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
