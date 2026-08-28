# NaroIX Helvetica — Selektionsmethodik

**Typ:** Kundenspezifischer Schweizer Multi-Asset-Index
**Basiswährung der Anzeige:** CHF (die Datenwährung wird nicht zusätzlich umgerechnet)
**Stand:** 2026-06-16

---

## 1. Überblick

Helvetica ist **kein reiner Aktienindex**, sondern ein **Multi-Asset-Index** mit fixer
Asset-Allokation. Er besteht aus zwei Teilen:

| Teil | Gewicht | Inhalt |
|------|---------|--------|
| **Statisch** | **45 %** | Feste ETF-/Cash-Sleeves (werden *nicht* selektiert, sondern als Ziel-Gewichte gesetzt) |
| **Selektiert** | **55 %** | Tool-selektierte Schweizer Aktien (40 %) + Real Estate (15 %), gleichgewichtet |

Die Selektion läuft über eine **eigenständige Schweiz-Pipeline** (`build_helvetica_pipeline`),
die **vor** der EUMSS-Kalibrierung der NaroIX-Hauptserie ansetzt und keine DM/EM-Logik nutzt.

---

## 2. Statischer Teil (45 %) — fix gesetzt

| Sleeve | Instrument(e) | Gewicht |
|--------|---------------|---------|
| Cash | CASH-CHF | 5,0 % |
| Government Bonds | CSBGC7-SWX (3-7J) 5 % + CSBGC0-SWX (7-15J) 5 % | 10,0 % |
| Corporate Bonds | CHCORP-SWX | 15,0 % |
| Gold | Amundi Physical Gold ETC (FR0013416716) 7,5 % + Xtrackers Physical Gold ETC (DE000A1E0HR8) 7,5 % | 15,0 % |
| **Summe** | | **45,0 %** |

Diese Sleeves sind feste Zielgewichte — keine Titelselektion, kein Buffer, keine Coverage-Cuts.

> **Hinweis Gold:** Die maßgeblichen Live-Instrumente sind **Amundi (FR0013416716)** +
> **Xtrackers (DE000A1E0HR8)** (je 7,5 %). Der Tool-Backtest (`HELVETICA_STATIC`) nutzt
> bewusst **PPFB-XEX + XAD5-XEX** als Proxy (längere Historie) — reine Backtest-Entscheidung,
> nicht das Live-Instrument.

---

## 3. Selektierter Teil (55 %) — Zielgewichte

| Sleeve | Auswahl | Ziel-Gewicht | Gewicht je Titel |
|--------|---------|--------------|------------------|
| Large Cap | Top 10 des Large-Segments (Kaskade: aus Mid nachziehen) | 10 % | 1,0 % |
| Mid Cap | Top 10 des Mid-Segments (Kaskade: aus Small nachziehen) | 15 % | 1,5 % |
| Small Cap | Top 10 des Small-Segments (Kaskade: aus Micro nachziehen) | 15 % | 1,5 % |
| Real Estate | **alle** qualifizierten (inkl. Micro) | 15 % | 15 % / n |
| **Summe** | | **55 %** | |

Die Equity-Sleeves sind auf **feste 10/10/10** ausgelegt (siehe Schritt 5). Die **Top-10-Auswahl** je
Sleeve erfolgt nach **Free-Float-MCap (Adj_FF_MCap)** — also die 10 größten Konstituenten des
Float-MCap-gewichteten Sub-Index. (Die Segment-KLASSE Large/Mid/Small wird separat über Total MCap
bestimmt, Schritt 4.)

**Gleichgewichtung:** Jeder Sleeve wird durch die Anzahl seiner tatsächlichen Titel (n) geteilt
(`Sleeve-Gewicht / n`). Durch das feste 10/10/10-Design (Schritt 5) ist in der Regel n = 10 je
Sleeve (Large 1,0 %, Mid/Small je 1,5 % pro Titel). Nur falls selbst mit Auffüllen aus den kleineren
Segmenten keine 10 Titel zusammenkommen (sehr kleines Universe), verteilt sich das Sleeve-Gewicht auf
weniger Titel. Die Sleeve-Summe bleibt immer auf Ziel.

---

## 4. Selektions-Pipeline (Schritt für Schritt)

Die Aktien-/RE-Selektion durchläuft folgende Schritte. Ausgangspunkt ist das bereits global
gefilterte Universe (`build_new_universe`: Preis-Filter, Ausschlüsse, FOL/IF, Delisting — siehe §6).

### Schritt 1 — Hard-Filter (Universe)
- **Exchange Country = Switzerland** (Börsenland/Listing, **nicht** Mapping Country/Domizil).
  → Es zählt, **wo** der Titel notiert ist, nicht wo das Unternehmen domiziliert.
- **Free Float MCap > 0**.
- **Variante B:** Primary- und Secondary-Listings laufen zunächst gemeinsam durch.

### Schritt 2 — Mindest-Free-Float (FF %)
Pro Titel, abhängig vom Status:

| | Entry (Neukandidat) | Maintenance (Bestand/Inkumbent) |
|---|---|---|
| Min FF % | ≥ 10 % | ≥ 7,5 % |

Maintenance-Schwelle gilt, wenn der Titel in den Vorperioden-Konstituenten ist (Multi-Period) oder
der globale Buffer-Modus aktiv ist.

### Schritt 3 — Liquidität
Pro Titel, abhängig vom Status (gleiche Inkumbenten-Definition wie Schritt 2):

| | Entry (Neukandidat) | Maintenance (Bestand/Inkumbent) |
|---|---|---|
| 3M ADTV | ≥ Schwelle | ≥ 75 % der Schwelle |

- Entry-Schwelle: **CHF 1,00 Mio.**, Maintenance **CHF 0,75 Mio.** Die Helvetica-Daten kommen in
  CHF (eigenes File), es wird nichts umgerechnet.
- **Wo die Werte herkommen:** solange die Guideline nicht final ist (der ETF ist noch nicht live),
  werden die Selektionsschwellen aus der Sidebar gelesen — Coverage-Cuts, Min FF %, ADTV und die
  Buffer-Bandbreiten. So lassen sich Anpassungen ohne Code-Änderung durchrechnen. Nachvollziehbar
  bleibt jeder Lauf über den Settings-Stempel, der als Blatt **„Settings"** in jedem
  Helvetica-Export liegt. Die hier dokumentierten Werte sind die Defaults und stimmen mit den
  Guideline-Größen überein; die Konstante `HELVETICA_RULES` im Code hält sie als Fallback für
  Tests und Headless-Läufe. Mit dem Live-Gang sollte diese Kopplung wieder gelöst werden.
- Das Verhältnis 75 % entspricht der NaroIX-Serie (Entry $1,0 Mio., Maintenance $750k).
- Der Buffer wirkt **pro Linie**: die Schwestergattung eines Bestandstitels ist selbst kein
  Indexmitglied und läuft weiter gegen die Entry-Schwelle.

### Schritt 3b — Company-Level-Dedup (vor dem Coverage-Cut)
- Pro Unternehmen (**Entity ID**) bleibt nur die **liquideste Linie** (höchstes 3M-ADTV).
- Verhindert Doppelzählung von Mehrfach-Listings (Variante B) in der Coverage-Kumulation —
  jedes Unternehmen zählt **genau einmal**, mit derselben Linie, die später im Sleeve landet.
- Für echte Paare = die Primary-Linie (Roche ROP, Swatch UHR, Schindler SCHP). Bei Lindt gewinnt
  LISP, weil es rund doppelt so liquide ist wie LISN — in 47 von 48 Perioden; nur am 2016-08-17
  lag LISN mit Faktor 1,010 vorn. Der Dedup kennt keinen Bestandsschutz: ein Linienwechsel zählt
  im Rang-Band-Buffer als Abgang plus Zugang.

### Schritt 4 — Coverage-Cut → Segmentierung (Large / Mid / Small / Micro)
- Sortierung: **Total MCap absteigend** (Tiebreaker: Adj_FF_MCap absteigend).
- Kumulative Coverage `_c_before` = vorlaufende Summe Adj_FF_MCap / Gesamt-Adj_FF_MCap (in %).
- Zuordnung nach Coverage-Schwellen:

| Segment | Entry (neue Firma) | Maintenance-Band (Bestands-Firma) |
|---------|--------------------|-----------------------------------|
| Large Cap | _c_before < 70 % | bleibt Large bis < **75 %** (+5 pp) |
| Mid Cap | 70 – 85 % | bleibt Mid **65 – 90 %** (±5 pp) |
| Small Cap | 85 – 99 % | bleibt Small **84,5 – 99,5 %** (±0,5 pp) |
| Micro Cap (nur für RE-Pool relevant) | ≥ 99 % | — |

**Firmen-interne ±5/±0,5-Hysterese (Multi-Period):** Eine **Bestands-Firma** (Segment der Vorperiode)
bleibt in ihrem Segment, solange ihre Coverage im Band liegt; **neue Firmen** werden hart geschnitten
(70/85/99 %). Der Cut läuft über **Total MCap** (firmenweit → pro Firma einmal). Damit sind Helveticas
Größenklassen **deckungsgleich mit den Swiss-Size-Sub-Indizes** (siehe „Swiss Size Sub-Indizes"). Der
zusätzliche **Top-10-Bestandsschutz** läuft über den Rang-Band-Buffer (Schritt 5).

### Schritt 5 — Sleeve-Zusammenstellung (feste 10/10/10, sequenzielle Kaskade)
- **Equity als Top-down-Kaskade (Large → Mid → Small):** Die Sleeves werden **nacheinander** aus
  einem gemeinsamen Restbestand befüllt. Jeder Sleeve nimmt die **Top 10 seines EIGENEN
  Coverage-Segments** (Rang nach **Free-Float-MCap = Adj_FF_MCap**, Total MCap als Tiebreaker;
  Gewicht = Sleeve-Gewicht / n). Die gewählten Titel werden danach **aus dem Restbestand entfernt**,
  bevor das nächstkleinere Segment an der Reihe ist.
  - **Kaskaden-Auffüllen:** Hat ein Segment **weniger als 10** eigene Titel im Restbestand, zieht es
    die **besten** Titel (nach Adj_FF_MCap) aus **allen kleineren** Segmenten nach
    (Large ← Mid/Small/Micro, Mid ← Small/Micro, Small ← Micro). In der Praxis ist das immer das
    nächstkleinere, weil nach Float sortiert wird und dieses nie erschöpft ist. Solche Titel werden
    als **„Aufrücker"** markiert; ihre echte Coverage-Klasse (`True_Segment`) bleibt im Reporting
    erhalten. **Micro Cap ist dabei ausschliesslich Quelle, nie eigenes Sleeve.**
  - **„≥ 10" gilt auf dem Restbestand:** Weil die nachgezogenen Titel entfernt sind, prüft das nächste
    Segment seine 10er-Schwelle auf dem **reduzierten** Bestand. Drückt ein knappes Large das
    Mid-Segment unter 10, zieht **Mid** seinerseits aus Small nach (usw.) — die Kaskade pflanzt sich
    fort. Aufrücker entsteht also **genau dann**, wenn ein Segment **nach Abzug** der größeren
    Sleeves selbst < 10 Titel hat.
  - **Kein Übertrag nach unten:** Größere Segmente sind als Auffüll-Quelle **ausgeschlossen**.
    Behält ein Segment nach Abzug **mehr als 10** Titel, nimmt es seine Top 10; der **Überschuss wird
    verworfen** (nicht in den kleineren Sleeve verschoben).
  - **Inkumbenten-Schutz:** Im Multi-Period läuft der **Rang-Band-Buffer (8 / 13)** über die Top-10
    des **eigenen** Segments, sodass der Rang-10-Schnitt stabil ist; das Kaskaden-Nachziehen deckt nur
    den echten Fehlbetrag.
  - **Status je Titel:** `Kern` (echte Klasse = Sleeve) oder `Aufrücker` (aus kleinerer Klasse
    nachgezogen) — beides in der Index-Anzeige und im Excel-Export ausgewiesen.
- **Real Estate:** **alle** qualifizierten CH-RE-Titel (FactSet Industry *Real Estate Development*
  oder *Real Estate Investment Trusts*, **inkl. Micro**, kein Coverage-Cut). Gewicht = 15 % / n.

### Swiss Size Sub-Indizes (Zwei-Schichten-Logik)

Der Equity-Teil ist konzeptionell ein **Zwei-Schichten-Modell**:

**Schicht 1 — drei eigenständige Swiss Size Sub-Indizes** (Large / Mid / Small Cap):
- gleiches CH-Universe wie oben (Exchange Country = CH, FF % ≥ 10 %, 3M-ADTV ≥ Schwelle,
  Hochpreis-Regel nach §6 — jeweils mit Maintenance-Schwelle für Bestandstitel);
- **Variante B:** *alle* Share Lines dürfen vertreten sein (z. B. Roche ROP **und** RO);
- Segment = firmen-interner Coverage-Cut (Schritt 4, inkl. ±5/±0,5-Hysterese); jede Linie erbt das
  Segment **ihrer Firma**;
- **Float-MCap-gewichtet** (Adj_FF_MCap), je Sub-Index auf 100 % normiert;
- Real Estate ausgeschlossen (eigenes Sleeve).

**Schicht 2 — Helvetica** zieht je Sub-Index die **Top 10 Firmen** (bei Mehrfach-Listing nur die
**liquideste Linie**), **gleichgewichtet** auf die SAA (Large 10 % / Mid 15 % / Small 15 %), mit
Rang-Band-Buffer (8/13) und Kaskaden-Nachziehen (Schritt 5).

Damit sind die Größenklassen familien-konsistent (gleiche Logik wie die NaroIX-Coverage-Indizes), und
Helvetica ist als „Top-10 je Sub-Index, gleichgewichtet" sauber definiert. Die cap-gewichteten
Sub-Indizes werden im Tool als eigene Sicht/Export ausgewiesen (ohne eigene ISINs).

---

## 5. Größenmaße: Total MCap, Adj_FF_MCap & FOL/IF

- **Coverage-Cut / Segment-Klasse:** **Total MCap** absteigend (Adj_FF_MCap als Tiebreaker); die
  Coverage-Grenzen (70/85/99 %) werden auf der **kumulierten Adj_FF_MCap** gezogen.
- **Top-10-Auswahl je Sleeve:** nach **Free-Float-MCap (Adj_FF_MCap)** (Total MCap als Tiebreaker) —
  die 10 größten Konstituenten des Float-MCap-gewichteten Sub-Index.
- **Real-Estate-Korb:** nach **Adj_FF_MCap** sortiert (alle qualifizierten, gleichgewichtet).
- **Gewichtung:** in allen Equity-/RE-Sleeves **gleichgewichtet** (Sleeve-Gewicht / n), nicht
  kapitalgewichtet.

**Adj_FF_MCap** (Free-Float-bereinigte, investierbarkeitsgewichtete Marktkapitalisierung):

```
Adj_FF_MCap = Free Float MCap  ×  IF
IF          = min(1, FOL / Free-Float-%)
```

- **FOL** (Foreign Ownership Limit) aus der FOL-Matrix v1.9; für die Schweiz i. d. R. ohne Limit
  (IF = 1).
- Titel mit **IF = 0** (nicht investierbar) sind über Adj_FF_MCap = 0 ausgeschlossen.

---

## 6. Globale Filter (aus `build_new_universe`, vorgelagert)

Bereits **vor** der Helvetica-Pipeline angewendet:

- **Hochpreis-Regel (Closing Price ≥ 20.000 USD).** Identisch zur NaroIX-Serie und aus derselben
  Sidebar-Einstellung. Zwei Modi:
  - *ATVR-Bedingung (Default):* der Titel bleibt, wenn **min(ATVR 3M, ATVR 6M)** die Schwelle
    erreicht — **10 %** für Neukandidaten, **5 %** für Bestandstitel. Geprüft auf der
    Liquiditätsstufe, weil die ATVR vorher nicht berechnet ist.
  - *Ausschluss (altes Verhalten):* harter Cut in `build_new_universe`.
  Ein nominell hoher Kurs sagt nichts über die Handelbarkeit. In der Schweiz betrifft die Regel
  über alle 48 Perioden **ausschliesslich die Lindt-Namenaktie** (LISN, ~117k), deren ATVR bei
  17 bis 56 % liegt und die Bedingung damit immer besteht.
- **Ausschlüsse:** HK (CNY), Country of Risk = @NA, Exchange Euro MTF/@NA,
  Name enthält ETF/SICAV. (Der NAICS-Ausschluss "Investment Funds" ist am 2026-08-23 entfallen,
  weil das FactSet-Feld operative Asset Manager als Fonds markierte. Im Master 05/2026 traf er
  keinen Schweizer Titel.)
- **Delisting:** Listing Status = inaktiv (1) ausgeschlossen.
- **FOL/IF** angewendet (siehe §5).

---

## 7. Turnover-Steuerung (Multi-Period)

Bei laufender Pflege (separater „Helvetica Multi-Period"-Tab) wird der Umschlag über einen echten
Inkumbenten-Buffer gedämpft:

| Bereich | Buffer-Regel |
|---------|--------------|
| **Equity (je Sleeve)** | **Rang-Band-Buffer**: neuer Titel muss in die **Top 8** (hart); ein Bestandstitel bleibt in den Top 10, solange sein Rang **≤ 13** ist. |
| **Real Estate** | **FF-Inkumbenten-Buffer**: Bestands-RE-Titel bleiben mit **FF % ≥ 7,5 %** drin. |
| **Liquidität (alle Sleeves)** | **ADTV-Inkumbenten-Buffer**: Bestandstitel laufen gegen **75 % der Entry-Schwelle** (Schritt 3). |
| **Spin-off-Kinder** | Ein aus einem Helvetica-Konstituenten abgespaltener Titel wird beim Ereignis als **Bestandstitel** aufgenommen und erbt das Segment der Mutter. |
| **Coverage-Cuts (Segment)** | **±5/±0,5-Hysterese pro Firma**: eine Bestands-Firma bleibt in ihrem Segment (Large < 75 %, Mid 65–90 %, Small 84,5–99,5 %); neue Firmen werden hart geschnitten (70/85/99 %). |

- Inkumbenten = die selektierten Konstituenten (55 %) der **Vorperiode**.
- Die vier Mechanismen hängen an zwei Schaltern: *Buffer Rules* steuert die
  Maintenance-Schwellen (FF, ADTV) und das Rang-Band, *Size Buffer* die Coverage-Hysterese.
  Beide sind im Regelbetrieb an; abgeschaltet ist der Lauf nicht guideline-konform.

### Spin-off-Aufnahme
- Quelle ist die kuratierte Liste `Spin-Off Data.xlsx` (dieselbe wie in der NaroIX-Serie).
- Ein Kind wird nur geseedet, wenn die **Mutter in der Vorperiode selektierter Helvetica-Konstituent**
  war. Abspaltungen ausländischer Mütter (z. B. Italgas aus Snam, Magnum aus Unilever) werden
  protokolliert und verworfen.
- Das Kind erbt das **Segment der Mutter**, wird danach aber normal behandelt: die
  ±5/±0,5-Hysterese hält es nur, solange seine Coverage im Band liegt. Ein zu kleiner
  Abspaltungs-Stumpf fällt deshalb von selbst in die passende Größenklasse. Beispiel Sandoz
  (aus Novartis, 2023-11-15): erbt *Large Cap*, landet über die Coverage aber in *Small Cap*.
- **Liquiditäts-Ausnahme:** ein 3M-Fenster, das seit dem Ex-Date rechnerisch nicht voll sein kann,
  wird nicht geprüft, solange der Wert **fehlt oder 0** ist. Ein vorhandener Wert unter der
  Schwelle schließt weiterhin aus.
- Matching läuft über die **Entity ID**, weil dort die Segmente der Vorperiode liegen; die
  geseedeten Firmen werden für die Schwellen- und Rang-Band-Prüfung auf ISIN zurückgespiegelt.

### In-Eligible-Liste
- `In-Eligible.xlsx` wird **nach der Segmentierung** angewendet, an derselben Stelle wie in der
  NaroIX-Serie: der Titel bleibt Teil des Marktes, der die Größengrenzen definiert, darf aber
  nicht selektiert werden.
- Wirkung je Sleeve: die Equity-Sleeves **rücken auf 10 Titel nach**; Real Estate verliert den
  Titel und verteilt die 15 % gleichmäßig auf die verbleibenden.
- Die Swiss-Size-Sub-Indizes filtern identisch, damit dort kein Titel erscheint, den der Index
  nicht halten darf.
- **Sanktionsscreen (EU/CFSP, OFAC, OFSI, sektoral):** die Guideline fordert ihn, umgesetzt wird er
  über genau diese In-Eligible-Tabelle. Die Sanktionslisten der Datenanbieter werden also nicht
  direkt eingelesen, sondern in `In-Eligible.xlsx` gepflegt. Bis das befüllt ist, bleibt der Screen
  faktisch offen. Für die Schweiz ohne Folgen: keiner der 285 CH-gelisteten Titel im Master steht
  auf einer der geprüften Listen.
- Rebalancing erfolgt **quartalsweise**. Das Tool bietet dafür keine Auswahl mehr: es rechnet
  über alle Selection Dates des geladenen Files. Ein kürzerer Lauf entsteht über ein kürzeres File,
  nicht über eine Einstellung.

---

## 8. Designprinzipien (zusammengefasst)

1. **Multi-Asset, fix:** 45 % statische ETF-/Cash-Sleeves + 55 % selektiert.
2. **Schweiz über Exchange Country** (Listing), nicht Domizil.
3. **Zwei Schichten:** Sub-Indizes = Variante B (alle Share Lines, cap-gewichtet); **Helvetica** nimmt
   pro Firma nur die **liquideste Linie** (Top-10, gleichgewichtet) — keine Doppelgewichte, kein
   Doppelzählen in der Coverage.
4. **Gleichgewichtung** je Sleeve; feste 10/10/10 (Top 10 je Segment, sequenzielle Kaskade
   Large → Mid → Small zum Nachziehen), RE alle qualifizierten.
5. **Eigenständige CH-Pipeline** (kein EUMSS, kein DM/EM-Split).
6. **Inkumbenten-Buffer** (Rang-Band Equity 8/13, FF-Buffer RE 7,5 %) nur im Multi-Period.

---

## 9. Hinweise zur Größenklassen-Logik

- **Konzentration im Large-Cap-Segment:** Der Schweizer Large-Cap-Markt wird von wenigen Giganten
  dominiert (Nestlé/Novartis/Roche), sodass der Coverage-Cut (Large = erste 70 % der CH-Adj-FF-MCap)
  historisch teils **weniger als 10** echte Large Caps liefert (z. B. 2014: nur 5). Das feste
  10/10/10-Design löst das per **Kaskaden-Nachziehen**: fehlende Slots werden mit den besten
  Titeln aus dem Mid-Segment besetzt (als „Aufrücker" markiert). Da diese aus dem Restbestand
  entfernt werden, kann ein knappes Large das Mid-Segment unter 10 drücken, das dann seinerseits aus
  Small nachzieht (Kaskade). So bleibt der Large-Cap-Sleeve stets mit 10 Titeln (je 1 %) besetzt,
  ohne die echte MSCI-Klassifikation zu verlieren.
- **Bezug zu MSCI:** Die Coverage-Schwellen (70/85/99 %) entsprechen exakt der MSCI-GIMI-Logik
  (Large 70 %, Standard 85 %, IMI 99 %). MSCI verzichtet bewusst auf feste Titelzahlen je Klasse;
  Helvetica ergänzt das feste 10/10/10 als Kunden-Anforderung über das Kaskaden-Nachziehen — die
  Klassifikation selbst bleibt MSCI-konform, der Überschuss großer Segmente wird **nicht** abgestuft,
  sondern verworfen (kein „Übertrag").
