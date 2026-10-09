import csv

import pytest

from risk_analysis import (
    CYBERSECURITY,
    IMPATTO_IA,
    Asset,
    CasoUso,
    ClasseAIAct,
    Interesse,
    RiskRegister,
    assess_use_case,
    to_csv_combined,
)

SOLLECITI = CasoUso(
    nome="Format di sollecito",
    sistema="Assistente generativo",
    finalita="redazione di modelli di sollecito",
    interessati="debitori",
    impatti={"D": 3, "I": 3, "R": 2},
    vulnerabili=True,
)


def test_impatto_massimo_sugli_interessi_colpiti_con_aggravio():
    assert SOLLECITI.impact("R") == 3          # 2 + 1 per persone vulnerabili
    assert SOLLECITI.impact("DI") == 4         # 3 + 1
    assert SOLLECITI.impact([Interesse.S]) == 2  # non indicato: vale 1, + 1


def test_aggravio_limitato_e_massimo_cinque():
    caso = CasoUso("x", "s", "f", "i", impatti={"E": 5}, vulnerabili=True,
                   larga_scala=True, irreversibile=True)
    assert caso.aggravio == 1
    assert caso.impact("E") == 5
    caso2 = CasoUso("x", "s", "f", "i", impatti={"E": 3}, vulnerabili=True,
                    larga_scala=True, aggravio_massimo=2)
    assert caso2.impact("E") == 5


def test_senza_aggravanti():
    caso = CasoUso("x", "s", "f", "i", impatti={"R": 3})
    assert caso.aggravio == 0
    assert caso.impact("R") == 3


def test_interessi_e_livelli_non_validi():
    with pytest.raises(ValueError):
        SOLLECITI.impact("X")
    with pytest.raises(ValueError):
        SOLLECITI.impact("")
    with pytest.raises(ValueError):
        CasoUso("x", "s", "f", "i", impatti={"R": 6})
    with pytest.raises(ValueError):
        CasoUso("x", "s", "f", "i", impatti={"Z": 2})


def test_valutazione_equivale_al_dominio_con_m_ricavato():
    r = assess_use_case(SOLLECITI, "DI", P=3, V=2)
    atteso = IMPATTO_IA.assess(3, 4, 2)
    assert r.value == atteso.value
    assert r.level == atteso.level
    assert r.details["impatto_D"] == 3
    assert r.details["aggravio"] == 1
    assert "impatto_S" not in r.details


def test_pratica_vietata_non_si_valuta_con_il_punteggio():
    caso = CasoUso("Riconoscimento emozioni", "s", "f", "lavoratori",
                   impatti={"D": 2}, classe=ClasseAIAct.VIETATO)
    r = assess_use_case(caso, "D", P=1, V=1)
    assert r.level == "Vietato"


def test_rischio_residuo_con_v_ridotta():
    reg = RiskRegister(IMPATTO_IA, label="IA")
    e = reg.add_use_case("IA01", "Tono vessatorio", SOLLECITI, "D", P=3, V=4,
                         V_residual=2, measures="revisione dei format", owner="Resp. AI")
    assert e.residual is not None
    assert e.residual.value < e.result.value
    assert e.residual.details["M"] == e.result.details["M"]
    assert "[Format di sollecito]" in e.description


def test_registro_combinato_ia_e_isms(tmp_path):
    ia = RiskRegister(IMPATTO_IA, label="IA")
    ia.add_use_case("IA01", "Tono vessatorio", SOLLECITI, "D", P=3, V=3,
                    V_residual=2, links=["ISMS01"])
    isms = RiskRegister(CYBERSECURITY, label="ISMS")
    posta = Asset("Posta", confidentiality=4, integrity=3, availability=3)
    isms.add_scenario("ISMS01", "Prompt injection", posta, "C", P=3, V=4,
                      V_residual=3, links="IA01")
    path = tmp_path / "registro.csv"
    to_csv_combined(str(path), [ia, isms])
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh, delimiter=";"))
    h = rows[0]
    assert [r[h.index("Valutazione")] for r in rows[1:]] == ["IA", "ISMS"]
    assert rows[1][h.index("Collegamenti")] == "ISMS01"
    assert rows[2][h.index("Livello residuo")] != ""


def test_registro_combinato_rifiuta_codici_duplicati(tmp_path):
    a = RiskRegister(IMPATTO_IA)
    a.add_use_case("X1", "a", SOLLECITI, "D", P=1, V=1)
    b = RiskRegister(IMPATTO_IA)
    b.add_use_case("X1", "b", SOLLECITI, "D", P=1, V=1)
    with pytest.raises(ValueError):
        to_csv_combined(str(tmp_path / "x.csv"), [a, b])
