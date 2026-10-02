"""Registro dei rischi: valuta più scenari dello stesso dominio e li ordina."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import List, Optional

from .core import Mode, RiskResult
from .domains.base import Domain
from .models import RiskModel


@dataclass
class RiskEntry:
    code: str
    description: str
    result: RiskResult


class RiskRegister:
    """Elenco di scenari di rischio valutati con lo stesso dominio.

    Esempio::

        reg = RiskRegister(SICUREZZA_LAVORO)
        reg.add("R01", "Caduta dall'alto da cestello", P=2, M=4, V=2)
        for entry in reg.ranked():
            print(entry.code, entry.result)
    """

    def __init__(self, domain: Domain, model: Optional[RiskModel] = None):
        self.domain = domain
        self.model = model
        self.entries: List[RiskEntry] = []

    def add(
        self,
        code: str,
        description: str,
        P: float,
        M: float,
        V: float,
        mode: Mode = Mode.QUALITATIVE,
        model: Optional[RiskModel] = None,
    ) -> RiskEntry:
        if any(e.code == code for e in self.entries):
            raise ValueError(f"Codice rischio duplicato: {code}")
        result = self.domain.assess(P, M, V, mode=mode, model=model or self.model)
        entry = RiskEntry(code, description, result)
        self.entries.append(entry)
        return entry

    def ranked(self) -> List[RiskEntry]:
        """Scenari ordinati dal rischio più alto al più basso.

        Gli scenari qualitativi sono ordinati per indice normalizzato, quelli
        quantitativi per valore; i qualitativi vengono prima.
        """
        qualitative = [e for e in self.entries if e.result.index is not None]
        quantitative = [e for e in self.entries if e.result.index is None]
        qualitative.sort(key=lambda e: e.result.index, reverse=True)
        quantitative.sort(key=lambda e: e.result.value, reverse=True)
        return qualitative + quantitative

    def to_csv(self, path: str, delimiter: str = ";") -> None:
        """Esporta il registro ordinato. Il separatore ';' si apre bene in Excel italiano."""
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh, delimiter=delimiter)
            writer.writerow(
                ["Codice", "Descrizione", "Modalità", "P", "M", "V",
                 "Modello", "R", "Unità", "Indice", "Livello"]
            )
            for e in self.ranked():
                r = e.result
                writer.writerow([
                    e.code, e.description, r.mode.value,
                    _fmt(r.details["P"]), _fmt(r.details["M"]), _fmt(r.details["V"]),
                    r.model, _fmt(r.value), r.unit,
                    "" if r.index is None else _fmt(r.index), r.level or "",
                ])

    def __len__(self) -> int:
        return len(self.entries)


def _fmt(x: float) -> str:
    return f"{x:.4g}".replace(".", ",")
