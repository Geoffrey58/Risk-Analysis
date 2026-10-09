"""Profili di dominio pronti all'uso."""

from .base import Domain
from .cia import CIA, Asset, assess_scenario, availability_from_downtime
from .cybersecurity import CYBERSECURITY
from .impatto_ia import IMPATTO_IA, CasoUso, ClasseAIAct, Interesse, assess_use_case
from .sicurezza_lavoro import SICUREZZA_LAVORO

DOMAINS = {
    "sicurezza_lavoro": SICUREZZA_LAVORO,
    "cybersecurity": CYBERSECURITY,
    "impatto_ia": IMPATTO_IA,
}

__all__ = [
    "Domain",
    "CYBERSECURITY",
    "SICUREZZA_LAVORO",
    "DOMAINS",
    "CIA",
    "Asset",
    "assess_scenario",
    "availability_from_downtime",
    "IMPATTO_IA",
    "CasoUso",
    "ClasseAIAct",
    "Interesse",
    "assess_use_case",
]
