"""Risk Analysis — strumento per il calcolo del rischio R = f(P, M, V).

P = probabilità dell'evento, M = magnitudo del danno, V = vulnerabilità del sistema.
"""

from .classification import Classifier
from .core import Mode, RiskInput, RiskResult, Scale
from .domains import CYBERSECURITY, DOMAINS, SICUREZZA_LAVORO, Domain
from .models import (
    Multiplicative,
    RiskAversion,
    RiskModel,
    WeightedAdditive,
    WeightedGeometric,
    compare,
)
from .montecarlo import PERT, Fixed, Triangular, Uniform, simulate
from .register import RiskRegister

__version__ = "0.1.0"

__all__ = [
    "Classifier",
    "Mode",
    "RiskInput",
    "RiskResult",
    "Scale",
    "Domain",
    "DOMAINS",
    "CYBERSECURITY",
    "SICUREZZA_LAVORO",
    "RiskModel",
    "Multiplicative",
    "WeightedGeometric",
    "WeightedAdditive",
    "RiskAversion",
    "compare",
    "simulate",
    "Fixed",
    "Uniform",
    "Triangular",
    "PERT",
    "RiskRegister",
]
