"""Canonical serialization used for hashes (SPEC section 1).

json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True), every float rounded with
round(x, 12) first, numpy types converted to Python types.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from collections.abc import Mapping
from enum import Enum
from typing import Any

import numpy as np

from tesaron.atoms import Atom, atom_str
from tesaron.degrees import Membership, Probability


def _key(k: Any) -> str:
    if isinstance(k, str):
        return k
    if isinstance(k, Atom):
        return atom_str(k)
    if isinstance(k, Enum):
        return k.name
    if isinstance(k, (int, np.integer)) and not isinstance(k, bool):
        return str(int(k))
    raise TypeError(f"cannot use {type(k).__name__} as a canonical dict key")


def to_jsonable(obj: Any) -> Any:
    """Convert obj to plain JSON types, rounding floats to 12 digits."""
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, Enum):
        return obj.name
    if isinstance(obj, (Membership, Probability)):
        return to_jsonable(obj.value)
    if isinstance(obj, np.generic):
        return to_jsonable(obj.item())
    if isinstance(obj, np.ndarray):
        return to_jsonable(obj.tolist())
    if isinstance(obj, int):
        return int(obj)
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("non-finite float in canonical serialization")
        return round(obj, 12)
    if isinstance(obj, Atom):
        return atom_str(obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            ks = _key(k)
            if ks in out:
                raise ValueError(f"duplicate canonical key {ks!r}")
            out[ks] = to_jsonable(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, (set, frozenset)):
        items = [to_jsonable(x) for x in obj]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
    raise TypeError(f"cannot serialize {type(obj).__name__}")


def canonical_json(obj: Any) -> str:
    return json.dumps(to_jsonable(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("ascii")).hexdigest()
