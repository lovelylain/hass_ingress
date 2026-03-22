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
    AGENT = "agent"
    YAML = "yaml"
