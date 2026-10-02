import json
import math
from pathlib import Path

import pytest

from risk_analysis import Asset, ImpactCriteria, availability_from_downtime

CONFIG = Path(__file__).parent.parent / "config" / "criteri_impatto.json"


def test_livello_da_danno_economico():
    c = ImpactCriteria()  # 2k / 10k / 50k / 250k
    assert c.level_from_loss(0) == 1
    assert c.level_from_loss(2_000) == 1          # soglia inclusa nel livello inferiore
    assert c.level_from_loss(2_001) == 2
    assert c.level_from_loss(30_000) == 3
    assert c.level_from_loss(250_000) == 4
    assert c.level_from_loss(1_000_000) == 5


def test_intervalli_e_danno_tipico():
    c = ImpactCriteria()
    assert c.loss_range(1) == (0.0, 2_000)
    assert c.loss_range(3) == (10_000, 50_000)
    assert c.loss_range(5)[1] == math.inf
    assert c.representative_loss(1) == pytest.approx(1_000)
    assert c.representative_loss(3) == pytest.approx(math.sqrt(10_000 * 50_000))
    assert c.representative_loss(5) == pytest.approx(500_000)
    for level in range(1, 6):   # il danno tipico ricade nel suo livello
        assert c.level_from_loss(c.representative_loss(level)) == level


def test_soglie_personalizzate():
    c = ImpactCriteria("Piccola impresa", economic_limits=(500, 2_000, 10_000, 50_000),
                       downtime_hours=(8, 48, 120, 336))
    assert c.level_from_loss(30_000) == 4
    assert c.level_from_downtime(36) == 4
    assert availability_from_downtime(36, c) == 4
    assert availability_from_downtime(36) == 3   # criteri predefiniti


@pytest.mark.parametrize(
    "limits",
    [(1, 2, 3), (1, 2, 3, 4, 5), (10, 5, 20, 30), (0, 1, 2, 3), (1, 1, 2, 3)],
)
def test_soglie_non_valide(limits):
    with pytest.raises(ValueError):
        ImpactCriteria(economic_limits=limits)


def test_file_di_configurazione_del_repository():
    c = ImpactCriteria.load(CONFIG)
    assert c == ImpactCriteria()   # il modello coincide con i valori predefiniti


def test_salva_e_rileggi(tmp_path):
    c = ImpactCriteria("Alfa S.r.l.", "€", (1_000, 5_000, 20_000, 100_000), (2, 12, 48, 120))
    path = tmp_path / "criteri.json"
    c.save(path)
    assert ImpactCriteria.load(path) == c
    assert json.loads(path.read_text(encoding="utf-8"))["organizzazione"] == "Alfa S.r.l."


def test_chiavi_mancanti_usano_i_predefiniti(tmp_path):
    path = tmp_path / "parziale.json"
    path.write_text('{"organizzazione": "Beta", "soglie_economiche": [1, 2, 3, 4]}', encoding="utf-8")
    c = ImpactCriteria.load(path)
    assert c.organization == "Beta"
    assert c.downtime_hours == ImpactCriteria().downtime_hours


def test_asset_da_stime_economiche():
    c = ImpactCriteria()
    a = Asset.from_estimates("CRM", loss_confidentiality=80_000, loss_integrity=15_000,
                             tolerable_hours=36, criteria=c)
    assert (a.confidentiality, a.integrity, a.availability) == (4, 3, 3)
    # con fermo e danno di disponibilità vale il livello più alto
    b = Asset.from_estimates("CRM", 80_000, 15_000, tolerable_hours=36,
                             loss_availability=300_000, criteria=c)
    assert b.availability == 5
    with pytest.raises(ValueError):
        Asset.from_estimates("CRM", 1, 1, criteria=c)


def test_danno_tipico_dello_scenario():
    c = ImpactCriteria()
    a = Asset("x", confidentiality=4, integrity=2, availability=1)
    assert a.impact_loss("R", c) == pytest.approx(c.representative_loss(4))
    assert a.impact_loss("D", c) == pytest.approx(c.representative_loss(1))


def test_descrizione_con_criteri():
    c = ImpactCriteria()
    testo = Asset("x", 3, 1, 5).describe(c)
    assert "da 10.000 € a 50.000 €" in testo
    assert "sotto 4 ore" in testo
