"""Utility functions for the inspector."""

import copy
import types


def safe_repr(value, max_len=120):
    """Return a safe, truncated repr of a value."""
    try:
        r = repr(value)
    except Exception:
        r = "<unrepresentable>"
    if len(r) > max_len:
        r = r[: max_len - 3] + "..."
    return r


def is_user_variable(name, value):
    """Filter out dunder names, modules, functions, and classes."""
    if name.startswith("__") and name.endswith("__"):
        return False
    if isinstance(value, (types.ModuleType, types.FunctionType, type)):
        return False
    return True


def shallow_copy(variables: dict) -> dict:
    """Best-effort shallow copy of a variable dict for diff detection."""
    snapshot = {}
    for k, v in variables.items():
        try:
            snapshot[k] = copy.copy(v)
        except Exception:
            snapshot[k] = v
    return snapshot
