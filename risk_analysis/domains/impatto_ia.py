"""Valutazione d'impatto dei sistemi di IA sulle persone (AI Act).

È la valutazione che affianca, senza sostituirla, quella di sicurezza delle
informazioni (profilo ``CYBERSECURITY`` e modulo ``cia``):

- la valutazione ISMS guarda agli **asset informativi** dell'organizzazione
  (riservatezza, integrità, disponibilità);
- la valutazione d'impatto IA guarda alle **persone** su cui ricadono gli
  effetti di un caso d'uso del sistema di IA (salute e sicurezza, diritti
  fondamentali), nella logica degli artt. 9 e 27 del Regolamento (UE) 2024/1689.

L'oggetto della valutazione è il **caso d'uso** (un sistema impiegato per una
certa finalità su certe categorie di persone), non il sistema in astratto:
lo stesso sistema usato per finalità diverse dà casi d'uso diversi.

Classificazione AI Act
----------------------
Prima del calcolo il caso d'uso è classificato (``ClasseAIAct``). Un caso
d'uso che ricade nelle pratiche vietate (art. 5) non si valuta: il risultato
ha livello "Vietato". La classificazione resta registrata nei dettagli.

Impatto M
---------
Per ciascun caso d'uso si stima, una volta sola, quanto sarebbe grave per le
persone la lesione di ciascun interesse tutelato (scala 1-5):

- S  Salute e sicurezza
- R  Riservatezza e protezione dei dati personali
- N  Non discriminazione ed equità di trattamento
- D  Dignità e correttezza del trattamento (pressioni indebite, toni vessatori, manipolazione)
- I  Informazione corretta e autodeterminazione (decisioni prese su informazioni errate)
- E  Effetti economici e giuridici sulla persona

Lo scenario indica quali interessi colpisce e, come per R, I, D sugli asset,
M è il massimo tra quelli colpiti. M è poi aggravato di un livello (fino a 5)
in presenza di almeno un fattore aggravante del caso d'uso:

- persone vulnerabili (es. debitori in difficoltà economica, minori, lavoratori)
- larga scala (molte persone coinvolte dallo stesso evento)
- effetti difficilmente reversibili

    M = min(5, max{ L_k · δ_k } + aggravio),   aggravio = min(n. aggravanti, aggravio_massimo)

Vulnerabilità V
---------------
V misura quanto sono carenti le misure che impediscono all'evento di produrre
il danno: supervisione umana effettiva, verifica degli output, trasparenza,
formazione, controlli documentati. Il rischio residuo si ottiene con la V
dopo le misure, a parità di P e M.

Le scale e le soglie sono convenzioni da tarare sull'organizzazione.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, Optional, Tuple, Union

from ..classification import Classifier
from ..core import Mode, RiskResult, Scale
from ..models import Multiplicative, RiskModel
from .base import Domain


class ClasseAIAct(str, Enum):
    """Classificazione del caso d'uso ai sensi del Regolamento (UE) 2024/1689."""

    VIETATO = "Pratica vietata (art. 5)"
    ALTO_RISCHIO = "Alto rischio (art. 6, Allegati I e III)"
    TRASPARENZA = "Obblighi di trasparenza (art. 50)"
    MINIMO = "Non ad alto rischio"


class Interesse(str, Enum):
    """Interessi delle persone tutelati nella valutazione d'impatto."""

    S = "Salute e sicurezza"
    R = "Riservatezza e dati personali"
    N = "Non discriminazione"
    D = "Dignità e correttezza"
    I = "Informazione corretta"
    E = "Effetti economici e giuridici"


SCALE_P = Scale(
    name="Probabilità dell'evento (P)",
    minimum=1,
    maximum=5,
    labels=("Rara", "Improbabile", "Possibile", "Probabile", "Quasi certa"),
    descriptions=(
        "richiede condizioni eccezionali; mai osservato",
        "non osservato nell'uso aziendale, ma noto in letteratura per sistemi simili",
        "comportamento noto del sistema (es. errori, invenzioni); può verificarsi nell'uso ordinario",
        "già osservato occasionalmente nell'uso aziendale",
        "ricorrente; si verifica regolarmente nell'uso ordinario",
    ),
)

SCALE_M = Scale(
    name="Gravità dell'impatto sulle persone (M)",
    minimum=1,
    maximum=5,
    labels=("Trascurabile", "Limitato", "Significativo", "Grave", "Critico"),
    descriptions=(
        "disagio minimo, subito rimediabile, nessun effetto sui diritti",
        "disagio o errore correggibile senza conseguenze per la persona",
        "lesione di un diritto o effetto economico rimediabile (es. comunicazione errata, dati visti da terzi)",
        "lesione rilevante di diritti fondamentali o effetti economici o giuridici difficilmente rimediabili",
        "danno alla salute o alla sicurezza, discriminazione sistematica, effetti irreversibili",
    ),
)

SCALE_V = Scale(
    name="Carenza delle misure (V)",
    minimum=1,
    maximum=5,
    labels=("Molto bassa", "Bassa", "Media", "Alta", "Molto alta"),
    descriptions=(
        "supervisione umana effettiva su ogni output, verifiche documentate e controllate, personale formato",
        "misure efficaci con lacune minori; controlli a campione regolari",
        "supervisione prevista ma non verificata; regole solo organizzative",
        "supervisione formale (rischio di automation bias), nessuna verifica documentata",
        "nessuna supervisione: l'output è usato direttamente",
    ),
)

SCALES: Dict[Interesse, Scale] = {k: SCALE_M for k in Interesse}

# Stesse soglie del profilo cyber: 0,4 / 0,6 / 0,8 corrispondono a P = M = V = 2, 3, 4,
# così i livelli delle due valutazioni sono confrontabili.
CLASSIFIER = Classifier(
    thresholds=[(0.4, "Basso"), (0.6, "Medio"), (0.8, "Alto")],
    top_label="Critico",
)

IMPATTO_IA = Domain(
    name="Impatto IA sulle persone (AI Act)",
    scale_p=SCALE_P,
    scale_m=SCALE_M,
    scale_v=SCALE_V,
    qualitative_classifier=CLASSIFIER,
    quantitative_unit="persone danneggiate/anno",
    default_model=Multiplicative(),
)

LIVELLO_VIETATO = "Vietato"

InteresseSpec = Union[str, Interesse]


def _parse_interessi(interessi: Iterable[InteresseSpec]) -> Tuple[Interesse, ...]:
    """Accetta Interesse.R oppure le lettere 'S', 'R', 'N', 'D', 'I', 'E'."""
    out = []
    for x in interessi:
        if isinstance(x, Interesse):
            k = x
        else:
            key = str(x).strip().upper()
            try:
                k = Interesse[key]
            except KeyError:
                raise ValueError(
                    f"Interesse sconosciuto: {x!r} (usare S, R, N, D, I, E)"
                ) from None
        if k not in out:
            out.append(k)
    if not out:
        raise ValueError("Lo scenario deve colpire almeno un interesse tra S, R, N, D, I, E")
    return tuple(out)


@dataclass(frozen=True)
class CasoUso:
    """Caso d'uso di un sistema di IA, con il suo profilo d'impatto sulle persone.

    ``impatti`` associa a ciascun interesse la gravità (1-5) di una sua lesione;
    gli interessi non indicati valgono 1. Si può passare un dizionario con le
    lettere: ``{"R": 4, "D": 3}``.
    """

    nome: str
    sistema: str
    finalita: str
    interessati: str
    impatti: Dict[InteresseSpec, int] = field(default_factory=dict)
    classe: ClasseAIAct = ClasseAIAct.MINIMO
    vulnerabili: bool = False
    larga_scala: bool = False
    irreversibile: bool = False
    aggravio_massimo: int = 1
    note: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        normalizzati = {}
        for k, v in dict(self.impatti).items():
            (key,) = _parse_interessi([k])
            SCALE_M.validate(v)
            normalizzati[key] = int(v)
        object.__setattr__(self, "impatti", normalizzati)
        if self.aggravio_massimo < 0:
            raise ValueError("aggravio_massimo non può essere negativo")

    def livello(self, interesse: InteresseSpec) -> int:
        (k,) = _parse_interessi([interesse])
        return self.impatti.get(k, 1)

    @property
    def aggravanti(self) -> Tuple[str, ...]:
        out = []
        if self.vulnerabili:
            out.append("persone vulnerabili")
        if self.larga_scala:
            out.append("larga scala")
        if self.irreversibile:
            out.append("effetti irreversibili")
        return tuple(out)

    @property
    def aggravio(self) -> int:
        return min(len(self.aggravanti), self.aggravio_massimo)

    def impact(self, affects: Iterable[InteresseSpec]) -> int:
        """M = massimo tra gli interessi colpiti, aggravato e limitato a 5."""
        base = max(self.livello(k) for k in _parse_interessi(affects))
        return min(SCALE_M.maximum, base + self.aggravio)

    def describe(self) -> str:
        lines = [
            f"Caso d'uso: {self.nome}",
            f"  Sistema:      {self.sistema}",
            f"  Finalità:     {self.finalita}",
            f"  Interessati:  {self.interessati}",
            f"  AI Act:       {self.classe.value}",
            f"  Aggravanti:   {', '.join(self.aggravanti) or 'nessuno'}",
        ]
        for k in Interesse:
            lvl = self.livello(k)
            lines.append(f"  {k.name} {k.value:<30} {lvl}  {SCALE_M.label(lvl)}")
        return "\n".join(lines)


def assess_use_case(
    caso: CasoUso,
    affects: Iterable[InteresseSpec],
    P: float,
    V: float,
    model: Optional[RiskModel] = None,
) -> RiskResult:
    """Valuta uno scenario qualitativo su un caso d'uso di IA.

    Se il caso d'uso è una pratica vietata il livello è "Vietato",
    indipendentemente dal punteggio.
    """
    interessi = _parse_interessi(affects)
    m = caso.impact(interessi)
    result = IMPATTO_IA.assess(P, m, V, mode=Mode.QUALITATIVE, model=model)
    result.details.update({f"impatto_{k.name}": caso.livello(k) for k in interessi})
    result.details["aggravio"] = caso.aggravio
    if caso.classe is ClasseAIAct.VIETATO:
        result.level = LIVELLO_VIETATO
    return result
