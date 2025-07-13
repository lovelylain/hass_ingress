import aiohttp
from aiohttp import hdrs, web, WSMsgType
from aiohttp.helpers import must_be_empty_body
import asyncio
from functools import lru_cache
from homeassistant.components import frontend, http
from ipaddress import ip_address
import json
from multidict import CIMultiDict
import re
from typing import TYPE_CHECKING, cast
from urllib.parse import urlencode, quote
from yarl import URL

from .const import DOMAIN, LOGGER as _LOGGER, API_BASE, URL_BASE, WorkMode, UIMode, RewriteMode

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from typing import Any, Callable, Iterable

    from .config import IngressStore, IngressCfg, RewriteCfg

X_INGRESS_NAME = "X-Ingress-Name"
X_ORIGINAL_URL = "X-Original-Url"
X_HASS_ORIGIN = "X-Hass-Origin"
X_INGRESS_PATH = "X-Ingress-Path"
X_INGRESS_SUBPATH = "X-Ingress-Subpath"
HEADER_AUTO_PH = "$auto"

INGRESS_MODES = (WorkMode.INGRESS, WorkMode.SUBAPP)
METH_ALLOW_REDIRECT = (hdrs.METH_GET, hdrs.METH_HEAD)

INIT_HEADERS_FILTER = {
    hdrs.CONTENT_LENGTH,
    hdrs.CONTENT_ENCODING,
    hdrs.TRANSFER_ENCODING,
    hdrs.SEC_WEBSOCKET_EXTENSIONS,
    hdrs.SEC_WEBSOCKET_PROTOCOL,
    hdrs.SEC_WEBSOCKET_VERSION,
    hdrs.SEC_WEBSOCKET_KEY,
}
RESPONSE_HEADERS_FILTER = {
    hdrs.TRANSFER_ENCODING,
    hdrs.CONTENT_LENGTH,
    hdrs.CONTENT_TYPE,
    hdrs.CONTENT_ENCODING,
}

MAX_SIMPLE_REQUEST_SIZE = 4194000

DISABLED_TIMEOUT = aiohttp.ClientTimeout(total=None)


class IngressView(http.HomeAssistantView):  # type: ignore
    """ingress view to handle request."""

    name = "api:ingress:proxy"
    url = API_BASE + "/{name}/{path:.*}"
    requires_auth = False

    def __init__(
        self, hass: "HomeAssistant", config: "IngressStore", websession: aiohttp.ClientSession
    ):
        self._hass = hass
        self._config = config
        self._websession = websession

    async def _handle_auth(self, request: web.Request) -> web.Response:
        # check required header
        name = request.headers.get(X_INGRESS_NAME)
        url = request.headers.get(X_ORIGINAL_URL)
        if not name or not url:
            raise web.HTTPNotFound

        # check ingress_token from query
        url = URL(url)
        cookie_name = self._config.cookie_name(name)
        if cookie_name in url.query:
            cfg, token = self._config.check_token(self._hass, url.query[cookie_name])
            if cfg:
                # valid, remove ingressToken if has X-Hass-Origin else return 200
                hass_origin = request.headers.get(X_HASS_ORIGIN)
                if hass_origin and request.method in METH_ALLOW_REDIRECT:
                    query = url.query.copy()
                    query.pop(cookie_name)
                    resp = web.HTTPUnauthorized(headers={hdrs.LOCATION: str(url.with_query(query))})
                else:
                    resp = web.Response(headers=cfg.headers)
                resp.set_cookie(cfg.cookie_name, token, httponly=True)
                return resp

        # check ingress_token from cookie
        token = request.cookies.get(cookie_name, "")
        if cfg := self._config.check_token(self._hass, token, False)[0]:
            # valid, return 200
            return web.Response(headers=cfg.headers)

        # cookie invalid, try redirect to entry
        if cfg := self._config.get(name):
            params = {"replace": ""}
            root = cfg.sub_path + "/"
            if url.path.startswith(root):
                url = URL.build(
                    path=url.path[len(root) :], query_string=url.query_string, fragment=url.fragment
                )
                params["index"] = str(url)
            hass_origin = request.headers.get(X_HASS_ORIGIN, "")
            url = f"{hass_origin}/{cfg.entry}?{urlencode(params)}"
            raise web.HTTPUnauthorized(headers={hdrs.LOCATION: url})

        raise web.HTTPNotFound

    async def _handle_redirect(self, cfg: "IngressCfg", path: str) -> web.Response | None:
        # find frontend config
        hass_data, token = self._hass.data, cfg.token

        def get_front_config():
            def get_config(config: dict[str, "Any"]):
                fields = ("url", "index")
                config = {k: config[k] for k in fields if k in config}
                if "index" in config:
                    config["index"] = path.lstrip("/")
                config["ui_mode"] = UIMode.REPLACE
                return config

            for panel in hass_data[DOMAIN]["panels"]:
                panel = hass_data[frontend.DATA_PANELS].get(panel)
                if not panel:
                    continue
                if panel.config.get("token") is token:
                    return get_config(panel.config)
                for child in panel.config.get("children", {}).values():
                    if child.get("token") is token:
                        return get_config(child)

        if not (config := get_front_config()):
            return

        # redirect to target url
        html = f"""\
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8"/>
    <script async src="{URL_BASE}/entrypoint.js"></script>
    <script>(async () => {{
await customElements.whenDefined("ha-panel-ingress");
document.querySelector("ha-panel-ingress").setProperties({{panel: {{
  config: {json.dumps(config)},
}}}});
}})();</script>
  </head>
  <body><ha-panel-ingress></ha-panel-ingress></body>
</html>
"""
        return web.Response(text=html, content_type="text/html")

    async def _handle(
        self, request: web.Request, name: str, path: str
    ) -> web.Response | web.StreamResponse | web.WebSocketResponse:
        if name == "_" and path == "auth":
            return await self._handle_auth(request)

        cfg, token = self._config.check_token(self._hass, name)
        if cfg and request.method in METH_ALLOW_REDIRECT:
            # only redirect when get or head method
            url = f"{API_BASE}/{cfg.name}/"
            path = quote(path) + (f"?{request.query_string}" if request.query_string else "")
            resp = web.HTTPFound(url + path)
            # set self cookie
            resp.set_cookie(cfg.cookie_name, token, path=url, httponly=True)
            # set subapp's cookies
            for cfg in cfg.sub_apps:
                resp.headers.add(
                    hdrs.SET_COOKIE,
                    f"{cfg.cookie_name}={cfg.token['value']}; HttpOnly; Path={API_BASE}/{cfg.name}/",
                )
            raise resp

        if not cfg:
            token = request.cookies.get(self._config.cookie_name(name), "")
            cfg = self._config.check_token(self._hass, token, False)[0]
        if not cfg or cfg.mode not in INGRESS_MODES:
            # cookie invalid, try redirect to entry
            if cfg := cfg or self._config.get(name):
                path = quote(path) + (f"?{request.query_string}" if request.query_string else "")
                if cfg.mode == WorkMode.AUTH:
                    if (resp := await self._handle_redirect(cfg, path)) is not None:
                        return resp
                path = urlencode({"replace": "", "index": path})
                raise web.HTTPFound(f"/{cfg.entry}?{path}")
            raise web.HTTPNotFound

        url = _create_url(cfg, path)
        try:
            # Websocket
            if _is_websocket(request):
                return await self._handle_websocket(request, cfg, url)
            # Request
            return await self._handle_request(request, cfg, url)
        except aiohttp.ClientError as err:
            _LOGGER.debug("Ingress error with %s / %s: %s", cfg.name, url, err)
            raise web.HTTPBadGateway from None

    get = _handle
    post = _handle
    put = _handle
    delete = _handle
    patch = _handle
    # options = _handle
    head = _handle

    async def _handle_websocket(
        self, request: web.Request, cfg: "IngressCfg", url: URL
    ) -> web.WebSocketResponse:
        """Ingress route for websocket."""
        req_protocols: Iterable[str]
        if hdrs.SEC_WEBSOCKET_PROTOCOL in request.headers:
            req_protocols = [
                str(proto.strip())
                for proto in request.headers[hdrs.SEC_WEBSOCKET_PROTOCOL].split(",")
            ]
        else:
            req_protocols = ()

        ws_server = web.WebSocketResponse(protocols=req_protocols, autoclose=False, autoping=False)
        await ws_server.prepare(request)

        # Support GET query
        if request.query_string:
            url = url.with_query(request.query_string)

        # Start proxy
        async with self._websession.ws_connect(
            url,
            headers=_init_header(request, cfg),
            protocols=req_protocols,
            autoclose=False,
            autoping=False,
        ) as ws_client:
            # Proxy requests
            ws_client = cast(web.WebSocketResponse, ws_client)
            await asyncio.wait(
                [
                    asyncio.create_task(_websocket_forward(ws_server, ws_client)),
                    asyncio.create_task(_websocket_forward(ws_client, ws_server)),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

        return ws_server

    async def _handle_request(
        self, request: web.Request, cfg: "IngressCfg", url: URL
    ) -> web.Response | web.StreamResponse:
        """Ingress route for request."""
        data = request.content
        if not request.body_exists or (
            (clen := request.headers.get(hdrs.CONTENT_LENGTH))
            and (clen := int(clen)) <= MAX_SIMPLE_REQUEST_SIZE
        ):
            data = await data.read()
        async with self._websession.request(
            request.method,
            url,
            headers=_init_header(request, cfg),
            params=request.query,
            allow_redirects=False,
            data=data,
            timeout=DISABLED_TIMEOUT,
            skip_auto_headers={hdrs.CONTENT_TYPE},
        ) as result:
            headers = _response_header(result)
            if ctype := result.headers.get(hdrs.CONTENT_TYPE):
                ctype = ctype.partition(";")[0].strip()
            else:
                ctype = "application/octet-stream"

            rewrite_body = None
            if cfg.rewrites:
                path = url.path
                for rule in cfg.rewrites:
                    if rule.path and not re.match(rule.path, path, re.I):
                        continue
                    if rule.mode == RewriteMode.HEADER:
                        for name, value in headers.items():
                            if rule.name and not re.match(rule.name, name, re.I):
                                continue
                            for i in range(len(value)):
                                value[i] = re.sub(rule.match, rule.replace, value[i])
                    elif rule.mode == RewriteMode.BODY:
                        if rule.name and not re.match(rule.name, ctype, re.I):
                            continue
                        rewrite_body = _make_rewrite(rule, rewrite_body)

            headers = CIMultiDict((k, v) for k, vs in headers.items() for v in vs if v)
            # Simple request
            if rewrite_body or must_be_empty_body(request.method, result.status):
                # Return Response
                body = await result.read()
                if rewrite_body:
                    body = rewrite_body(body)
                return web.Response(
                    headers=headers, status=result.status, content_type=ctype, body=body
                )

            # Stream response
            response = web.StreamResponse(status=result.status, headers=headers)
            response.content_type = ctype

            try:
                await response.prepare(request)
                async for data, _ in result.content.iter_chunks():
                    await response.write(data)
            except (aiohttp.ClientError, aiohttp.ClientPayloadError, ConnectionResetError) as err:
                _LOGGER.debug("Stream error with %s / %s: %s", cfg.name, url, err)
            return response


def _make_rewrite(
    rule: "RewriteCfg", rewrite_body: "Callable[[bytes], bytes] | None"
) -> "Callable[[bytes], bytes]":
    if rewrite_body is None:
        rewrite_body = lambda body: body
    return lambda body: re.sub(rule.match.encode(), rule.replace.encode(), rewrite_body(body))


@lru_cache
def _create_url(cfg: "IngressCfg", path: str) -> URL:
    """Create URL to service."""
    base_path = f"{cfg.sub_path}/"
    try:
        url = cfg.origin.join(URL(base_path + quote(path.lstrip("/"))))
    except ValueError as err:
        raise web.HTTPBadRequest from err
    if not url.path.startswith(base_path):
        raise web.HTTPBadRequest
    return url


@lru_cache(maxsize=32)
def _forwarded_for_header(forward_for: str | None, peer_name: str) -> str:
    """Create X-Forwarded-For header."""
    connected_ip = ip_address(peer_name)
    return f"{forward_for}, {connected_ip!s}" if forward_for else f"{connected_ip!s}"


def _init_header(request: web.Request, cfg: "IngressCfg") -> dict[str, str]:
    """Create initial header."""
    headers: dict[str, str] = {}
    for name, value in request.headers.items():
        name = std_header_name(name)
        if name in INIT_HEADERS_FILTER:
            continue
        if name == hdrs.COOKIE:
            if not (value := cfg.remove_token_from_cookie(value)):
                continue
        headers[name] = value
    for name, value in cfg.headers.items():
        if value != HEADER_AUTO_PH:
            headers[name] = value

    # Ingress information
    headers[X_INGRESS_PATH] = f"{API_BASE}/{cfg.name}"
    headers[X_INGRESS_SUBPATH] = cfg.sub_path

    # Set X-Forwarded-For
    assert request.transport
    if (peername := request.transport.get_extra_info("peername")) is None:
        _LOGGER.error("Can't set forward_for header, missing peername")
        raise web.HTTPBadRequest
    headers[hdrs.X_FORWARDED_FOR] = _forwarded_for_header(
        request.headers.get(hdrs.X_FORWARDED_FOR), peername[0]
    )

    # Set X-Forwarded-Host
    if not (forward_host := request.headers.get(hdrs.X_FORWARDED_HOST)):
        forward_host = request.host
    headers[hdrs.X_FORWARDED_HOST] = forward_host

    # Set X-Forwarded-Proto
    if not (forward_proto := request.headers.get(hdrs.X_FORWARDED_PROTO)):
        forward_proto = request.scheme
    headers[hdrs.X_FORWARDED_PROTO] = forward_proto

    # Replace Origin placeholder
    if hdrs.ORIGIN in headers and cfg.headers.get(hdrs.ORIGIN) == HEADER_AUTO_PH:
        headers[hdrs.ORIGIN] = f"{forward_proto}://{forward_host}"

    return headers


def _response_header(response: aiohttp.ClientResponse) -> dict[str, list[str]]:
    """Create response header."""
    headers: dict[str, list[str]] = {}
    for name, value in response.headers.items():
        name = std_header_name(name)
        if name in RESPONSE_HEADERS_FILTER:
            continue
        headers.setdefault(name, []).append(value)
    return headers


def _is_websocket(request: web.Request) -> bool:
    """Return True if request is a websocket."""
    headers = request.headers
    return bool(
        "upgrade" in headers.get(hdrs.CONNECTION, "").lower()
        and headers.get(hdrs.UPGRADE, "").lower() == "websocket"
    )


async def _websocket_forward(ws_from: web.WebSocketResponse, ws_to: web.WebSocketResponse) -> None:
    """Handle websocket message directly."""
    try:
        async for msg in ws_from:
            if msg.type is WSMsgType.TEXT:
                await ws_to.send_str(msg.data)
            elif msg.type is WSMsgType.BINARY:
                await ws_to.send_bytes(msg.data)
            elif msg.type is WSMsgType.PING:
                await ws_to.ping()
            elif msg.type is WSMsgType.PONG:
                await ws_to.pong()
            elif ws_to.closed:
                await ws_to.close(code=ws_to.close_code, message=msg.extra)  # type: ignore
    except RuntimeError:
        _LOGGER.debug("Ingress Websocket runtime error")
    except ConnectionResetError:
        _LOGGER.debug("Ingress Websocket Connection Reset")


def _init():
    from multidict import istr

    special_hdrs = {}
    for name in dir(hdrs):
        if type(value := getattr(hdrs, name)) != istr or (key := value.title()) == value:
            continue
        special_hdrs[key] = value

    def std_header_name(name: str):
        name = name.title()
        return special_hdrs.get(name, name)

    return std_header_name


std_header_name = _init()
