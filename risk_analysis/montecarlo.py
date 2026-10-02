"""Simulazione Monte Carlo: P, M e V come distribuzioni invece che numeri singoli.

Serve a rappresentare l'incertezza delle stime. Ogni fattore si descrive con
una distribuzione (per esempio triangolare: minimo, più probabile, massimo);
si simulano molti scenari e si ottiene la distribuzione del rischio, con media,
percentili e probabilità di ricadere in ciascun livello.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Union

import numpy as np

from .core import Mode
from .domains.base import Domain
from .models import RiskModel


class Distribution:
    def sample(self, rng: np.random.Generator, n: int) -> np.ndarray:
        raise NotImplementedError


@dataclass(frozen=True)
class Fixed(Distribution):
    value: float

    def sample(self, rng, n):
        return np.full(n, float(self.value))


@dataclass(frozen=True)
class Uniform(Distribution):
    low: float
    high: float

    def __post_init__(self):
        if self.high < self.low:
            raise ValueError("Uniform: high deve essere >= low")

    def sample(self, rng, n):
        return rng.uniform(self.low, self.high, n)


@dataclass(frozen=True)
class Triangular(Distribution):
    """Distribuzione triangolare: minimo, valore più probabile, massimo."""

    low: float
    mode: float
    high: float

    def __post_init__(self):
        if not (self.low <= self.mode <= self.high):
            raise ValueError("Triangular: serve low <= mode <= high")

    def sample(self, rng, n):
        if self.low == self.high:
            return np.full(n, float(self.low))
        return rng.triangular(self.low, self.mode, self.high, n)


@dataclass(frozen=True)
class PERT(Distribution):
    """Distribuzione PERT (beta): come la triangolare ma con code più morbide.

    ``lam`` regola il peso del valore più probabile (4 è il valore classico).
    """

    low: float
    mode: float
    high: float
    lam: float = 4.0

    def __post_init__(self):
        if not (self.low <= self.mode <= self.high):
            raise ValueError("PERT: serve low <= mode <= high")

    def sample(self, rng, n):
        if self.low == self.high:
            return np.full(n, float(self.low))
        span = self.high - self.low
        alpha = 1 + self.lam * (self.mode - self.low) / span
        beta = 1 + self.lam * (self.high - self.mode) / span
        return self.low + span * rng.beta(alpha, beta, n)


Spec = Union[float, int, Distribution]


def _as_distribution(spec: Spec) -> Distribution:
    return spec if isinstance(spec, Distribution) else Fixed(float(spec))


@dataclass
class MonteCarloResult:
    samples: np.ndarray
    unit: str
    index_samples: Optional[np.ndarray] = None
    level_probabilities: Optional[Dict[str, float]] = None

    @property
    def mean(self) -> float:
        return float(self.samples.mean())

    @property
    def std(self) -> float:
        return float(self.samples.std(ddof=1))

    def percentile(self, q: float) -> float:
        return float(np.percentile(self.samples, q))

    def summary(self) -> str:
        f = _fmt
        lines = [
            f"Simulazioni: {len(self.samples)}",
            f"Media:   {f(self.mean)} {self.unit}",
            f"Dev.std: {f(self.std)}",
            f"P5:  {f(self.percentile(5))}   P50: {f(self.percentile(50))}   "
            f"P95: {f(self.percentile(95))}",
        ]
        if self.level_probabilities:
            lines.append("Probabilità per livello:")
            for label, prob in self.level_probabilities.items():
                lines.append(f"  {label:<12} {prob * 100:5.1f}%")
        return "\n".join(lines)


def _fmt(x: float) -> str:
    """Formato numerico all'italiana: 58.440 oppure 23,98."""
    if abs(x) >= 1000:
        return f"{x:,.0f}".replace(",", ".")
    return f"{x:.4g}".replace(".", ",")


def simulate(
    domain: Domain,
    P: Spec,
    M: Spec,
    V: Spec,
    mode: Mode = Mode.QUALITATIVE,
    model: Optional[RiskModel] = None,
    n: int = 10_000,
    seed: Optional[int] = None,
) -> MonteCarloResult:
    """Simula il rischio di uno scenario con fattori incerti.

    In modalità qualitativa i campioni sono limitati all'intervallo di ciascuna
    scala; in modalità quantitativa V è limitata a [0, 1] e P, M a valori >= 0.
    """
    if n < 2:
        raise ValueError("Servono almeno 2 simulazioni")
    model = model or domain.default_model
    if mode not in model.modes:
        raise ValueError(f"Il modello '{model.name}' non supporta la modalità {mode.value}")

    rng = np.random.default_rng(seed)
    p = _as_distribution(P).sample(rng, n)
    m = _as_distribution(M).sample(rng, n)
    v = _as_distribution(V).sample(rng, n)

    if mode is Mode.QUALITATIVE:
        sp, sm, sv = domain.scales
        p = np.clip(p, sp.minimum, sp.maximum)
        m = np.clip(m, sm.minimum, sm.maximum)
        v = np.clip(v, sv.minimum, sv.maximum)
        values, index = model.compute(p, m, v, mode, domain.scales)
        classifier = domain.qualitative_classifier
        unit = model.default_unit(mode, domain.scales)
    else:
        p = np.clip(p, 0, None)
        m = np.clip(m, 0, None)
        v = np.clip(v, 0, 1)
        values, index = model.compute(p, m, v, mode, None)
        classifier = domain.quantitative_classifier
        unit = domain.quantitative_unit

    levels = None
    if classifier is not None:
        target = index if classifier.on == "index" else values
        if target is not None:
            limits = np.array([t for t, _ in classifier.thresholds]) + 1e-9
            positions = np.searchsorted(limits, target, side="left")
            counts = np.bincount(positions, minlength=len(classifier.labels))
            levels = {label: float(c) / n for label, c in zip(classifier.labels, counts)}

    return MonteCarloResult(
        samples=np.asarray(values, dtype=float),
        unit=unit,
        index_samples=None if index is None else np.asarray(index, dtype=float),
        level_probabilities=levels,
    )
