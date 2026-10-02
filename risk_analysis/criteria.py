"""Criteri di impatto configurabili per organizzazione.

Ogni organizzazione definisce che cosa significa, in euro e in ore di fermo,
ciascun livello di impatto 1-5. In questo modo:

- i livelli di riservatezza, integrità e disponibilità sono confrontabili tra loro
- un danno stimato in euro si traduce in un livello (e viceversa)
- la valutazione qualitativa si collega a quella quantitativa (ALE)

I criteri si leggono da un file JSON, con questa struttura::

    {
      "organizzazione": "Nome S.r.l.",
      "valuta": "€",
      "soglie_economiche": [2000, 10000, 50000, 250000],
      "fermo_tollerabile_ore": [4, 24, 72, 168]
    }

``soglie_economiche`` sono i limiti superiori dei livelli 1, 2, 3 e 4: oltre
l'ultima soglia il livello è 5. ``fermo_tollerabile_ore`` sono i limiti dei
livelli di disponibilità: sotto 4 ore il livello è 5, sotto 24 è 4, sotto 72 è 3,
sotto 168 è 2, altrimenti 1.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Tuple, Union

LEVELS = (1, 2, 3, 4, 5)


def _check_ascending(values: Sequence[float], what: str) -> Tuple[float, ...]:
    values = tuple(float(v) for v in values)
    if len(values) != 4:
        raise ValueError(f"{what}: servono 4 valori (limiti tra i livelli 1-5), trovati {len(values)}")
    if any(v <= 0 for v in values):
        raise ValueError(f"{what}: i valori devono essere positivi")
    if any(b <= a for a, b in zip(values, values[1:])):
        raise ValueError(f"{what}: i valori devono essere strettamente crescenti")
    return values


@dataclass(frozen=True)
class ImpactCriteria:
    """Soglie economiche e di fermo che definiscono i livelli di impatto 1-5."""

    organization: str = "Esempio"
    currency: str = "€"
    economic_limits: Tuple[float, ...] = (2_000, 10_000, 50_000, 250_000)
    downtime_hours: Tuple[float, ...] = (4, 24, 72, 168)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "economic_limits", _check_ascending(self.economic_limits, "soglie_economiche")
        )
        object.__setattr__(
            self, "downtime_hours", _check_ascending(self.downtime_hours, "fermo_tollerabile_ore")
        )

    # --- euro <-> livello ----------------------------------------------------

    def level_from_loss(self, loss: float) -> int:
        """Livello di impatto (1-5) corrispondente a un danno economico."""
        if loss < 0:
            raise ValueError("Il danno economico non può essere negativo")
        for level, limit in zip(LEVELS, self.economic_limits):
            if loss <= limit:
                return level
        return 5

    def loss_range(self, level: int) -> Tuple[float, float]:
        """Intervallo di danno (minimo, massimo) di un livello; il livello 5 non ha massimo."""
        _check_level(level)
        low = 0.0 if level == 1 else self.economic_limits[level - 2]
        high = math.inf if level == 5 else self.economic_limits[level - 1]
        return low, high

    def representative_loss(self, level: int) -> float:
        """Danno tipico di un livello, per passare dal qualitativo al quantitativo.

        Livelli 2-4: media geometrica degli estremi (adatta a scale che crescono
        per moltiplicazione). Livello 1: metà della prima soglia. Livello 5: il
        doppio dell'ultima soglia. Sono convenzioni: per stime accurate conviene
        valutare direttamente il danno in euro.
        """
        low, high = self.loss_range(level)
        if level == 1:
            return high / 2
        if level == 5:
            return low * 2
        return math.sqrt(low * high)

    # --- fermo tollerabile -> livello di disponibilità ------------------------

    def level_from_downtime(self, tolerable_hours: float) -> int:
        """Livello di disponibilità (1-5) dato il fermo massimo tollerabile, in ore."""
        if tolerable_hours <= 0:
            raise ValueError("Il fermo tollerabile deve essere positivo")
        for limit, level in zip(self.downtime_hours, (5, 4, 3, 2)):
            if tolerable_hours < limit:
                return level
        return 1

    # --- lettura, scrittura, descrizione -------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> "ImpactCriteria":
        defaults = cls()
        return cls(
            organization=data.get("organizzazione", defaults.organization),
            currency=data.get("valuta", defaults.currency),
            economic_limits=tuple(data.get("soglie_economiche", defaults.economic_limits)),
            downtime_hours=tuple(data.get("fermo_tollerabile_ore", defaults.downtime_hours)),
        )

    def to_dict(self) -> dict:
        return {
            "organizzazione": self.organization,
            "valuta": self.currency,
            "soglie_economiche": list(self.economic_limits),
            "fermo_tollerabile_ore": list(self.downtime_hours),
        }

    @classmethod
    def load(cls, path: Union[str, Path]) -> "ImpactCriteria":
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        # le chiavi che iniziano con "_" sono note per chi compila il file
        return cls.from_dict({k: v for k, v in data.items() if not k.startswith("_")})

    def save(self, path: Union[str, Path]) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    def describe(self) -> str:
        c = self.currency
        lines = [f"Criteri di impatto — {self.organization}", "", "Livello  Danno economico"]
        for level in LEVELS:
            low, high = self.loss_range(level)
            if level == 1:
                text = f"fino a {_money(high, c)}"
            elif level == 5:
                text = f"oltre {_money(low, c)}"
            else:
                text = f"da {_money(low, c)} a {_money(high, c)}"
            lines.append(f"   {level}     {text}")
        h = self.downtime_hours
        lines += [
            "",
            "Livello  Fermo tollerabile",
            f"   5     meno di {h[0]:g} ore",
            f"   4     da {h[0]:g} a {h[1]:g} ore",
            f"   3     da {h[1]:g} a {h[2]:g} ore",
            f"   2     da {h[2]:g} a {h[3]:g} ore",
            f"   1     {h[3]:g} ore o più",
        ]
        return "\n".join(lines)


def _check_level(level: int) -> None:
    if level not in LEVELS:
        raise ValueError(f"Livello {level} non valido: deve essere tra 1 e 5")


def _money(x: float, currency: str) -> str:
    return f"{x:,.0f}".replace(",", ".") + f" {currency}"


DEFAULT_CRITERIA = ImpactCriteria()
