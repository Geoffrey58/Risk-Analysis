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
from ..criteria import DEFAULT_CRITERIA, ImpactCriteria
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


def availability_from_downtime(
    tolerable_hours: float, criteria: ImpactCriteria = DEFAULT_CRITERIA
) -> int:
    """Livello di disponibilità (1-5) dato il fermo massimo tollerabile, in ore.

    Le soglie in ore sono quelle dei criteri dell'organizzazione.
    """
    return criteria.level_from_downtime(tolerable_hours)


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

    def impact_loss(
        self, affects: Iterable[DimensionSpec], criteria: ImpactCriteria = DEFAULT_CRITERIA
    ) -> float:
        """Danno tipico in euro dell'impatto dello scenario, secondo i criteri.

        Utile come stima di prima approssimazione della SLE quando non si ha
        una valutazione economica diretta.
        """
        return criteria.representative_loss(self.impact(affects))

    @classmethod
    def from_estimates(
        cls,
        name: str,
        loss_confidentiality: float,
        loss_integrity: float,
        tolerable_hours: Optional[float] = None,
        loss_availability: Optional[float] = None,
        criteria: ImpactCriteria = DEFAULT_CRITERIA,
        value: Optional[float] = None,
    ) -> "Asset":
        """Crea l'asset dalle stime di danno in euro, tradotte in livelli dai criteri.

        Per la disponibilità si può indicare il fermo tollerabile in ore
        (``tolerable_hours``), il danno in euro (``loss_availability``) o
        entrambi: in quest'ultimo caso vale il livello più alto, per prudenza.
        """
        levels = []
        if tolerable_hours is not None:
            levels.append(criteria.level_from_downtime(tolerable_hours))
        if loss_availability is not None:
            levels.append(criteria.level_from_loss(loss_availability))
        if not levels:
            raise ValueError("Per la disponibilità serve tolerable_hours oppure loss_availability")
        return cls(
            name=name,
            confidentiality=criteria.level_from_loss(loss_confidentiality),
            integrity=criteria.level_from_loss(loss_integrity),
            availability=max(levels),
            value=value,
        )

    def describe(self, criteria: Optional[ImpactCriteria] = None) -> str:
        """Profilo leggibile. Con ``criteria`` mostra le fasce dell'organizzazione
        (euro per riservatezza e integrità, ore di fermo per la disponibilità)
        invece delle descrizioni standard."""
        lines = [f"Asset: {self.name}"]
        for dim in CIA:
            scale = SCALES[dim]
            lvl = self.level(dim)
            if criteria is None:
                text = scale.descriptions[lvl - scale.minimum]
            elif dim is CIA.A:
                text = _downtime_text(lvl, criteria)
            else:
                text = _loss_text(lvl, criteria)
            lines.append(f"  {dim.value:<14} {lvl}  {scale.label(lvl):<13} {text}")
        return "\n".join(lines)


def _money(x: float, currency: str) -> str:
    return f"{x:,.0f}".replace(",", ".") + f" {currency}"


def _loss_text(level: int, criteria: ImpactCriteria) -> str:
    low, high = criteria.loss_range(level)
    c = criteria.currency
    if level == 1:
        return f"danno fino a {_money(high, c)}"
    if level == 5:
        return f"danno oltre {_money(low, c)}"
    return f"danno da {_money(low, c)} a {_money(high, c)}"


def _downtime_text(level: int, criteria: ImpactCriteria) -> str:
    h = criteria.downtime_hours
    return {
        5: f"fermo tollerabile sotto {h[0]:g} ore",
        4: f"fermo tollerabile da {h[0]:g} a {h[1]:g} ore",
        3: f"fermo tollerabile da {h[1]:g} a {h[2]:g} ore",
        2: f"fermo tollerabile da {h[2]:g} a {h[3]:g} ore",
        1: f"fermo tollerabile di {h[3]:g} ore o più",
    }[level]


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
