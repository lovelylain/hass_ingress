import asyncio
import base64
from ipaddress import ip_address
import re
import os
import time
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_HEADERS
from homeassistant.components import panel_custom, panel_iframe, frontend
from homeassistant.components.frontend import EVENT_PANELS_UPDATED
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import aiohttp
from aiohttp import hdrs, web, WSMsgType
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs, quote

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'ingress'
CONF_MATCH = 'match'
CONF_REPLACE = 'replace'
CONF_DEFAULT = 'default'
CONF_INDEX = 'index'
CONF_PARENT = 'parent'
CONF_INGRESS = 'ingress'
CONF_WORK_MODE = 'work_mode'
CONF_TOOLBAR = 'toolbar'
CONF_UI_MODE = 'ui_mode'
CONF_COOKIE_NAME = 'cookie_name'
CONF_EXPIRE_TIME = 'expire_time'
CONF_DISABLE_CHUNKED = 'disable_chunked'
API_BASE = '/api/ingress'
URL_BASE = '/files/ingress'

WORK_MODES = ['ingress', 'iframe', 'auth', 'hassio']
UI_MODES = ['normal', 'toolbar', 'replace']

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: cv.schema_with_slug_keys(vol.Schema({
        vol.Optional(panel_iframe.CONF_TITLE): cv.string,
        vol.Optional(panel_iframe.CONF_ICON): cv.icon,
        vol.Optional(panel_iframe.CONF_REQUIRE_ADMIN, default=False): cv.boolean,
        vol.Required(panel_iframe.CONF_URL): vol.Any(cv.string, vol.Schema({
            vol.Required(CONF_MATCH): cv.string,
            vol.Required(CONF_REPLACE): cv.string,
            vol.Required(CONF_DEFAULT): cv.string,
        })),
        vol.Optional(CONF_INDEX, default=''): cv.string,
        vol.Optional(CONF_PARENT): cv.string,
        vol.Optional(CONF_INGRESS, default=True): cv.boolean,
        vol.Optional(CONF_WORK_MODE): vol.In(WORK_MODES),
        vol.Optional(CONF_TOOLBAR): cv.boolean,
        vol.Optional(CONF_UI_MODE): vol.In(UI_MODES),
        vol.Optional(CONF_HEADERS): vol.Schema({str: cv.string}),
        vol.Optional(CONF_COOKIE_NAME): cv.string,
        vol.Optional(CONF_EXPIRE_TIME): cv.positive_int,
        vol.Optional(CONF_DISABLE_CHUNKED): cv.boolean,
    })),
}, extra=vol.ALLOW_EXTRA)

class IngressCfg:
    headers = {}
    cookie_name = 'ingress_token'
    cookie_names = {}
    expire_time = 3600
    disable_chunked = False

    def __init__(self, **kwargs):
        self.__dict__.update((k,v) for k,v in kwargs.items() if v)
        if self.cookie_name != IngressCfg.cookie_name:
            IngressCfg.cookie_names[self.name] = self.cookie_name
        self.token = {}

def new_token(now, cfgs, cfg: IngressCfg):
    while True:
        token = base64.urlsafe_b64encode(os.urandom(33)).decode()
        if token not in cfgs:
            break
    tkcfg = cfg.token
    cfgs.pop(tkcfg.get('value'), None)
    cfgs[token] = cfg
    tkcfg['value'] = token
    tkcfg['expire'] = now + cfg.expire_time
    return tkcfg

def get_cfg_by_token(hass, cfgs, token):
    cfg = cfgs.get(token)
    if cfg:
        # token valid, check refresh
        now = int(time.time())
        tkcfg = cfg.token
        if now >= tkcfg['expire']:
            token = new_token(now, cfgs, cfg)['value']
            hass.bus.async_fire(EVENT_PANELS_UPDATED)
    return token, cfg

def get_cfg_by_cookie(request, cfgs, name):
    cookie_name = IngressCfg.cookie_names.get(name) or IngressCfg.cookie_name
    return cfgs.get(request.cookies.get(cookie_name))

async def _async_setup_reload_service(hass, domain, async_reset, async_setup):
    from homeassistant.const import SERVICE_RELOAD
    from homeassistant.helpers.reload import async_integration_yaml_config
    from homeassistant.helpers.service import async_register_admin_service
    async def reload_config(call):
        config = await async_integration_yaml_config(hass, domain)
        await async_reset(hass)
        await async_setup(hass, config)
        hass.bus.async_fire(f'event_{domain}_reloaded', context=call.context)
    async_register_admin_service(hass, domain, SERVICE_RELOAD, reload_config)

async def async_setup(hass, config):
    now = int(time.time())
    cfgs, panels, children = {}, {}, []
    for name, data in config.get(DOMAIN, {}).items():
        ingress_cfg = None
        work_mode = data.get(CONF_WORK_MODE)
        if work_mode is None:
            work_mode = 'ingress' if data[CONF_INGRESS] else 'iframe'
        url, front_url = data[panel_iframe.CONF_URL], {}
        if isinstance(url, dict):
            url, front_url = url[CONF_DEFAULT], url
        if work_mode != 'iframe':
            if work_mode == 'hassio':
                url, addon = 'hassio', url
            else:
                url = url.rstrip('/')
                if '://' not in url:
                    url = f'http://{url}'
            ingress_cfg = dict(
                name=name, url=url, entry=name,
                cookie_name=data.get(CONF_COOKIE_NAME),
                expire_time=data.get(CONF_EXPIRE_TIME),
            )
            if work_mode != 'auth':
                ingress_cfg.update(
                    headers=data.get(CONF_HEADERS),
                    disable_chunked=data.get(CONF_DISABLE_CHUNKED),
                )
            ingress_cfg = IngressCfg(**ingress_cfg)
            token = new_token(now, cfgs, ingress_cfg)
            cfg = {'token': token, 'index': data[CONF_INDEX].lstrip('/')}
            if work_mode == 'auth':
                cfg['url'] = front_url
            elif work_mode == 'hassio':
                cfg['addon'] = addon
        else:
            cfg = {'url': front_url}
            if data[CONF_INDEX]:
                url = url.rstrip('/')
                cfg['index'] = data[CONF_INDEX].lstrip('/')
        if front_url.get(CONF_MATCH):
            front_url[CONF_DEFAULT] = url
        elif 'url' in cfg:
            cfg['url'] = url

        ui_mode = data.get(CONF_UI_MODE)
        if ui_mode is None:
            ui_mode = 'toolbar' if data.get(CONF_TOOLBAR) else 'normal'
        cfg['ui_mode'] = ui_mode
        title = data.get(panel_iframe.CONF_TITLE)
        parent = data.get(CONF_PARENT)
        if parent:
            if name.startswith(parent) and name[len(parent):len(parent)+1] == '_':
                name = name[len(parent)+1:]
            if ingress_cfg:
                ingress_cfg.entry = f'{parent}/{name}'
            if title: cfg['title'] = title
            children.append((name, parent, cfg))
            continue

        panels[name] = dict(
            webcomponent_name = 'ha-panel-ingress',
            js_url = f'{URL_BASE}/entrypoint.js',
            frontend_url_path = name,
            sidebar_title = title,
            sidebar_icon = data.get(panel_iframe.CONF_ICON),
            require_admin = data[panel_iframe.CONF_REQUIRE_ADMIN],
            embed_iframe = False,
            config = cfg,
        )

    for child, parent, cfg in children:
        if parent not in panels:
            _LOGGER.error('parent panel[%s] not found, skip child panel[%s]!', parent, child)
            continue
        panels[parent]['config'].setdefault('children', {})[child] = cfg

    await asyncio.gather(*(panel_custom.async_register_panel(hass, **v) for v in panels.values()))

    data = hass.data.setdefault(DOMAIN, {})
    if 'config' in data:
        data['config'].update(cfgs)
        data['panels'].update(panels)
    else:
        hass.http.register_static_path(URL_BASE, os.path.join(__path__[0], 'www'), False)
        hass.http.register_view(IngressView(hass, cfgs, async_get_clientsession(hass)))
        data.update(config=cfgs, panels=set(panels))

        async def async_reset(hass):
            data = hass.data[DOMAIN]
            for name in data['panels']:
                frontend.async_remove_panel(hass, name)
            data['panels'].clear()
            data['config'].clear()
            IngressCfg.cookie_names.clear()
        await _async_setup_reload_service(hass, DOMAIN, async_reset, async_setup)
    return True


class IngressView(HomeAssistantView):
    name = 'api:ingress:proxy'
    url = API_BASE + '/{token}/{path:.*}'
    requires_auth = False

    def __init__(self, hass, config, websession):
        self._hass = hass
        self._config = config
        self._websession = websession

    async def _handle_auth(self, request):
        # check required header
        name = request.headers.get('X-Ingress-Name')
        url = request.headers.get('X-Original-URI')
        if not name or not url:
            raise web.HTTPNotFound()
        # check ingressToken parameter
        cfg = None
        url = urlparse(url)
        params = parse_qs(url.query)
        if 'ingressToken' in params:
            token, cfg = get_cfg_by_token(self._hass, self._config, params['ingressToken'][0])
        if cfg:
            # valid, return 200
            resp = web.Response()
            resp.set_cookie(cfg.cookie_name, token, httponly=True)
            return resp
        # check ingress_token cookie
        cfg = get_cfg_by_cookie(request, self._config, name)
        if cfg:
            # valid, return 200
            return web.Response()
        # cookie invalid, try redirect to entry
        for cfg in self._config.values():
            if cfg.name == name and cfg.url != 'hassio':
                params = {'replace': ''}
                root = urlparse(cfg.url + '/').path
                if url.path.startswith(root):
                    params['index'] = urlunparse(('', '', url.path[len(root):]) + url[3:])
                url = f'/{cfg.entry}?{urlencode(params)}'
                raise web.HTTPUnauthorized(headers={'Location': url})
        raise web.HTTPNotFound()

    async def _handle(self, request, token, path):
        if token == '_' and path == 'auth':
            return await self._handle_auth(request)
        token, cfg = get_cfg_by_token(self._hass, self._config, token)
        if cfg:
            url = f'{API_BASE}/{cfg.name}/'
            if request.query_string:
                path = f'{path}?{request.query_string}'
            resp = web.HTTPFound(url + path)
            resp.set_cookie(cfg.cookie_name, token, path=url, httponly=True)
            raise resp
        cfg = get_cfg_by_cookie(request, self._config, token)
        if not cfg:
            # cookie invalid, try redirect to entry
            for cfg in self._config.values():
                if cfg.name == token:
                    if request.query_string:
                        path = f'{path}?{request.query_string}'
                    path = urlencode({'replace':'', 'index':path})
                    raise web.HTTPFound(f'/{cfg.entry}?{path}')
            raise web.HTTPNotFound()
        if cfg.url == 'hassio':
            if not path:
                raise web.HTTPFound(f'/{cfg.entry}?replace')
            url = f'http://{os.environ['SUPERVISOR']}/ingress/{quote(path)}'
        else:
            url = f'{cfg.url}/{path}'

        try:
            # Websocket
            if _is_websocket(request):
                return await self._handle_websocket(request, cfg, url)
            # Request
            return await self._handle_request(request, cfg, url)
        except aiohttp.ClientError as err:
            _LOGGER.debug('Ingress error with %s: %s', url, err)
        raise web.HTTPBadGateway() from None

    get = _handle
    post = _handle
    put = _handle
    delete = _handle
    patch = _handle
    options = _handle

    async def _handle_websocket(self, request, cfg, url):
        if hdrs.SEC_WEBSOCKET_PROTOCOL in request.headers:
            req_protocols = [
                str(proto.strip())
                for proto in request.headers[hdrs.SEC_WEBSOCKET_PROTOCOL].split(',')
            ]
        else:
            req_protocols = ()

        ws_server = web.WebSocketResponse(
            protocols=req_protocols, autoclose=False, autoping=False
        )
        await ws_server.prepare(request)

        # Support GET query
        if request.query_string:
            url = f'{url}?{request.query_string}'

        # Start proxy
        async with self._websession.ws_connect(
            url,
            headers=_init_header(request, cfg, url),
            protocols=req_protocols,
            autoclose=False,
            autoping=False,
        ) as ws_client:
            # Proxy requests
            await asyncio.wait(
                [
                    asyncio.create_task(_websocket_forward(ws_server, ws_client)),
                    asyncio.create_task(_websocket_forward(ws_client, ws_server)),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

        return ws_server

    async def _handle_request(self, request, cfg, url):
        data = request.content
        if (request.headers.get(hdrs.TRANSFER_ENCODING) != 'chunked' and
            (cfg.disable_chunked or int(request.headers.get(hdrs.CONTENT_LENGTH, 0)) < 4194000)):
            data = await data.read()
        async with self._websession.request(
            request.method,
            url,
            headers=_init_header(request, cfg, url),
            params=request.query,
            allow_redirects=False,
            data=data,
            timeout=aiohttp.ClientTimeout(total=None),
            skip_auto_headers=[hdrs.CONTENT_TYPE],
        ) as result:
            headers = _response_header(result)

            # Simple request
            if (
                hdrs.CONTENT_LENGTH in result.headers
                and int(result.headers.get(hdrs.CONTENT_LENGTH, 0)) < 4194000
            ) or result.status in (204, 304):
                # Return Response
                body = await result.read()
                return web.Response(
                    headers=headers,
                    status=result.status,
                    content_type=result.content_type,
                    body=body,
                )

            # Stream response
            response = web.StreamResponse(status=result.status, headers=headers)
            response.content_type = result.content_type

            try:
                await response.prepare(request)
                async for data in result.content.iter_chunked(4096):
                    await response.write(data)
            except (
                aiohttp.ClientError,
                aiohttp.ClientPayloadError,
                ConnectionResetError,
            ) as err:
                _LOGGER.debug('Stream error with %s: %s', url, err)

            return response


def _init_header(request, cfg, url):
    headers = {}

    # filter flags
    for name, value in request.headers.items():
        if name in (
            hdrs.CONTENT_LENGTH,
            hdrs.CONTENT_ENCODING,
            hdrs.TRANSFER_ENCODING,
            hdrs.SEC_WEBSOCKET_EXTENSIONS,
            hdrs.SEC_WEBSOCKET_PROTOCOL,
            hdrs.SEC_WEBSOCKET_VERSION,
            hdrs.SEC_WEBSOCKET_KEY,
        ):
            continue
        if name == hdrs.COOKIE:
            value = '; '.join(f'{k}={v}' for k,v in request.cookies.items() if k != cfg.cookie_name)
            if not value: continue
        headers[name] = value
    for name, value in cfg.headers.items():
        headers[name] = value

    # Set X-Ingress-Path
    ingress_path = f'{API_BASE}/{cfg.name}'
    if cfg.url == 'hassio':
        ingress_path += re.search(r'/ingress(/[^/]+)/', url).group(1)
    headers['X-Ingress-Path'] = ingress_path

    # Set X-Forwarded-For
    forward_for = request.headers.get(hdrs.X_FORWARDED_FOR)
    if (peername := request.transport.get_extra_info('peername')) is None:
        _LOGGER.error("Can't set forward_for header, missing peername")
        raise web.HTTPBadRequest()

    connected_ip = ip_address(peername[0])
    if forward_for:
        forward_for = f'{forward_for}, {connected_ip!s}'
    else:
        forward_for = f'{connected_ip!s}'
    headers[hdrs.X_FORWARDED_FOR] = forward_for

    # Set X-Forwarded-Host
    if not (forward_host := request.headers.get(hdrs.X_FORWARDED_HOST)):
        forward_host = request.host
    headers[hdrs.X_FORWARDED_HOST] = forward_host

    # Set X-Forwarded-Proto
    forward_proto = request.headers.get(hdrs.X_FORWARDED_PROTO)
    if not forward_proto:
        forward_proto = request.url.scheme
    headers[hdrs.X_FORWARDED_PROTO] = forward_proto

    return headers


def _response_header(response):
    headers = {}

    for name, value in response.headers.items():
        if name in (
            hdrs.TRANSFER_ENCODING,
            hdrs.CONTENT_LENGTH,
            hdrs.CONTENT_TYPE,
            hdrs.CONTENT_ENCODING,
        ):
            continue
        headers[name] = value

    return headers


def _is_websocket(request):
    headers = request.headers
    return ('upgrade' in headers.get(hdrs.CONNECTION, '').lower()
        and headers.get(hdrs.UPGRADE, '').lower() == 'websocket')

async def _websocket_forward(ws_from, ws_to):
    try:
        async for msg in ws_from:
            if msg.type == WSMsgType.TEXT:
                await ws_to.send_str(msg.data)
            elif msg.type == WSMsgType.BINARY:
                await ws_to.send_bytes(msg.data)
            elif msg.type == WSMsgType.PING:
                await ws_to.ping()
            elif msg.type == WSMsgType.PONG:
                await ws_to.pong()
            elif ws_to.closed:
                await ws_to.close(code=ws_to.close_code, message=msg.extra)
    except RuntimeError:
        _LOGGER.debug('Ingress Websocket runtime error')
    except ConnectionResetError:
        _LOGGER.debug('Ingress Websocket Connection Reset')
