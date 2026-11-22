"""Seed derivation (PREREG section 7, R1-3).

    seed(core, salt, role, i) = 1_000_000 + (first 8 bytes of SHA-256("<core>|<salt>|<role>|<i>") as a big-endian integer)
                                mod 10**9

Roles: world-cal, world-test, enc-cal, enc-test, aux, perm and n2; i is the draw index (for perm: 3 * draw + p, for n2:
2 * draw and 2 * draw + 1). The core is the core_sha256 of the freeze manifest; the salt is 32 random bytes (hex) drawn
by the Independent session after the freeze commit is public, so no real seed can be computed before then.

The development mapping dev_seed(role, i) = 900000 + (h mod 1000), with h computed from core "dev" and salt "dev", is
used ONLY in dev mode, so that nothing that runs before the freeze touches a seed outside 900000-900999 (SPEC section 11).
"""

from __future__ import annotations

import hashlib

ROLES = ("world-cal", "world-test", "enc-cal", "enc-test", "aux", "perm", "n2")
DEV_CORE = "dev"
DEV_SALT = "dev"
DEV_LOW, DEV_HIGH = 900000, 900999


def _h(core: str, salt: str, role: str, i: int) -> int:
    if role not in ROLES:
        raise ValueError(f"unknown seed role {role!r}")
    if not isinstance(i, int) or isinstance(i, bool) or i < 0:
        raise ValueError("seed index must be a non-negative int")
    digest = hashlib.sha256(f"{core}|{salt}|{role}|{i}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def seed(core_sha256: str, salt: str, role: str, i: int) -> int:
    """The real seed of PREREG section 7 (range 1_000_000 .. 1_000_999_999, disjoint from development seeds)."""
    if not salt:
        raise ValueError("a real seed needs a salt")
    return 1_000_000 + _h(core_sha256, salt, role, i) % 10**9


def dev_seed(role: str, i: int) -> int:
    """Development-mode seed in 900000..900999 (never used in a real run)."""
    return DEV_LOW + _h(DEV_CORE, DEV_SALT, role, i) % 1000


def seeder(core_sha256: str, salt: str | None = None):
    """seed(role, i) function for a core and salt; the core string "dev" selects the development mapping."""
    if core_sha256 == DEV_CORE:
        return dev_seed
    return lambda role, i: seed(core_sha256, salt or "", role, i)
