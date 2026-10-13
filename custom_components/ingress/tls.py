"""Build a private TLS policy for an ingress without reading certificate files."""

import re
import ssl

from .const import CONF_TLS_CERTIFICATE, CONF_TLS_MODE, TLSMode, WorkMode


class InvalidTLS(ValueError):
    """Invalid TLS settings with a form translation key."""

    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def tls_context(panel) -> ssl.SSLContext | bool:
    """Keep system trust by default; custom trust uses only the supplied PEMs."""
    mode = panel.get(CONF_TLS_MODE, TLSMode.SYSTEM)
    if mode == TLSMode.SYSTEM:
        return True
    url = panel["url"]
    if isinstance(url, dict):
        url = url["default"]
    if (
        mode not in (TLSMode.CUSTOM, TLSMode.DISABLED)
        or panel.get("work_mode", WorkMode.INGRESS) not in (WorkMode.INGRESS, WorkMode.SUBAPP)
        or not url.lower().startswith("https://")
    ):
        raise InvalidTLS("invalid_tls_mode", "TLS options require an HTTPS ingress or subapp proxy.")
    if mode == TLSMode.DISABLED:
        return False

    certificate = panel.get(CONF_TLS_CERTIFICATE, "")
    try:
        if not re.fullmatch(
            r"(?:\s*-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----\s*)+",
            certificate,
        ):
            raise ValueError("Expected PEM certificates")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cadata=certificate)
        # An explicitly trusted server or intermediate certificate can end the chain.
        context.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
        return context
    except (ssl.SSLError, ValueError, TypeError) as err:
        raise InvalidTLS(
            "invalid_tls_certificate",
            "Custom TLS trust requires one or more valid PEM CA or server certificates.",
        ) from err
