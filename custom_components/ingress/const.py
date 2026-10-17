"""Ingress const variables."""

try:
    from enum import StrEnum  # type: ignore
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final


DOMAIN: "Final" = "ingress"
LOGGER: "Final" = logging.getLogger(__package__)

API_BASE: "Final" = "/api/ingress"
URL_BASE: "Final" = "/files/ingress"

# Panel options. These are shared by the YAML schema, the graphical forms and the
# stored configuration, so they live here to keep the storage backends in sync.
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
CONF_ENABLE_COMPRESS: "Final" = "enable_compress"
CONF_SHOW_IN_SIDEBAR: "Final" = "show_in_sidebar"
CONF_UI_CONFIGURED: "Final" = "ui_configured"
CONF_TLS_MODE = "tls_mode"
CONF_TLS_CERTIFICATE = "tls_certificate"


from homeassistant.const import (
    CONF_DEFAULT,
    CONF_HEADERS,
    CONF_ICON,
    CONF_MODE,
    CONF_NAME,
    CONF_PATH,
    CONF_URL,
)

#: Key of the panel map inside the config entry options. Only used on cores
#: without config subentry support.
CONF_PANELS: "Final" = "panels"
#: Subentry type used for a single ingress panel.
SUBENTRY_TYPE: "Final" = "panel"


class TLSMode(StrEnum):
    SYSTEM = "system"
    CUSTOM = "custom"
    DISABLED = "disabled"


class WorkMode(StrEnum):
    INGRESS = "ingress"
    SUBAPP = "subapp"
    IFRAME = "iframe"
    AUTH = "auth"
    HASSIO = "hassio"
    CUSTOM = "custom"


class UIMode(StrEnum):
    NORMAL = "normal"
    TOOLBAR = "toolbar"
    REPLACE = "replace"


class RewriteMode(StrEnum):
    HEADER = "header"
    BODY = "body"


class ConfMode(StrEnum):
    UI = "ui"
    AGENT = "agent"
    YAML = "yaml"
