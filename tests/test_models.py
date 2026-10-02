import math

import pytest

from risk_analysis import (
    CYBERSECURITY,
    SICUREZZA_LAVORO,
    Mode,
    Multiplicative,
    RiskAversion,
    RiskInput,
    Scale,
    WeightedAdditive,
    WeightedGeometric,
)
from risk_analysis.domains.cybersecurity import ale, impact_cia, rosi, sle

S4 = (Scale("P", 1, 4), Scale("M", 1, 4), Scale("V", 1, 4))


# --- Modelli -----------------------------------------------------------------

def test_moltiplicativo_qualitativo():
    r = Multiplicative().evaluate(RiskInput(2, 3, 4), S4)
    assert r.value == 24
    assert r.index == pytest.approx((24 / 64) ** (1 / 3))


def test_moltiplicativo_quantitativo_perdita_attesa():
    r = Multiplicative().evaluate(RiskInput(P=0.5, M=40, V=0.1, mode=Mode.QUANTITATIVE))
    assert r.value == pytest.approx(2.0)
    assert r.index is None


def test_geometrico_pesi_uguali_equivale_al_moltiplicativo():
    for p, m, v in [(1, 1, 1), (2, 3, 4), (4, 4, 4), (3, 1, 2)]:
        a = Multiplicative().evaluate(RiskInput(p, m, v), S4)
        b = WeightedGeometric().evaluate(RiskInput(p, m, v), S4)
        assert a.index == pytest.approx(b.index)


def test_geometrico_resta_sulla_scala_degli_ingressi():
    assert WeightedGeometric().evaluate(RiskInput(4, 4, 4), S4).value == pytest.approx(4)
    assert WeightedGeometric().evaluate(RiskInput(1, 1, 1), S4).value == pytest.approx(1)


def test_geometrico_pesa_di_piu_la_magnitudo():
    pesato = WeightedGeometric(weights=(1, 2, 1))
    alto_m = pesato.evaluate(RiskInput(1, 4, 1), S4).index
    alto_p = pesato.evaluate(RiskInput(4, 1, 1), S4).index
    assert alto_m > alto_p


def test_additivo_e_compensativo():
    r = WeightedAdditive().evaluate(RiskInput(1, 4, 4), S4)
    assert r.index == pytest.approx((0.25 + 1 + 1) / 3)


def test_avversione_k1_identita():
    base = Multiplicative()
    for p, m, v in [(2, 3, 4), (1, 2, 1)]:
        a = base.evaluate(RiskInput(p, m, v), S4)
        b = RiskAversion(base, k=1).evaluate(RiskInput(p, m, v), S4)
        assert a.value == pytest.approx(b.value)


def test_avversione_quantitativa_penalizza_i_danni_grandi():
    model = RiskAversion(Multiplicative(), k=2, m_ref=1000)
    piccolo = model.evaluate(RiskInput(1, 500, 1, Mode.QUANTITATIVE)).value
    grande = model.evaluate(RiskInput(1, 4000, 1, Mode.QUANTITATIVE)).value
    assert piccolo == pytest.approx(250)
    assert grande == pytest.approx(16000)


def test_avversione_quantitativa_richiede_m_ref():
    with pytest.raises(ValueError):
        RiskAversion(Multiplicative(), k=2).evaluate(RiskInput(1, 1, 1, Mode.QUANTITATIVE))


def test_pesi_negativi_rifiutati():
    with pytest.raises(ValueError):
        WeightedGeometric(weights=(1, -1, 1))


# --- Validazione ---------------------------------------------------------------

def test_punteggio_fuori_scala():
    with pytest.raises(ValueError):
        Multiplicative().evaluate(RiskInput(5, 1, 1), S4)


def test_v_quantitativa_deve_essere_probabilita():
    with pytest.raises(ValueError):
        Multiplicative().evaluate(RiskInput(1, 100, 1.5, Mode.QUANTITATIVE))


def test_modello_solo_qualitativo_rifiuta_quantitativa():
    with pytest.raises(ValueError):
        WeightedGeometric().evaluate(RiskInput(1, 1, 0.5, Mode.QUANTITATIVE))


# --- Sicurezza sul lavoro ------------------------------------------------------

def classic_pd_level(pd):
    if pd <= 2:
        return "Basso"
    if pd <= 4:
        return "Medio"
    if pd <= 8:
        return "Alto"
    return "Molto alto"


@pytest.mark.parametrize("p", [1, 2, 3, 4])
@pytest.mark.parametrize("d", [1, 2, 3, 4])
def test_con_v_massima_si_ritrova_la_matrice_pxd(p, d):
    r = SICUREZZA_LAVORO.assess(p, d, 4)
    assert r.level == classic_pd_level(p * d)


def test_misure_efficaci_riducono_il_livello():
    senza = SICUREZZA_LAVORO.assess(3, 4, 4).level
    con = SICUREZZA_LAVORO.assess(3, 4, 1).level
    ordine = ["Basso", "Medio", "Alto", "Molto alto"]
    assert ordine.index(con) < ordine.index(senza)


# --- Cybersecurity -------------------------------------------------------------

@pytest.mark.parametrize("x,level", [(1, "Basso"), (2, "Basso"), (3, "Medio"), (4, "Alto"), (5, "Critico")])
def test_soglie_ancorate_alla_diagonale(x, level):
    assert CYBERSECURITY.assess(x, x, x).level == level


def test_impatto_cia():
    assert impact_cia(2, 5, 3) == 5
    assert impact_cia(2, 5, 3, method="mean") == pytest.approx(10 / 3)
    with pytest.raises(ValueError):
        impact_cia(6, 1, 1)


def test_ale_e_rosi():
    perdita = sle(400_000, 0.30)
    assert perdita == pytest.approx(120_000)
    prima = ale(2.0, 0.15, perdita)
    dopo = ale(2.0, 0.03, perdita)
    assert prima == pytest.approx(36_000)
    assert dopo == pytest.approx(7_200)
    assert rosi(prima, dopo, 15_000) == pytest.approx((36_000 - 7_200 - 15_000) / 15_000)


def test_sle_fattore_esposizione_valido():
    with pytest.raises(ValueError):
        sle(1000, 1.2)


def test_risultato_leggibile():
    testo = str(SICUREZZA_LAVORO.assess(2, 4, 3))
    assert "R = 24" in testo and "Alto" in testo
    assert not math.isnan(SICUREZZA_LAVORO.assess(2, 4, 3).index)
