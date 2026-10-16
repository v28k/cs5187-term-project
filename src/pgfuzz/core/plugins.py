from __future__ import annotations

import importlib
from typing import Any, TypeVar

T = TypeVar("T")


class PluginError(RuntimeError):
    pass


def load_class(spec: str) -> type:
    """Resolve ``"package.module:ClassName"`` to a class."""
    if ":" not in spec:
        raise PluginError(f"plugin spec {spec!r} must look like 'package.module:ClassName'")
    module_name, _, attr = spec.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise PluginError(f"cannot import module {module_name!r} for plugin {spec!r}: {e}") from e
    try:
        return getattr(module, attr)
    except AttributeError as e:
        raise PluginError(f"module {module_name!r} has no attribute {attr!r}") from e


def instantiate(spec: str, base: type[T], params: dict[str, Any] | None = None) -> T:
    cls = load_class(spec)
    if not (isinstance(cls, type) and issubclass(cls, base)):
        raise PluginError(f"{spec!r} is not a subclass of {base.__module__}.{base.__name__}")
    try:
        return cls(**(params or {}))
    except TypeError as e:
        raise PluginError(f"cannot construct {spec!r} with params {params!r}: {e}") from e
