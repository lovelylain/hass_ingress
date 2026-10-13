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
)
from custom_components.ingress.const import CONF_PANELS, DOMAIN, ConfMode


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
        options={CONF_PANELS: deepcopy(saved)},
    )
    entry.add_to_hass(hass)
    frontend.async_register_built_in_panel(hass, "config")

    with patch("homeassistant.helpers.reload.async_integration_yaml_config") as yaml:
        assert await async_setup(hass, CONFIG_SCHEMA({DOMAIN: {"ignored": {CONF_URL: "old:80"}}}))
        assert await async_setup_entry(hass, entry)
        assert "router" in hass.data[frontend.DATA_PANELS]
        assert "ignored" not in hass.data[frontend.DATA_PANELS]
        store = hass.data[DOMAIN]["config"]
        old_token = store.get("router").token["value"]
        old_session = store.generate_user_token({"id": "user"})
        assert store.get("router").rewrites[0].replace == "/api/ingress/router/"
        assert entry.options[CONF_PANELS] == saved

        assert await async_unload_entry(hass, entry)
        assert "router" not in hass.data[frontend.DATA_PANELS]
        assert "config" in hass.data[frontend.DATA_PANELS]
        assert store.check_token(hass, old_token)[0] is None
        assert store.check_user_token(old_session) is None
        assert await async_setup_entry(hass, entry)
        assert "router" in hass.data[frontend.DATA_PANELS]
        assert store.get("router").token["value"] != old_token
        assert entry.options[CONF_PANELS] == saved

        hass.config_entries.async_update_entry(entry, options={CONF_PANELS: {}})
        await hass.services.async_call(DOMAIN, "reload", blocking=True)
        assert store.get("router") is None
        assert "router" not in hass.data[frontend.DATA_PANELS]
        assert "config" in hass.data[frontend.DATA_PANELS]
        yaml.assert_not_called()


async def test_dynamic_url_is_not_mutated(hass, http):
    """Parsing must not modify saved frontend URL rules."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MODE: ConfMode.UI},
        options={CONF_PANELS: {
            "router": {
                CONF_URL: {"match": "hass", "replace": "router", "default": "http://router/"},
                "work_mode": "iframe",
            }
        }},
    )
    entry.add_to_hass(hass)
    original = deepcopy(dict(entry.options))
    assert await async_setup_entry(hass, entry)
    assert entry.options == original
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
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MODE: ConfMode.UI}, options={CONF_PANELS: {}})
    assert await async_setup_entry(hass, entry)
    data = hass.data[DOMAIN]
    client = data["client"] = Mock()
    await setup_domain(hass, data, CONFIG_SCHEMA({DOMAIN: {"router": {CONF_URL: "router:80"}}}))
    assert await async_unload_entry(hass, entry)
    client.disconnect.assert_called_once()
    assert "client" not in data
    assert not data["panels"]
    assert data["config"].get("router") is None
