"""Modelli matematici per R = f(P, M, V).

Tutti i modelli condividono la stessa interfaccia: si possono scambiare e
confrontare sullo stesso scenario. Il calcolo (``compute``) funziona sia su
numeri singoli sia su array numpy, così lo stesso modello è usato anche dalla
simulazione Monte Carlo.

Modelli disponibili
-------------------
- ``Multiplicative``       R = P · M · V                    (qualitativa e quantitativa)
- ``WeightedGeometric``    R = P^a · M^b · V^c, a+b+c = 1  (qualitativa)
- ``WeightedAdditive``     R = a·P + b·M + c·V              (qualitativa, compensativo)
- ``RiskAversion``         sostituisce M con M^k, k > 1     (si applica a un altro modello)

Indice comune
------------
In modalità qualitativa ogni modello restituisce, oltre al valore, un indice in
(0, 1] che rappresenta il livello medio dei tre fattori normalizzati (media
geometrica per i modelli moltiplicativi, aritmetica per l'additivo). Grazie a
questo le soglie di classificazione di un dominio valgono per tutti i modelli.

In modalità quantitativa il modello moltiplicativo coincide con la perdita
attesa: R = λ · V · M, con λ frequenza annua (o probabilità) dell'evento,
V probabilità che il sistema ceda dato l'evento, M danno per evento.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence, Tuple

from .core import Mode, RiskInput, RiskResult, Scale

Scales = Tuple[Scale, Scale, Scale]


def _normalize_weights(weights: Sequence[float]) -> Tuple[float, float, float]:
    if len(weights) != 3:
        raise ValueError("Servono tre pesi, nell'ordine (P, M, V)")
    if any(w < 0 for w in weights):
        raise ValueError("I pesi non possono essere negativi")
    total = float(sum(weights))
    if total <= 0:
        raise ValueError("La somma dei pesi deve essere positiva")
    return tuple(w / total for w in weights)  # type: ignore[return-value]


def validate_input(inp: RiskInput, scales: Optional[Scales]) -> None:
    """Controlla che P, M, V siano coerenti con la modalità scelta."""
    if inp.mode is Mode.QUALITATIVE:
        if scales is None:
            raise ValueError("In modalità qualitativa servono le scale di P, M e V")
        sp, sm, sv = scales
        sp.validate(inp.P)
        sm.validate(inp.M)
        sv.validate(inp.V)
    else:
        if inp.P < 0:
            raise ValueError("P (probabilità o frequenza) non può essere negativa")
        if inp.M < 0:
            raise ValueError("M (magnitudo del danno) non può essere negativa")
        if not (0.0 <= inp.V <= 1.0):
            raise ValueError(
                "In modalità quantitativa V è una probabilità condizionata: deve stare in [0, 1]"
            )


class RiskModel(ABC):
    """Interfaccia comune di tutti i modelli."""

    name: str = "modello"
    modes = frozenset({Mode.QUALITATIVE})

    def evaluate(
        self,
        inp: RiskInput,
        scales: Optional[Scales] = None,
        unit: str = "",
    ) -> RiskResult:
        if inp.mode not in self.modes:
            supported = ", ".join(m.value for m in self.modes)
            raise ValueError(
                f"Il modello '{self.name}' non supporta la modalità {inp.mode.value} "
                f"(supporta: {supported})"
            )
        validate_input(inp, scales)
        value, index = self.compute(inp.P, inp.M, inp.V, inp.mode, scales)
        return RiskResult(
            value=float(value),
            index=None if index is None else float(index),
            model=self.name,
            mode=inp.mode,
            unit=unit or self.default_unit(inp.mode, scales),
            details={"P": inp.P, "M": inp.M, "V": inp.V},
        )

    @abstractmethod
    def compute(self, p, m, v, mode: Mode, scales: Optional[Scales]):
        """Restituisce (valore, indice normalizzato o None). Accetta array numpy."""

    def default_unit(self, mode: Mode, scales: Optional[Scales]) -> str:
        return ""

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


class Multiplicative(RiskModel):
    """R = P · M · V.

    Qualitativa: il valore è il prodotto dei punteggi (con scale 1-4 va da 1 a 64).
    L'indice è la radice cubica del prodotto dei valori normalizzati, cioè il
    "livello medio equivalente" dei tre fattori: così è confrontabile con gli
    indici degli altri modelli e si classifica con le stesse soglie.
    Quantitativa: è la perdita attesa per periodo, nell'unità di M.
    Se un fattore è nullo il rischio è nullo: il modello non è compensativo.
    """

    name = "moltiplicativo"
    modes = frozenset({Mode.QUALITATIVE, Mode.QUANTITATIVE})

    def compute(self, p, m, v, mode, scales):
        value = p * m * v
        if mode is Mode.QUANTITATIVE:
            return value, None
        sp, sm, sv = scales
        index = (sp.normalize(p) * sm.normalize(m) * sv.normalize(v)) ** (1 / 3)
        return value, index

    def default_unit(self, mode, scales):
        if mode is Mode.QUALITATIVE:
            sp, sm, sv = scales
            return f"punti (1-{sp.maximum * sm.maximum * sv.maximum})"
        return ""


class WeightedGeometric(RiskModel):
    """R = P^a · M^b · V^c con a + b + c = 1 (media geometrica pesata).

    Mantiene la logica moltiplicativa ma riporta il risultato sulla stessa scala
    degli ingressi: con P, M, V tutti su scala 1-5, anche R va da 1 a 5.
    I pesi permettono di dare più importanza a un fattore (es. la magnitudo).
    """

    name = "geometrico pesato"

    def __init__(self, weights: Sequence[float] = (1, 1, 1)):
        self.weights = _normalize_weights(weights)

    def compute(self, p, m, v, mode, scales):
        a, b, c = self.weights
        sp, sm, sv = scales
        index = sp.normalize(p) ** a * sm.normalize(m) ** b * sv.normalize(v) ** c
        common = _common_maximum(scales)
        value = index * common if common else index
        return value, index

    def default_unit(self, mode, scales):
        common = _common_maximum(scales)
        return f"punti (scala 1-{common})" if common else "indice (0-1]"

    def __repr__(self) -> str:
        return f"WeightedGeometric(weights={tuple(round(w, 3) for w in self.weights)})"


class WeightedAdditive(RiskModel):
    """R = a·P + b·M + c·V con a + b + c = 1.

    Attenzione: il modello è compensativo. Un evento quasi impossibile ma con
    danno enorme ottiene comunque un punteggio alto. Va usato come indice di
    priorità, non come stima del rischio.
    """

    name = "additivo pesato"

    def __init__(self, weights: Sequence[float] = (1, 1, 1)):
        self.weights = _normalize_weights(weights)

    def compute(self, p, m, v, mode, scales):
        a, b, c = self.weights
        sp, sm, sv = scales
        index = a * sp.normalize(p) + b * sm.normalize(m) + c * sv.normalize(v)
        common = _common_maximum(scales)
        value = index * common if common else index
        return value, index

    def default_unit(self, mode, scales):
        common = _common_maximum(scales)
        return f"punti (scala 1-{common})" if common else "indice (0-1]"

    def __repr__(self) -> str:
        return f"WeightedAdditive(weights={tuple(round(w, 3) for w in self.weights)})"


class RiskAversion(RiskModel):
    """Correzione per avversione al rischio: M viene sostituita da M^k, k > 1.

    Penalizza gli eventi rari ma catastrofici. Per non alterare le unità:

    - qualitativa:  M' = Mmax · (M / Mmax)^k   (resta nella stessa scala)
    - quantitativa: M' = Mref · (M / Mref)^k   (Mref = danno di riferimento)

    Con k = 1 il modello coincide con quello di base.
    """

    def __init__(self, base: RiskModel, k: float = 1.5, m_ref: Optional[float] = None):
        if k < 1:
            raise ValueError("L'esponente di avversione k deve essere >= 1")
        self.base = base
        self.k = float(k)
        self.m_ref = m_ref
        self.name = f"{base.name} + avversione (k={self.k:g})"
        self.modes = base.modes

    def compute(self, p, m, v, mode, scales):
        if mode is Mode.QUALITATIVE:
            m_max = scales[1].maximum
            m_adj = m_max * (m / m_max) ** self.k
        else:
            if not self.m_ref:
                raise ValueError(
                    "In modalità quantitativa serve m_ref, il danno di riferimento "
                    "rispetto a cui misurare l'avversione"
                )
            m_adj = self.m_ref * (m / self.m_ref) ** self.k
        return self.base.compute(p, m_adj, v, mode, scales)

    def default_unit(self, mode, scales):
        return self.base.default_unit(mode, scales)

    def __repr__(self) -> str:
        return f"RiskAversion({self.base!r}, k={self.k:g}, m_ref={self.m_ref})"


def _common_maximum(scales: Optional[Scales]) -> Optional[int]:
    if not scales:
        return None
    maxima = {s.maximum for s in scales}
    return maxima.pop() if len(maxima) == 1 else None


def compare(
    inp: RiskInput,
    models: Sequence[RiskModel],
    scales: Optional[Scales] = None,
    unit: str = "",
):
    """Valuta lo stesso scenario con più modelli, saltando quelli non applicabili."""
    results = []
    for model in models:
        if inp.mode in model.modes:
            results.append(model.evaluate(inp, scales, unit))
    return results
