"""Esempio: valutazione dei rischi per un cantiere, modalità qualitativa e quantitativa.

Esecuzione:  python examples/esempio_sicurezza_lavoro.py
"""

from risk_analysis import (
    SICUREZZA_LAVORO,
    Mode,
    Multiplicative,
    RiskAversion,
    RiskInput,
    RiskRegister,
    Triangular,
    WeightedGeometric,
    compare,
    simulate,
)
from risk_analysis.domains.sicurezza_lavoro import action_for

dominio = SICUREZZA_LAVORO

print("=" * 70)
print("1. Registro dei rischi (scale 1-4)")
print("=" * 70)
reg = RiskRegister(dominio)
reg.add("R01", "Caduta dall'alto da piattaforma di lavoro elevabile", P=2, M=4, V=2)
reg.add("R02", "Elettrocuzione su quadro in tensione", P=2, M=4, V=3)
reg.add("R03", "Investimento da traffico veicolare", P=3, M=4, V=2)
reg.add("R04", "Movimentazione manuale dei carichi", P=3, M=2, V=3)
reg.add("R05", "Tagli e abrasioni", P=3, M=1, V=2)

for e in reg.ranked():
    r = e.result
    print(f"{e.code}  {e.description:<52} P={r.details['P']:.0f} M={r.details['M']:.0f} "
          f"V={r.details['V']:.0f}  R={r.value:>4.0f}  {r.level:<10}")
    print(f"      -> {action_for(r.level)}")

print()
print("=" * 70)
print("2. Stesso scenario, modelli diversi (R04: P=3, M=2, V=3)")
print("=" * 70)
scenario = RiskInput(P=3, M=2, V=3)
modelli = [
    Multiplicative(),
    WeightedGeometric(),
    WeightedGeometric(weights=(1, 2, 1)),   # magnitudo con peso doppio
    RiskAversion(Multiplicative(), k=1.5),  # penalizza meno i danni lievi
]
for res in compare(scenario, modelli, dominio.scales):
    dominio.qualitative_classifier.classify(res)
    print(res)

print()
print("=" * 70)
print("3. Incertezza sulle stime: Monte Carlo (R03)")
print("=" * 70)
mc = simulate(
    dominio,
    P=Triangular(2, 3, 4),
    M=4,
    V=Triangular(1, 2, 3),
    n=20_000,
    seed=1,
)
print(mc.summary())

print()
print("=" * 70)
print("4. Modalità quantitativa: giorni di inabilità attesi per anno")
print("=" * 70)
# 0,5 eventi pericolosi/anno, nel 10% dei casi le barriere non bastano,
# danno medio di 40 giorni di inabilità per infortunio
r = dominio.assess(P=0.5, M=40, V=0.10, mode=Mode.QUANTITATIVE,
                   unit="giorni di inabilità/anno")
print(r)
