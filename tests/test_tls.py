"""Test certificate validation and isolated TLS policies against real local servers."""

import asyncio
import socket
import ssl
from unittest.mock import Mock, patch

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest

from custom_components.ingress import CONFIG_SCHEMA, _parse_config, setup_domain
from custom_components.ingress.config import IngressStore
from custom_components.ingress.const import DOMAIN
from custom_components.ingress.ingress import IngressView
from custom_components.ingress.tls import InvalidTLS, tls_context


def panel(**settings):
    return {"url": "https://localhost", **settings}


def test_secure_default_and_private_custom_trust(tls_certificates):
    assert tls_context(panel()) is True
    assert tls_context(panel(tls_mode="system", tls_certificate="")) is True
    with (
        patch.object(ssl.SSLContext, "load_default_certs", side_effect=AssertionError("File I/O")),
        patch.object(ssl.SSLContext, "set_default_verify_paths", side_effect=AssertionError("File I/O")),
    ):
        first = tls_context(panel(tls_mode="custom", tls_certificate=tls_certificates["ca"]))
        second = tls_context(panel(tls_mode="custom", tls_certificate=tls_certificates["ca"] + tls_certificates["valid"]))
    assert first is not second
    assert first.check_hostname
    assert first.verify_mode == ssl.CERT_REQUIRED
    assert first.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN
    assert len(first.get_ca_certs()) == 1
    assert tls_context(panel(tls_mode="disabled")) is False


@pytest.mark.parametrize("pem", [
    "", " \n", "not a certificate", "-----BEGIN CERTIFICATE-----\ninvalid\n-----END CERTIFICATE-----",
    "ca+invalid", "ca+key", "ca+junk",
])
def test_invalid_pem_rejected(pem, tls_certificates):
    if pem.startswith("ca+"):
        suffix = {"ca+invalid": "-----BEGIN CERTIFICATE-----\ninvalid\n-----END CERTIFICATE-----",
                  "ca+key": tls_certificates["key"], "ca+junk": "junk"}[pem]
        pem = tls_certificates["ca"] + suffix
    config = CONFIG_SCHEMA({DOMAIN: {"app": panel(tls_mode="custom", tls_certificate=pem)}})
    with pytest.raises(InvalidTLS, match="valid PEM"):
        _parse_config(Mock(), config)


@pytest.mark.parametrize("settings", [
    {"url": "http://localhost"}, {"work_mode": "iframe"}, {"work_mode": "auth"},
    {"work_mode": "hassio"}, {"work_mode": "custom"}, {"tls_mode": "unknown"},
])
def test_non_proxy_tls_options_rejected(settings):
    with pytest.raises(InvalidTLS, match="HTTPS ingress or subapp"):
        tls_context(panel(**({"tls_mode": "disabled"} | settings)))


@pytest.fixture
async def tls_server(hass, tmp_path, tls_certificates, socket_enabled):
    """Run local HTTPS and WSS endpoints using a requested certificate."""
    servers = []
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()

    def handle_exception(loop, context):
        # Rejected TLS handshakes reset the fixture's incoming server transport.
        if (context.get("message") == "Error on transport creation for incoming connection"
                and isinstance(context.get("exception"), ConnectionResetError)):
            return
        previous_handler(loop, context)

    loop.set_exception_handler(handle_exception)

    async def create(name):
        def context():
            certificate = tmp_path / f"{name}.pem"
            key = tmp_path / "key.pem"
            certificate.write_text(tls_certificates[name])
            key.write_text(tls_certificates["key"])
            result = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            result.load_cert_chain(certificate, key)
            return result

        async def response(request):
            return web.Response(text="trusted", headers={"X-Received-Auth": request.headers.get("Authorization", "")})

        async def websocket(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            await ws.send_str("trusted")
            async for message in ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    await ws.send_str(message.data)
            return ws

        app = web.Application()
        app.router.add_get("/", response)
        app.router.add_get("/ws", websocket)
        server = TestServer(app, scheme="https")
        await server.start_server(ssl=await hass.async_add_executor_job(context))
        servers.append(server)
        return server.make_url("/").with_host("localhost")

    yield create
    for server in servers:
        await server.close()
    loop.set_exception_handler(previous_handler)


@pytest.mark.parametrize("server_certificate,trust,success", [
    ("valid", "ca", True), ("valid", "valid", True), ("valid", "ca+valid", True),
    ("self_signed", "self_signed", True),
    ("wrong_host", "ca", False), ("wrong_host", "wrong_host", False),
    ("expired", "ca", False), ("expired", "expired", False),
    ("self_signed", "ca", False),
])
async def test_custom_tls_verifies_server_identity(tls_server, tls_certificates, server_certificate, trust, success):
    url = await tls_server(server_certificate)
    pem = "".join(tls_certificates[name] for name in trust.split("+"))
    context = tls_context(panel(url=str(url), tls_mode="custom", tls_certificate=pem))
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(family=socket.AF_INET)) as session:
        if not success:
            with pytest.raises(aiohttp.ClientConnectorCertificateError) as error:
                await session.get(url, ssl=context)
            if server_certificate == "wrong_host":
                assert error.value.certificate_error.verify_code == 62
            elif server_certificate == "expired":
                assert error.value.certificate_error.verify_code == 10
            return
        async with session.get(url, ssl=context) as response:
            assert await response.text() == "trusted"
        async with session.ws_connect(url.joinpath("ws"), ssl=context) as ws:
            assert (await ws.receive()).data == "trusted"


@pytest.mark.parametrize("mode", ["custom", "disabled"])
async def test_proxy_http_and_websocket_keep_other_panels_secure(
    hass, tls_server, tls_certificates, aiohttp_client, mode,
):
    """The real proxy shares its HA session, but never shares a panel's TLS policy."""
    url = (await tls_server("self_signed")).with_host("127.0.0.1")
    config = CONFIG_SCHEMA({DOMAIN: {
        "secure": panel(url=str(url), static_token="secure-token"),
        "custom": panel(url=str(url), static_token="custom-token", tls_mode=mode,
                        tls_certificate=tls_certificates["self_signed"], headers={"Authorization": "secret"}),
        "child": panel(url=str(url), static_token="child-token", work_mode="subapp", parent="custom"),
        "custom_child": panel(url=str(url), static_token="custom_child-token", work_mode="subapp", parent="custom",
                              tls_mode=mode, tls_certificate=tls_certificates["self_signed"]),
    }})
    store = IngressStore()
    await setup_domain(hass, {"config": store, "panels": set()}, config)
    session = async_get_clientsession(hass)
    original_ssl = session.connector._ssl
    with patch.object(session, "request", wraps=session.request) as http:
        view = IngressView(hass, store, session)
        app = web.Application()

        async def proxy(request):
            return await view._handle(request, **request.match_info)

        app.router.add_route("*", "/api/ingress/{name}/{path:.*}", proxy)
        client = await aiohttp_client(app)
        with patch.object(session, "ws_connect", wraps=session.ws_connect) as websocket:
            for slug in ("secure", "custom", "child", "custom_child", "secure"):
                async with client.get(f"/api/ingress/{slug}/", cookies={"ingress_token": f"t-{slug}-token"}) as response:
                    assert response.status == (200 if slug in ("custom", "custom_child") else 502)
                    if slug in ("custom", "custom_child"):
                        assert await response.text() == "trusted"
                    if slug == "custom":
                        assert response.headers["X-Received-Auth"] == "secret"
                assert http.call_args.kwargs["ssl"] is store.get(slug).ssl
            for slug in ("custom", "custom_child"):
                async with client.ws_connect(f"/api/ingress/{slug}/ws", headers={"Cookie": f"ingress_token=t-{slug}-token"}) as ws:
                    assert (await ws.receive()).data == "trusted"
                    await ws.send_str("echo")
                    assert (await ws.receive()).data == "echo"
                    assert websocket.call_args.kwargs["ssl"] is store.get(slug).ssl
            assert store.get("secure").ssl is True
            assert store.get("child").ssl is True
            assert session.connector._ssl is original_ssl


async def test_invalid_runtime_update_preserves_existing_panels(hass):
    data = {"config": IngressStore(), "panels": set()}
    await setup_domain(hass, data, CONFIG_SCHEMA({DOMAIN: {"app": panel()}}))
    old = data["config"].get("app")
    with pytest.raises(InvalidTLS, match="valid PEM"):
        await setup_domain(hass, data, CONFIG_SCHEMA({DOMAIN: {"app": panel(tls_mode="custom")}}))
    assert data["config"].get("app") is old
