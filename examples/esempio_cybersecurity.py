"""Esempio: rischio cyber, qualitativo (ISO/IEC 27005) e quantitativo (ALE, ROSI).

Esecuzione:  python examples/esempio_cybersecurity.py
"""

from pathlib import Path

from risk_analysis import CYBERSECURITY, PERT, Asset, ImpactCriteria, Mode, RiskRegister, simulate
from risk_analysis import availability_from_downtime as disp
from risk_analysis.domains.cybersecurity import ale, rosi, sle

dominio = CYBERSECURITY

print("=" * 70)
print("0. Criteri di impatto dell'organizzazione (config/criteri_impatto.json)")
print("=" * 70)
criteri = ImpactCriteria.load(Path(__file__).parent.parent / "config" / "criteri_impatto.json")
print(criteri.describe())
print()
crm = Asset.from_estimates(
    "CRM commerciale",
    loss_confidentiality=80_000,   # sanzioni e danno d'immagine se i dati escono
    loss_integrity=15_000,         # ricostruzione dei dati alterati
    tolerable_hours=36,
    criteria=criteri,
)
print(crm.describe(criteri))
print(f"Danno tipico di un data breach (solo R): "
      f"{crm.impact_loss('R', criteri):,.0f} €".replace(",", "."))
print()
print("=" * 70)
print("1. Asset con il loro profilo R, I, D (scale 1-5)")
print("=" * 70)
gestionale = Asset("Gestionale clienti", confidentiality=4, integrity=4,
                   availability=disp(tolerable_hours=48))
file_server = Asset("File server", confidentiality=3, integrity=3,
                    availability=disp(tolerable_hours=8))
posta = Asset("Posta elettronica", confidentiality=3, integrity=2,
              availability=disp(tolerable_hours=24))
for a in (gestionale, file_server, posta):
    print(a.describe())

print()
print("=" * 70)
print("2. Registro: M calcolato solo sulle dimensioni colpite")
print("=" * 70)
reg = RiskRegister(dominio)
reg.add_scenario("C01", "Phishing con furto di credenziali", posta, affects="CI", P=4, V=3)
reg.add_scenario("C02", "Ransomware", file_server, affects="IA", P=3, V=3)
reg.add_scenario("C03", "Data breach", gestionale, affects="C", P=2, V=2)
reg.add_scenario("C04", "Guasto hardware senza ridondanza", file_server, affects="A", P=2, V=4)

for e in reg.ranked():
    r = e.result
    colpite = ", ".join(k[-1] for k in r.details if k.startswith("impatto_"))
    print(f"{e.code}  {e.description:<52} colpite: {colpite:<5} M={r.details['M']:.0f}  "
          f"R={r.value:>3.0f}/125  {r.level}")

print()
print("=" * 70)
print("3. Quantitativo: ransomware, prima e dopo la contromisura")
print("=" * 70)
perdita = sle(asset_value=400_000, exposure_factor=0.30)    # 120.000 € per evento
prima = ale(aro=2.0, vulnerability=0.15, single_loss=perdita)   # backup non isolati
dopo = ale(aro=2.0, vulnerability=0.03, single_loss=perdita)    # EDR + backup immutabili
costo = 15_000


def euro(x):
    return f"{x:>10,.0f}".replace(",", ".")


print(f"SLE:            {euro(perdita)} €")
print(f"ALE prima:      {euro(prima)} €/anno")
print(f"ALE dopo:       {euro(dopo)} €/anno")
print(f"Costo annuo:    {euro(costo)} €")
print(f"ROSI:           {rosi(prima, dopo, costo) * 100:>9.0f}%")

print()
print("=" * 70)
print("4. Monte Carlo sull'ALE con stime incerte")
print("=" * 70)
mc = simulate(
    dominio,
    P=PERT(0.5, 2, 6),             # tentativi efficaci/anno
    M=PERT(40_000, 120_000, 400_000),
    V=PERT(0.05, 0.15, 0.30),
    mode=Mode.QUANTITATIVE,
    n=50_000,
    seed=7,
)
print(mc.summary())
