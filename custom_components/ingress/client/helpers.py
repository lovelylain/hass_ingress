from dataclasses import is_dataclass, asdict
import logging
import orjson
from typing import Any


# logger
LOGGER = logging.getLogger(__package__)


# json helpers
def omit_none(obj: Any) -> Any:
    """Omit dict none fields."""
    return _omit_none(obj) if isinstance(obj, dict) else obj


def _omit_none(obj: dict):
    for k in [k for k, v in obj.items() if v is None]:
        del obj[k]
    for v in obj.values():
        if isinstance(v, dict):
            _omit_none(v)
    return obj


def to_dict(obj: Any) -> dict:
    """Convert obj(msg) to dict."""
    if isinstance(obj, dict):
        pass
    elif callable(to_dict := getattr(obj, "to_dict", None)):
        obj = to_dict()
    elif is_dataclass(obj) and not isinstance(obj, type):
        obj = asdict(obj)
    else:
        raise TypeError(f"Type can not to_dict: {type(obj).__name__}")
    return _omit_none(obj)


def _json_dumps_default(obj: Any) -> Any:
    """orjson.dumps default handler."""
    if callable(to_dict := getattr(obj, "to_dict", None)):
        return omit_none(to_dict())
    if is_dataclass(obj) and not isinstance(obj, type):
        return _omit_none(asdict(obj))
    raise TypeError(f"Type is not JSON serializable: {type(obj).__name__}")


json_loads = orjson.loads


def json_dumps(obj: Any, option: int = 0) -> bytes:
    option |= orjson.OPT_PASSTHROUGH_DATACLASS
    return orjson.dumps(omit_none(obj), default=_json_dumps_default, option=option)
