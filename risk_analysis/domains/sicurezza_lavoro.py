"""Profilo per la sicurezza sul lavoro.

Modalità qualitativa
--------------------
Estende la matrice P × D tradizionale dei DVR con un terzo fattore, la
vulnerabilità V, che misura quanto le misure di prevenzione e protezione in
atto sono carenti. Scale 1-4 per tutti e tre i fattori.

Le soglie sono costruite in modo che, con V = 4 (misure del tutto carenti),
il modello ricada esattamente nella classica matrice P × D:

    P×D 1-2 basso | 3-4 medio | 6-8 alto | 9-16 molto alto

Misure di prevenzione efficaci (V più bassa) riducono il livello di rischio.

Modalità quantitativa
---------------------
- P: frequenza attesa dell'evento pericoloso (eventi/anno)
- V: probabilità che l'evento produca un danno, date le barriere in atto [0, 1]
- M: danno per evento, in un'unità a scelta (giorni di inabilità, euro, ...)

R è il danno atteso per anno, nell'unità di M.
"""

from __future__ import annotations

from ..classification import Classifier
from ..core import Scale
from ..models import Multiplicative
from .base import Domain

SCALE_P = Scale(
    name="Probabilità (P)",
    minimum=1,
    maximum=4,
    labels=("Improbabile", "Poco probabile", "Probabile", "Altamente probabile"),
    descriptions=(
        "il danno può derivare solo dal concorso di più eventi poco probabili; nessun episodio noto",
        "il danno può derivare solo in circostanze sfortunate; episodi rarissimi",
        "il danno può derivare, anche se non in modo automatico; episodi noti in azienda o nel settore",
        "correlazione diretta tra la mancanza rilevata e il danno; episodi già verificatisi",
    ),
)

SCALE_M = Scale(
    name="Magnitudo del danno (M)",
    minimum=1,
    maximum=4,
    labels=("Lieve", "Medio", "Grave", "Gravissimo"),
    descriptions=(
        "infortunio o esposizione con inabilità rapidamente reversibile",
        "infortunio o esposizione con inabilità reversibile",
        "infortunio o esposizione con effetti di invalidità parziale",
        "infortunio o esposizione con effetti letali o di invalidità totale",
    ),
)

SCALE_V = Scale(
    name="Vulnerabilità (V)",
    minimum=1,
    maximum=4,
    labels=("Bassa", "Media", "Alta", "Molto alta"),
    descriptions=(
        "misure collettive, DPI, procedure e formazione presenti ed efficaci",
        "misure presenti ma con carenze lievi o non sempre applicate",
        "misure parziali, formazione o vigilanza insufficienti",
        "misure di prevenzione e protezione assenti o inefficaci",
    ),
)

# Soglie sull'indice comune (radice cubica del prodotto normalizzato).
# Con V = 4 l'indice vale (P·D/16)^(1/3): le soglie corrispondono a P·D = 2, 4, 8.
CLASSIFIER = Classifier(
    thresholds=[
        ((2 / 16) ** (1 / 3), "Basso"),
        ((4 / 16) ** (1 / 3), "Medio"),
        ((8 / 16) ** (1 / 3), "Alto"),
    ],
    top_label="Molto alto",
)

ACTIONS = {
    "Basso": "Azioni migliorative da valutare in fase di programmazione",
    "Medio": "Azioni correttive da programmare nel breve-medio termine",
    "Alto": "Azioni correttive necessarie, da programmare con urgenza",
    "Molto alto": "Azioni correttive indilazionabili",
}

SICUREZZA_LAVORO = Domain(
    name="Sicurezza sul lavoro",
    scale_p=SCALE_P,
    scale_m=SCALE_M,
    scale_v=SCALE_V,
    qualitative_classifier=CLASSIFIER,
    quantitative_unit="danno atteso/anno (unità di M)",
    default_model=Multiplicative(),
)


def action_for(level: str) -> str:
    """Priorità di intervento associata al livello di rischio."""
    return ACTIONS.get(level, "")
