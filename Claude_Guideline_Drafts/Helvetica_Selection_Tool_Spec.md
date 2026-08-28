# Swiss-Made Portfolio Index (intern: Helvetica)

## Vollständiges Regelwerk als Bau-Spezifikation für ein eigenständiges Selektions-Tool

**Index:** **Swiss-Made Portfolio Index**, ISIN **DE000A4AV9S7**, EUR, Net Total Return
**Typ:** regelbasierter Schweizer Multi-Asset-Strategieindex, fixe Strategic Asset Allocation
**Index Owner / Sponsor:** Helvetica SCM, Chêne-Bougeries (CH)
**Selection Party, Administrator, Calculation Agent:** NaroIX GmbH, Köln
**Währung der Selektionskriterien:** CHF (siehe 4.2), Indexwährung EUR
**Basiswert:** 1000 zum 01.01.2015 (Backtest-Beginn), live seit 03.07.2026 mit 2.579,40
**Stand dieses Dokuments:** 2026-08-10

### Autoritätsreihenfolge, verbindlich

| Rang | Quelle | Rolle |
|---|---|---|
| 1 | **Index Guideline "Swiss-Made Portfolio Index", Version 1.0, Juli 2026** | **die publizierte Methodik. Sie ist für den Live-Index allein maßgeblich.** |
| 2 | Dieses Dokument | Übersetzung der Guideline in eine implementierungsfertige Spec, plus Datenfeld- und Randfall-Details, die die Guideline offen lässt |
| 3 | Tool-Code (`naroix_benchmark.py`, `pipeline_core.py`) | **Backtest-Referenz.** Erzeugt die publizierte Historie, weicht an drei Stellen von der Guideline ab (siehe unten) |

**Referenz-Implementierung des Backtests:** `naroix_benchmark.py` (`build_helvetica_pipeline`,
`build_helvetica_composite`, `_helv_dedup_most_liquid`, `build_swiss_size_subindices`) und
`pipeline_core.py` (`build_new_universe`, `apply_universe_exclusions`, `_rank_band_select`,
`_norm_isin`).

> **Wichtigste Konsequenz für den Nachbau:** Wo Guideline und Code auseinanderlaufen, ist **die
> Guideline zu implementieren**, nicht der Code. Der Code bleibt unverändert, damit die publizierte
> Backtest-Historie reproduzierbar bleibt. Jede solche Stelle ist unten und in Abschnitt 14 einzeln
> ausgewiesen.
> **Nichts darf darüber hinaus beim Nachbau "verbessert" werden**, ohne ausdrückliche Freigabe als
> Methodik-Änderung. Auch scheinbare Schönheitsfehler (Sortierreihenfolgen, Tiebreaker, Rundungen)
> sind Teil der Methodik, weil sie die Selektion beeinflussen.

### 0. Guideline gegen Backtest-Code: die drei echten Abweichungen

| # | Thema | Guideline (umzusetzen) | Backtest-Code | Wirkung |
|---|---|---|---|---|
| 1 | **ADTV-Maintenance** | Inkumbent bleibt bei **3M ADTV ≥ CHF 750.000** (Entry CHF 1,0 Mio.) | **keine** ADTV-Maintenance, eine Schwelle für alle | Turnover, vor allem im REIT-Sleeve. Siehe 6.3 |
| 2 | **Fill-up Micro nach Small** | Micro Cap ist **ausdrücklich Fill-up-Quelle** für den Small-Sleeve | unmöglich, der Quellpool enthält kein Micro Cap | greift, wenn Small nach Large und Mid unter 10 Titel fällt. Siehe 6.7 |
| 3 | **Sanktionslisten** | Titel sanktionierter Emittenten sind **aus dem Universe ausgeschlossen** (EU, SECO, OFAC, UN, OFSI) | kein Sanktions-Screen | Compliance-Pflicht. Siehe 6.0 |

Zusätzlich präzisiert die Guideline drei Punkte, die im Code so implementiert sind, in der Doku aber
bisher fehlten oder offen waren: Real Estate bleibt im Coverage-Pool (6.5), der Rebalancing-Kalender
ist fix (Abschnitt 5.4), und die Maintenance Buffer sind **kein optionaler Schalter**, sondern
Bestandteil der publizierten Methodik (6.A).

---

## 1. Was das Tool leisten muss

**Aufgabe:** Für ein gegebenes Selection Date aus zwei Inputs die vollständige Index-Zusammensetzung
mit Zielgewichten erzeugen.

| | Input | Rolle |
|---|---|---|
| A | **FactSet Screener Output** (Wertpapier-Querschnitt zum Selection Date) | Selektionsdaten: Universe, Größe, Float, Liquidität, Klassifikation |
| B | **Close File aus der Engine** (Stand vor dem Rebalancing) | Bestands-State: wer ist Inkumbent, welches Segment hatte welche Firma, Schlusskurse |

**Output:** eine Zeile pro Indexposition mit Sleeve, Identifikatoren und `Index_Weight` in Prozent des
Gesamtindex, Summe **100,00 %**. Optional zusätzlich die Stückzahlen (Abschnitt 12).

**Nicht Aufgabe des Tools:** Index-Berechnung, NTR-Behandlung, FX-Umrechnung nach EUR, Divisor-Pflege,
Corporate Actions. Das bleibt in der Engine.

**Was ausdrücklich NICHT angewendet wird** (obwohl es in der NaroIX-Hauptpipeline existiert):

* kein EUMSS-Größen-Floor, kein Global Minimum Size Range, kein IMI-Floor,
* keine DM/EM/FM-Klassifikationslogik (Helvetica ist rein CH),
* **keine In-Eligible-Liste** (`In-Eligible.xlsx` wird im Helvetica-Pfad nicht gezogen),
* kein UCITS-5/10/40-Capping (Gleichgewichtung macht es unnötig),
* kein ATVR-Filter (nur ADTV, siehe 6.3).

---

## 2. Index-Architektur auf einer Seite

```
Gesamtindex 100 %
├─ 45 % STATISCH (fixe Zielgewichte, keine Selektion, kein Buffer)
│   ├─ Cash CHF                                    5,0 %
│   ├─ Government Bonds  2 ETFs je 5,0 %          10,0 %
│   ├─ Corporate Bonds   1 ETF                    15,0 %
│   └─ Gold              2 ETCs je 7,5 %          15,0 %
└─ 55 % SELEKTIERT (Tool-Selektion, gleichgewichtet je Sleeve)
    ├─ Equity Large Cap  Top 10                   10,0 %   (1,0 % je Titel)
    ├─ Equity Mid Cap    Top 10                   15,0 %   (1,5 % je Titel)
    ├─ Equity Small Cap  Top 10                   15,0 %   (1,5 % je Titel)
    └─ Real Estate       ALLE qualifizierten      15,0 %   (15 % / n)
```

Zwei-Schichten-Denkmodell für den Equity-Teil:

1. **Schicht 1:** drei Swiss Size Sub-Indizes (Large/Mid/Small), Float-MCap-gewichtet, alle Share
   Lines. Diese Schicht ist nur Referenz und Kontrolle, sie hat keine eigenen ISINs.
2. **Schicht 2 (= Helvetica):** je Sub-Index die **Top 10 Firmen**, pro Firma nur die liquideste
   Linie, **gleichgewichtet** auf die Zielgewichte der SAA.

Für das Selektions-Tool ist Schicht 1 optional. Sie ist aber ein sehr gutes Kontrollinstrument
(Abschnitt 13).

---

## 3. Statischer Teil (45 %), fixe Liste

**Maßgeblich für den Live-Index (publizierte Fassung):**

| Sleeve (Guideline-Bezeichnung) | Instrument | ISIN | Ticker | Gewicht |
|---|---|---|---|---|
| Cash (CHF) | CHF-Kassaposition im Index | keine | CASH-CHF | 5,0 % |
| Swiss Government Bonds (via ETF) | iShares Swiss Domestic Government Bond 3-7 ETF (CH) | **CH0016999846** | CSBGC7-SWX | 5,0 % |
| Swiss Government Bonds (via ETF) | iShares Swiss Domestic Government Bond 7-15 ETF (CH) | **CH0016999861** | CSBGC0-SWX | 5,0 % |
| Swiss Corporate Bonds (via ETF) | iShares Core CHF Corporate Bond ETF (CH) | **CH0226976816** | CHCORP-SWX | 15,0 % |
| Gold (via Gold ETC) | Amundi Physical Gold ETC | **FR0013416716** | | 7,5 % |
| Gold (via Gold ETC) | Xtrackers Physical Gold ETC | **DE000A1E0HR8** | | 7,5 % |
| | | | **Summe** | **45,0 %** |

ISINs und Bezeichnungen aus Guideline 4.2.3 (Bonds), 4.2.4 (Gold) und 4.2.5 (Cash). Die Bond-ETFs sind
an der SIX notiert, die Gold-ETCs an der Xetra. Die Auswahl der Instrumente ist in der Guideline über
objektive, nicht diskretionäre Kriterien begründet: bei den Bonds die breiteste und repräsentativste
Abdeckung der jeweiligen Segmente, beim Gold die zwei größten europäischen Gold-ETC-Emittenten nach
verwaltetem Vermögen zum Launch-Datum.

> **Achtung, häufigste Verwechslung:** Der Tool-Backtest (`HELVETICA_STATIC` in
> `naroix_benchmark.py`) führt beim Gold **PPFB-XEX (iShares) + XAD5-XEX (Xtrackers)**. Das ist ein
> bewusst gewählter **Backtest-Proxy** wegen der längeren Historie und **nicht** das Live-Instrument.
> Das Selektions-Tool muss die **Amundi + Xtrackers**-Zeile ausgeben. Wer die Backtest-Zahlen
> reproduzieren will, muss dagegen die Proxy-Ticker verwenden.

Diese acht Zeilen sind Konstanten: keine Titelselektion, kein Coverage-Cut, kein Buffer, keine
Neugewichtung. Sie stehen unverändert in jeder Periode im Output.

---

## 4. Input A: FactSet Screener Output

### 4.1 Pflichtfelder

Interner Standardname links, typische FactSet-/Master-Schreibweise rechts. Das Tool sollte die
Aliase beim Einlesen normalisieren (genau so macht es `load_master_excel`).

| Interner Name | Alias im Screener / Master | Typ | Verwendung |
|---|---|---|---|
| `Exchange Country Name` | `Country Name`, `Exchange Country` | Text | CH-Hard-Filter, Groß geschrieben verglichen |
| `Total MCap Y2025` | `Total MCap <date>` | Zahl, **CHF** | Sortierung für den Coverage-Cut, Tiebreaker |
| `Free Float MCap Y2025` | `Float MCap <date>`, `FloatMCap`, `Free Float MCap` | Zahl, **CHF** | Basis von `Adj_FF_MCap`, Coverage-Kumulation, Rang |
| `Free Float Percent` | `Float PCT <date>`, `Free Float Percent <date>` | **Dezimal 0 bis 1** | Min-Free-Float-Schwelle, IF-Formel |
| `3M ADTV Y2025` | `3M ADTV <date>` | Zahl, **CHF** pro Tag | Liquiditätsfilter, Dedup-Kriterium |
| `Closing Price` | `Closing Price <date>` | Zahl, **CHF** | Max-Price-Ausschluss |
| `Listing Status` | `Listing Status <date>` | 0/1 | Delisting-Ausschluss (1 = inaktiv) |
| `FactSet Industry` | `Industry`, `Inudstry` (Alt-Typo) | Text | Real-Estate-Erkennung |
| `FactSet Econ Sector` | `Sector`, `FactSet Sector` | Text | nur für FOL, für CH irrelevant |
| `Entity ID` | `Entity ID (Company)` | Text | Firmen-Schlüssel: Dedup, Segment-State |
| `Perm ID` | `Perm ID (Security)` | Text | empfohlener Inkumbenten-Schlüssel (siehe 5.3) |
| `ISIN` | `ISIN` | Text | Inkumbenten-Matching im Tool-Stand, Output |
| `Exchange Ticker` | `Exchange Ticker` | Text | Output, Join zur Engine |
| `Name` | `Name` | Text | Output, ETF/SICAV-Ausschluss |
| `Listing` | `Listing` | `Primary`/`Secondary` | Ausschlussregel, Reporting |
| `Sec Type` | `Sec Type` | Text | Thailand-Logik (für CH irrelevant) |
| `Trading Currency` | `Trading Currency` | Text | Ausschlussregeln |
| `Exchange Name` | `Exchange Name` | Text | Ausschluss Euro MTF / @NA |
| `NAICS` | `NAICS` | Text | nur Info, seit 2026-08-23 keine Ausschlussregel |
| `Country of Risk` | `Country of Risk` | Text | Ausschluss `@NA`, Mapping-Fallback |
| `Country of Incorp` | `Country of Incorp` | Text | Mapping-Fallback |
| `Mapping Country` | `Country Mapping` | Text | Reporting-Feld im Output |
| `Symbol` | `Symbol` | Text | Header-Erkennung im Master-Format |

### 4.2 Währungsregime: CHF

**Verbindliche Festlegung (2026-08-10):** Der Screener-Output wird in **CHF** gezogen, und die beiden
absoluten Schwellen sind **runde CHF-Werte**.

| | Wert |
|---|---|
| Währung aller Geldbeträge im Input | **CHF** (Total MCap, Free Float MCap, 3M ADTV, Closing Price) |
| 3M-ADTV-Schwelle | **>= CHF 1 000 000** |
| Max Closing Price | **< CHF 20 000** |

**Nur diese zwei Kriterien sind überhaupt währungsabhängig.** Alles andere ist einheitenfrei und
bleibt von der Umstellung unberührt:

* `Free Float Percent` ist ein Verhältnis,
* die Coverage-Cuts (70 / 85 / 99) sind **relative** Anteile an der Summe der `Adj_FF_MCap` und damit
  **währungsinvariant**, solange alle Werte in derselben Währung stehen,
* Ränge, Tiebreaker, Rang-Band 8/13 und die Gleichgewichtung sind reine Ordnungs- und
  Aufteilungsregeln.

**Eine Mischung von Währungen innerhalb eines Laufs ist der gefährlichste Fehlerfall.** Wenn
beispielsweise MCap in CHF und ADTV in USD ankommt, bleibt die Coverage-Kurve unauffällig, aber der
Liquiditätsfilter arbeitet auf dem falschen Niveau, und nichts davon fällt in einem Plausibilitätsblick
auf. Konsequenz für den Nachbau: **Währung je Feld beim Einlesen prüfen, im Parameterprotokoll
festhalten und bei Abweichung den Lauf abbrechen**, nicht warnen und weiterrechnen.

> **Methodik-Hinweis, wichtig für den Vergleich mit dem Backtest:** Der publizierte Backtest lief auf
> **USD**-Daten mit **USD**-Schwellen (ADTV 1,0 Mio. USD, Max Price 20 000 USD). Die runden
> CHF-Schwellen sind damit **nicht** wirtschaftlich deckungsgleich: solange der Franken über dem
> Dollar steht, ist CHF 1,0 Mio. die **strengere** Hürde. Betroffen ist vor allem der
> Real-Estate-Korb, weil dort jede Titelzahl direkt das Einzelgewicht verändert (15 % / n). Der
> Equity-Teil reagiert kaum, weil die zehn größten Titel je Segment ohnehin weit über jeder dieser
> Schwellen liegen. Für die Reproduktion des Backtests gilt deshalb Test T11 in Abschnitt 13: dort
> ausdrücklich mit USD-Daten und USD-Schwellen laufen lassen.

### 4.2.1 Weitere Einheiten und Fallen
* **`Free Float Percent` ist ein Dezimalwert 0 bis 1**, nicht 0 bis 100. Die Schwelle 10 % ist im Code
  als `0.10` hinterlegt. Kommt der Screener mit 0 bis 100, ist der Filter faktisch aus.
* Alle numerischen Felder mit `to_numeric(errors="coerce").fillna(0)` einlesen: fehlende Werte werden
  zu 0 und fallen dadurch systematisch durch die Filter, statt eine Exception zu werfen.
* Textvergleiche laufen auf **getrimmt und UPPERCASE** (`Exchange Country Name == "SWITZERLAND"`).
* `@NA` ist der FactSet-Platzhalter und ist wie "leer" zu behandeln, außer wo er explizit
  ausgeschlossen wird.

### 4.3 Ein Datenpunkt weniger: FOL und Inclusion Factor

Formal gilt in der ganzen NaroIX-Pipeline:

```
IF          = min(1, FOL / Free Float Percent)      (FOL aus der FOL-Matrix v1.9)
Adj_FF_MCap = Free Float MCap × IF
```

**Für Helvetica gilt vereinfacht `IF = 1` und damit `Adj_FF_MCap = Free Float MCap`.** Begründung:
`_resolve_fol_row` kennt nur zwölf Jurisdiktionen (IN, VN, SA, QA, AE, MY, KW, ID, KR, PH, TH, TW).
Die Schweiz ist nicht darunter, der Resolver gibt `1.0` zurück ("Nicht in YAML"). China-Stock-Connect
und Thailand-NVDR-Overrides greifen bei CH nicht.

**Konsequenz für den Nachbau:** Das Tool braucht die FOL-Matrix nicht. Es sollte `Adj_FF_MCap` aber
trotzdem als eigene Spalte führen und mit `Free Float MCap × 1.0` befüllen, damit die Formeln,
Exporte und Vergleiche mit dem Benchmark-Tool eins zu eins lesbar bleiben und ein späterer
FOL-Wechsel nur eine Stelle betrifft.

---

## 5. Input B: Close File aus der Engine

Das Close File liefert den **Bestands-State**, ohne den die Turnover-Regeln nicht funktionieren. Die
Selektion ist **pfadabhängig**: Bei identischen Marktdaten kommt je nach Bestand ein anderes Ergebnis
heraus. Das ist gewollt und darf nicht durch einen "sauberen" zustandslosen Nachbau ersetzt werden.

### 5.1 Was gebraucht wird

| Größe | Inhalt | Wozu |
|---|---|---|
| `incumbents` | Menge der Identifikatoren aller **selektierten** Positionen der Vorperiode, also Equity **und** Real Estate, ohne die statischen Sleeves | Min-Free-Float-Maintenance (7,5 %), Rang-Band-Buffer 8/13 |
| `prior_segments` | Mapping **Entity ID (Firma) -> Segment der Vorperiode** (`Large Cap` / `Mid Cap` / `Small Cap` / `Micro Cap`) | Coverage-Hysterese ±5 / ±0,5 |
| `close_price` | Schlusskurs je Position (optional) | nur falls Stückzahlen erzeugt werden, Abschnitt 12 |

**Wichtig zu `prior_segments`:** Das Mapping wird im Tool nicht aus den 30 selektierten Titeln
gebildet, sondern aus dem **kompletten CH-Pool der Vorperiode inklusive Micro Cap**
(`helv_full_pool`), eine Zeile je Firma. Enthält das Close File nur die Indexmitglieder, fehlen die
Segmente aller Nicht-Mitglieder, und ein Titel der letzte Periode knapp draußen war wird bei
Wiedereintritt falsch klassifiziert. Zwei zulässige Lösungen:

* **Empfohlen:** das Selektions-Tool schreibt seinen eigenen State (Firma -> Segment über den ganzen
  CH-Pool) neben dem Close File fort und liest ihn in der nächsten Periode zurück. Das ist genau das
  Verhalten des Multi-Period-Laufs.
* Alternativ: das Close File um eine Sektion "CH-Pool-Segmente" erweitern.

### 5.2 Seed-Periode

Wenn kein Bestand existiert (Erstaufsetzung, oder `incumbents` leer):

* `incumbents = leer`, `prior_segments = leer`,
* damit gelten **Entry-Schwellen** (Free Float ≥ 10 %, Coverage 70/85/99),
* Segment-Zuordnung **hart**, ohne Hysterese,
* Equity-Auswahl = **schlichte Top 10** je Segment, ohne Rang-Band-Buffer.

Der Multi-Period-Lauf erkennt die Seed-Periode an `len(prev) == 0` und schaltet Buffer und Hysterese
gezielt aus, **auch wenn der Hauptschalter `Maintenance Buffer` auf AN steht** (siehe 6.A). Beim
Nachbau ist das explizit zu implementieren, nicht implizit über "leere Menge liefert schon das
Richtige", weil `use_buffer` und `prior_segments` unterschiedliche Codepfade auslösen.

### 5.3 Matching-Schlüssel

| | Verwendeter Schlüssel im Tool-Stand | Empfehlung Live |
|---|---|---|
| Inkumbenten (Titel-Ebene) | normalisierte **ISIN** (`fillna("") -> str -> strip -> upper`) | **Perm ID** mit ISIN-Fallback (`_match_key`), robust gegen ISIN- und Ticker-Wechsel |
| Segmente (Firmen-Ebene) | **Entity ID**, als String getrimmt | Entity ID beibehalten |

Ein Wechsel von ISIN auf Perm ID ist eine **Methodik-Änderung mit Ergebniswirkung** (ein Titel mit
ISIN-Wechsel würde seinen Bestandsschutz nicht mehr verlieren) und muss freigegeben werden. Bis dahin
ist die normalisierte ISIN maßgeblich, damit die Ergebnisse mit dem Backtest vergleichbar bleiben.

### 5.4 Rebalancing-Kalender, fix vorgegeben

Aus Guideline 4.3 und 5.1. Das ist keine Wahlmöglichkeit mehr, sondern der publizierte Terminplan:

| | Regel |
|---|---|
| Frequenz | **quartalsweise** |
| **Selection Day** | Schluss des **3. Mittwochs** im **Februar, Mai, August, November** |
| **Rebalancing Day** | Schluss des **1. Mittwochs** im **März, Juni, September, Dezember** |
| Datenstand | die Selektion nutzt Daten **des Selection Day** |
| Wirksamkeit | die am Selection Day bestimmten Zielgewichte werden **zum Schluss des Rebalancing Day** wirksam |
| Zwischenzeit | zwischen Selection und Rebalancing Day sind Anpassungen für dazwischenliegende Corporate Actions möglich |
| Handelshemmnis | ist eine Komponente am Rebalancing Day wegen Feiertag oder Marktschließung nicht handelbar, verschiebt sich das Rebalancing auf den nächsten Business Day |
| Vorankündigung | alle Komponentenänderungen werden **vor** dem Rebalancing Day auf `ix.naroiq.com` publiziert |

**Drei Konsequenzen für das Tool:**

1. **Die Selection Dates sind vorgegeben**, nicht frei wählbar. Der Frequenz-Auswahlknopf im
   Multi-Period-Tab (quartalsweise, halbjährlich, jährlich, eigene Monate) ist eine reine
   Backtest-Funktion. Produktion ist immer der Kalender oben. Damit ist der frühere offene Punkt zur
   Rebalancing-Frequenz erledigt.
2. **Inkumbent bezieht sich auf das vorangehende Rebalancing**, nicht auf den vorangehenden Selection
   Day (Guideline 4.3 und Definition "Incumbent"). Bei quartalsweisem Rhythmus ist das dieselbe
   Zusammensetzung, aber es ist der saubere Bezugspunkt für das Close File: gebraucht wird der Stand
   **nach** dem letzten Rebalancing.
3. **Außerordentliches Rebalancing** (Guideline 5.2) kann außerhalb des Quartalsrhythmus stattfinden,
   unter anderem bei Aufnahme eines Titels auf eine Sanktionsliste, bei einem Delisting oder bei einem
   Corporate Event, nach dem eine Komponente die Eignungskriterien nicht mehr erfüllt. Das Tool sollte
   deshalb auf ein **beliebiges Stichtagsdatum** lauffähig sein, nicht nur auf die Quartalstermine.

---

## 6. Selektionskette, Schritt für Schritt

Reihenfolge ist verbindlich. Jeder Schritt arbeitet auf dem Output des vorherigen.

### 6.A Maintenance und Bestandsschutz, vollständig

Helvetica arbeitet durchgehend mit **zwei Schwellensätzen**: `Entry` für Neukandidaten und
`Maintenance` für Inkumbenten.

#### Der Hauptschalter: "Maintenance Buffer"

**In der publizierten Methodik ist der Maintenance Buffer kein Schalter, sondern fester Bestandteil
der Regeln.** Die Guideline definiert ihn in Abschnitt 2 als Begriff und in 4.2.1 und 4.2.2 als
verbindliche Regel. Es gibt keine zulässige Betriebsart ohne ihn. Im **Tool** ist er dagegen ein
Schalter, weil dort auch Vergleichsläufe gefahren werden.

Im Multi-Period-Lauf hängt das **gesamte** Maintenance-Paket an diesem einen Schalter
(`_mp_buffer` im Tool, Default **AN**). Er entscheidet nicht über einzelne Schwellen, sondern darüber,
**ob der Bestands-State überhaupt an die Pipeline übergeben wird**:

| Schalter | `incumbents` | `prior_segments` | Wirkung |
|---|---|---|---|
| **AN (Produktion)** | Konstituenten der Vorperiode | Segmente der Vorperiode je Firma | alle Regeln der Tabelle unten sind aktiv |
| AUS | `None` | `None` | **jede Periode reine Entry-Regeln**, kein Bestandsschutz auf irgendeiner Achse. Das ist die Turnover-Referenz (Variante D, 74 Eintritte über 48 Perioden) |

Zwei Feinheiten, die man beim Nachbau abbilden muss:

* **Die Seed-Periode übersteuert den Schalter.** Auch bei AN wird in der ersten Periode nichts
  übergeben, weil es keinen Bestand gibt: `inc = prev wenn (buffer AND NOT seed) sonst None`.
* **`Maintenance Buffer` und `use_buffer` sind zwei verschiedene Dinge** und werden wegen des
  ähnlichen Namens ständig verwechselt:

| | `Maintenance Buffer` (`_mp_buffer`) | `use_buffer` |
|---|---|---|
| Wo | Multi-Period-Tab | Single-Snapshot-Tab |
| Was | schaltet den **echten** Bestandsschutz ein: pro Titel und pro Firma | setzt die Maintenance-Cuts **global für alle** |
| Default | **AN** | AUS |
| Im MP-Lauf | steuernd | im Code fest `False` |
| Produktion | **AN** | nie |

#### Alle Bestandsschutz-Regeln auf einen Blick

Diese Tabelle ist die vollständige Liste, die Details stehen in den angegebenen Abschnitten. Sie gilt,
wenn der Hauptschalter AN und die Periode keine Seed-Periode ist.

| Regel | Entry | Maintenance | Maintenance greift, wenn | Achse | Abschnitt |
|---|---|---|---|---|---|
| Minimum Free Float | `>= 0,10` | `>= 0,075` | normalisierte ISIN des Titels in `incumbents` | Titel | 6.2 |
| 3M ADTV | `>= CHF 1,0 Mio.` | **`>= CHF 750 000`** | ISIN in `incumbents` | Titel | 6.3 |
| Coverage-Cut, Segment | 70 / 85 / 99 | **75 / 90 / 99,5**, angewendet als firmen-interne Hysterese: Large `< 75`, Mid `65 bis 90`, Small `84,5 bis 99,5` | Firma hat ein Segment in `prior_segments` | **Firma** | 6.6 |
| Coverage-Cut, globale Variante | 70 / 85 / 99 | **dieselben** 75 / 90 / 99,5, aber für **alle** Firmen inkl. Neukandidaten | nur `use_buffer = True`, Sensitivitäts-Analyse | global | 6.6 |
| Sleeve-Mitgliedschaft, Top 10 | Rang `<= 8` | Rang `<= 13` | ISIN des Titels in `incumbents` | Titel je Sleeve | 6.8 |
| Real Estate, Mitgliedschaft | Free Float `>= 0,10` | Free Float `>= 0,075` | ISIN des Titels in `incumbents` | Titel | 6.9 |

**Vier Punkte, die man beim Nachbau leicht falsch macht:**

1. **Maintenance ist in Produktion nie global, sondern immer pro Titel beziehungsweise pro Firma.**
   In derselben Periode gelten für verschiedene Zeilen verschiedene Schwellen. Wer den
   Maintenance-Satz global setzt, baut den Analyse-Modus `use_buffer` nach, nicht die Produktionsregel.
2. **Zwei verschiedene Achsen, zwei verschiedene Schlüssel.** Free Float, Rang-Band und Real Estate
   laufen über den **Titel** (normalisierte ISIN). Der Coverage-Cut läuft über die **Firma**
   (Entity ID). Ein Titel kann Inkumbent sein, ohne dass seine Firma ein Vorperioden-Segment hat,
   und umgekehrt.
3. **Der Coverage-Buffer hat einen weiteren Adressatenkreis als die anderen.** Free Float, ADTV und
   Rang-Band gelten nur für **Inkumbenten**, also für Titel, die tatsächlich Konstituenten der
   Vorperiode waren. Der Coverage-Buffer gilt laut Guideline für **jeden Titel, dem bei der
   vorherigen Selektion ein Size Bucket zugewiesen wurde**, unabhängig davon, ob er selektiert war.
   Genau deshalb muss `prior_segments` aus dem **vollen** CH-Pool kommen und nicht aus den 30
   selektierten Titeln (siehe 5.1).
4. **Alle vier Maintenance-Regeln sind Pflicht, keine Option.** Die Guideline kennt keinen Betrieb
   ohne Maintenance Buffer. Der Tool-Schalter existiert nur für Vergleichsläufe.

In der **Seed-Periode** ist `incumbents` und `prior_segments` leer, damit greift ausschließlich der
Entry-Satz und die Auswahl ist eine schlichte Top 10 (siehe 5.2).

### 6.0 Stufe 0: globale Investability-Ausschlüsse

Entspricht `apply_universe_exclusions`. Wird auf den kompletten Screener-Output angewendet,
**bevor** auf die Schweiz gefiltert wird. Auf einem reinen CH-Screener ist das Ergebnis identisch,
weil alle Regeln zeilenweise wirken.

| # | Regel | Bedingung zum Ausschluss | Für CH relevant |
|---|---|---|---|
| 1 | Free Float MCap | `Free Float MCap <= 0` | ja |
| 2 | Max Price | `Closing Price >= 20 000` (**CHF**) | **ja, wichtig** |
| 3 | HK in CNY | Ticker enthält `HKG` **und** `Trading Currency == CNY` | nein |
| 4 | London-USD-Secondary | `Listing == secondary` **und** Ticker enthält `LON` **und** Currency `USD` | selten |
| 5 | Country of Risk | `Country of Risk == "@NA"` | selten |
| 6 | Börsenplatz | `Exchange Name` in `{Euro MTF, @NA}` | selten |
| 7 | ETF / SICAV | `Name` matcht Regex `\bETF\b|\bSICAV\b|%` (case-insensitive) | ja |
| 8 | Delisting | `Listing Status == 1` | ja |

**Entfallen am 2026-08-23:** die frühere Regel 6, Fondsausschluss über `NAICS` enthält
`Open-End Investment Fund`. Das FactSet-Feld markierte überwiegend operative Asset Manager als
Fonds (WisdomTree, Jupiter Fund Management, IntegraFin, Groww). Im Master 05/2026 traf die Regel
16 Titel, davon keinen Schweizer, für die CH-Selektion war sie also ohnehin wirkungslos. Echte
Fondsvehikel bleiben über Regel 7 (ETF/SICAV) und die Größenschwellen draußen.

**Zu Regel 2:** Der Preisfilter bei CHF 20 000 ist bei Helvetica methodisch wirksam. Er entfernt die
Lindt-Namenaktie (Kurs im sechsstelligen Bereich), während der Lindt-Partizipationsschein drin
bleibt. Genau deshalb ist der Dedup in 6.4 auf "liquideste Linie" und nicht auf "Primary" gebaut:
Lindt kommt korrekt über LISP herein, obwohl LISN die Primary-Linie ist.

**Zu Regel 7:** Der Regex enthält `%` und wirft damit auch Namen mit Prozentzeichen heraus, das sind
typischerweise Zertifikate und Anleihe-artige Linien.

**Welche dieser Regeln die Guideline deckt:** Die Guideline nennt in 4.2.1 nur Börse, Preis,
Free Float und ADTV. Die neun Regeln oben sind der **Engine-Hygiene-Filter** der NaroIX-Pipeline. Für
ein CH-Universe sind die Regeln 3, 4, 5 und 7 praktisch wirkungslos, die Regeln 1, 2, 6, 8 und 9 sind
sachlich notwendig (kein Fonds und kein delisteter Titel gehört in einen Aktienindex) und
widersprechen der Guideline nicht. **Beibehalten**, aber im Parameterprotokoll ausweisen, damit
nachvollziehbar bleibt, was über die Guideline hinaus gefiltert wurde.

#### Zwei Ausschlüsse, die die Guideline zusätzlich fordert

**A) Sanktionslisten (Abweichung 3 gegen den Backtest-Code).** Die Guideline definiert in Abschnitt 2
unter "Sanctions List": Titel von Emittenten, die auf einer Sanktionsliste einer zuständigen Behörde
stehen, sind **aus dem Index Universe ausgeschlossen**. Genannt werden ausdrücklich, aber nicht
abschließend:

| Behörde | Liste |
|---|---|
| Europäische Union | EU-Sanktionsliste |
| Schweiz | SECO (Staatssekretariat für Wirtschaft) |
| USA | OFAC (Office of Foreign Assets Control) |
| Vereinte Nationen | UN Security Council |
| Vereinigtes Königreich | OFSI (Office of Financial Sanctions Implementation) |

Der Tool-Code hat **keinen** Sanktions-Screen. Das Selektions-Tool braucht ihn. Da es kein Feld im
Screener-Output ist, ist es ein eigener Abgleich gegen bezogene Listen, auf Emittenten-Ebene (Entity),
nicht auf Wertpapier-Ebene. Zwei Dinge sind dabei festzulegen: die **Bezugsquelle** der Listen und der
**Matching-Schlüssel** (Name-Matching ist fehleranfällig, LEI oder Entity ID ist vorzuziehen). Siehe
offener Punkt 9. Ein Sanktionsfall ist außerdem ein Grund für ein **außerordentliches Rebalancing**
(Guideline 5.2), nicht nur für den Ausschluss beim nächsten regulären Termin.

**B) Eligible Exchanges.** Die Guideline verweist auf die **NaroIX Eligible Exchanges Policy**
(`naroiq.com/governance`). Für einen Index, dessen Universe ohnehin auf die SIX Swiss Exchange
begrenzt ist, ist das ohne praktische Wirkung, sollte aber als Prüfschritt existieren, damit der Tool
und die Policy nicht auseinanderlaufen.

Zusätzlich setzt `build_new_universe` `Mapping Country` (primär Feld `Country Mapping`, Fallback
Risk-First über Country of Risk, dann Country of Incorp, dann Exchange, wobei eine Liste von
33 Steueroasen-Domizilen übersprungen wird) und wirft Zeilen ohne DM/EM/FM-Klassifikation heraus.
**Der Klassifikations-Filter ist für Helvetica ohne Wirkung** (die Schweiz ist immer DM), das Feld
`Mapping Country` wird aber im Output mitgeführt.

### 6.1 Stufe 1: Schweiz-Hard-Filter

```
Exchange Country Name == "SWITZERLAND"    AND    Free Float MCap > 0
```

**Entscheidend:** Es zählt das **Börsenland des Listings**, nicht das Domizil und nicht die Mapping
Country. Ein in der Schweiz notierter Titel mit ausländischem Domizil ist im Universe, ein
schweizerisches Unternehmen mit ausschließlich ausländischer Notierung nicht.

**Variante B:** Primary- und Secondary-Listings laufen gemeinsam durch. Beide Linien einer Firma
können die Filter einzeln bestehen. Die Reduktion auf eine Linie erfolgt erst in 6.4.

> **Formulierungsunterschied zur Guideline, bitte klären (offener Punkt 8).** Die Guideline schreibt
> in 4.1 "all equity securities of companies **listed on the SIX Swiss Exchange**" und listet in 4.2.1
> als erstes Kriterium "**Primary Exchange:** SIX Swiss Exchange". Der Code filtert dagegen auf
> `Exchange Country Name == "SWITZERLAND"` und lässt Secondary-Linien mitlaufen.
>
> Die beiden Lesarten unterscheiden sich in zwei Fällen:
> 1. Ein Titel an einer **anderen** schweizerischen Börse als der SIX (zum Beispiel BX Swiss) wäre im
>    Code drin, nach dem SIX-Wortlaut draußen.
> 2. Ein Titel, dessen **primäre** Notierung im Ausland liegt und der an der SIX nur eine
>    Secondary-Linie hat, wäre im Code drin, nach der Lesart "Primary Exchange = SIX" draußen.
>
> Für Fall 2 spricht die Guideline selbst gegen die strenge Lesart: ihre Definition der
> **Most-Liquid Share Line** nennt ausdrücklich "a primary **and a secondary listing**" als Fall, den
> die Regel behandelt. Wären Secondary-Linien schon vorher ausgeschlossen, wäre diese Klausel sinnlos.
> **Auslegung für dieses Dokument:** "Primary Exchange: SIX Swiss Exchange" ist als
> Marktplatz-Anforderung zu lesen (der Titel wird an der SIX gehandelt), nicht als Ausschluss von
> Secondary-Linien. Empfehlung: den Filter auf `Exchange Name == SIX` verengen (statt Land =
> Schweiz), Secondary-Linien aber weiterhin zulassen, weil der Dedup in 6.4 sie ohnehin auf eine Linie
> reduziert. Das ist mit Nico zu bestätigen, weil es das Universe verändern kann.

### 6.2 Stufe 2: Minimum Free Float, je Titel

| | Entry (Neukandidat) | Maintenance (Inkumbent) |
|---|---|---|
| `Free Float Percent >=` | **0,10** (10 %) | **0,075** (7,5 %) |

Die Maintenance-Schwelle gilt für einen Titel genau dann, wenn seine normalisierte ISIN in
`incumbents` liegt. Die Prüfung ist **zeilenweise**, nicht global: in derselben Periode gelten für
verschiedene Titel verschiedene Schwellen.

Der Schalter `use_buffer` im Single-Snapshot-Tab setzt die Maintenance-Schwellen global für alle
Titel. Das ist ein **Analyse-Modus für Sensitivitäten und nicht die Produktionsregel**. Im
Multi-Period-Lauf ist er immer `False`. Das Selektions-Tool sollte ihn entweder nicht anbieten oder
sichtbar als Analyse-Modus kennzeichnen.

### 6.3 Stufe 3: Liquidität

```
3M ADTV >= adtv_thr          Default adtv_thr = CHF 1 000 000
```

**Maintenance-Schwelle: `3M ADTV >= CHF 750 000` für Inkumbenten.**

| | Entry (Neukandidat) | Maintenance (Inkumbent) |
|---|---|---|
| 3M ADTV | `>= CHF 1 000 000` | `>= CHF 750 000` |

Quelle: Index Guideline 3.1 ("ADTV ≥ CHF 1,000,000 (Maintenance ≥ CHF 750,000) over 3 months"),
bestätigt in 4.2.1 für Aktien und 4.2.2 für REITs. Die Umschaltung erfolgt **pro Titel** über die
Inkumbenten-Menge, genau wie beim Free Float (6.2).

> **Interne Unstimmigkeit in der Guideline, sollte in v1.1 bereinigt werden.** Die ADTV-Maintenance
> steht dreimal in den Kriterien-Listen (3.1, 4.2.1, 4.2.2), jeweils mit konkreter Zahl. Sie fehlt
> aber in den beiden Aufzählungen, die den Maintenance Buffer beschreiben: die Definition in
> Abschnitt 2 nennt drei Buffer (Free Float, Coverage-Hysterese, Rang-Band), und 4.2.1 formuliert
> "Incumbency protection operates through **three** mechanisms". Eine geschlossene Dreier-Aufzählung
> und eine dreifach genannte vierte Schwelle widersprechen sich.
> **Auslegung für dieses Dokument:** Die Kriterien-Angabe gewinnt, weil sie an drei Stellen steht und
> eine konkrete Zahl nennt, während die Aufzählungen erkennbar den früheren Stand ohne
> ADTV-Maintenance beschreiben. Also: **CHF 750.000 implementieren.** Bitte in der Guideline die
> Aufzählungen auf vier Mechanismen erweitern, siehe offener Punkt 7.

> **Abweichung 1 gegen den Backtest-Code, unbedingt beachten.** Der Tool-Code kennt **keine**
> ADTV-Maintenance: `build_helvetica_pipeline` vergleicht alle Zeilen gegen dasselbe `adtv_thr`, die
> Titel-Logik `_maint()` wird dort nicht aufgerufen. Der publizierte Backtest ist also **ohne** die
> 750.000-Schwelle gerechnet. **Das Selektions-Tool muss sie implementieren**, weil sie in der
> publizierten Guideline steht. Konsequenz: eine Abweichung gegen den Tool-Export ist an dieser
> Stelle **erwartet**, und zwar in Richtung **weniger** Turnover, vor allem im REIT-Sleeve.
>
> Der Mechanismus existiert in der Engine bereits: `apply_liquidity_new` in `pipeline_core.py` kennt
> `m_adtv_dm` und `m_adtv_em`, schaltet pro Titel über `incumbents_isin` und fällt auf die
> Entry-Werte zurück, wenn sie `None` sind. Für Helvetica ist die Funktion nur nie verdrahtet worden.

**Ausnahme für unvollständige Historie (Guideline 3.1 und 4.3):** Fehlt einem Titel die vollen drei
Monate ADTV-Historie, wird **der maximal verfügbare Zeitraum** verwendet. Das gilt für

* **Spin-Offs** aus einem Indexmitglied, die vor dem Selection Day hinzukommen, und
* **Mega-IPOs**, definiert als Neuemission, Direct Listing, Transfer Listing oder neu gelistetes
  Depositary Receipt mit einer **Total Market Capitalization von mindestens USD 100 Mrd.** zum
  Zeitpunkt der Eignungsprüfung.

Achtung auf die Währung: die Mega-IPO-Schwelle ist in der Guideline **in USD** angegeben, während alle
Selektionskriterien in CHF stehen. Das ist so übernommen und nicht umzurechnen.

**Umsetzung im Tool:** Da der Screener nur die fertigen ADTV-Fenster liefert, braucht die Ausnahme
eine Fallback-Kette auf das nächstkürzere verfügbare Fenster (`3M`, sonst `1M`), analog zu der Logik,
die `build_new_universe` für den ATVR verwendet. Titel ohne jede Historie erfüllen das Kriterium
nicht.
* Umschaltbare Alternativen: **CHF 0,25 Mio. und CHF 0,5 Mio.** Niedrigere Schwellen machen
  vor allem den Real-Estate-Korb breiter. **Produktionswert ist CHF 1,0 Mio.**, jede andere
  Einstellung ist ein Szenario und muss im Output protokolliert werden.
* Kein ATVR-Filter. Der ATVR-Teil der Hauptpipeline wird für Helvetica nicht angewendet.

**Reihenfolge-Schalter `label_before_liquidity`, Default `False`:**

* `False` (Produktion): Liquiditätsfilter **vor** dem Coverage-Cut. Die Größengrenzen werden auf dem
  liquiden Pool gezogen.
* `True`: Coverage-Labeling zuerst auf dem vollen CH-Pool, danach Liquidität nur als
  Mitgliedschafts-Gate. Illiquide Titel definieren dann die Größengrenzen mit, fallen aber selbst
  heraus.

Der Schalter verändert die Segmentgrenzen und damit die Zusammensetzung. **Im Nachbau auf `False`
festnageln**, sonst ist das Ergebnis nicht mit dem Backtest vergleichbar.

### 6.4 Stufe 3b: Company-Level-Dedup vor dem Coverage-Cut

Pro Firma bleibt genau **eine** Linie: die mit dem **höchsten 3M ADTV**.

```
key = Entity ID (getrimmt)                        wenn vorhanden und nicht "" / "nan"
key = "ISIN::" + normalisierte ISIN               sonst
Sortiere nach 3M ADTV absteigend, behalte die erste Zeile je key
```

Der ISIN-Fallback ist wichtig: ohne ihn würden alle Zeilen ohne Entity ID zu einer einzigen Zeile
kollabieren.

**Warum vor dem Coverage-Cut:** Sonst zählt eine Firma mit zwei Linien zweimal in die kumulierte
Coverage und verschiebt alle Größengrenzen. Betroffene CH-Paare: Roche (RO/ROP), Swatch (UHR/UHRN),
Schindler (SCHN/SCHP), Lindt (LISN/LISP). Bei echten Paaren gewinnt in der Praxis die Primary-Linie,
weil sie liquider ist. Bei Lindt gewinnt LISP, weil LISN vorher am Preisfilter scheitert.

**Nach diesem Schritt gilt: eine Zeile = eine Firma.** Alle folgenden Schritte sind damit
firmen-eben, auch wenn sie technisch auf Wertpapierzeilen laufen.

### 6.5 Stufe 4: Sortierung und Coverage-Basis

```
Sortiere absteigend nach [Total MCap, Adj_FF_MCap]          # Tiebreaker: Adj_FF_MCap
tot       = Summe(Adj_FF_MCap) über den gefilterten CH-Pool
_c_before = kumulierte Adj_FF_MCap VOR der aktuellen Zeile / tot × 100
```

**Real Estate bleibt im Coverage-Pool.** Das ist die wichtigste Aussage dieser Stufe und der
verbreitetste Nachbau-Fehler. Die Guideline sagt es zweimal ausdrücklich (Definition "Cumulative FF
MCAP Coverage" und 4.2.1 "Real Estate treatment"): der Pool für die Coverage-Rechnung umfasst **alle**
eligiblen Schweizer Aktien **inklusive** Real Estate. RE-Titel zählen also in den Nenner `tot`, in die
Sortierung und in die Kumulation. Sie werden **erst nach** der Bucket-Zuordnung aus Large, Mid und
Small entfernt und in den REIT-Sleeve überführt.

Wer Real Estate schon am Anfang herausfiltert, verkleinert den Nenner, verschiebt jede
Coverage-Prozentzahl und bekommt **andere** Large-, Mid- und Small-Buckets. Der Tool-Code macht es
korrekt: `build_helvetica_pipeline` filtert Real Estate nirgends heraus, die Trennung passiert erst in
`build_helvetica_composite` über `helv[~is_re(helv)]`.

Zwei weitere Details, die exakt so implementiert werden müssen:

1. **Die Sortierung läuft über `Total MCap`, die Kumulation über `Adj_FF_MCap`.** Das ist gewollt: die
   Größenklasse ordnet nach Unternehmensgröße, die Coverage misst investierbares Kapital.
2. **`_c_before` ist eine Straddle-Coverage**, also der Wert **vor** der Zeile (`cumsum().shift(1)`,
   erste Zeile = 0). Eine Firma, die eine Schwelle überschreitet, wird noch dem **kleineren**
   `_c_before` und damit dem größeren Segment zugeordnet. Wer stattdessen `cumsum()` nach der Zeile
   nimmt, verschiebt an jeder Grenze genau einen Titel. Das ist der klassische Off-by-one beim
   Nachbau.
3. Bei `tot == 0`: `_c_before = 0` für alle Zeilen, kein Fehler.

### 6.6 Stufe 5: Segmentierung, harter Cut plus Hysterese

**Harter Cut (Entry), gilt immer für Firmen ohne Vorperioden-Segment:**

| Segment | Bedingung |
|---|---|
| Large Cap | `_c_before < 70` |
| Mid Cap | `70 <= _c_before < 85` |
| Small Cap | `85 <= _c_before < 99` |
| Micro Cap | `_c_before >= 99` |

**Maintenance-Cut-Satz (Bestandsschutz auf der Coverage-Achse):**

| Segment | Maintenance-Bedingung | Herleitung |
|---|---|---|
| Large Cap | `_c_before < 75` | Entry 70 **+ 5** |
| Mid Cap | `_c_before < 90` | Entry 85 **+ 5** |
| Small Cap | `_c_before < 99,5` | Entry 99 **+ 0,5** |
| Micro Cap | `_c_before >= 99,5` | Rest |

Das sind **die** Maintenance-Schwellen des Index: eine Bestands-Firma verliert ihr Segment erst, wenn
sie diese Grenze überschreitet, nicht schon an der Entry-Grenze. Sie haben **zwei
Anwendungsformen**, mit identischen Zahlen und unterschiedlichem Adressatenkreis:

| Form | Adressatenkreis | Auslöser | Einsatz |
|---|---|---|---|
| **Firmen-intern (Hysterese)** | jede Firma mit Vorperioden-Segment, **auch wenn sie nie selektiert war** | `prior_segments` gefüllt | **Produktion, Multi-Period** |
| **Global** | **alle** Firmen, auch Neukandidaten | `use_buffer = True` | Sensitivitäts-Analyse im Single-Snapshot-Tab |

Der Adressatenkreis der firmen-internen Form ist in der Guideline ausdrücklich weiter gefasst als bei
den anderen Buffern: "This buffer applies to **any security assigned to a size bucket at the preceding
selection, whether or not it was a selected constituent**" (4.2.1). Deshalb speist sich
`prior_segments` aus dem vollen CH-Pool, nicht aus den 30 Konstituenten (5.1).

Die globale Form ist nicht falsch, sie ist nur **kein Bestandsschutz**: sie lockert die Grenzen auch
für Titel, die noch nie im Index waren, und beantwortet die Frage "wie sieht das Universe mit
gelockerten Schwellen aus". Im Live-Betrieb ist deshalb die firmen-interne Form zu verwenden, im
Multi-Period-Lauf ist `use_buffer` im Code fest auf `False`.

Die firmen-interne Form ergänzt zu den Obergrenzen noch **Untergrenzen** (Mid ab 65, Small ab 84,5).
Die sind nötig, damit eine Firma, die echt gewachsen ist, auch **aufsteigen** kann: ohne Untergrenze
bliebe ein Mid-Titel, dessen Coverage auf 40 % gestiegen ist, für immer Mid. Large braucht keine
Untergrenze, es ist bereits die oberste Klasse.

**Welcher Cut gilt, Entscheidungslogik:**

```
use_buffer == True                                ->  globaler MAINT-Satz 75 / 90 / 99,5 für ALLE,
                                                      keine Hysterese          (Analyse, nicht Produktion)
use_buffer == False  und  prior_segments leer      ->  harter ENTRY-Satz 70 / 85 / 99        (Seed)
use_buffer == False  und  prior_segments gefüllt   ->  ENTRY-Satz plus firmen-interne Hysterese
                                                                                              (PRODUKTION)
```

Die beiden Mechanismen schließen sich aus: entweder global gelockerte Grenzen oder firmen-interner
Bestandsschutz. Setzt man im Nachbau beides gleichzeitig, berechnet der Code den harten Cut aus dem
MAINT-Satz, die Hysterese-Bänder aber weiterhin aus den ENTRY-Werten (70 / 85 / 99). Diese
Kombination ist nirgends definiert oder getestet und sollte im Nachbau **technisch verboten** werden,
zum Beispiel über eine Assertion.

**Hysterese für Bestands-Firmen (Multi-Period), auf Basis `prior_segments[Entity ID]`:**

```
prior == "Large Cap"  und  _c_before < 75.0                    ->  bleibt "Large Cap"    (70 + 5)
prior == "Mid Cap"    und  65.0 <= _c_before < 90.0            ->  bleibt "Mid Cap"      (70 - 5 bis 85 + 5)
prior == "Small Cap"  und  84.5 <= _c_before < 99.5            ->  bleibt "Small Cap"    (85 - 0,5 bis 99 + 0,5)
sonst                                                          ->  harter Entry-Cut
```

Reihenfolge der Auswertung: erst den harten Cut für alle berechnen, dann für Bestands-Firmen
überschreiben, wenn die jeweilige Bandbedingung greift. Die Bänder sind **absichtlich asymmetrisch**:
Large und Mid haben ±5 Prozentpunkte, Small nur ±0,5 Prozentpunkte, weil die Small-Grenze bei 99 %
Coverage in einem extrem dicht besetzten Bereich liegt und ein ±5-Band dort fast das ganze
Micro-Segment einschließen würde.

**Was die Hysterese bewirkt und was nicht:** Sie hält die Größenklassen deckungsgleich mit den Swiss
Size Sub-Indizes und stabilisiert die **Labels**. Sie ändert die 30 selektierten Titel praktisch
nicht, weil die Top-10-Auswahl rang- und nicht labelbasiert ist. Sie verschiebt aber die Zuordnung
zwischen Mid und Small Sleeve und die Kern/Aufrücker-Kennzeichnung. Der eigentliche Turnover-Schutz
liegt im Rang-Band-Buffer (6.7).

**Micro Cap:** kommt nicht in die Equity-Sleeves. Micro-Titel sind nur über den Real-Estate-Sleeve
indexfähig.

**Zwei Pools sind das Ergebnis dieser Stufe:**

| Pool | Inhalt | Verwendung |
|---|---|---|
| `helv` | nur Large / Mid / Small | Equity-Sleeves |
| `helv_full_pool` | alle vier Segmente inklusive Micro | Real Estate, State-Fortschreibung |

Wenn `label_before_liquidity = True`, wird der ADTV-Filter erst hier angewendet, nach dem Labeling.

### 6.7 Stufe 6: Equity-Sleeves, feste 10/10/10 als sequenzielle Kaskade

**Basis:** der volle Pool **ohne Real Estate**, company-dedupliziert, sortiert **absteigend nach
`[Adj_FF_MCap, Total MCap]`**. Also `helv_full_pool` minus Real Estate, **inklusive Micro Cap**: Micro
ist zwar für die Sleeves selbst nicht eligible, aber laut Guideline Fill-up-Quelle für Small (siehe
Kaskade unten). Der Tool-Code verwendet hier `helv` ohne Micro, das ist Abweichung 2.

Achtung auf den Wechsel des Sortierschlüssels gegenüber 6.5: Die **Segment-Klasse** kommt aus der
Total-MCap-Ordnung, die **Auswahl innerhalb des Sleeves** läuft nach **Free-Float-MCap**. Damit zieht
Helvetica genau die zehn größten Konstituenten des Float-MCap-gewichteten Sub-Index. Beide Schlüssel
sind verbindlich, sie liefern nicht dieselbe Reihenfolge.

**Ablauf, Reihenfolge Large, dann Mid, dann Small:**

```
available = voller Pool ohne Real Estate, inkl. Micro Cap      # gemeinsamer Restbestand
für seg in [Large Cap (10 %), Mid Cap (15 %), Small Cap (15 %)]:
    own = available[Segment == seg]  nach [Adj_FF_MCap, Total MCap] absteigend

    wenn incumbents nicht leer:   sel = rank_band_select(own, 10, incumbents, 8, 13)
    sonst:                        sel = own.head(10)

    wenn len(sel) < 10:                              # Kaskade, Quelle inkl. Micro Cap
        fb  = available[Segment ist KLEINER als seg]  nach [Adj_FF_MCap, Total MCap] absteigend
        sel = sel + fb.head(10 - len(sel))           # nachgezogene Titel = "Aufrücker"

    available = available ohne sel                   # entfernen, bevor das nächste Segment dran ist
    n = len(sel)
    Gewicht je Titel = Sleeve-Zielgewicht / n
```

Segment-Ordnung für "kleiner als": `Large Cap = 0 < Mid Cap = 1 < Small Cap = 2 < Micro Cap = 3`.

**Die fünf Regeln dahinter:**

1. **Jeder Sleeve nimmt die Top 10 seines eigenen Segments**, gerankt nach `Adj_FF_MCap`.
2. **Kaskade nur nach unten:** Fehlen eigene Titel, wird aus dem **nächstkleineren** Segment
   nachgezogen (Large aus Mid, Mid aus Small). Größere Segmente sind als Quelle ausgeschlossen.
3. **Kein Übertrag nach unten:** Hat ein Segment mehr als 10 Titel, nimmt es seine Top 10, der
   **Überschuss wird verworfen** und wandert nicht in den kleineren Sleeve.
4. **Entfernen vor dem nächsten Sleeve:** Die 10er-Prüfung des nächsten Segments läuft auf dem
   **reduzierten** Bestand. Ein knappes Large kann Mid unter 10 drücken, dann zieht Mid seinerseits
   aus Small nach. Die Kaskade pflanzt sich fort.
5. **Statusfeld je Titel:** `Kern`, wenn die echte Klasse dem Sleeve entspricht, sonst `Aufrücker`.
   `True_Segment` bewahrt in jedem Fall die echte Coverage-Klasse für das Reporting.

**Warum die Kaskade nötig ist:** Der CH-Large-Cap-Markt wird von Nestlé, Novartis und Roche
dominiert. Die ersten 70 % der Float-Coverage sind historisch teils nach fünf Titeln erreicht (2014:
fünf Large Caps). Ohne Kaskade wäre der Large-Sleeve unterbesetzt und die Sleeve-Gewichte würden auf
zu wenige Titel verteilt. Die Kundenanforderung "10/10/10" wird über das Nachziehen erfüllt, ohne die
MSCI-konforme Klassifikation aufzugeben.

> **Abweichung 2 gegen den Backtest-Code: Micro Cap IST Fill-up-Quelle für Small.** Die publizierte
> Guideline ist hier eindeutig und sagt es an zwei Stellen: die Definition "Fill-up Constituent" nennt
> die Kette **Mid nach Large, Small nach Mid, Micro nach Small**, und 4.2.1 schreibt zu den
> Micro-Titeln, sie seien "not eligible for the equity sleeves; they remain available **only as
> fill-up candidates for the Small Cap sleeve**".
>
> Der Tool-Code kann das nicht: sein Quellpool ist `helv`, und `helv` enthält per Definition nur
> Large, Mid und Small (`Segment_New.isin([...])`). Für den Small-Sleeve ist der Fallback deshalb immer
> leer, ein unterbesetzter Small-Sleeve bleibt unterbesetzt und die 15 % verteilen sich auf weniger
> Titel.
>
> **Für das Selektions-Tool gilt die Guideline: der Kaskaden-Quellpool ist der volle Pool inklusive
> Micro Cap** (`helv_full_pool` ohne Real Estate), nicht `helv`. Praktische Wirkung: nur dann, wenn
> Small nach Abzug von Large und Mid unter 10 Titel fällt. Ein so nachgezogener Micro-Titel ist ein
> **Fill-up Constituent**, behält seine echte Größenklasse im Reporting (`True_Segment = Micro Cap`,
> `Status = Aufrücker`) und erhält das normale Sleeve-Gewicht von 1,5 %.

### 6.8 Rang-Band-Buffer 8/13, `rank_band_select`

Aktiv **nur, wenn Inkumbenten existieren**, also ab der zweiten Periode. Läuft **je Sleeve über die
Kandidatenliste des eigenen Segments** (nicht über den Gesamtpool), Rang 1 = größter `Adj_FF_MCap`.

```
Eingabe: df (bereits nach Rang sortiert), top_n = 10, incumbents, hard = 8, exit = 13
rank(Zeile) = Position, 1-basiert

Schritt 1: alle mit rank <= 8                       -> fest drin (Bestand oder neu, egal)
Schritt 2: Restplätze (10 - Anzahl aus Schritt 1)   -> an INKUMBENTEN mit 8 < rank <= 13,
                                                       in Rangfolge
Schritt 3: noch freie Plätze                        -> beste verbleibende Titel mit rank >= 9,
                                                       in Rangfolge (auch Neulinge, auch
                                                       Inkumbenten mit rank > 13)
Rückgabe: die gewählten Zeilen, wieder in Rangfolge, maximal top_n
```

**Asymmetrie als Kern der Regel:** Ein **neuer** Titel muss sich auf **Rang 8** hocharbeiten, um
sicher hereinzukommen. Ein **Bestandstitel** darf bis **Rang 13** abrutschen, bevor er sicher
herausfällt. Die Lücke zwischen 8 und 13 ist der Puffer.

**Beispiel, Bestand aus der Vorperiode:**

| Titel | Rang | Bestand | drin | Grund |
|---|---|---|---|---|
| A | 3 | nein | ja | Rang ≤ 8, harte Aufnahme |
| B | 9 | ja | ja | Inkumbent im Band 9 bis 13, Restplatz |
| C | 12 | ja | ja | Inkumbent im Band, zweiter Restplatz |
| D | 10 | nein | **nein** | Neuling über Rang 8, Restplätze schon an B und C |
| E | 15 | ja | **nein** | Inkumbent, aber Rang über 13 |

**Nebenbedingung, die man nicht verletzen darf:** `hard (8) < top_n (10)`. Wäre der harte Cut gleich
oder größer als die Sleeve-Größe, blieben keine Plätze reserviert und der Buffer wäre wirkungslos, es
wäre wieder eine schlichte Top-10.

**Warum genau dieser Buffer und nicht die Coverage-Hysterese:** In einem Index mit **fixer
Titelzahl** liegt die bindende Grenze am **Rang-10-Schnitt**, nicht an der Coverage-Grenze. Ein Titel,
der die 70 %-Grenze überschreitet, wechselt sein **Label**, nicht seinen Rang. Die ±5/±0,5-Hysterese
kann deshalb den Rang-10-Schnitt nicht stabilisieren. Aus der Simulation über 48 Perioden
(Equity-Eintritte): 8/13 ergibt 53 Eintritte (−28 % gegen kein Buffer), nur ±5/±0,5 ergibt 69
(−7 %), kein Buffer 74. Die beiden Regeln sind also nicht austauschbar, sie stabilisieren
verschiedene Achsen und werden **beide** gebraucht.

### 6.9 Stufe 7: Real-Estate-Sleeve

```
Basis:   helv_full_pool   (inklusive Micro Cap, KEIN Coverage-Cut)
Filter:  FactSet Industry in {"Real Estate Development", "Real Estate Investment Trusts"}
Dedup:   liquideste Linie je Firma
Sortierung: Adj_FF_MCap absteigend  (nur für die Ausgabe, nicht selektionsrelevant)
Auswahl: ALLE qualifizierten, kein Top-N
Gewicht: 15,0 % / n_RE   je Titel
```

**Der Sleeve heißt in der publizierten Guideline "Swiss REITs"** (Abschnitt 4.2.2). Für die Ausgabe ist
diese Bezeichnung zu verwenden, siehe 8.

* **Alle Eignungskriterien gelten unverändert auch für REITs** (Guideline 4.2.2, eigene Aufzählung):
  SIX-Notierung, `Closing Price < CHF 20 000`, `Free Float Percent >= 10 %` (Maintenance 7,5 %),
  `3M ADTV >= CHF 1,0 Mio.` (Maintenance **CHF 750 000**), eine Linie je Firma. Der einzige
  Unterschied zum Equity-Teil ist, dass **keine Größensegmentierung** angewendet wird.
* Real Estate ist aus den Equity-Sleeves **ausgeschlossen** (`~is_re(...)` in 6.7), es gibt also keine
  Doppelzählung. **Trotzdem bleibt Real Estate im Coverage-Pool** und beeinflusst die Größengrenzen
  des Equity-Teils, siehe 6.5.
* **Kein Rang-Band-Buffer**, und die Guideline begründet es ausdrücklich: da der Sleeve alle
  qualifizierten Titel aufnimmt und kein Top-N zieht, gibt es keine Rangkante, die zu stabilisieren
  wäre. Der Bestandsschutz läuft hier über die beiden Schwellen-Buffer, Free Float 7,5 % und ADTV
  CHF 750 000.
* Der Sleeve ist **stark liquiditätsabhängig**. Bei CHF 1,0 Mio. ADTV ist der Korb konzentriert, bei
  CHF 0,25 Mio. deutlich breiter. Da alle Titel gleich gewichtet werden, verändert n direkt das
  Einzelgewicht.
* Die Industry-Strings müssen **exakt** matchen. Weicht der Screener in der Schreibweise ab (Plural,
  Bindestriche, `@NA`), fällt der ganze Sleeve leer aus und der Index kommt auf 85 % Gesamtgewicht.
  Das ist der zweite wahrscheinliche stille Fehler beim Nachbau, siehe Test T4 in Abschnitt 13.

---

## 7. Gewichtung

| Sleeve | Formel | Regelfall |
|---|---|---|
| Statische Sleeves | fixe Konstanten | 45,0 % zusammen |
| Large Cap | `10,0 % / n`, n ≤ 10 | 1,00 % je Titel |
| Mid Cap | `15,0 % / n`, n ≤ 10 | 1,50 % je Titel |
| Small Cap | `15,0 % / n`, n ≤ 10 | 1,50 % je Titel |
| Real Estate | `15,0 % / n_RE` | variabel |

* **Gleichgewichtung, nicht kapitalgewichtet.** `Adj_FF_MCap` bestimmt ausschließlich, **wer**
  hereinkommt, nicht **mit welchem Gewicht**.
* **Das Sleeve-Gewicht bleibt immer auf Ziel.** Bei weniger als 10 Titeln wird auf n statt auf 10
  verteilt, das Einzelgewicht steigt entsprechend.
* **Genau eine Lücke:** Ist ein Sleeve komplett leer (n = 0), ist sein Gewicht 0 und der Index summiert
  auf weniger als 100 %. Das Tool muss diesen Fall sichtbar melden und **darf nicht** stillschweigend
  auf 100 % renormieren, weil das die SAA verändern würde. Der Streamlit-Tab warnt bei einer Abweichung
  über 0,01 Prozentpunkte.
* Rundung: intern mit voller Genauigkeit rechnen, erst in der Anzeige runden (Tool zeigt vier
  Dezimalstellen). Der Backtest-Export gibt Fraktionen (Gewicht / 100).

---

## 8. Output-Schema

Eine Zeile je Position, in dieser Reihenfolge: erst die statischen Sleeves in der Reihenfolge von
Abschnitt 3, dann Large, Mid, Small, dann Real Estate.

| Spalte | Inhalt | statische Zeilen |
|---|---|---|
| `Sleeve` | `Cash`, `Government Bonds`, `Corporate Bonds`, `Gold`, `Large Cap`, `Mid Cap`, `Small Cap`, `Real Estate` | gefüllt |
| `Type` | `Cash`, `Bond - ETF`, `Gold - ETC`, `Equity`, `Real Estate` | gefüllt |
| `Exchange Ticker` | Ticker beziehungsweise Kennung des statischen Instruments | gefüllt |
| `Name` | Wertpapiername | gefüllt |
| `ISIN` | ISIN | leer im Tool-Stand, für die Live-Ausgabe sollten die Gold-ISINs stehen |
| `Mapping Country` | Mapping Country | leer |
| `FactSet Industry` | Industry | leer |
| `Adj_FF_MCap` | Adj_FF_MCap | leer / NaN |
| `Index_Weight` | Zielgewicht in **Prozent des Gesamtindex** | gefüllt |
| `True_Segment` | echte Coverage-Klasse, bei RE `Real Estate` | leer |
| `Status` | `Kern` oder `Aufrücker`, nur Equity | leer |

**Sinnvolle Ergänzungen für den Live-Betrieb** (im Tool-Stand nicht vorhanden): `Selection Date`,
`Entity ID`, `Perm ID`, `Rang im Sleeve`, `Free Float Percent`, `3M ADTV`, `_c_before`, sowie eine
Änderungsspalte gegen die Vorperiode (`Gehalten` / `Neu` / `Raus`). Das erleichtert die Abnahme
erheblich.

**Zusätzlich auszugeben, Parameterprotokoll je Lauf:** Selection Date, ADTV-Schwelle, Free-Float-
Schwellen, Coverage-Cuts, Buffer-Parameter, Anzahl Inkumbenten, Seed ja/nein, Währung des Inputs,
Gesamtgewicht. Ohne dieses Protokoll ist ein Lauf im Nachhinein nicht reproduzierbar.

---

## 9. State-Fortschreibung für die nächste Periode

Nach jedem Lauf schreibt das Tool zwei Dinge fort:

```
incumbents_next    = { normalisierte ISIN aller Zeilen mit Type in ("Equity", "Real Estate") }
                     # ausdrücklich OHNE die statischen Sleeves
prior_segments_next = { Entity ID (getrimmt) -> Segment_New }  über helv_full_pool,
                     # also den KOMPLETTEN CH-Pool inklusive Micro Cap, nicht nur die Mitglieder
```

Beides gehört in einen versionierten Artefakt-Store, ein Lauf pro Selection Date. Ohne
lückenlose Kette lässt sich die Selektion nicht reproduzieren, weil die Regeln pfadabhängig sind.

**Reihenfolge im Mehrperiodenlauf:** streng chronologisch. Ein nachträglich eingeschobenes
Rebalancing-Datum verändert alle Folgeperioden.

---

## 10. Parameter-Referenz

| Parameter | Produktionswert | Alternativen | Wirkung |
|---|---|---|---|
| **`Maintenance Buffer`** (Hauptschalter MP) | **AN** | AUS = Turnover-Referenz ohne Bestandsschutz | übergibt `incumbents` und `prior_segments`, siehe 6.A |
| Min Free Float, Entry | 10,0 % (`0.10`) | fix | Aufnahmeschwelle |
| Min Free Float, Maintenance | 7,5 % (`0.075`) | fix | Bestandsschutz |
| Coverage-Cuts, Entry | 70 / 85 / 99 % | fix | Large / Mid / Small |
| Coverage-Cuts, Maintenance | **75 / 90 / 99,5 %** | fix | Bestandsschutz, Segment-Obergrenzen |
| Anwendungsform Maintenance-Cut | **firmen-intern (Hysterese)** | global via `use_buffer`, nur Analyse | wer profitiert: nur Bestand oder alle |
| Hysterese-Bänder, vollständig | Large < 75, Mid 65 bis 90, Small 84,5 bis 99,5 | fix | Untergrenzen erlauben den Aufstieg |
| 3M-ADTV-Schwelle, Entry | **CHF 1 000 000** | CHF 500 000 / 250 000 nur als Szenario | Aufnahmeschwelle |
| 3M-ADTV-Schwelle, Maintenance | **CHF 750 000** | fix | Bestandsschutz, Guideline 3.1 |
| ADTV-Fenster bei kurzer Historie | maximal verfügbarer Zeitraum | fix | nur Spin-Offs und Mega-IPOs |
| Mega-IPO-Schwelle | **USD 100 Mrd.** Total MCap | fix | in USD, nicht CHF |
| Selection Day | 3. Mittwoch Feb / Mai / Aug / Nov | fix | Guideline 5.1 |
| Rebalancing Day | 1. Mittwoch Mär / Jun / Sep / Dez | fix | Guideline 5.1 |
| `label_before_liquidity` | `False` | `True` | Reihenfolge Liquidität gegen Coverage |
| Sleeve-Zielgewichte Equity | Large 10 %, Mid 15 %, Small 15 % | fix | SAA |
| Titel je Equity-Sleeve (`TOPN`) | 10 | fix | fixe Titelzahl |
| Real-Estate-Sleeve | 15 % | fix | alle qualifizierten |
| RE-Industrien | `Real Estate Development`, `Real Estate Investment Trusts` | fix | exaktes String-Match |
| Rang-Band hart / exit | 8 / 13 | fix | Turnover-Schutz Equity |
| Statische Sleeves | 45 % (Cash 5, Gov 10, Corp 15, Gold 15) | fix | SAA |
| Max Closing Price | **CHF 20 000** | Sidebar | Lindt-Namenaktie |
| Währung aller Geldbeträge | **CHF** | keine | Input und Schwellen, siehe 4.2 |
| Rang-Schlüssel Sleeve-Auswahl | `Adj_FF_MCap`, dann `Total MCap` | fix | wer kommt herein |
| Sortierschlüssel Coverage | `Total MCap`, dann `Adj_FF_MCap` | fix | Größenklasse |
| Dedup-Kriterium | höchstes 3M ADTV je Entity ID | fix | eine Linie je Firma |

Rebalancing-Termine: fix nach Guideline 5.1, siehe 5.4. Die Frequenzauswahl im Multi-Period-Tab
(quartalsweise, halbjährlich, jährlich, eigene Monate) ist eine Backtest-Funktion und keine
Produktionsoption.

---

## 11. Pseudocode, eine Periode am Stück

```
# ---- Eingaben -------------------------------------------------------------
screener        = lade_factset_screener(selection_date)     # Feldnamen normalisieren
incumbents      = lade_incumbents(close_file)               # Stand nach letztem Rebalancing, leer = Seed
prior_segments  = lade_prior_segments(state_store)          # Entity ID -> Segment, voller Pool, leer = Seed
ADTV_ENTRY      = 1_000_000                                 # CHF
ADTV_MAINT      =   750_000                                 # CHF, nur für Inkumbenten
SEED            = (incumbents ist leer)

# ---- Stufe 0: globale Ausschlüsse ---------------------------------------
u = apply_universe_exclusions(screener, max_price=20_000)   # CHF
u = u[nicht auf Sanktionsliste(Emittent)]                    # EU / SECO / OFAC / UN / OFSI
u["Adj_FF_MCap"] = u["Free Float MCap"]                      # CH: IF = 1, kein FOL

# ---- Stufe 1 bis 3b: CH-Pool -------------------------------------------
d = u[(u["Exchange Country Name"] == "SWITZERLAND") & (u["Free Float MCap"] > 0)]

ff_min   = für jede Zeile:  0.075     wenn norm_isin(ISIN) in incumbents sonst 0.10
adtv_min = für jede Zeile:  ADTV_MAINT wenn norm_isin(ISIN) in incumbents sonst ADTV_ENTRY

d = d[d["Free Float Percent"] >= ff_min]
d = d[d["3M ADTV"] >= adtv_min]                             # label_before_liquidity = False
d = dedup_liquideste_linie(d, key="Entity ID", fallback="ISIN::"+ISIN, liq="3M ADTV")
# HINWEIS: Real Estate bleibt hier IM Pool, es wird erst nach der Bucket-Zuordnung getrennt

# ---- Stufe 4: Coverage --------------------------------------------------
d = d.sortiere_absteigend(["Total MCap", "Adj_FF_MCap"])
tot = summe(d["Adj_FF_MCap"])
d["_c_before"] = (cumsum(d["Adj_FF_MCap"]).shift(1).fillna(0) / tot * 100) wenn tot > 0 sonst 0

# ---- Stufe 5: Segmentierung --------------------------------------------
d["Segment"] = harter_cut(d["_c_before"], 70, 85, 99)       # Large/Mid/Small/Micro
wenn prior_segments nicht leer:
    für jede Zeile:
        p = prior_segments.get(trim(Entity ID))
        wenn p == "Large Cap" und _c_before < 75.0:                       Segment = "Large Cap"
        sonst wenn p == "Mid Cap"   und 65.0 <= _c_before < 90.0:         Segment = "Mid Cap"
        sonst wenn p == "Small Cap" und 84.5 <= _c_before < 99.5:         Segment = "Small Cap"

full = d                                                    # inkl. Micro UND Real Estate

# ---- Stufe 6: Equity 10/10/10 ------------------------------------------
# Quellpool: alles außer Real Estate, INKLUSIVE Micro Cap (Micro = Fill-up-Quelle für Small)
eq = full[nicht RE].sortiere_absteigend(["Adj_FF_MCap","Total MCap"])
zeilen = []
verfügbar = eq
für (seg, sleeve_w) in [("Large Cap",10.0), ("Mid Cap",15.0), ("Small Cap",15.0)]:
    own = verfügbar[Segment == seg].sortiere_absteigend(["Adj_FF_MCap","Total MCap"])
    sel = rank_band_select(own, 10, incumbents, 8, 13) wenn nicht SEED sonst own.head(10)
    wenn len(sel) < 10:
        fb  = verfügbar[seg_rank(Segment) > seg_rank(seg)].sortiere_absteigend(["Adj_FF_MCap","Total MCap"])
        sel = sel + fb.head(10 - len(sel))       # Fill-up: Mid->Large, Small->Mid, Micro->Small
    verfügbar = verfügbar ohne sel
    w = sleeve_w / len(sel) wenn len(sel) > 0 sonst 0
    für r in sel:
        status = "Kern" wenn r.Segment == seg sonst "Aufrücker"
        zeilen.append(sleeve=seg, type="Equity", weight=w, true_segment=r.Segment, status=status, ...)

# ---- Stufe 7: Swiss REITs ----------------------------------------------
re_pool = full[Industry in RE_INDUSTRIES].sortiere_absteigend("Adj_FF_MCap")
w_re = 15.0 / len(re_pool) wenn len(re_pool) > 0 sonst 0
für r in re_pool:
    zeilen.append(sleeve="Swiss REITs", type="Real Estate", weight=w_re, true_segment="Real Estate", ...)

# ---- Statische Sleeves + Abschluss -------------------------------------
zeilen = STATISCHE_45_PROZENT + zeilen
prüfe  summe(weight) == 100.0 (Toleranz 0,01) sonst WARNUNG, NICHT renormieren

# ---- State fortschreiben ------------------------------------------------
incumbents_next     = { norm_isin(ISIN) für Zeilen mit type in ("Equity","Real Estate") }
prior_segments_next = { trim(Entity ID) -> Segment für alle Zeilen in full }
```

---

## 12. Von Zielgewichten zu Stückzahlen, falls die Engine das erwartet

Falls das Selektions-Tool nicht Gewichte, sondern Stückzahlen an die Engine übergeben soll, ist das
der Standardweg (**Konvention der Engine ist zu bestätigen, insbesondere die FX-Richtung**):

```
Positions-Marktwert = Index-Marktwert × Index_Weight / 100
Stückzahl           = Positions-Marktwert / (Schlusskurs am Rebalancing-Stichtag × FX in Indexwährung)
```

Der Schlusskurs kommt aus dem Close File und steht bei CH-Titeln in **CHF**, ebenso wie die
Selektionsdaten (4.2). Die **Indexwährung ist dagegen EUR** (NTR-Variante), hier liegt also die
einzige Stelle im ganzen Prozess, an der überhaupt ein FX-Kurs gebraucht wird. Die **Selektion selbst
ist FX-frei**: sie läuft vollständig in CHF. Ob gerundet wird, ob Bruchstücke erlaubt sind und ob der Divisor beim
Rebalancing neu gesetzt wird, entscheidet die Engine, nicht das Selektions-Tool. **Wenn die Engine
Gewichte akzeptiert, sollte das Selektions-Tool nur Gewichte liefern**, dann bleibt die Selektion
frei von Kurs- und FX-Annahmen und ist einfacher zu prüfen.

---

## 13. Abnahmetests, die vor dem Live-Betrieb grün sein müssen

| # | Test | Erwartung |
|---|---|---|
| T1 | Gesamtgewicht | 100,00 % ± 0,01 pp |
| T2 | Sleeve-Summen | Cash 5, Gov 10, Corp 15, Gold 15, Large 10, Mid 15, Small 15, RE 15 |
| T3 | Titelzahlen Equity | 10 / 10 / 10, jede Abweichung mit Begründung im Log |
| T4 | RE-Sleeve nicht leer | n_RE > 0, sonst Industry-Strings prüfen |
| T5 | Keine Firma doppelt | `Entity ID` über alle selektierten Zeilen eindeutig |
| T6 | Kein Titel in zwei Sleeves | ISIN über Equity und RE eindeutig |
| T7 | Free Float | jeder selektierte Titel ≥ 10 %, Inkumbenten ≥ 7,5 % |
| T8 | Liquidität | jeder selektierte Titel ≥ CHF 1,0 Mio., Inkumbenten ≥ CHF 750 000, keine weitere Ausnahme außer Spin-Off / Mega-IPO |
| T9 | Micro Cap | kein Micro-Titel als **Kern**-Konstituent eines Equity-Sleeves. Zulässig sind nur der REIT-Sleeve und ein **Fill-up** in den Small-Sleeve (6.7) |
| T9b | Coverage-Pool | Summe `Adj_FF_MCap` des Nenners **enthält Real Estate**. Gegenprobe: Nenner ohne RE gerechnet muss andere Bucket-Grenzen ergeben, sonst ist RE fälschlich vorher gefiltert |
| T9c | Sanktionslisten | Screen läuft, Trefferliste wird protokolliert, auch wenn sie leer ist |
| T10 | Determinismus | zweimal derselbe Input inklusive State ergibt bitidentischen Output |
| T11 | Seed-Reproduktion | Seed-Periode gegen den Excel-Export des Streamlit-Tabs, Ticker-Liste identisch |
| T12 | Buffer-Wirkung | mit 8/13 muss der Turnover niedriger sein als ohne, Größenordnung −28 % über viele Perioden |
| T13 | Sub-Index-Konsistenz | jeder selektierte Equity-Titel ist im Swiss Size Sub-Index seines Sleeves enthalten |
| T14 | Währung einheitlich | **jedes** Geldfeld in CHF (Total MCap, Free Float MCap, 3M ADTV, Closing Price), im Parameterprotokoll dokumentiert, bei Abweichung Abbruch statt Warnung |
| T15 | Maintenance ist nie global | ein **Nicht**-Inkumbent mit Free Float zwischen 7,5 % und 10 % darf **nicht** selektiert werden, ein Inkumbent im selben Band schon |
| T16 | Schalterstellung | `Maintenance Buffer = AN` und `use_buffer = False` in jedem Produktionslauf, Kombination von `use_buffer` mit `prior_segments` per Assertion verboten (6.A, 6.6) |
| T16b | Hauptschalter wirkt | derselbe Lauf mit `Maintenance Buffer = AUS` muss **mehr** Eintritte erzeugen als mit AN, sonst wird der State nicht wirklich übergeben |
| T17 | Rang-Band-Asymmetrie | ein Neuling auf Rang 9 oder 10 kommt nur herein, wenn kein Inkumbent im Band 9 bis 13 den Restplatz beansprucht |

**Wichtigster Test ist T11.** Der Referenz-Abgleich läuft über den Excel-Export
`Helvetica_Composition_<datum>.xlsx` aus dem Streamlit-Tool (Sheets `Helvetica Composition`,
`Allocation Summary`, `Parameter Settings`). Für einen echten Vergleich muss der Nachbau auf dieselben
Parameter gestellt werden: `label_before_liquidity = False`, `use_buffer = False`, und beim Gold die
**Backtest-Proxy-Ticker** (PPFB/XAD5), weil der Tool-Export sie so ausgibt. Erst danach auf die
Live-Gold-ISINs umstellen.

**Währung im Referenzvergleich, wichtig:** Der Tool-Export beruht auf **USD**-Daten und
**USD**-Schwellen (ADTV 1,0 Mio. USD, Max Price 20 000 USD). Für T11 muss der Nachbau deshalb in einem
eigenen **Vergleichsmodus** laufen: USD-Screener plus USD-Schwellen. Läuft er im Produktionsmodus
(CHF-Daten, CHF-Schwellen), sind Abweichungen im Real-Estate-Korb **erwartet** und kein Fehler, weil
CHF 1,0 Mio. die strengere Hürde ist (siehe 4.2). Der **Equity-Teil muss trotzdem identisch sein**:
die 30 Titel liegen weit über jeder dieser Schwellen, und die Coverage-Cuts sind relativ und damit
währungsinvariant. Genau das macht T11 zu einem starken Test: **Equity identisch, Real Estate
erklärbar unterschiedlich.** Weicht der Equity-Teil ab, liegt ein echter Implementierungsfehler vor
und keine Währungsdifferenz.

Für den Mehrperiodenvergleich gibt es zusätzlich `Helvetica_MultiPeriod_<von>_to_<bis>.xlsx`
(Summary, Long, Weight Matrix) und den Backtest-Export als Matrix Termin × Ticker mit Gewichten als
Fraktion.

**Kontrollgröße Schicht 1:** Die Swiss Size Sub-Indizes (`build_swiss_size_subindices`) sind für die
Selektion nicht nötig, eignen sich aber ideal als Kontrolle (T13). Regeln: gleiches CH-Universe wie
Helvetica, aber **kein Dedup** (Variante B, alle Share Lines dürfen vorkommen), jede Linie **erbt das
Segment ihrer Firma** aus dem firmen-internen Coverage-Cut, Gewicht = `Adj_FF_MCap` je Sub-Index auf
100 % normiert, Real Estate ausgeschlossen. Die Free-Float-Maintenance (7,5 %) muss identisch zur
Helvetica-Pipeline gesetzt sein, sonst fehlt ein Helvetica-Titel im Sub-Index und T13 schlägt
fälschlich an.

---

## 14. Offene Punkte und was die Guideline bereits entschieden hat

### Durch die Guideline v1.0 entschieden, hier nur zur Dokumentation

| früherer offener Punkt | Entscheidung durch die Guideline |
|---|---|
| Kaskadenquelle Micro Cap | **entschieden: Micro ist Fill-up-Quelle für Small** (Definition "Fill-up Constituent", 4.2.1). Der Code kann es nicht, das Tool muss es können. Siehe 6.7 |
| ADTV-Maintenance | **entschieden: CHF 750.000 für Inkumbenten** (3.1, 4.2.1, 4.2.2). Der Code hat keine. Siehe 6.3 |
| Rebalancing-Frequenz | **entschieden: quartalsweise**, Selection Day 3. Mittwoch Feb/Mai/Aug/Nov, Rebalancing Day 1. Mittwoch Mär/Jun/Sep/Dez (5.1). Siehe 5.4 |
| Gold-Instrumente | **entschieden: Amundi FR0013416716 und Xtrackers DE000A1E0HR8, je 7,5 %** (4.2.4). PPFB/XAD5 bleiben reiner Backtest-Proxy |
| Währung der Kriterien | **entschieden: CHF**, ADTV CHF 1,0 Mio., Preis CHF 20.000 (3.1, 4.2.1) |

### Weiterhin offen

1. **Gold-Instrumente im Vergleichslauf.** Sachlich entschieden (Amundi und Xtrackers), zu klären
   bleibt nur die Tool-Mechanik: das Selektions-Tool sollte beide Sets als Konfiguration führen, mit
   den Live-ISINs als Default und einem Backtest-Schalter auf PPFB/XAD5, damit T11 sauber läuft.
2. **Inkumbenten-Schlüssel.** ISIN (Tool-Stand) gegen Perm ID mit ISIN-Fallback (robuster). Wirkt auf
   den Bestandsschutz und ist damit ergebnisrelevant. Die Guideline schreibt keinen Schlüssel vor.
3. **`prior_segments`-Quelle im Live-Betrieb.** Enthält das Close File nur Indexmitglieder, braucht
   das Tool einen eigenen State über den vollen CH-Pool (siehe 5.1).
4. **Verhalten bei unterbesetztem Sleeve.** Regel für n < 10 ist klar (Guideline 4.2.1: Zielgewicht
   gleichmäßig auf die vorhandenen Titel). Der Fall **n = 0** ist in der Guideline nicht geregelt, dann
   summiert der Index unter 100 %. Ob es eine Eskalationsregel geben soll (zum Beispiel Umschichtung
   in Cash) sollte für den Live-Betrieb geklärt werden, auch wenn der Fall im Schweizer Universe
   praktisch nicht auftritt.
5. **`Free Float MCap` als Eingangsgröße.** In den FactSet-Daten gibt es eine bekannte Anomalie:
   ein Teil der Zeilen weist Free Float MCap größer als Total MCap aus, betroffen sind vor allem
   DM-Mega-Caps, während das Prozentfeld sauber ist. Für Helvetica trifft das potenziell Nestlé,
   Novartis und Roche und damit direkt die Coverage-Kurve. **Die aktuelle Methodik nutzt das
   Free-Float-MCap-Feld unverändert.** Empfehlung: eine reine **Plausibilitätsprüfung** einbauen
   (`Free Float MCap > Total MCap` melden, zusätzlich `Total MCap × Free Float Percent` als
   Vergleichswert ausweisen) und die Fälle berichten. Ein Umstellen der Berechnungsbasis wäre eine
   Methodik-Änderung und darf nicht ohne Freigabe passieren.
8. **Docstring gegen Implementierung beim Maintenance-Cut.** Der Docstring von
   `build_helvetica_pipeline` listet die Maintenance-Schwellen (Large `< 75`, Standard `< 90`,
   Small `< 99,5`) in derselben Tabelle wie den Minimum Free Float und schreibt darunter "Buffer PRO
   TITEL: Maintenance-Schwellen gelten, wenn der Titel in `incumbents_isin` ist". Wörtlich gelesen
   hieße das: ein Inkumbent bekommt seinen Coverage-Bestandsschutz **titelweise**. Der Code wendet die
   Titel-Logik (`_maint`) aber **nur auf den Minimum Free Float** an. Auf der Coverage-Achse arbeitet
   er entweder global (`use_buffer`) oder **firmenweise** über `prior_segments`. Wer den Docstring
   wörtlich nachbaut, vergibt einen Bestandsschutz, den der Backtest nie hatte. **Maßgeblich ist der
   Code, also Abschnitt 6.6.** Empfehlung: den Docstring präzisieren, damit die nächste Person nicht
   in dieselbe Falle läuft.
7. **Guideline v1.1: die Aufzählungen der Maintenance Buffer sind unvollständig.** Die Definition in
   Abschnitt 2 und der Satz "Incumbency protection operates through **three** mechanisms" in 4.2.1
   nennen nur Free Float, Coverage-Hysterese und Rang-Band. Die ADTV-Maintenance (CHF 750.000) steht
   dagegen dreimal in den Kriterien-Listen. Die Aufzählungen sollten auf **vier** Mechanismen
   erweitert werden, damit die Guideline in sich stimmt. Rein redaktionell, ohne Wirkung auf die
   Selektion, aber genau die Art Unstimmigkeit, über die eine Prüfung stolpert.
8. **Wortlaut "Primary Exchange: SIX Swiss Exchange" gegen `Exchange Country = Switzerland`.**
   Auslegung und Empfehlung stehen in 6.1. Zu bestätigen, weil die strenge Lesart Titel an anderen
   Schweizer Börsen und SIX-Secondary-Linien ausschließen würde.
9. **Sanktionslisten: Bezugsquelle und Matching-Schlüssel.** Die Guideline verlangt den Ausschluss
   (EU, SECO, OFAC, UN, OFSI), sagt aber nichts über die Umsetzung. Zu klären: woher die Listen
   bezogen werden, in welcher Frequenz, und über welchen Schlüssel gematcht wird. Name-Matching ist
   fehleranfällig, LEI oder Entity ID ist vorzuziehen. Dazu gehört auch der Prozess für das
   außerordentliche Rebalancing nach Guideline 5.2.
10. **Spin-Off- und Mega-IPO-Ausnahme in Daten abbilden.** Die Guideline erlaubt bei unvollständiger
    Historie den maximal verfügbaren ADTV-Zeitraum. Der Screener liefert nur fertige Fenster, also
    braucht das Tool eine Fallback-Kette (`3M`, sonst `1M`) und ein Kennzeichen, welche Titel über die
    Ausnahme hereinkamen. Ohne dieses Kennzeichen ist im Nachhinein nicht prüfbar, ob die Ausnahme
    korrekt angewendet wurde.
11. **Docstring gegen Implementierung beim Maintenance-Cut.** Der Docstring von
    `build_helvetica_pipeline` listet die Maintenance-Schwellen (Large `< 75`, Standard `< 90`,
    Small `< 99,5`) in derselben Tabelle wie den Minimum Free Float und schreibt darunter "Buffer PRO
    TITEL: Maintenance-Schwellen gelten, wenn der Titel in `incumbents_isin` ist". Wörtlich gelesen
    hieße das: ein Inkumbent bekommt seinen Coverage-Bestandsschutz **titelweise**. Der Code wendet
    die Titel-Logik (`_maint`) aber **nur auf den Minimum Free Float** an. Auf der Coverage-Achse
    arbeitet er entweder global (`use_buffer`) oder **firmenweise** über `prior_segments`, was der
    Guideline entspricht. Empfehlung: den Docstring präzisieren.

---

## 15. Designprinzipien, in einem Absatz

Der Swiss-Made Portfolio Index ist ein **Multi-Asset-Index mit fixer SAA**: 45 % statisch (Cash,
Bond-ETFs, Gold-ETCs), 55 % selektiert. Die Schweiz wird über die **Börse** definiert (SIX), nicht
über das Domizil. Die Größensegmentierung ist **selbstkalibrierend**: statt fester
Marktkapitalisierungsschwellen, die regelmäßig überprüft werden müssten, zieht die **kumulierte
Free-Float-Coverage** (70 / 85 / 99 %) die Grenzen automatisch anhand der jeweiligen Struktur des
Schweizer Marktes. Pro Firma zählt nur die **liquideste Linie**, Auswahl je Bucket sind die **Top 10**
nach Free-Float-MCap, **gleichgewichtet**. Die feste Zahl 10/10/10 wird über eine **Top-down-Kaskade**
mit Fill-up aus dem nächstkleineren Bucket erfüllt, ohne die Klassifikation aufzugeben. Der Turnover
wird auf **vier** Achsen gedämpft: Free Float 7,5 %, ADTV CHF 750.000, Coverage-Hysterese
±5 / ±0,5 und Rang-Band 8/13. Der Rang-Band-Buffer ist dabei der wirksamste, weil bei fixer Titelzahl
der **Rang-10-Schnitt** die bindende Grenze ist und nicht die Coverage-Grenze. Alle Buffer greifen nur
im laufenden Betrieb, weil sie Inkumbenten brauchen. Die Pipeline ist eigenständig: kein EUMSS, kein
DM/EM-Split, keine In-Eligible-Liste, kein UCITS-Capping, kein FOL (für die Schweiz ist IF = 1).

---

## 16. Referenzen

**Autoritative Quelle:**

| Dokument | Inhalt |
|---|---|
| **Index Guideline "Swiss-Made Portfolio Index", Version 1.0, 01.07.2026** | die publizierte Methodik. Für den Live-Index allein maßgeblich. Relevant für die Selektion: Abschnitt 2 (Definitionen, insbesondere Cumulative FF MCAP Coverage, Fill-up Constituent, Maintenance Buffer, Most-Liquid Share Line, Rank-Band Buffer, Sanctions List), 3.1 (Kriterien-Übersicht), 4.1 (Universe), 4.2.1 bis 4.2.5 (Zusammensetzung), 4.3 (Selection Day), 4.4 (SAA), 5.1 und 5.2 (Rebalancing) |

**Code:**

| Funktion | Datei | Inhalt |
|---|---|---|
| `build_helvetica_pipeline` | `naroix_benchmark.py` | Stufen 1 bis 5, Segmentierung |
| `build_helvetica_composite` | `naroix_benchmark.py` | Equity-Kaskade, Real Estate, statische Sleeves, Gewichte |
| `_helv_dedup_most_liquid` | `naroix_benchmark.py` | Company-Dedup |
| `build_swiss_size_subindices` | `naroix_benchmark.py` | Schicht 1, Kontrollgröße |
| `HELVETICA_*`-Konstanten | `naroix_benchmark.py` | alle Parameter aus Abschnitt 10 |
| `render_helvetica_tab` | `naroix_benchmark.py` | Single-Snapshot-Tab, Exporte |
| Tab `Helvetica Multi-Period` | `naroix_benchmark.py` | Mehrperiodenlauf, State-Fortschreibung |
| `build_new_universe` | `pipeline_core.py` | Stufe 0 |
| `apply_universe_exclusions` | `pipeline_core.py` | die neun Ausschlussregeln |
| `derive_mapping_country` | `pipeline_core.py` | Mapping Country, Risk-First-Fallback |
| `apply_fol_matrix`, `_resolve_fol_row` | `pipeline_core.py` | IF, für CH immer 1,0 |
| `_rank_band_select` | `pipeline_core.py` | Rang-Band-Buffer 8/13 |
| `_norm_isin`, `_match_key` | `pipeline_core.py` | Normalisierung, Matching-Schlüssel |
| `load_master_excel` | `pipeline_core.py` | Feld-Aliase und Normalisierung |

**Dokumente im Repo** (`Claude_Guideline_Drafts/`):

* `NaroIX_Helvetica_Index_Guideline.md`: Methodik-Guideline, Kundensicht
* `Helvetica_Selektionsprozess_Automatisierung.md`: Automatisierungs-Spezifikation, Vorgänger dieses Dokuments
* `Helvetica-Rang-Band-Buffer.md`: Buffer 8/13 im Detail, mit Beispiel
* `Helvetica-Buffer-Achsen.md`: warum 8/13 und ±5/±0,5 nicht austauschbar sind, mit Simulationsbelegen
* `HANDOVER.md`: Gesamtkontext der Engine

---

*Dieses Dokument setzt die Index Guideline "Swiss-Made Portfolio Index" v1.0 (01.07.2026) in eine
Bau-Spezifikation um, Stand 2026-08-10. **Maßgeblich ist die Guideline.** Wo dieses Dokument oder der
Tool-Code davon abweicht, gilt die Guideline, und die Abweichung ist in Abschnitt 0 und 14
ausgewiesen.*

**Vier bewusste Abweichungen des Tool-Codes, die NICHT als Doku-Fehler zu "korrigieren" sind:** Der
Backtest-Code arbeitet (a) in USD statt CHF, (b) ohne ADTV-Maintenance, (c) ohne Micro-nach-Small-
Fill-up und (d) ohne Sanktions-Screen. Er bleibt so, damit die publizierte Backtest-Historie
reproduzierbar bleibt. Das **Selektions-Tool** setzt in allen vier Punkten die Guideline um.
