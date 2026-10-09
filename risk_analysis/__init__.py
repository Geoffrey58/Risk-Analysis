"""Risk Analysis — strumento per il calcolo del rischio R = f(P, M, V).

P = probabilità dell'evento, M = magnitudo del danno, V = vulnerabilità del sistema.
"""

from .classification import Classifier
from .core import Mode, RiskInput, RiskResult, Scale
from .criteria import DEFAULT_CRITERIA, ImpactCriteria
from .domains import (
    CIA,
    CYBERSECURITY,
    DOMAINS,
    IMPATTO_IA,
    CasoUso,
    ClasseAIAct,
    Interesse,
    assess_use_case,
    SICUREZZA_LAVORO,
    Asset,
    Domain,
    assess_scenario,
    availability_from_downtime,
)
from .models import (
    Multiplicative,
    RiskAversion,
    RiskModel,
    WeightedAdditive,
    WeightedGeometric,
    compare,
)
from .montecarlo import PERT, Fixed, Triangular, Uniform, simulate
from .register import RiskRegister, to_csv_combined

__version__ = "0.1.0"

__all__ = [
    "Classifier",
    "Mode",
    "RiskInput",
    "RiskResult",
    "Scale",
    "ImpactCriteria",
    "DEFAULT_CRITERIA",
    "Domain",
    "DOMAINS",
    "CYBERSECURITY",
    "SICUREZZA_LAVORO",
    "CIA",
    "Asset",
    "assess_scenario",
    "availability_from_downtime",
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
    "to_csv_combined",
    "IMPATTO_IA",
    "CasoUso",
    "ClasseAIAct",
    "Interesse",
    "assess_use_case",
]
