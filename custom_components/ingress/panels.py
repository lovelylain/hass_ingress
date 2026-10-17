"""Panel storage that works with and without config subentries.

The runtime only ever needs a flat ``slug -> panel`` mapping. Where that mapping
is stored differs per core:

* Home Assistant 2025.8 and newer keep one config subentry per panel, so every
  panel gets its own row in *Settings -> Devices & services*.
* Older cores keep the whole mapping in ``entry.options["panels"]``.

Both backends store a sidebar title and a sidebar visibility flag next to the
panel fields. ``get_panels`` folds them back into the panel exactly the same way
for both, so the runtime configuration never depends on the backend.
"""

from copy import deepcopy
from types import MappingProxyType
from typing import TYPE_CHECKING

from . import compat
from .compat import ConfigSubentry
from .const import (
    CONF_PANELS,
    CONF_PARENT,
    CONF_SHOW_IN_SIDEBAR,
    CONF_TITLE,
    SUBENTRY_TYPE,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from typing import Any


def _fold_sidebar(panel: dict[str, "Any"], title: str, visible: bool) -> dict[str, "Any"]:
    """Mirror the visibility rule the runtime relies on.

    A panel that is neither in the sidebar nor a child panel keeps no title, so
    it is registered without a sidebar entry.
    """
    if visible or panel.get(CONF_PARENT):
        panel[CONF_TITLE] = title
    return panel


def _subentry_panels(entry: "ConfigEntry") -> dict[str, dict[str, "Any"]]:
    """Rebuild panels stored as config subentries."""
    panels: dict[str, dict[str, "Any"]] = {}
    for subentry in entry.subentries.values():
        panel = deepcopy(dict(subentry.data))
        visible = panel.pop(CONF_SHOW_IN_SIDEBAR, True)
        panels[subentry.unique_id] = _fold_sidebar(panel, subentry.title, visible)
    return panels


def _option_panels(entry: "ConfigEntry") -> dict[str, dict[str, "Any"]]:
    """Rebuild panels stored in the configuration entry options."""
    panels: dict[str, dict[str, "Any"]] = {}
    for slug, saved in entry.options.get(CONF_PANELS, {}).items():
        panel = deepcopy(saved)
        title = panel.pop(CONF_TITLE, None)
        visible = panel.pop(CONF_SHOW_IN_SIDEBAR, None)
        if visible is None:
            # Records written before the sidebar flag existed followed the same
            # rule the subentry backend uses: no title means no sidebar entry.
            visible = bool(title)
        panels[slug] = _fold_sidebar(panel, title or slug, visible)
    return panels


def get_panels(entry: "ConfigEntry") -> dict[str, dict[str, "Any"]]:
    """Return the saved panels keyed by slug, whatever the storage backend."""
    if compat.SUPPORTS_SUBENTRIES:
        return _subentry_panels(entry)
    return _option_panels(entry)


def entry_snapshot(entry: "ConfigEntry"):
    """Capture everything a flow depends on, so stale forms can be rejected."""
    subentries = {key: value.as_dict() for key, value in getattr(entry, "subentries", {}).items()}
    return deepcopy((dict(entry.data), dict(entry.options), subentries))


def subentry(slug: str, panel: dict[str, "Any"]) -> "ConfigSubentry":
    """Build the subentry that represents one panel."""
    panel = deepcopy(panel)
    title = panel.pop(CONF_TITLE, None)
    panel[CONF_SHOW_IN_SIDEBAR] = bool(title)
    return ConfigSubentry(
        subentry_type=SUBENTRY_TYPE,
        unique_id=slug,
        title=title or slug,
        data=MappingProxyType(panel),
    )


def option_record(
    slug: str, panel: dict[str, "Any"], title: str, show_in_sidebar: bool
) -> dict[str, "Any"]:
    """Build the option record that represents one panel."""
    record = deepcopy(panel)
    record[CONF_TITLE] = title or slug
    record[CONF_SHOW_IN_SIDEBAR] = show_in_sidebar
    return record


def option_records(entry: "ConfigEntry") -> dict[str, dict[str, "Any"]]:
    """Return the raw stored records of the options backend."""
    return deepcopy(entry.options.get(CONF_PANELS, {}))


def replace_panels(
    hass: "HomeAssistant", entry: "ConfigEntry", panels: dict[str, dict[str, "Any"]]
) -> None:
    """Store ``panels`` as the entry's panel set, keeping unlisted panels.

    Panels that already exist are overwritten and new ones are added; panels that
    are not listed keep their configuration. Used when importing YAML panels and
    when migrating older entries, where the panels already carry their sidebar
    title inside the panel itself.
    """
    if compat.SUPPORTS_SUBENTRIES:
        known = {item.unique_id: item for item in entry.subentries.values()}
        for slug, panel in panels.items():
            replacement = subentry(slug, panel)
            if existing := known.get(slug):
                hass.config_entries.async_update_subentry(
                    entry, existing, title=replacement.title, data=replacement.data
                )
            else:
                hass.config_entries.async_add_subentry(entry, replacement)
        return
    stored = option_records(entry)
    for slug, panel in panels.items():
        # A panel without a title is not shown in the sidebar, exactly like a
        # title-less subentry.
        title = panel.get(CONF_TITLE)
        stored[slug] = option_record(
            slug,
            {key: value for key, value in panel.items() if key != CONF_TITLE},
            title or slug,
            bool(title),
        )
    hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_PANELS: stored})
