# Risk Analysis

Strumento in Python per il calcolo del rischio come funzione di tre fattori:

$$R = f(P, M, V)$$

- **P** — probabilità (o frequenza) dell'evento
- **M** — magnitudo del danno conseguente
- **V** — vulnerabilità del sistema esposto

È pensato per essere applicato a più ambiti, con due profili già pronti:
**sicurezza sul lavoro** e **cybersecurity**. Funziona in due modalità:

| Modalità | P | M | V | R |
|---|---|---|---|---|
| Qualitativa | punteggio su scala | punteggio su scala | punteggio su scala | punteggio e livello |
| Quantitativa | probabilità o frequenza annua | danno per evento (€, giorni, ...) | probabilità condizionata in [0, 1] | danno atteso per anno |

## Installazione

```bash
git clone https://github.com/Geoffrey58/Risk-Analysis.git
cd Risk-Analysis
pip install -e .
```

Per eseguire gli esempi e i test:

```bash
python examples/esempio_sicurezza_lavoro.py
python examples/esempio_cybersecurity.py
pip install -e ".[test]" && pytest
```

## Uso rapido

```python
from risk_analysis import SICUREZZA_LAVORO, CYBERSECURITY, Mode

# Sicurezza sul lavoro, scale 1-4
r = SICUREZZA_LAVORO.assess(P=2, M=4, V=3)
print(r)            # [moltiplicativo] R = 24 punti (1-64) | indice 0.721 | livello: Alto

# Cybersecurity quantitativa: perdita annua attesa
r = CYBERSECURITY.assess(P=2.0, M=120_000, V=0.15, mode=Mode.QUANTITATIVE)
print(r.value)      # 36000.0  (€/anno)
```

## I modelli

Tutti i modelli hanno la stessa interfaccia e si possono confrontare sullo stesso scenario
con `compare(...)`. Nelle formule, $\hat{P} = P / P_{max}$ indica il valore normalizzato in (0, 1].

### Moltiplicativo — `Multiplicative()`

$$R = P \cdot M \cdot V$$

Estende la matrice P × D dei DVR. Non è compensativo: se un fattore è basso, il rischio
resta basso. In modalità quantitativa coincide con la **perdita attesa**
$R = \lambda \cdot V \cdot M$, dove λ è la frequenza annua dell'evento, V la probabilità
che il sistema ceda e M il danno per evento.

### Geometrico pesato — `WeightedGeometric(weights=(a, b, c))`

$$R = \hat{P}^{a} \cdot \hat{M}^{b} \cdot \hat{V}^{c}, \qquad a + b + c = 1$$

Stessa logica moltiplicativa, ma il risultato torna sulla scala degli ingressi
(scale 1-5 → R da 1 a 5) e i pesi permettono di privilegiare un fattore.
Con pesi uguali dà la stessa classificazione del modello moltiplicativo.

### Additivo pesato — `WeightedAdditive(weights=(a, b, c))`

$$R = a\hat{P} + b\hat{M} + c\hat{V}$$

**Compensativo**: un evento quasi impossibile ma con danno enorme ottiene comunque un
punteggio alto. Da usare come indice di priorità, non come stima del rischio.

### Avversione al rischio — `RiskAversion(modello, k, m_ref)`

Sostituisce M con $M^k$, $k > 1$, per pesare di più gli eventi rari ma catastrofici:

- qualitativa: $M' = M_{max} \cdot (M / M_{max})^k$
- quantitativa: $M' = M_{ref} \cdot (M / M_{ref})^k$, con $M_{ref}$ danno di riferimento

### Indice comune e classificazione

In modalità qualitativa ogni modello restituisce anche un **indice in (0, 1]** che
rappresenta il livello medio equivalente dei tre fattori (media geometrica per i modelli
moltiplicativi, aritmetica per l'additivo). Le soglie di ciascun dominio sono definite
su questo indice, quindi valgono per tutti i modelli.

## Profili di dominio

### Sicurezza sul lavoro — `SICUREZZA_LAVORO`

Scale 1-4.

| | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| **P** | Improbabile | Poco probabile | Probabile | Altamente probabile |
| **M** | Lieve | Medio | Grave | Gravissimo |
| **V** | Bassa | Media | Alta | Molto alta |

V esprime quanto sono carenti le misure di prevenzione e protezione in atto
(1 = misure collettive, DPI, procedure e formazione efficaci; 4 = assenti o inefficaci).

Le soglie sono costruite in modo che **con V = 4 si ritrovi esattamente la matrice P × D
tradizionale** (P·D 1-2 basso, 3-4 medio, 6-8 alto, 9-16 molto alto). Misure efficaci
abbassano il livello. A ogni livello è associata una priorità di intervento
(`action_for(livello)`).

In modalità quantitativa: P = eventi pericolosi/anno, V = probabilità che le barriere non
bastino, M = danno per evento (es. giorni di inabilità). R = danno atteso per anno.

### Cybersecurity — `CYBERSECURITY`

Scale 1-5, impostazione in linea con ISO/IEC 27005.

| | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| **P** minaccia | Rara | Improbabile | Possibile | Probabile | Quasi certa |
| **M** impatto | Trascurabile | Limitato | Significativo | Grave | Critico |
| **V** vulnerabilità | Molto bassa | Bassa | Media | Alta | Molto alta |

- livelli Basso / Medio / Alto / Critico, ancorati alla diagonale: i passaggi avvengono con P = M = V = 2, 3, 4

#### Impatto M da riservatezza, integrità e disponibilità

R, I e D (nel codice C, I, A, per non confondere la riservatezza con il rischio R)
si valutano **sull'asset**, una volta sola: *cosa succede se perdo la riservatezza,
l'integrità, la disponibilità di questo asset?*

| | Riservatezza | Integrità | Disponibilità (fermo tollerabile) |
|---|---|---|---|
| 1 | informazioni pubbliche | errore irrilevante o subito evidente | oltre 1 settimana |
| 2 | interne, nessun dato personale | correggibile, nessun effetto esterno | da 3 giorni a 1 settimana |
| 3 | dati personali comuni, info commerciali riservate | decisioni o documenti errati verso terzi | da 1 a 3 giorni |
| 4 | dati personali su larga scala, segreti industriali | errori contabili, contrattuali o legali | da 4 a 24 ore |
| 5 | categorie particolari (art. 9 GDPR), credenziali privilegiate | effetti su persone, impianti, obblighi di legge | meno di 4 ore |

Lo scenario indica poi **quali dimensioni la minaccia colpisce**, e M è il massimo
tra quelle sole:

$$M = \max\{C\,\delta_C,\; I\,\delta_I,\; A\,\delta_A\}, \qquad \delta = 1 \text{ se la dimensione è colpita}$$

Così un guasto hardware conta solo la disponibilità, un data breach solo la riservatezza.

```python
from risk_analysis import Asset, RiskRegister, CYBERSECURITY, availability_from_downtime

server = Asset("File server", confidentiality=3, integrity=3,
               availability=availability_from_downtime(tolerable_hours=8))

reg = RiskRegister(CYBERSECURITY)
reg.add_scenario("C01", "Ransomware", server, affects="IA", P=3, V=3)
reg.add_scenario("C02", "Guasto hardware", server, affects="A", P=2, V=4)
```

Le dimensioni si indicano con le lettere `"C"`, `"I"`, `"A"` oppure, all'italiana,
`"R"`, `"I"`, `"D"`. Consiglio pratico: ancora ogni livello anche a una soglia
economica dell'organizzazione (es. livello 3 = danno tra 10 e 50 mila €), così le tre
dimensioni restano confrontabili tra loro e con la modalità quantitativa.

In modalità quantitativa il modello calcola l'**ALE** (perdita annua attesa):

$$ALE = ARO \times V \times SLE, \qquad SLE = \text{valore asset} \times EF$$

con funzioni di supporto `sle(...)`, `ale(...)` e `rosi(...)` per il ritorno
dell'investimento in contromisure.

## Incertezza: simulazione Monte Carlo

Quando le stime sono incerte, P, M e V si descrivono con distribuzioni:

```python
from risk_analysis import SICUREZZA_LAVORO, Triangular, simulate

mc = simulate(SICUREZZA_LAVORO, P=Triangular(2, 3, 4), M=4, V=Triangular(1, 2, 3),
              n=20_000, seed=1)
print(mc.summary())   # media, percentili e probabilità di ricadere in ciascun livello
```

Distribuzioni disponibili: `Fixed`, `Uniform`, `Triangular`, `PERT`.

## Registro dei rischi

```python
from risk_analysis import RiskRegister, SICUREZZA_LAVORO

reg = RiskRegister(SICUREZZA_LAVORO)
reg.add("R01", "Caduta dall'alto da PLE", P=2, M=4, V=2)
reg.add("R02", "Elettrocuzione su quadro in tensione", P=2, M=4, V=3)
reg.to_csv("registro.csv")   # ordinato per rischio, separatore ';' per Excel
```

## Aggiungere un nuovo ambito

Basta definire tre `Scale` e un `Classifier` e creare un `Domain`
(vedi `risk_analysis/domains/` come modello).

## Avvertenze

Scale, descrizioni e soglie sono **convenzioni** e vanno tarate sulla realtà valutata
e sui criteri adottati dall'organizzazione. Lo strumento supporta la valutazione del
rischio, non sostituisce il giudizio del valutatore né gli obblighi normativi
(es. D.Lgs. 81/2008, GDPR, NIS2).

## Struttura

```
risk_analysis/
  core.py             scale, input e risultati
  models.py           modelli matematici
  classification.py   livelli di rischio
  montecarlo.py       simulazione dell'incertezza
  register.py         registro dei rischi ed export CSV
  domains/            profili: sicurezza sul lavoro, cybersecurity, impatto R/I/D
examples/             script d'esempio
tests/                test automatici
```
