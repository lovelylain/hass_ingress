"""Test configuration ownership and the panel lifecycle."""

from copy import deepcopy
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components import frontend
from homeassistant.const import CONF_MODE, CONF_URL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ingress import (
    CONFIG_SCHEMA,
    async_setup,
    async_setup_entry,
    async_unload_entry,
    setup_domain,
    async_migrate_entry,
    _panel_subentry,
    _subentry_panels,
)
from custom_components.ingress.const import DOMAIN, ConfMode


@pytest.fixture
def http(hass):
    """Replace only the HTTP server boundary; use the real runtime and services."""
    hass.http = Mock()
    hass.http.async_register_static_paths = AsyncMock()
    with patch("custom_components.ingress.get_version", return_value="1.3.2"):
        yield hass.http


async def test_ui_setup_reload_and_restart(hass, http):
    """Stored panels remain authoritative, including after deleting the last panel."""
    saved = {
        "router": {
            CONF_URL: "http://192.168.1.1",
            "title": "Router",
            "rewrite": [{"mode": "body", "match": "/api/", "replace": "$http_x_ingress_path/"}],
        }
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MODE: ConfMode.UI},
        version=2,
        subentries_data=[_panel_subentry(slug, panel).as_dict() for slug, panel in saved.items()],
    )
    entry.add_to_hass(hass)
    frontend.async_register_built_in_panel(hass, "config")

    with (
        patch("homeassistant.helpers.reload.async_integration_yaml_config") as yaml,
        patch.object(hass.config_entries, "async_reload", return_value=True),
    ):
        assert await async_setup(hass, CONFIG_SCHEMA({DOMAIN: {"ignored": {CONF_URL: "old:80"}}}))
        assert await async_setup_entry(hass, entry)
        assert "router" in hass.data[frontend.DATA_PANELS]
        assert "ignored" not in hass.data[frontend.DATA_PANELS]
        store = hass.data[DOMAIN]["config"]
        old_token = store.get("router").token["value"]
        old_session = store.generate_user_token({"id": "user"})
        assert store.get("router").rewrites[0].replace == "/api/ingress/router/"
        assert _subentry_panels(entry) == saved

        assert await async_unload_entry(hass, entry)
        assert "router" not in hass.data[frontend.DATA_PANELS]
        assert "config" in hass.data[frontend.DATA_PANELS]
        assert store.check_token(hass, old_token)[0] is None
        assert store.check_user_token(old_session) is None
        assert await async_setup_entry(hass, entry)
        assert "router" in hass.data[frontend.DATA_PANELS]
        assert store.get("router").token["value"] != old_token
        assert _subentry_panels(entry) == saved

        hass.config_entries.async_remove_subentry(entry, next(iter(entry.subentries)))
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
        assert store.get("router") is None
        assert "router" not in hass.data[frontend.DATA_PANELS]
        assert "config" in hass.data[frontend.DATA_PANELS]
        yaml.assert_not_called()
        await hass.async_block_till_done()


async def test_dynamic_url_is_not_mutated(hass, http):
    """Parsing must not modify saved frontend URL rules."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, data={CONF_MODE: ConfMode.UI},
        subentries_data=[_panel_subentry("router", {
            CONF_URL: {"match": "hass", "replace": "router", "default": "http://router/"},
            "work_mode": "iframe",
        }).as_dict()],
    )
    entry.add_to_hass(hass)
    original = deepcopy(_subentry_panels(entry))
    assert await async_setup_entry(hass, entry)
    assert _subentry_panels(entry) == original
    assert "router" in hass.data[frontend.DATA_PANELS]


async def test_yaml_entry_reloads_current_file(hass, http):
    """YAML setup and service reload use the YAML source."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MODE: ConfMode.YAML})
    entry.add_to_hass(hass)
    yaml_config = CONFIG_SCHEMA({DOMAIN: {"router": {CONF_URL: "router:80"}}})
    with patch(
        "homeassistant.helpers.reload.async_integration_yaml_config",
        return_value=yaml_config,
    ) as yaml:
        assert await async_setup_entry(hass, entry)
        assert "router" in hass.data[frontend.DATA_PANELS]
        yaml.return_value = CONFIG_SCHEMA({DOMAIN: {"other": {CONF_URL: "other:80"}}})
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
        assert "router" not in hass.data[frontend.DATA_PANELS]
        assert "other" in hass.data[frontend.DATA_PANELS]
        assert yaml.await_count == 2


async def test_empty_setup_does_not_import_yaml(hass, http):
    """Adding the integration from the UI must not create a competing YAML entry."""
    with patch.object(hass.config_entries.flow, "async_init") as flow:
        assert await async_setup(hass, {})
        await hass.async_block_till_done()
        flow.assert_not_called()


async def test_yaml_setup_starts_import(hass, http):
    """Existing YAML installations still create their integration entry."""
    with patch.object(hass.config_entries.flow, "async_init", new_callable=AsyncMock) as flow:
        assert await async_setup(hass, CONFIG_SCHEMA({DOMAIN: {"router": {CONF_URL: "router:80"}}}))
        await hass.async_block_till_done()
        flow.assert_awaited_once_with(DOMAIN, context={"source": "import"})


async def test_unload_disconnects_agent(hass, http):
    """Unloading also disconnects the agent and removes only owned panels."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MODE: ConfMode.UI}, version=2)
    assert await async_setup_entry(hass, entry)
    data = hass.data[DOMAIN]
    client = data["client"] = Mock()
    await setup_domain(hass, data, CONFIG_SCHEMA({DOMAIN: {"router": {CONF_URL: "router:80"}}}))
    assert await async_unload_entry(hass, entry)
    client.disconnect.assert_called_once()
    assert "client" not in data
    assert not data["panels"]
    assert data["config"].get("router") is None


async def test_native_rename_sidebar_toggle_and_orphan_recovery(hass, http):
    from homeassistant.helpers import issue_registry as ir

    panels = {
        "root": {"url": "root:80", "title": "Root"},
        "root_child": {"url": "child:80", "parent": "root", "work_mode": "ingress", "title": "Child", "static_token": "child-public"},
        "root_child_tab": {"url": "tab:80", "parent": "root_child", "work_mode": "subapp", "title": "Tab"},
        "other": {"url": "other:80", "title": "Other"},
    }
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, data={CONF_MODE: ConfMode.UI},
        subentries_data=[_panel_subentry(slug, panel).as_dict() for slug, panel in panels.items()],
    )
    entry.add_to_hass(hass)
    assert await async_setup_entry(hass, entry)
    root = next(subentry for subentry in entry.subentries.values() if subentry.unique_id == "root")
    # Exercise native persistence changes against the real runtime; reload through
    # the service here because setup is called directly rather than by the manager.
    with patch.object(hass.config_entries, "async_reload", return_value=True):
        hass.config_entries.async_update_subentry(entry, root, title="Renamed")
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
        assert hass.data[frontend.DATA_PANELS]["root"].sidebar_title == "Renamed"
        hass.config_entries.async_update_subentry(entry, root, data={**root.data, "show_in_sidebar": False})
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
        assert hass.data[frontend.DATA_PANELS]["root"].sidebar_title is None
        store = hass.data[DOMAIN]["config"]
        assert store.get("root_child") is not None
        child_token = store.get("root_child").token["value"]
        assert store.check_token(hass, child_token)[0] is not None
        hass.config_entries.async_remove_subentry(entry, root.subentry_id)
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
        assert store.get("root") is None and store.get("root_child") is None
        assert store.get("root_child_tab") is None
        assert store.check_token(hass, child_token)[0] is None
        assert store.get("other") is not None
        assert "root" not in hass.data[frontend.DATA_PANELS]
        assert len(entry.subentries) == 3
        issue_id = f"missing_parent_{entry.entry_id}"
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
        hass.config_entries.async_add_subentry(entry, _panel_subentry("root", panels["root"]))
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
        assert store.get("root_child") is not None
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
        await hass.async_block_till_done()


async def test_migrates_first_trial_panels_once_without_mutating_values(hass):
    panels = {"hidden": {"url": "app:80", "headers": {"Authorization": "secret"}, "static_token": "public"},
              "shown": {"url": "shown:80", "title": "Shown"}}
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MODE: ConfMode.UI}, options={"panels": deepcopy(panels)})
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2 and entry.options == {}
    assert _subentry_panels(entry) == panels
    hidden = next(subentry for subentry in entry.subentries.values() if subentry.unique_id == "hidden")
    assert hidden.title == "hidden" and not hidden.data["show_in_sidebar"]
    assert await async_migrate_entry(hass, entry)
    assert len(entry.subentries) == 2
