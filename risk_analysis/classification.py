"""Classificazione del rischio in livelli (basso, medio, alto, ...)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .core import RiskResult

# Tolleranza per gli arrotondamenti in virgola mobile: un valore che cade
# esattamente su una soglia appartiene al livello inferiore.
_TOLERANCE = 1e-9


@dataclass(frozen=True)
class Classifier:
    """Assegna un livello in base a soglie crescenti.

    ``thresholds`` è una sequenza di coppie (limite superiore incluso, etichetta);
    ``top_label`` è il livello per i valori oltre l'ultima soglia.
    ``on`` indica se confrontare l'indice normalizzato ("index") o il valore ("value").

    Esempio::

        Classifier([(0.125, "Basso"), (0.25, "Medio"), (0.5, "Alto")], "Molto alto")
    """

    thresholds: Sequence[Tuple[float, str]]
    top_label: str
    on: str = "index"

    def __post_init__(self) -> None:
        if self.on not in ("index", "value"):
            raise ValueError("'on' deve essere 'index' oppure 'value'")
        limits = [t for t, _ in self.thresholds]
        if limits != sorted(limits):
            raise ValueError("Le soglie devono essere in ordine crescente")

    def level_of(self, x: float) -> str:
        for limit, label in self.thresholds:
            if x <= limit + _TOLERANCE:
                return label
        return self.top_label

    def classify(self, result: RiskResult) -> RiskResult:
        x = result.index if self.on == "index" else result.value
        if x is None:
            raise ValueError(
                "Il risultato non ha un indice normalizzato: usare una classificazione sul valore"
            )
        result.level = self.level_of(x)
        return result

    @property
    def labels(self) -> Tuple[str, ...]:
        return tuple(label for _, label in self.thresholds) + (self.top_label,)
