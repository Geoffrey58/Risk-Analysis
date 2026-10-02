"""Esempio: rischio cyber, qualitativo (ISO/IEC 27005) e quantitativo (ALE, ROSI).

Esecuzione:  python examples/esempio_cybersecurity.py
"""

from risk_analysis import CYBERSECURITY, PERT, Mode, RiskRegister, simulate
from risk_analysis.domains.cybersecurity import ale, impact_cia, rosi, sle

dominio = CYBERSECURITY

print("=" * 70)
print("1. Registro qualitativo (scale 1-5)")
print("=" * 70)
reg = RiskRegister(dominio)
reg.add("C01", "Phishing con furto di credenziali", P=4, M=impact_cia(4, 3, 2), V=3)
reg.add("C02", "Ransomware sul file server", P=3, M=impact_cia(3, 5, 5), V=3)
reg.add("C03", "Data breach del gestionale clienti", P=2, M=impact_cia(5, 3, 2), V=2)
reg.add("C04", "Guasto hardware senza ridondanza", P=2, M=impact_cia(1, 2, 4), V=4)

for e in reg.ranked():
    r = e.result
    print(f"{e.code}  {e.description:<40} P={r.details['P']:.0f} M={r.details['M']:.0f} "
          f"V={r.details['V']:.0f}  R={r.value:>4.0f}/125  {r.level}")

print()
print("=" * 70)
print("2. Quantitativo: ransomware, prima e dopo la contromisura")
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
print("3. Monte Carlo sull'ALE con stime incerte")
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
