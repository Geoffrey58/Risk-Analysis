import csv

import pytest

from risk_analysis import (
    CYBERSECURITY,
    PERT,
    SICUREZZA_LAVORO,
    Mode,
    RiskRegister,
    Triangular,
    Uniform,
    simulate,
)


def test_ingressi_fissi_danno_il_valore_deterministico():
    mc = simulate(SICUREZZA_LAVORO, 2, 4, 3, n=100, seed=0)
    assert mc.mean == pytest.approx(24)
    assert mc.level_probabilities["Alto"] == pytest.approx(1.0)


def test_probabilita_dei_livelli_sommano_a_uno():
    mc = simulate(CYBERSECURITY, Triangular(1, 3, 5), Triangular(2, 4, 5), Uniform(1, 5), n=5000, seed=1)
    assert sum(mc.level_probabilities.values()) == pytest.approx(1.0)


def test_campioni_qualitativi_restano_nella_scala():
    mc = simulate(SICUREZZA_LAVORO, Uniform(0, 10), 4, 4, n=2000, seed=2)
    assert mc.samples.max() <= 64
    assert mc.samples.min() >= 16


def test_quantitativo_media_coerente():
    # E[P·M·V] = E[P]·E[M]·E[V] per fattori indipendenti
    mc = simulate(
        CYBERSECURITY,
        Uniform(1, 3), Uniform(1000, 3000), Uniform(0.1, 0.3),
        mode=Mode.QUANTITATIVE, n=200_000, seed=3,
    )
    assert mc.mean == pytest.approx(2 * 2000 * 0.2, rel=0.02)
    assert mc.unit == "€/anno"


def test_pert_entro_i_limiti():
    import numpy as np

    s = PERT(10, 20, 50).sample(np.random.default_rng(0), 10_000)
    assert s.min() >= 10 and s.max() <= 50


def test_registro_ordinamento_e_csv(tmp_path):
    reg = RiskRegister(SICUREZZA_LAVORO)
    reg.add("R01", "Basso", 1, 1, 1)
    reg.add("R02", "Alto", 4, 4, 4)
    reg.add("R03", "Medio", 2, 2, 4)
    assert [e.code for e in reg.ranked()] == ["R02", "R03", "R01"]

    with pytest.raises(ValueError):
        reg.add("R01", "duplicato", 1, 1, 1)

    path = tmp_path / "registro.csv"
    reg.to_csv(str(path))
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh, delimiter=";"))
    assert rows[0][0] == "Codice"
    assert rows[1][0] == "R02"
    assert rows[1][rows[0].index("Livello")] == "Molto alto"
