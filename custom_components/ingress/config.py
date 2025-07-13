import base64
from homeassistant.components.frontend import EVENT_PANELS_UPDATED  # type: ignore
import os
import re
import time
from typing import TYPE_CHECKING

from .const import LOGGER as _LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from typing import TypedDict
    from yarl import URL

    from .const import WorkMode, RewriteMode

    class Token(TypedDict):
        value: str
        expire: int


class RewriteCfg:
    mode: "RewriteMode"
    path = ""
    name = ""
    match: str
    replace: str

    def __init__(self, **kwargs):
        self.__dict__.update(
            (k, v) for k, v in kwargs.items() if v is not None and v != getattr(self, k, None)
        )


class IngressCfg:
    mode: "WorkMode"
    name: str
    entry: str
    origin: "URL"
    sub_path = ""
    headers = {}
    cookie_name = "ingress_token"
    _cookie_name_re = None
    expire_time = 3600
    static_token = ""
    rewrites: list[RewriteCfg] = []
    sub_apps: list["IngressCfg"] = []

    def __init__(self, **kwargs):
        self.__dict__.update(
            (k, v) for k, v in kwargs.items() if v is not None and v != getattr(self, k, None)
        )
        self.token: "Token" = {"value": "", "expire": 0}

    def remove_token_from_cookie(self, cookie):
        if self._cookie_name_re is None:
            self._cookie_name_re = re.compile(
                rf"(?:^|;\s*){re.escape(self.cookie_name)}=[^;]*(?=;|$)"
            )
        return self._cookie_name_re.sub("", cookie).strip("; ")


class IngressStore:
    """ingress configs."""

    def __init__(self):
        self._configs: dict[str, IngressCfg] = {}
        self._tokens: dict[str, IngressCfg] = {}

    def clear(self):
        self._configs.clear()
        self._tokens.clear()

    def get(self, name: str) -> IngressCfg | None:
        return self._configs.get(name)

    def del_ingress(self, name: str) -> IngressCfg | None:
        if cfg := self._configs.pop(name, None):
            self._tokens.pop(cfg.token["value"], None)
        return cfg

    def add_ingress(self, cfg: IngressCfg, now: int):
        self.del_ingress(cfg.name)
        cfg.token["value"] = ""
        self.new_token(cfg, now)
        self._configs[cfg.name] = cfg

    def new_token(self, cfg: IngressCfg, now: int) -> str:
        if cfg.static_token:
            token = f"t-{cfg.static_token}"
            old = self._tokens.get(token)
            if old and old is not cfg:
                _LOGGER.error(
                    "static_token conflict with %s, use dynamic for %s!", old.name, cfg.name
                )
                del cfg.static_token
        while not cfg.static_token:
            token = base64.urlsafe_b64encode(os.urandom(33)).decode()
            if token not in self._tokens:
                break
        tkcfg = cfg.token
        self._tokens.pop(tkcfg.get("value"), None)
        self._tokens[token] = cfg
        tkcfg["value"] = token
        tkcfg["expire"] = now + cfg.expire_time
        return token

    def check_token(
        self, hass: "HomeAssistant", token: str, refresh=True
    ) -> tuple[IngressCfg | None, str]:
        cfg = self._tokens.get(token)
        if cfg and refresh:
            # token valid, check refresh
            now = int(time.time())
            if now >= cfg.token["expire"]:
                token = self.new_token(cfg, now)
                hass.bus.async_fire(EVENT_PANELS_UPDATED)
        return cfg, token

    def cookie_name(self, name: str) -> str:
        cfg = self._configs.get(name)
        return cfg.cookie_name if cfg else IngressCfg.cookie_name
