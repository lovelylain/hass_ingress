"""Exercise the path taken on cores without config subentry support.

The Home Assistant version used to run these tests always supports subentries,
so the tests switch the storage backend off explicitly and drive the options
flow the way an older core would. The forms, validation and stored fields have
to stay identical to the subentry flow.
"""

from pathlib import Path
import subprocess
import sys
import textwrap
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant import config_entries
from homeassistant.components import frontend
from homeassistant.const import CONF_MODE
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ingress import (
    CONFIG_SCHEMA,
    async_migrate_entry,
    async_setup_entry,
)
from custom_components.ingress import compat
from custom_components.ingress.config_flow import IngressConfigFlow, IngressOptionsFlow
from custom_components.ingress.const import CONF_PANELS, DOMAIN, ConfMode
from custom_components.ingress.panels import get_panels, option_records, replace_panels, subentry


@pytest.fixture(autouse=True)
def legacy_core(monkeypatch):
    """Pretend the running core has no config subentry support."""
    monkeypatch.setattr(compat, "SUPPORTS_SUBENTRIES", False)
    monkeypatch.setattr(
        IngressConfigFlow,
        "async_get_options_flow",
        staticmethod(lambda config_entry: IngressOptionsFlow()),
        raising=False,
    )


def add_entry(hass, panels=None, mode=ConfMode.UI):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_MODE: mode},
        options={CONF_PANELS: panels} if panels is not None else {},
    )
    entry.add_to_hass(hass)
    return entry


async def start_options(hass, entry):
    return await hass.config_entries.options.async_init(entry.entry_id)


async def submit(hass, flow_id, user_input):
    return await hass.config_entries.options.async_configure(flow_id, user_input)


async def test_options_flow_is_registered(hass):
    """The core must be offered the options flow instead of subentries."""
    assert IngressConfigFlow.async_supports_options_flow(MockConfigEntry(domain=DOMAIN))


async def test_backends_parse_identically(hass):
    """Options storage must expose exactly what subentries expose."""
    panels = {
        "root": {"url": "root:80", "title": "Root"},
        "root_child": {"url": "child:80", "parent": "root", "title": "Child"},
        "hidden": {"url": "hidden:80"},
    }
    subentry_entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_MODE: ConfMode.UI},
        subentries_data=[subentry(slug, panel).as_dict() for slug, panel in panels.items()],
    )
    subentry_entry.add_to_hass(hass)
    with patch.object(compat, "SUPPORTS_SUBENTRIES", True):
        expected = get_panels(subentry_entry)

    options_entry = add_entry(hass)
    replace_panels(hass, options_entry, panels)
    assert get_panels(options_entry) == expected
    assert set(option_records(options_entry)) == set(panels)
    assert option_records(options_entry)["hidden"]["show_in_sidebar"] is False
    assert option_records(options_entry)["root"]["show_in_sidebar"] is True


async def test_options_flow_add_edit_delete(hass):
    """The full panel lifecycle works through the entry options."""
    entry = add_entry(hass)
    result = await start_options(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add"
    result = await submit(
        hass,
        result["flow_id"],
        {
            "slug": "router",
            "title": "Router",
            "url": "router:8080",
            "require_admin": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    saved = get_panels(entry)
    assert saved["router"]["url"] == "router:8080"
    assert saved["router"]["require_admin"] is True
    assert saved["router"]["title"] == "Router"
    assert option_records(entry)["router"]["show_in_sidebar"] is True

    result = await start_options(hass, entry)
    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {"add", "edit", "delete"}

    result = await submit(hass, result["flow_id"], {"next_step_id": "edit"})
    assert result["step_id"] == "select_edit"
    assert "slug" in result["data_schema"].schema
    result = await submit(hass, result["flow_id"], {"slug": "router"})
    assert result["step_id"] == "edit"
    assert "title" in result["data_schema"].schema
    title_field = next(key for key in result["data_schema"].schema if key == "title")
    assert title_field.description["suggested_value"] == "Router"
    result = await submit(hass, result["flow_id"], {"title": "New router", "url": "new:8080"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    saved = get_panels(entry)
    assert saved["router"]["url"] == "new:8080" and saved["router"]["title"] == "New router"

    result = await start_options(hass, entry)
    result = await submit(hass, result["flow_id"], {"next_step_id": "delete"})
    assert result["step_id"] == "delete"
    result = await submit(hass, result["flow_id"], {"slug": "router"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert get_panels(entry) == {}
    assert option_records(entry) == {}


@pytest.mark.parametrize(
    ("user_input", "error"),
    [
        ({"url": "ftp://host"}, "invalid_url"),
        ({"slug": "Bad slug"}, "invalid_panel"),
        (
            {
                "advanced": {
                    "headers": [{"name": "X-App", "value": "a"}, {"name": "x-app", "value": "b"}]
                }
            },
            "duplicate_headers",
        ),
        ({"advanced": {"parent": "missing"}}, "invalid_parent"),
        ({"advanced": {"work_mode": "subapp"}}, "invalid_parent"),
        (
            {"advanced": {"rewrite": [{"mode": "body", "match": "[", "replace": "x"}]}},
            "invalid_regex",
        ),
    ],
)
async def test_options_flow_rejects_the_same_values(hass, user_input, error):
    entry = add_entry(hass)
    result = await start_options(hass, entry)
    result = await submit(
        hass,
        result["flow_id"],
        {
            "slug": "app",
            "title": "App",
            "url": "app:80",
            **user_input,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == error
    assert get_panels(entry) == {}


@pytest.mark.parametrize(
    ("settings", "error"),
    [
        ({"tls_mode": "custom"}, "invalid_tls_certificate"),
        ({"tls_mode": "custom", "tls_certificate": "invalid"}, "invalid_tls_certificate"),
        ({"tls_mode": "disabled", "work_mode": "iframe"}, "invalid_tls_mode"),
    ],
)
async def test_options_flow_validates_tls(hass, settings, error):
    entry = add_entry(hass)
    result = await start_options(hass, entry)
    result = await submit(
        hass,
        result["flow_id"],
        {
            "slug": "app",
            "title": "App",
            "url": "https://localhost",
            "advanced": settings,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == error
    assert get_panels(entry) == {}


async def test_options_flow_rejects_duplicate_and_accepts_subapp(hass):
    entry = add_entry(hass, {"root": {"url": "root:80", "title": "Root"}})
    result = await start_options(hass, entry)
    result = await submit(hass, result["flow_id"], {"next_step_id": "add"})
    result = await submit(
        hass, result["flow_id"], {"slug": "root", "title": "Root", "url": "other:80"}
    )
    assert result["errors"] == {"slug": "duplicate_panel"}
    result = await submit(
        hass,
        result["flow_id"],
        {
            "slug": "child",
            "title": "Child",
            "url": "child:80",
            "advanced": {"work_mode": "subapp", "parent": "root"},
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert get_panels(entry)["child"]["parent"] == "root"


@pytest.mark.parametrize("mode", [ConfMode.AGENT, ConfMode.YAML])
async def test_options_flow_refuses_externally_managed_panels(hass, mode):
    entry = add_entry(hass, mode=mode)
    result = await start_options(hass, entry)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == ("agent_panels" if mode == ConfMode.AGENT else "yaml_panels")


async def test_setup_registers_panels_from_options(hass):
    """The runtime consumes options-stored panels like subentry-stored ones."""
    entry = add_entry(
        hass,
        {
            "router": {"url": "http://192.168.1.1", "title": "Router"},
            "hidden": {"url": "hidden:80"},
        },
    )
    hass.http = Mock()
    hass.http.async_register_static_paths = AsyncMock()
    with patch("custom_components.ingress.get_version", return_value="1.4.0"):
        assert await async_setup_entry(hass, entry)
    assert "router" in hass.data[frontend.DATA_PANELS]
    assert hass.data[frontend.DATA_PANELS]["router"].sidebar_title == "Router"
    assert "hidden" in hass.data[frontend.DATA_PANELS]
    assert hass.data[frontend.DATA_PANELS]["hidden"].sidebar_title is None
    assert hass.data[DOMAIN]["config"].get("router") is not None


async def test_migration_keeps_panels_in_options(hass):
    """A version 1 entry must stay usable without subentry support."""
    panels = {
        "hidden": {
            "url": "app:80",
            "headers": {"Authorization": "secret"},
            "static_token": "public",
        },
        "shown": {"url": "shown:80", "title": "Shown"},
    }
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, data={CONF_MODE: ConfMode.UI}, options={"panels": panels}
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert entry.data["ui_configured"] is True
    assert set(get_panels(entry)) == set(panels)
    assert get_panels(entry)["shown"]["title"] == "Shown"
    assert "title" not in get_panels(entry)["hidden"]
    assert option_records(entry)["hidden"]["title"] == "hidden"
    assert option_records(entry)["hidden"]["show_in_sidebar"] is False
    # Re-running the migration must not duplicate or drop anything.
    assert await async_migrate_entry(hass, entry)
    assert set(option_records(entry)) == set(panels)


async def test_options_flow_rejects_stale_forms(hass):
    """A form filled in before a configuration change must not be applied."""
    entry = add_entry(hass, {"router": {"url": "router:80", "title": "Router"}})
    result = await start_options(hass, entry)
    result = await submit(hass, result["flow_id"], {"next_step_id": "add"})
    assert "title" in result["data_schema"].schema
    hass.config_entries.async_update_entry(entry, options={CONF_PANELS: {}})
    result = await submit(hass, result["flow_id"], {"slug": "app", "title": "App", "url": "app:80"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "configuration_changed"
    assert get_panels(entry) == {}


async def test_options_translations_cover_every_rendered_field(hass):
    """Every field the options flow renders must be translated."""
    import json
    from pathlib import Path

    from custom_components.ingress.config_flow import _panel_schema

    root = Path(__file__).resolve().parent.parent / "custom_components/ingress"
    strings = json.loads((root / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((root / "translations/en.json").read_text(encoding="utf-8"))
    assert strings == english, "translations/en.json must mirror strings.json"

    options = strings["options"]
    assert set(options["step"]["init"]["menu_options"]) == {"add", "edit", "delete"}
    for step_id, editing in (("add", False), ("edit", True)):
        schema = _panel_schema(editing)
        names = {getattr(marker, "schema", marker) for marker in schema.schema}
        translated = set(options["step"][step_id]["data"])
        assert names - {"advanced"} <= translated, names - {"advanced"} - translated
        advanced = schema.schema[
            next(
                marker
                for marker in schema.schema
                if getattr(marker, "schema", marker) == "advanced"
            )
        ]
        fields = {getattr(marker, "schema", marker) for marker in advanced.schema.schema}
        assert fields <= set(options["step"][step_id]["sections"]["advanced"]["data"])
    assert set(options["abort"]) >= {"agent_panels", "yaml_panels", "configuration_changed"}
    assert {"init", "add", "edit", "delete", "select_edit"} <= set(options["step"])


def test_translations_cover_every_key_without_repeating_one():
    """Every English key must be translated, and no JSON object may repeat a key.

    Duplicate keys are silently dropped by ``json.load``, so a translation file
    could look complete while actually shadowing an earlier entry.
    """
    import json

    root = Path(__file__).resolve().parent.parent / "custom_components/ingress"

    def load(path):
        duplicates = []

        def hook(pairs):
            seen = set()
            for key, _ in pairs:
                if key in seen:
                    duplicates.append(key)
                seen.add(key)
            return dict(pairs)

        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=hook), duplicates

    def flatten(node, prefix=""):
        if isinstance(node, dict):
            for key, value in node.items():
                yield from flatten(value, f"{prefix}{key}.")
        else:
            yield prefix.rstrip(".")

    english, duplicates = load(root / "translations/en.json")
    assert duplicates == [], f"en.json repeats {duplicates}"
    strings, duplicates = load(root / "strings.json")
    assert duplicates == [], f"strings.json repeats {duplicates}"
    assert english == strings, "translations/en.json must mirror strings.json"
    english_keys = set(flatten(english))

    translated, duplicates = load(root / "translations/zh-Hans.json")
    assert duplicates == [], f"zh-Hans.json repeats {duplicates}"
    translated_keys = set(flatten(translated))
    missing = sorted(english_keys - translated_keys)
    assert missing == [], f"zh-Hans.json is missing {len(missing)} keys: {missing}"
    stale = sorted(translated_keys - english_keys)
    assert stale == [], f"zh-Hans.json has {len(stale)} stale keys: {stale}"


async def test_import_yaml_writes_options(hass):
    """Switching from YAML to the local UI stores the panels in the options."""
    entry = add_entry(hass, mode=ConfMode.YAML)
    yaml_panels = {"app": {"url": "http://app", "headers": {"Authorization": "resolved-secret"}}}
    with patch(
        "custom_components.ingress.config_flow.async_integration_yaml_config",
        return_value={DOMAIN: yaml_panels},
    ), patch.object(hass.config_entries, "async_reload", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"mode": ConfMode.UI}
        )
        assert result["step_id"] == "import_yaml"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"confirm": True}
        )
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_MODE] == ConfMode.UI
    expected = CONFIG_SCHEMA({DOMAIN: yaml_panels})[DOMAIN]
    assert get_panels(entry) == expected
    assert get_panels(entry)["app"]["headers"]["Authorization"] == "resolved-secret"
    await hass.async_block_till_done()


def test_old_core_module_definition():
    """The import-time branch must expose the options flow when subentries are gone.

    ``config_flow`` reads the capability flag while it is imported, so the branch
    an old core actually executes is only reachable in a fresh interpreter. Doing
    it in-process would leave every other module holding a stale flow class.
    """
    script = textwrap.dedent("""
        from custom_components.ingress import compat

        compat.SUPPORTS_SUBENTRIES = False
        compat.ConfigSubentry = None
        compat.ConfigSubentryFlow = None

        from custom_components.ingress import config_flow

        assert config_flow._SubentryFlowBase is object
        own = config_flow.IngressConfigFlow.__dict__
        assert "async_get_supported_subentry_types" not in own
        factory = own["async_get_options_flow"]
        assert isinstance(factory, staticmethod)
        assert isinstance(factory.__func__(None), config_flow.IngressOptionsFlow)
        assert isinstance(config_flow.IngressPanelFlow, type)
        print("OK")
        """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


async def test_edit_picker_does_not_reuse_the_edit_form_description(hass):
    """The panel picker must not render a description that needs the slug.

    The picker and the edit form once shared the ``edit`` step, so the picker
    rendered the form's ``{slug}`` description without a placeholder and the
    frontend logged a formatting error instead of showing the form.
    """
    import json

    root = Path(__file__).resolve().parent.parent / "custom_components/ingress"
    steps = json.loads((root / "strings.json").read_text(encoding="utf-8"))["options"]["step"]
    assert "{slug}" not in steps["select_edit"]["description"]

    entry = add_entry(hass, {"router": {"url": "router:80", "title": "Router"}})
    result = await start_options(hass, entry)
    result = await submit(hass, result["flow_id"], {"next_step_id": "edit"})
    assert result["step_id"] == "select_edit"
    assert "slug" in result["data_schema"].schema
    result = await submit(hass, result["flow_id"], {"slug": "router"})
    assert result["step_id"] == "edit"
    assert result["description_placeholders"] == {"slug": "router"}
