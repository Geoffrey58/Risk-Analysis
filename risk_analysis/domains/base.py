"""Profilo di dominio: scale, soglie e unità di misura di un ambito applicativo."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..classification import Classifier
from ..core import Mode, RiskInput, RiskResult, Scale
from ..models import Multiplicative, RiskModel


@dataclass
class Domain:
    """Raccoglie tutto ciò che serve per valutare il rischio in un ambito.

    - ``scale_p``, ``scale_m``, ``scale_v``: scale qualitative dei tre fattori
    - ``qualitative_classifier``: soglie sull'indice normalizzato
    - ``quantitative_classifier``: soglie sul valore fisico (facoltative)
    - ``quantitative_unit``: unità del rischio in modalità quantitativa
    - ``default_model``: modello usato se non ne viene indicato un altro

    Soglie e scale sono convenzioni: vanno tarate sulla realtà valutata.
    """

    name: str
    scale_p: Scale
    scale_m: Scale
    scale_v: Scale
    qualitative_classifier: Classifier
    quantitative_classifier: Optional[Classifier] = None
    quantitative_unit: str = ""
    default_model: RiskModel = field(default_factory=Multiplicative)

    @property
    def scales(self):
        return (self.scale_p, self.scale_m, self.scale_v)

    def assess(
        self,
        P: float,
        M: float,
        V: float,
        mode: Mode = Mode.QUALITATIVE,
        model: Optional[RiskModel] = None,
        unit: str = "",
    ) -> RiskResult:
        """Valuta uno scenario e, quando possibile, ne assegna il livello.

        ``unit`` sostituisce l'unità di default in modalità quantitativa
        (es. "giorni di inabilità/anno").
        """
        model = model or self.default_model
        inp = RiskInput(P=P, M=M, V=V, mode=mode)
        if mode is Mode.QUALITATIVE:
            result = model.evaluate(inp, self.scales)
            return self.qualitative_classifier.classify(result)
        result = model.evaluate(inp, unit=unit or self.quantitative_unit)
        if self.quantitative_classifier is not None:
            self.quantitative_classifier.classify(result)
        return result

    def describe(self) -> str:
        """Testo leggibile con le scale del dominio."""
        lines = [f"Dominio: {self.name}"]
        for scale in self.scales:
            lines.append(f"\n{scale.name} ({scale.minimum}-{scale.maximum})")
            for i, score in enumerate(range(scale.minimum, scale.maximum + 1)):
                label = scale.labels[i] if scale.labels else ""
                desc = scale.descriptions[i] if scale.descriptions else ""
                lines.append(f"  {score} {label}" + (f": {desc}" if desc else ""))
        lines.append("\nLivelli (indice normalizzato):")
        for limit, label in self.qualitative_classifier.thresholds:
            lines.append(f"  <= {limit:g}  {label}")
        lines.append(f"  oltre      {self.qualitative_classifier.top_label}")
        return "\n".join(lines)
