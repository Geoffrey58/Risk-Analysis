"""Strutture di base: scale qualitative, input del rischio e risultati.

Il rischio è espresso come R = f(P, M, V), dove:

- P  probabilità (o frequenza) dell'evento
- M  magnitudo del danno conseguente
- V  vulnerabilità del sistema esposto

Lo strumento lavora in due modalità:

- ``Mode.QUALITATIVE``: P, M e V sono punteggi su scale ordinali (es. 1-4, 1-5)
- ``Mode.QUANTITATIVE``: P è una probabilità o una frequenza annua, V è una
  probabilità condizionata in [0, 1], M è un valore fisico (euro, giorni, ...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Sequence


class Mode(str, Enum):
    """Modalità di valutazione."""

    QUALITATIVE = "qualitativa"
    QUANTITATIVE = "quantitativa"


@dataclass(frozen=True)
class Scale:
    """Scala ordinale per un fattore di rischio.

    I punteggi vanno da ``minimum`` a ``maximum``. Il valore normalizzato è
    ``punteggio / maximum``, quindi sempre in (0, 1]: anche il livello più basso
    di una scala resta un valore positivo (un evento "improbabile" non è un
    evento impossibile).
    """

    name: str
    minimum: int = 1
    maximum: int = 4
    labels: Sequence[str] = field(default_factory=tuple)
    descriptions: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.minimum < 1:
            raise ValueError("Il minimo della scala deve essere >= 1")
        if self.maximum <= self.minimum:
            raise ValueError("Il massimo della scala deve superare il minimo")
        levels = self.maximum - self.minimum + 1
        if self.labels and len(self.labels) != levels:
            raise ValueError(
                f"La scala '{self.name}' ha {levels} livelli ma {len(self.labels)} etichette"
            )
        if self.descriptions and len(self.descriptions) != levels:
            raise ValueError(
                f"La scala '{self.name}' ha {levels} livelli ma {len(self.descriptions)} descrizioni"
            )

    def validate(self, score: float) -> float:
        if not (self.minimum <= score <= self.maximum):
            raise ValueError(
                f"{self.name}: punteggio {score} fuori dalla scala "
                f"{self.minimum}-{self.maximum}"
            )
        return float(score)

    def normalize(self, score):
        """Riporta il punteggio in (0, 1]. Accetta anche array numpy."""
        return score / self.maximum

    def label(self, score: int) -> str:
        if not self.labels:
            return str(score)
        return self.labels[int(round(score)) - self.minimum]


@dataclass(frozen=True)
class RiskInput:
    """I tre fattori di un singolo scenario di rischio."""

    P: float
    M: float
    V: float
    mode: Mode = Mode.QUALITATIVE


@dataclass
class RiskResult:
    """Esito di una valutazione.

    - ``value``: valore del rischio nell'unità del modello (punteggio grezzo,
      indice, oppure grandezza fisica come euro/anno)
    - ``index``: indice normalizzato in [0, 1], disponibile in modalità qualitativa
    - ``level``: classe di rischio, se è stata applicata una classificazione
    """

    value: float
    model: str
    mode: Mode
    unit: str = ""
    index: Optional[float] = None
    level: Optional[str] = None
    details: Dict[str, float] = field(default_factory=dict)

    def __str__(self) -> str:
        parts = [f"R = {self.value:.4g}"]
        if self.unit:
            parts[0] += f" {self.unit}"
        if self.index is not None:
            parts.append(f"indice {self.index:.3f}")
        if self.level:
            parts.append(f"livello: {self.level}")
        return f"[{self.model}] " + " | ".join(parts)
