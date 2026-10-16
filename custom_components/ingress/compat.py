"""Compatibility helpers so the integration also runs on older cores.

Home Assistant 2025.8 introduced config subentries. This integration keeps one
ingress panel per subentry there, which is what gives every panel its own row in
*Settings -> Devices & services*. Cores without subentry support have no such
storage, so the very same panels live in the configuration entry options and are
managed by a regular options flow instead.

Everything below hides that difference from the rest of the code, so the ingress
proxy, the panel registration and the YAML import keep working unchanged on both
kinds of core.
"""

from homeassistant import config_entries
from homeassistant.helpers import selector

#: Config subentries (and their flows) exist since Home Assistant 2025.8.
ConfigSubentry = getattr(config_entries, "ConfigSubentry", None)
ConfigSubentryFlow = getattr(config_entries, "ConfigSubentryFlow", None)
SUPPORTS_SUBENTRIES = ConfigSubentry is not None and ConfigSubentryFlow is not None

#: The object selector only gained ``fields``/``multiple`` after 2025.1. Older
#: cores accept no configuration at all and render a plain YAML editor, which is
#: still enough to edit the header and rewrite lists.
SUPPORTS_OBJECT_FIELDS = "fields" in getattr(
    getattr(selector, "ObjectSelectorConfig", object), "__annotations__", {}
)


def object_selector(config=None):
    """Return an object selector that every supported core can serialize."""
    if SUPPORTS_OBJECT_FIELDS:
        return selector.ObjectSelector(config)
    return selector.ObjectSelector()


def async_update_and_abort(flow, entry, **kwargs):
    """Finish a reconfigure flow, whether or not the core knows subentries.

    ``async_update_and_abort`` replaced ``async_update_reload_and_abort`` in the
    same release that added subentries, so an older core only has the latter.
    """
    update = getattr(flow, "async_update_and_abort", None)
    if update is not None:
        return update(entry, **kwargs)
    return flow.async_update_reload_and_abort(entry, **kwargs)
