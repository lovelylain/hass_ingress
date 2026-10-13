"""Exercise native Home Assistant config and options flow managers."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.data_entry_flow import FlowManagerIndexView
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ingress import CONFIG_SCHEMA
from custom_components.ingress.config_flow import _panel_form
from custom_components.ingress.const import CONF_PANELS, DOMAIN, ConfMode
from custom_components.ingress.config import RewriteCfg
from custom_components.ingress.ingress import _make_rewrite


@pytest.fixture(autouse=True)
async def setup_boundary(hass):
    """Keep real HA flows; mock integration runtime/network at their boundary."""
    with (
        patch("custom_components.ingress.async_setup", return_value=True),
        patch("custom_components.ingress.async_setup_entry", return_value=True),
        patch("custom_components.ingress.async_unload_entry", return_value=True),
    ):
        yield
        for entry in hass.config_entries.async_entries(DOMAIN):
            await hass.config_entries.async_unload(entry.entry_id)


def add_entry(hass, panels=None, mode=ConfMode.UI, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"mode": mode},
        options=options if options is not None else {CONF_PANELS: panels or {}},
    )
    entry.add_to_hass(hass)
    return entry


async def start_options(hass, entry, action):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": action})


async def start_import(hass, entry):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
    )
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": ConfMode.UI})


async def test_initial_ui_and_singleton(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["data_schema"]({})["mode"] == ConfMode.UI
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": ConfMode.UI})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"mode": ConfMode.UI}
    assert result["result"].options == {CONF_PANELS: {}}
    await hass.async_block_till_done()
    duplicate = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert duplicate["reason"] == "single_instance_allowed"


async def test_crud_last_panel_and_automatic_reload(hass):
    entry = add_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        result = await start_options(hass, entry, "add")
        result = await hass.config_entries.options.async_configure(result["flow_id"], {
            "slug": "router", "title": "Router", "url": "router:8080", "require_admin": True,
        })
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        assert entry.options[CONF_PANELS]["router"]["require_admin"]
        assert reload.call_count == 1
        result = await start_options(hass, entry, "edit")
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"panel": "router"})
        assert "slug" not in result["data_schema"].schema
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"title": "New router", "url": "new:8080"})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        assert entry.options[CONF_PANELS]["router"]["title"] == "New router"
        assert reload.call_count == 2
        result = await start_options(hass, entry, "remove")
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"panel": "router"})
        assert result["step_id"] == "remove_confirm"
        assert "router" in entry.options[CONF_PANELS]
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"confirm": True})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        assert entry.options[CONF_PANELS] == {}
        assert reload.call_count == 3


async def test_graphical_schema_serializes(hass):
    entry = add_entry(hass)
    result = await start_options(hass, entry, "add")
    prepared = FlowManagerIndexView(hass.config_entries.options)._prepare_result_json(result)
    json.dumps(prepared)
    fields = {field["name"]: field for field in prepared["data_schema"]}
    assert "text" in fields["slug"]["selector"]
    assert fields["advanced"]["type"] == "expandable"
    advanced = {field["name"]: field for field in fields["advanced"]["schema"]}
    for name in ("headers", "rewrite"):
        config = advanced[name]["selector"]["object"]
        assert config["multiple"]
        assert config["fields"]
        assert all("default" not in field for field in config["fields"].values())
    headers = advanced["headers"]["selector"]["object"]
    assert headers["label_field"] == "name"
    assert "description_field" not in headers
    assert headers["fields"]["value"]["selector"] == {"text": {"type": "password", "multiline": False, "multiple": False}}
    replacement = advanced["rewrite"]["selector"]["object"]["fields"]["replace"]
    assert not replacement.get("required", False)


@pytest.mark.parametrize("replacement", [{}, {"replace": ""}])
async def test_empty_rewrite_replacement(hass, replacement):
    """The graphical editor must allow rules that remove matched text."""
    entry = add_entry(hass)
    result = await start_options(hass, entry, "add")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "slug": "app", "url": "app:80",
        "advanced": {"rewrite": [{"mode": "body", "match": "prefix/", **replacement}]},
    })
    assert result["type"] is FlowResultType.CREATE_ENTRY
    rule = entry.options[CONF_PANELS]["app"]["rewrite"][0]
    assert rule["replace"] == ""
    assert _make_rewrite(RewriteCfg(**rule), None)(b"prefix/path") == b"path"


async def test_advanced_roundtrip_and_clear_optional(hass):
    original = CONFIG_SCHEMA({DOMAIN: {"app": {
        "title": "App", "icon": "mdi:web", "require_admin": True,
        "url": {"default": "http://app", "match": r"(?<host>.*)", "replace": "https://$<host>/$12"},
        "work_mode": "iframe", "ui_mode": "toolbar", "index": "start", "cookie_name": "app_cookie",
        "static_token": "public-token", "expire_time": 123,
        "headers": {"Authorization": "secret", "X-App": "value"},
        "rewrite": [{"mode": "header", "path": "^/", "name": "Location", "match": "(old)", "replace": r"\1/new"}, {"mode": "body", "match": "old", "replace": "new"}],
    }}})[DOMAIN]
    entry = add_entry(hass, original)
    result = await start_options(hass, entry, "edit")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"panel": "app"})
    form = _panel_form(original["app"])
    url_marker = next(key for key in result["data_schema"].schema if key == "url")
    assert url_marker.description["suggested_value"] == "http://app"
    result = await hass.config_entries.options.async_configure(result["flow_id"], form)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_PANELS] == original
    result = await start_options(hass, entry, "edit")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"panel": "app"})
    # Suggested values must not become defaults and resurrect cleared fields.
    cleaned = result["data_schema"]({"url": "/local/app", "icon": "", "advanced": {"work_mode": "iframe", "headers": [], "rewrite": []}})
    assert "cookie_name" not in cleaned["advanced"]
    result = await hass.config_entries.options.async_configure(result["flow_id"], cleaned)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    saved = entry.options[CONF_PANELS]["app"]
    assert saved["url"] == "/local/app"
    assert "icon" not in saved and "static_token" not in saved and "cookie_name" not in saved
    assert saved["headers"] == {} and saved["rewrite"] == []


@pytest.mark.parametrize(("input", "error"), [
    ({"url": ""}, "invalid_panel"),
    ({"url": "ftp://host"}, "invalid_url"),
    ({"slug": "Bad slug"}, "invalid_panel"),
    ({"advanced": {"headers": [{"name": "X-App", "value": "a"}, {"name": "x-app", "value": "b"}]}}, "duplicate_headers"),
    ({"advanced": {"headers": [{"name": "X-App", "value": "a\r\nb"}]}}, "invalid_headers"),
    ({"advanced": {"headers": [{"name": "Bad header", "value": "a"}]}}, "invalid_headers"),
    ({"advanced": {"cookie_name": "bad;cookie"}}, "invalid_token"),
    ({"advanced": {"static_token": "token\r\n"}}, "invalid_token"),
    ({"advanced": {"parent": "missing"}}, "invalid_parent"),
    ({"advanced": {"work_mode": "subapp"}}, "invalid_parent"),
    ({"advanced": {"url_replace": "http://app"}}, "invalid_regex"),
    ({"advanced": {"rewrite": [{"mode": "body", "match": "[", "replace": "x"}]}}, "invalid_regex"),
    ({"advanced": {"rewrite": [{"mode": "header", "match": "(a)", "replace": r"\2"}]}}, "invalid_regex"),
    ({"advanced": {"rewrite": [{"mode": "body", "path": "[", "match": "x", "replace": "y"}]}}, "invalid_regex"),
])
async def test_invalid_values_do_not_save(hass, input, error):
    entry = add_entry(hass)
    result = await start_options(hass, entry, "add")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"slug": "app", "url": "app:80", **input})
    assert result["errors"] == {"base": error}
    assert entry.options[CONF_PANELS] == {}


async def test_duplicate_panel_and_foreign_route(hass):
    entry = add_entry(hass, {"app": {"url": "app:80"}})
    result = await start_options(hass, entry, "add")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"slug": "app", "url": "other:80"})
    assert result["errors"] == {"slug": "duplicate_panel"}
    hass.data[DATA_PANELS] = {"config": object(), "app": object()}
    hass.data[DOMAIN] = {"panels": {"app"}}
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"slug": "config", "url": "other:80"})
    assert result["errors"] == {"base": "route_conflict"}
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"slug": "new", "url": "other:80"})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_parent_delete_and_route_alias(hass):
    panels = {"root": {"url": "root:80"}, "root_child": {"url": "child:80", "parent": "root", "work_mode": "subapp"}}
    entry = add_entry(hass, panels)
    result = await start_options(hass, entry, "remove")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"panel": "root"})
    assert result["errors"] == {"base": "parent_has_children"}
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"confirm": True})
    assert result["errors"] == {"base": "parent_has_children"}
    assert entry.options[CONF_PANELS] == panels
    result = await start_options(hass, entry, "add")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"slug": "child", "url": "other:80", "advanced": {"parent": "root"}})
    assert result["errors"] == {"base": "route_conflict"}


async def test_remove_cancelled(hass):
    entry = add_entry(hass, {"app": {"url": "app:80"}})
    result = await start_options(hass, entry, "remove")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"panel": "app"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"confirm": False})
    assert result["reason"] == "remove_cancelled"
    assert "app" in entry.options[CONF_PANELS]


async def test_yaml_import_cancel_then_success(hass):
    entry = add_entry(hass, mode=ConfMode.YAML, options={})
    yaml_panels = {"app": {"url": "http://app", "headers": {"Authorization": "resolved-secret"}}}
    with patch("custom_components.ingress.config_flow.async_integration_yaml_config", return_value={DOMAIN: yaml_panels}) as loader:
        result = await start_import(hass, entry)
        assert result["step_id"] == "import_yaml"
        assert entry.data["mode"] == ConfMode.YAML and entry.options == {}
        hass.config_entries.flow.async_abort(result["flow_id"])
        loader.assert_not_called()
        result = await start_import(hass, entry)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"confirm": False})
        assert result["reason"] == "import_cancelled"
        loader.assert_not_called()
        result = await start_import(hass, entry)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"confirm": True})
        assert result["reason"] == "reconfigure_successful"
        assert entry.data["mode"] == ConfMode.UI
        assert entry.options[CONF_PANELS] == CONFIG_SCHEMA({DOMAIN: yaml_panels})[DOMAIN]
        assert entry.options[CONF_PANELS]["app"]["headers"]["Authorization"] == "resolved-secret"
        loader.assert_awaited_once()
    await hass.async_block_till_done()


@pytest.mark.parametrize("failure", [None, OSError("unreadable"), {DOMAIN: {"app": {"url": "ftp://host"}}}])
async def test_yaml_import_failure(hass, failure):
    entry = add_entry(hass, mode=ConfMode.YAML, options={})
    result = await start_import(hass, entry)
    kwargs = {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}
    with patch("custom_components.ingress.config_flow.async_integration_yaml_config", **kwargs):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"confirm": True})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] in ("yaml_load_failed", "invalid_url")
    assert entry.data["mode"] == ConfMode.YAML and entry.options == {}


async def test_empty_map_survives_mode_switch_without_import(hass):
    entry = add_entry(hass, mode=ConfMode.YAML, options={CONF_PANELS: {}})
    with patch("custom_components.ingress.config_flow.async_integration_yaml_config") as loader:
        result = await start_import(hass, entry)
        assert result["reason"] == "reconfigure_successful"
        assert entry.options[CONF_PANELS] == {}
        loader.assert_not_called()
    await hass.async_block_till_done()


async def test_stale_options_and_mode_write(hass):
    entry = add_entry(hass)
    result = await start_options(hass, entry, "add")
    hass.config_entries.async_update_entry(entry, options={CONF_PANELS: {"other": {"url": "other:80"}}})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"slug": "app", "url": "app:80"})
    assert result["reason"] == "configuration_changed"
    assert set(entry.options[CONF_PANELS]) == {"other"}
    result = await start_options(hass, entry, "add")
    hass.config_entries.async_update_entry(entry, data={"mode": ConfMode.YAML})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"slug": "app", "url": "app:80"})
    assert result["reason"] == "configuration_changed"
    assert set(entry.options[CONF_PANELS]) == {"other"}


async def test_stale_yaml_import(hass):
    entry = add_entry(hass, mode=ConfMode.YAML, options={})
    result = await start_import(hass, entry)
    hass.config_entries.async_update_entry(entry, options={CONF_PANELS: {"later": {"url": "later:80"}}})
    with patch("custom_components.ingress.config_flow.async_integration_yaml_config", return_value={DOMAIN: {"old": {"url": "old:80"}}}):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"confirm": True})
    assert result["reason"] == "configuration_changed"
    assert entry.data["mode"] == ConfMode.YAML
    assert set(entry.options[CONF_PANELS]) == {"later"}


@pytest.mark.parametrize(("mode", "reason"), [(ConfMode.AGENT, "agent_options"), (ConfMode.YAML, "yaml_options")])
async def test_external_options_explain_reconfigure(hass, mode, reason):
    entry = add_entry(hass, mode=mode)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["reason"] == reason


@pytest.mark.parametrize(("mode", "url"), [("iframe", "/local/app"), ("custom", "/local/app.js"), ("hassio", "core_configurator")])
async def test_mode_specific_urls(hass, mode, url):
    entry = add_entry(hass)
    result = await start_options(hass, entry, "add")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"slug": "app", "url": url, "advanced": {"work_mode": mode}})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_PANELS]["app"]["url"] == url


@pytest.mark.parametrize("input", [
    {"url": "/local/app"},
    {"url": "http://addon", "advanced": {"work_mode": "hassio"}},
    {"advanced": {"parent": "app"}},
    {"advanced": {"parent": "root", "work_mode": "subapp"}},
    {"advanced": {"expire_time": 1.5}},
])
async def test_invalid_mode_parent_and_lifetime(hass, input):
    entry = add_entry(hass, {"root": {"url": "/local/root", "work_mode": "iframe"}})
    result = await start_options(hass, entry, "add")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"slug": "app", "url": "app:80", **input})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] in ("invalid_url", "invalid_parent", "invalid_panel")
    assert set(entry.options[CONF_PANELS]) == {"root"}


async def test_yaml_mode_keeps_ui_panels(hass):
    panels = {"app": {"url": "app:80"}}
    entry = add_entry(hass, panels)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": ConfMode.YAML})
    assert result["reason"] == "reconfigure_successful"
    assert entry.options[CONF_PANELS] == panels
    with patch("custom_components.ingress.config_flow.async_integration_yaml_config") as loader:
        result = await start_import(hass, entry)
        assert result["reason"] == "reconfigure_successful"
        loader.assert_not_called()
    assert entry.options[CONF_PANELS] == panels
    await hass.async_block_till_done()


async def test_agent_connection_flow_preserved(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": ConfMode.AGENT})
    assert result["step_id"] == "my_agent"
    with patch("custom_components.ingress.client.create_client") as factory:
        client = factory.return_value
        client.connect = AsyncMock()
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": "agent:8080/"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"mode": ConfMode.AGENT, "url": "http://agent:8080"}
    client.connect.assert_awaited_once()
    client.disconnect.assert_called_once()
    await hass.async_block_till_done()
