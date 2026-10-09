"""Registro dei rischi: valuta più scenari dello stesso dominio e li ordina."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

from .core import Mode, RiskResult
from .domains.base import Domain
from .models import RiskModel


@dataclass
class RiskEntry:
    """Voce del registro.

    - ``result``: rischio inerente (prima delle misure, o con le misure attuali)
    - ``residual``: rischio residuo, se è stata indicata la V dopo le misure
    - ``measures``: misure di mitigazione che portano da ``result`` a ``residual``
    - ``owner``: responsabile del rischio (risk owner)
    - ``links``: codici di rischi collegati, anche di altri registri
      (es. un rischio d'impatto IA collegato a uno scenario ISMS)
    """

    code: str
    description: str
    result: RiskResult
    residual: Optional[RiskResult] = None
    measures: str = ""
    owner: str = ""
    links: Tuple[str, ...] = field(default_factory=tuple)


class RiskRegister:
    """Elenco di scenari di rischio valutati con lo stesso dominio.

    Esempio::

        reg = RiskRegister(SICUREZZA_LAVORO)
        reg.add("R01", "Caduta dall'alto da cestello", P=2, M=4, V=2)
        for entry in reg.ranked():
            print(entry.code, entry.result)
    """

    def __init__(self, domain: Domain, model: Optional[RiskModel] = None, label: str = ""):
        self.domain = domain
        self.model = model
        self.label = label or domain.name
        self.entries: List[RiskEntry] = []

    def _check_code(self, code: str) -> None:
        if any(e.code == code for e in self.entries):
            raise ValueError(f"Codice rischio duplicato: {code}")

    def _append(self, code, description, result, residual, measures, owner, links) -> RiskEntry:
        if isinstance(links, str):
            links = (links,)
        entry = RiskEntry(code, description, result, residual, measures, owner, tuple(links))
        self.entries.append(entry)
        return entry

    def add(
        self,
        code: str,
        description: str,
        P: float,
        M: float,
        V: float,
        mode: Mode = Mode.QUALITATIVE,
        model: Optional[RiskModel] = None,
        V_residual: Optional[float] = None,
        measures: str = "",
        owner: str = "",
        links: Iterable[str] = (),
    ) -> RiskEntry:
        """Aggiunge uno scenario. Con ``V_residual`` calcola anche il rischio
        residuo, a parità di P e M: le misure agiscono sulla vulnerabilità."""
        self._check_code(code)
        model = model or self.model
        result = self.domain.assess(P, M, V, mode=mode, model=model)
        residual = None
        if V_residual is not None:
            residual = self.domain.assess(P, M, V_residual, mode=mode, model=model)
        return self._append(code, description, result, residual, measures, owner, links)

    def add_scenario(
        self,
        code: str,
        description: str,
        asset,
        affects,
        P: float,
        V: float,
        model: Optional[RiskModel] = None,
        V_residual: Optional[float] = None,
        measures: str = "",
        owner: str = "",
        links: Iterable[str] = (),
    ) -> RiskEntry:
        """Scenario cyber su un asset: M è ricavato dalle dimensioni C, I, A colpite."""
        from .domains.cia import assess_scenario

        self._check_code(code)
        model = model or self.model
        result = assess_scenario(asset, affects, P, V, model=model)
        residual = None
        if V_residual is not None:
            residual = assess_scenario(asset, affects, P, V_residual, model=model)
        return self._append(code, f"{description} [{asset.name}]", result, residual,
                            measures, owner, links)

    def add_use_case(
        self,
        code: str,
        description: str,
        caso,
        affects,
        P: float,
        V: float,
        model: Optional[RiskModel] = None,
        V_residual: Optional[float] = None,
        measures: str = "",
        owner: str = "",
        links: Iterable[str] = (),
    ) -> RiskEntry:
        """Scenario d'impatto IA su un caso d'uso: M è ricavato dagli interessi
        delle persone colpiti (S, R, N, D, I, E), con gli aggravanti del caso d'uso."""
        from .domains.impatto_ia import assess_use_case

        self._check_code(code)
        model = model or self.model
        result = assess_use_case(caso, affects, P, V, model=model)
        residual = None
        if V_residual is not None:
            residual = assess_use_case(caso, affects, P, V_residual, model=model)
        return self._append(code, f"{description} [{caso.nome}]", result, residual,
                            measures, owner, links)

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
        to_csv_combined(path, [self], delimiter=delimiter)

    def __len__(self) -> int:
        return len(self.entries)


HEADER = [
    "Codice", "Descrizione", "Modalità", "P", "M", "V",
    "Modello", "R", "Unità", "Indice", "Livello",
    "V residua", "R residuo", "Livello residuo", "Misure", "Responsabile",
    "Collegamenti", "Valutazione",
]


def _row(e: RiskEntry, label: str) -> List[str]:
    r, res = e.result, e.residual
    return [
        e.code, e.description, r.mode.value,
        _fmt(r.details["P"]), _fmt(r.details["M"]), _fmt(r.details["V"]),
        r.model, _fmt(r.value), r.unit,
        "" if r.index is None else _fmt(r.index), r.level or "",
        "" if res is None else _fmt(res.details["V"]),
        "" if res is None else _fmt(res.value),
        "" if res is None else (res.level or ""),
        e.measures, e.owner, ", ".join(e.links), label,
    ]


def to_csv_combined(
    path: str, registers: Sequence[RiskRegister], delimiter: str = ";"
) -> None:
    """Esporta più registri in un unico file, con la colonna "Valutazione".

    Serve a tenere distinte ma affiancate la valutazione d'impatto IA e quella
    di sicurezza delle informazioni. Ogni registro resta ordinato per rischio.
    """
    codes = [e.code for reg in registers for e in reg.entries]
    dup = {c for c in codes if codes.count(c) > 1}
    if dup:
        raise ValueError(f"Codici duplicati tra registri: {', '.join(sorted(dup))}")
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=delimiter)
        writer.writerow(HEADER)
        for reg in registers:
            for e in reg.ranked():
                writer.writerow(_row(e, reg.label))


def _fmt(x: float) -> str:
    return f"{x:.4g}".replace(".", ",")
