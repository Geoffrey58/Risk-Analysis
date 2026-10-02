import pytest

from risk_analysis import CIA, Asset, RiskRegister, assess_scenario, availability_from_downtime
from risk_analysis import CYBERSECURITY

ASSET = Asset("Gestionale", confidentiality=5, integrity=3, availability=2)


def test_impatto_solo_sulle_dimensioni_colpite():
    assert ASSET.impact("A") == 2            # guasto: la riservatezza non conta
    assert ASSET.impact("C") == 5            # data breach
    assert ASSET.impact("IA") == 3           # ransomware senza esfiltrazione
    assert ASSET.impact("CIA") == 5


def test_notazione_italiana_r_i_d():
    assert ASSET.impact("RID") == ASSET.impact("CIA")
    assert ASSET.impact(["D"]) == ASSET.impact([CIA.A])


def test_dimensioni_non_valide():
    with pytest.raises(ValueError):
        ASSET.impact("X")
    with pytest.raises(ValueError):
        ASSET.impact("")


def test_asset_fuori_scala():
    with pytest.raises(ValueError):
        Asset("x", 6, 1, 1)


@pytest.mark.parametrize(
    "hours,level",
    [(2, 5), (3.9, 5), (4, 4), (23, 4), (24, 3), (71, 3), (72, 2), (167, 2), (168, 1), (500, 1)],
)
def test_disponibilita_da_fermo_tollerabile(hours, level):
    assert availability_from_downtime(hours) == level


def test_scenario_equivale_a_valutazione_con_m_ricavato():
    r = assess_scenario(ASSET, "A", P=3, V=4)
    atteso = CYBERSECURITY.assess(3, 2, 4)
    assert r.value == atteso.value
    assert r.level == atteso.level
    assert r.details["impatto_A"] == 2
    assert "impatto_C" not in r.details


def test_registro_con_scenari():
    reg = RiskRegister(CYBERSECURITY)
    reg.add_scenario("C01", "Data breach", ASSET, "C", P=3, V=3)
    reg.add_scenario("C02", "Guasto", ASSET, "A", P=3, V=3)
    assert [e.code for e in reg.ranked()] == ["C01", "C02"]
    assert "[Gestionale]" in reg.entries[0].description
    with pytest.raises(ValueError):
        reg.add_scenario("C01", "dup", ASSET, "C", P=1, V=1)
