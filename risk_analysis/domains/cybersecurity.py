"""Profilo per la cybersecurity.

Modalità qualitativa
--------------------
Impostazione in linea con l'approccio di ISO/IEC 27005: il rischio di uno
scenario dipende dalla verosimiglianza della minaccia (P), dall'impatto
sull'asset (M) e dalla vulnerabilità sfruttata (V). Scale 1-5.

L'impatto M si ricava dal profilo di riservatezza, integrità e disponibilità
dell'asset, considerando solo le dimensioni colpite dalla minaccia: vedi
``Asset`` e ``assess_scenario`` nel modulo ``cia``. ``impact_cia`` resta
disponibile come scorciatoia quando lo scenario le colpisce tutte e tre.

Le soglie sono ancorate alla diagonale: il passaggio di livello avviene quando
tutti e tre i fattori valgono 2, 3 e 4. Con P = M = V = 3, ad esempio, il
rischio è esattamente al limite superiore del livello "Medio".

Modalità quantitativa (ALE)
---------------------------
- P: ARO, frequenza annua degli eventi di minaccia (tentativi/anno)
- V: probabilità che un evento di minaccia vada a segno [0, 1]
- M: SLE, perdita per singolo evento = valore dell'asset × fattore di esposizione

R = ARO × V × SLE è la perdita annua attesa (ALE), in €/anno.
"""

from __future__ import annotations

from ..classification import Classifier
from ..core import Mode, Scale
from ..models import Multiplicative
from .base import Domain

SCALE_P = Scale(
    name="Verosimiglianza della minaccia (P)",
    minimum=1,
    maximum=5,
    labels=("Rara", "Improbabile", "Possibile", "Probabile", "Quasi certa"),
    descriptions=(
        "meno di una volta ogni 10 anni; nessun attore motivato noto",
        "una volta ogni 3-10 anni",
        "una volta ogni 1-3 anni; minaccia diffusa nel settore",
        "più volte l'anno; campagne attive contro realtà simili",
        "continua o mensile; attacchi già osservati sull'organizzazione",
    ),
)

SCALE_M = Scale(
    name="Impatto (M)",
    minimum=1,
    maximum=5,
    labels=("Trascurabile", "Limitato", "Significativo", "Grave", "Critico"),
    descriptions=(
        "nessun effetto apprezzabile su servizi, dati o reputazione",
        "disservizio breve, dati non sensibili, effetti interni",
        "disservizio rilevante o dati personali coinvolti; possibile notifica",
        "fermo prolungato, violazione di dati su larga scala, sanzioni",
        "compromissione dei processi essenziali, danni gravi a persone o all'organizzazione",
    ),
)

SCALE_V = Scale(
    name="Vulnerabilità (V)",
    minimum=1,
    maximum=5,
    labels=("Molto bassa", "Bassa", "Media", "Alta", "Molto alta"),
    descriptions=(
        "controlli robusti e verificati; sfruttamento non praticabile",
        "controlli efficaci con lacune minori",
        "controlli parziali; sfruttamento richiede competenze specifiche",
        "debolezza nota, controlli insufficienti, exploit disponibili",
        "debolezza esposta e banale da sfruttare, nessun controllo",
    ),
)

# Soglie sull'indice comune: 0,4 / 0,6 / 0,8 corrispondono a P = M = V = 2, 3, 4.
CLASSIFIER = Classifier(
    thresholds=[(0.4, "Basso"), (0.6, "Medio"), (0.8, "Alto")],
    top_label="Critico",
)

CYBERSECURITY = Domain(
    name="Cybersecurity",
    scale_p=SCALE_P,
    scale_m=SCALE_M,
    scale_v=SCALE_V,
    qualitative_classifier=CLASSIFIER,
    quantitative_unit="€/anno",
    default_model=Multiplicative(),
)


def impact_cia(confidentiality: int, integrity: int, availability: int, method: str = "max") -> float:
    """Impatto M a partire da riservatezza, integrità e disponibilità (scala 1-5).

    ``method="max"`` (default) prende il valore peggiore, approccio prudenziale;
    ``method="mean"`` la media aritmetica.
    """
    values = (confidentiality, integrity, availability)
    for x in values:
        SCALE_M.validate(x)
    if method == "max":
        return float(max(values))
    if method == "mean":
        return sum(values) / 3
    raise ValueError("method deve essere 'max' oppure 'mean'")


def sle(asset_value: float, exposure_factor: float) -> float:
    """Single Loss Expectancy: perdita per singolo evento = valore × fattore di esposizione."""
    if asset_value < 0:
        raise ValueError("Il valore dell'asset non può essere negativo")
    if not (0.0 <= exposure_factor <= 1.0):
        raise ValueError("Il fattore di esposizione deve stare in [0, 1]")
    return asset_value * exposure_factor


def ale(aro: float, vulnerability: float, single_loss: float) -> float:
    """Annualized Loss Expectancy: ALE = ARO × V × SLE."""
    return CYBERSECURITY.assess(aro, single_loss, vulnerability, mode=Mode.QUANTITATIVE).value


def rosi(ale_before: float, ale_after: float, annual_cost: float) -> float:
    """Ritorno dell'investimento in sicurezza: (riduzione dell'ALE − costo) / costo."""
    if annual_cost <= 0:
        raise ValueError("Il costo annuo della contromisura deve essere positivo")
    return (ale_before - ale_after - annual_cost) / annual_cost
