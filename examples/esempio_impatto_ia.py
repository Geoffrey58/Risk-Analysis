"""Esempio: valutazione d'impatto IA (AI Act) affiancata alla valutazione ISMS.

Azienda fittizia di servizi amministrativi che usa assistenti generativi.
Le due valutazioni restano distinte (persone / asset informativi) ma sono
collegate tra loro ed esportate in un unico registro.

Esecuzione:  python examples/esempio_impatto_ia.py
"""

from risk_analysis import (
    CYBERSECURITY,
    IMPATTO_IA,
    Asset,
    CasoUso,
    ClasseAIAct,
    RiskRegister,
    to_csv_combined,
)
from risk_analysis import availability_from_downtime as disp

print("=" * 72)
print("1. Casi d'uso dei sistemi di IA (oggetto della valutazione d'impatto)")
print("=" * 72)
comunicazioni = CasoUso(
    "Bozze di comunicazioni ai clienti", sistema="Assistente generativo",
    finalita="redazione di modelli di lettera", interessati="clienti privati",
    impatti={"D": 3, "I": 3, "E": 2}, vulnerabili=True,
)
selezione = CasoUso(
    "Sintesi dei curricula", sistema="Assistente generativo",
    finalita="supporto alla selezione del personale", interessati="candidati",
    impatti={"N": 4, "E": 4, "R": 3}, larga_scala=True,
    classe=ClasseAIAct.ALTO_RISCHIO,   # gestione dei lavoratori: Allegato III, punto 4
)
for c in (comunicazioni, selezione):
    print(c.describe())
    print()

print("=" * 72)
print("2. Registro d'impatto IA: inerente (V=5, nessuna misura) e residuo")
print("=" * 72)
ia = RiskRegister(IMPATTO_IA, label="IA")
ia.add_use_case("IA01", "Tono scorretto o informazioni inesatte", comunicazioni, "DI",
                P=3, V=5, V_residual=2, measures="modelli approvati; revisione umana",
                owner="Responsabile AI", links=["IS01"])
ia.add_use_case("IA02", "Esclusione discriminatoria di candidati", selezione, "NE",
                P=3, V=5, V_residual=3, measures="decisione umana; criteri documentati",
                owner="HR")

for e in ia.ranked():
    r, res = e.result, e.residual
    print(f"{e.code}  {e.description:<58} M={r.details['M']:.0f}  "
          f"inerente {r.level:<8} → residuo {res.level}")

print()
print("=" * 72)
print("3. Registro ISMS sugli asset informativi, collegato al precedente")
print("=" * 72)
posta = Asset("Posta elettronica", confidentiality=4, integrity=3,
              availability=disp(tolerable_hours=24))
isms = RiskRegister(CYBERSECURITY, label="ISMS")
isms.add_scenario("IS01", "Dati di clienti inseriti in un servizio di IA gratuito", posta,
                  affects="C", P=3, V=5, V_residual=3,
                  measures="piano aziendale; DLP; formazione", owner="CISO", links=["IA01"])
for e in isms.ranked():
    print(f"{e.code}  {e.description:<58} inerente {e.result.level:<8} "
          f"→ residuo {e.residual.level}")

to_csv_combined("registro_integrato_esempio.csv", [ia, isms])
print("\nRegistro integrato salvato in registro_integrato_esempio.csv")
