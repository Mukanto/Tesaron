"""Faulty twins (PREREG section 6.2). Each wraps or replaces exactly one step of the system; tesaron/ is untouched."""

from audit.twins.n1 import N1a, N1b
from audit.twins.n2 import N2
from audit.twins.n3 import N3
from audit.twins.n4 import N4
from audit.twins.n5 import N5
from audit.twins.n6 import N6
from audit.twins.n7 import N7
from audit.twins.n8 import N8
from audit.twins.nt import TRADE_OFF, with_trade_off

# test id -> twin classes of that test (NT is not a System: it transforms metric points)
TWINS_BY_TEST = {
    "G1": (N1a, N1b),
    "G2": (N2,),
    "G3": (N3,),
    "G4": (N4,),
    "G5": (N5,),
    "G6": (N6,),
    "G7": (N7,),
    "G8": (N8,),
}

__all__ = [
    "N1a", "N1b", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "TRADE_OFF", "TWINS_BY_TEST", "with_trade_off",
]
