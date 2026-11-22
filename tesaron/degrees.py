"""Membership and Probability (SPEC section 2).

A membership degree is the degree to which something belongs to a set; it is not a probability.
The two classes are separate, immutable, and refuse to mix.
"""

from __future__ import annotations

from typing import Any

import numpy as np

_NUMERIC = (int, float, np.integer, np.floating)


class _Degree:
    """Immutable wrapper of a float in [0, 1]. Base of Membership and Probability."""

    __slots__ = ("_value",)

    def __init__(self, value: Any) -> None:
        if isinstance(value, _Degree):
            raise TypeError(
                f"cannot build {type(self).__name__} from {type(value).__name__}; "
                "use the explicit conversion function"
            )
        if isinstance(value, bool) or not isinstance(value, _NUMERIC):
            raise TypeError(f"{type(self).__name__} needs a real number, got {type(value).__name__}")
        v = float(value)
        if not (0.0 <= v <= 1.0):  # also false for NaN
            raise ValueError(f"{type(self).__name__} must lie in [0, 1], got {v!r}")
        object.__setattr__(self, "_value", v)

    @property
    def value(self) -> float:
        return self._value

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def _other(self, other: Any) -> float:
        """Plain value of `other`, or NotImplemented. Mixing Membership and Probability raises."""
        if isinstance(other, _Degree):
            if type(other) is not type(self):
                raise TypeError(
                    f"cannot compare or combine {type(self).__name__} with {type(other).__name__}"
                )
            return other._value
        if isinstance(other, bool):
            return NotImplemented  # type: ignore[return-value]
        if isinstance(other, _NUMERIC):
            return float(other)
        return NotImplemented  # type: ignore[return-value]

    def __lt__(self, other: Any):
        o = self._other(other)
        return NotImplemented if o is NotImplemented else self._value < o

    def __le__(self, other: Any):
        o = self._other(other)
        return NotImplemented if o is NotImplemented else self._value <= o

    def __gt__(self, other: Any):
        o = self._other(other)
        return NotImplemented if o is NotImplemented else self._value > o

    def __ge__(self, other: Any):
        o = self._other(other)
        return NotImplemented if o is NotImplemented else self._value >= o

    def __eq__(self, other: Any):
        o = self._other(other)
        return NotImplemented if o is NotImplemented else self._value == o

    def __ne__(self, other: Any):
        o = self._other(other)
        return NotImplemented if o is NotImplemented else self._value != o

    def __hash__(self) -> int:  # only for dict/set membership, never for ordering
        return hash(self._value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value!r})"


def _no_arithmetic(self: _Degree, *args: Any, **kwargs: Any):
    raise TypeError(f"arithmetic is not defined on {type(self).__name__}")


for _name in (
    "__add__", "__radd__", "__sub__", "__rsub__", "__mul__", "__rmul__",
    "__truediv__", "__rtruediv__", "__floordiv__", "__rfloordiv__",
    "__mod__", "__rmod__", "__pow__", "__rpow__", "__neg__", "__pos__", "__abs__",
):
    setattr(_Degree, _name, _no_arithmetic)
del _name


class Membership(_Degree):
    """Degree of membership in a set, in [0, 1]. Not a probability."""

    __slots__ = ()


class Probability(_Degree):
    """A probability in [0, 1]. Used only inside the world generator."""

    __slots__ = ()


def tconorm_max(*ms: Membership) -> Membership:
    """Maximum t-conorm. With no argument it returns the identity Membership(0.0)."""
    for m in ms:
        if not isinstance(m, Membership):
            raise TypeError(f"tconorm_max needs Membership, got {type(m).__name__}")
    return Membership(max((m.value for m in ms), default=0.0))


def tnorm_min(*ms: Membership) -> Membership:
    """Minimum t-norm. With no argument it returns the identity Membership(1.0)."""
    for m in ms:
        if not isinstance(m, Membership):
            raise TypeError(f"tnorm_min needs Membership, got {type(m).__name__}")
    return Membership(min((m.value for m in ms), default=1.0))


def support_degrees_from_world(world: Any) -> dict[str, Membership]:
    """Context support degrees from the generator's source reliabilities.

    v0 modelling choice: the context's support degree for a source equals, numerically, the
    generator's probability that the source reports correctly; in the encoder it is a membership
    degree and is only combined with max.

    This is the only place where a Probability is turned into a Membership.
    """
    out: dict[str, Membership] = {}
    for source in sorted(world.source_reliabilities):
        p = world.source_reliabilities[source]
        if not isinstance(p, Probability):
            raise TypeError(f"source reliability of {source!r} must be a Probability")
        out[source] = Membership(p.value)
    return out
