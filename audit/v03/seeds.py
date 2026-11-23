"""Seed derivation of Tesaron v0.3 (PREREG_v0.3 section 7).

    seed(core, salt, role, i) = 1_000_000 + (first 8 bytes of SHA-256("<core>|<salt>|<role>|<i>") as a big-endian integer)
                                mod 10**9

The formula is that of v0.2 (`audit.seeds`); the core hash and the salt are v0.3's own (the core hash of
`prereg/v03/FREEZE_v0.3.json`, the salt of `run/v03/SALT.json`), so v0.3's worlds are independent of v0.2's.

Roles: world-cal, world-test, enc-cal, enc-test, aux, perm, n2, and world-calalt-<b> and enc-calalt-<b> for b = 0..19
(the 20 draw-sensitivity calibration sets). i is the draw index d, except for perm (i = 3d + p, p = 0, 1, 2) and n2
(i = 2d and 2d + 1).

Development mapping (used only with the core "dev"; nothing that runs before the freeze touches a seed outside
930000..934999 and the encoder/aux offsets below). It is a plain counter, not a hash, so that every development set is
"the first valid seeds from a base upward" and the sets are disjoint:
  world-test        930000 + d          enc-test        world seed + 10000        aux   world-test seed + 20000
  world-cal         930100 + d          enc-cal         world seed + 10000
  world-calalt-<b>  931000 + 200 b + d  enc-calalt-<b>  world seed + 10000        (blocks of 200 = the cap of draws per set)
  perm              960000 + i          n2              970000 + i
The test and calibration blocks overlap only if a test set needed more than 100 draws (the world set refuses a duplicate
world seed inside one set, not across sets); the development sets used so far need about 51 draws.
"""

from __future__ import annotations

import hashlib
import re

N_ALT = 20
BASE_ROLES = ("world-cal", "world-test", "enc-cal", "enc-test", "aux", "perm", "n2")
ALT_ROLES = tuple(f"{kind}-calalt-{b}" for b in range(N_ALT) for kind in ("world", "enc"))
ROLES = BASE_ROLES + ALT_ROLES
_ALT = re.compile(r"(world|enc)-calalt-(\d+)")
DEV_CORE = "dev"
DEV_SALT = "dev"
ENC_OFFSET = 10000
AUX_OFFSET = 20000
DEV_TEST_START = 930000
DEV_CAL_START = 930100
DEV_ALT_START = 931000
DEV_ALT_BLOCK = 200
DEV_PERM_START = 960000
DEV_N2_START = 970000


def calalt_role(kind: str, b: int) -> str:
    """"world-calalt-<b>" or "enc-calalt-<b>" for b in 0..19."""
    if kind not in ("world", "enc") or not isinstance(b, int) or isinstance(b, bool) or not 0 <= b < N_ALT:
        raise ValueError(f"bad calibration-alt role {kind!r}, {b!r}")
    return f"{kind}-calalt-{b}"


def _h(core: str, salt: str, role: str, i: int) -> int:
    if role not in ROLES:
        raise ValueError(f"unknown seed role {role!r}")
    if not isinstance(i, int) or isinstance(i, bool) or i < 0:
        raise ValueError("seed index must be a non-negative int")
    digest = hashlib.sha256(f"{core}|{salt}|{role}|{i}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def seed(core_sha256: str, salt: str, role: str, i: int) -> int:
    """The real seed (range 1_000_000 .. 1_000_999_999, disjoint from the development ranges)."""
    if not salt:
        raise ValueError("a real seed needs a salt")
    return 1_000_000 + _h(core_sha256, salt, role, i) % 10**9


def dev_seed(role: str, i: int) -> int:
    """Development-mode seed (see the module docstring for the mapping)."""
    if role not in ROLES:
        raise ValueError(f"unknown seed role {role!r}")
    if not isinstance(i, int) or isinstance(i, bool) or i < 0:
        raise ValueError("seed index must be a non-negative int")
    if role == "world-test":
        return DEV_TEST_START + i
    if role == "world-cal":
        return DEV_CAL_START + i
    if role in ("enc-test", "enc-cal"):
        return dev_seed("world-" + role[4:], i) + ENC_OFFSET
    if role == "aux":
        return dev_seed("world-test", i) + AUX_OFFSET
    if role == "perm":
        return DEV_PERM_START + i
    if role == "n2":
        return DEV_N2_START + i
    kind, b = _ALT.fullmatch(role).groups()
    base = DEV_ALT_START + DEV_ALT_BLOCK * int(b) + i
    return base if kind == "world" else base + ENC_OFFSET


def seeder(core_sha256: str, salt: str | None = None):
    """seed(role, i) for a core and salt; the core string "dev" selects the development mapping."""
    if core_sha256 == DEV_CORE:
        return dev_seed
    return lambda role, i: seed(core_sha256, salt or "", role, i)
