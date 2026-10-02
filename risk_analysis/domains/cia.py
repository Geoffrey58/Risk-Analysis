"""Impatto M a partire da riservatezza, integrità e disponibilità.

Le tre dimensioni si valutano sull'asset, una volta sola, con la domanda:
"cosa succede se perdo la riservatezza / l'integrità / la disponibilità di
questo asset?" (logica della Business Impact Analysis).

Lo scenario di rischio indica poi quali dimensioni la minaccia compromette.
L'impatto è il massimo tra le sole dimensioni colpite:

    M = max { C·δC , I·δI , A·δA }     con δ = 1 se la dimensione è colpita

Notazione: nel codice si usano C, I, A (Confidentiality, Integrity,
Availability) al posto di R, I, D per non confondere la riservatezza con il
rischio R.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional, Tuple, Union

from ..core import Mode, RiskResult, Scale
from ..models import RiskModel


class CIA(str, Enum):
    """Dimensioni della sicurezza delle informazioni."""

    C = "Riservatezza"
    I = "Integrità"
    A = "Disponibilità"


SCALE_C = Scale(
    name="Riservatezza (C)",
    minimum=1,
    maximum=5,
    labels=("Trascurabile", "Limitato", "Significativo", "Grave", "Critico"),
    descriptions=(
        "informazioni pubbliche",
        "informazioni interne, nessun dato personale",
        "dati personali comuni o informazioni commerciali riservate",
        "dati personali su larga scala, segreti industriali, dati finanziari",
        "categorie particolari di dati (art. 9 GDPR), dati giudiziari, credenziali privilegiate",
    ),
)

SCALE_I = Scale(
    name="Integrità (I)",
    minimum=1,
    maximum=5,
    labels=("Trascurabile", "Limitato", "Significativo", "Grave", "Critico"),
    descriptions=(
        "errore irrilevante o subito evidente",
        "correggibile con poco lavoro, nessun effetto esterno",
        "decisioni o documenti errati, effetti su clienti o fornitori",
        "errori contabili, contrattuali o legali con effetti economici rilevanti",
        "effetti sulla sicurezza fisica delle persone, sugli impianti o sugli obblighi di legge",
    ),
)

SCALE_A = Scale(
    name="Disponibilità (A)",
    minimum=1,
    maximum=5,
    labels=("Trascurabile", "Limitato", "Significativo", "Grave", "Critico"),
    descriptions=(
        "fermo tollerabile oltre 1 settimana",
        "fermo tollerabile da 3 giorni a 1 settimana",
        "fermo tollerabile da 1 a 3 giorni",
        "fermo tollerabile da 4 a 24 ore",
        "fermo tollerabile inferiore a 4 ore (servizi essenziali)",
    ),
)

SCALES = {CIA.C: SCALE_C, CIA.I: SCALE_I, CIA.A: SCALE_A}

# Ore di fermo tollerabile che delimitano i livelli di disponibilità (dal 5 al 2)
_AVAILABILITY_HOURS = ((4, 5), (24, 4), (72, 3), (168, 2))


def availability_from_downtime(tolerable_hours: float) -> int:
    """Livello di disponibilità (1-5) dato il fermo massimo tollerabile, in ore."""
    if tolerable_hours <= 0:
        raise ValueError("Il fermo tollerabile deve essere positivo")
    for limit, level in _AVAILABILITY_HOURS:
        if tolerable_hours < limit:
            return level
    return 1


DimensionSpec = Union[str, CIA]


def _parse_dimensions(dimensions: Iterable[DimensionSpec]) -> Tuple[CIA, ...]:
    """Accetta CIA.C oppure le lettere 'C', 'I', 'A' (anche 'R', 'I', 'D')."""
    alias = {"C": CIA.C, "R": CIA.C, "I": CIA.I, "A": CIA.A, "D": CIA.A}
    out = []
    for d in dimensions:
        if isinstance(d, CIA):
            dim = d
        else:
            key = str(d).strip().upper()
            if key not in alias:
                raise ValueError(f"Dimensione sconosciuta: {d!r} (usare C, I, A oppure R, I, D)")
            dim = alias[key]
        if dim not in out:
            out.append(dim)
    if not out:
        raise ValueError("Lo scenario deve colpire almeno una dimensione tra C, I, A")
    return tuple(out)


@dataclass(frozen=True)
class Asset:
    """Asset informativo con il suo profilo di impatto C, I, A (scale 1-5).

    ``value`` (facoltativo) è il valore economico dell'asset, utile in
    modalità quantitativa per calcolare la perdita per evento (SLE).
    """

    name: str
    confidentiality: int
    integrity: int
    availability: int
    value: Optional[float] = None
    notes: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        SCALE_C.validate(self.confidentiality)
        SCALE_I.validate(self.integrity)
        SCALE_A.validate(self.availability)
        if self.value is not None and self.value < 0:
            raise ValueError("Il valore dell'asset non può essere negativo")

    def level(self, dim: CIA) -> int:
        return {CIA.C: self.confidentiality, CIA.I: self.integrity, CIA.A: self.availability}[dim]

    def impact(self, affects: Iterable[DimensionSpec]) -> int:
        """M = massimo tra le sole dimensioni colpite dallo scenario."""
        return max(self.level(d) for d in _parse_dimensions(affects))

    def describe(self) -> str:
        lines = [f"Asset: {self.name}"]
        for dim in CIA:
            scale = SCALES[dim]
            lvl = self.level(dim)
            lines.append(
                f"  {dim.value:<14} {lvl}  {scale.label(lvl):<13} "
                f"{scale.descriptions[lvl - scale.minimum]}"
            )
        return "\n".join(lines)


def assess_scenario(
    asset: Asset,
    affects: Iterable[DimensionSpec],
    P: float,
    V: float,
    model: Optional[RiskModel] = None,
) -> RiskResult:
    """Valuta uno scenario cyber qualitativo su un asset.

    M è ricavato dall'asset considerando solo le dimensioni colpite.
    Nei dettagli del risultato sono riportate le dimensioni considerate.
    """
    from .cybersecurity import CYBERSECURITY  # import locale per evitare cicli

    dims = _parse_dimensions(affects)
    m = asset.impact(dims)
    result = CYBERSECURITY.assess(P, m, V, mode=Mode.QUALITATIVE, model=model)
    result.details.update({f"impatto_{d.name}": asset.level(d) for d in dims})
    return result
