# Multi-Period Run — Spezifikation

> Beschreibt die beiden Multi-Period-Tabs der NaroIX-Benchmark-App: den regulären
> **🔁 Multi-Period Run** (Baseline, Segmentierung je Land) und den optionalen
> **🇪🇺 Europe MP (Pooled)** (Developed Europe als ein Markt). Stand: 2026-08-15.
>
> Verwandte Dokumente: `SELECTION.md` (Selektionsprozess), `INDEX_SERIES.md` (Produktkatalog),
> `NaroIX_Europe_Global_Index_Guideline.md` (Methodik EU/GM), `HANDOVER.md` (Designentscheidungen).

---

## 1. Zweck

Ein Multi-Period-Lauf rechnet die Indexserie über mehrere Selection Dates hinweg und schreibt
dabei den Bestand fort. Erst dadurch werden die pfadabhängigen Mechanismen wirksam, die es im
Einzelperioden-Lauf nicht gibt:

- **Maintenance Buffer** (Mitgliedschaft)
- **Size Buffer** (Segment-Hysterese)
- **Rang-Band-Buffer** (Fixed-Count-Produkte)
- **Turnover-Statistik** (Zu- und Abgänge je Periode)

Ohne Multi-Period gibt es keine Incumbents, also auch keine Puffer.

---

## 2. Voraussetzungen

- Sidebar-Datenmodus = **„Master File (Multi-Period)"**, Master-File hochgeladen.
- Der Kalender kommt aus `Selection Dates.xlsx`: **48 Termine, 2014-11-19 bis 2026-05-20**,
  in den Monaten **Februar, Mai, August, November** (plus ein Januar-Ausreißer).
  Das entspricht der Review-Kadenz der etablierten Anbieter (Semi-Annual Mai/November,
  Quarterly Februar/August).

---

## 3. Rechenmodell (Option Y)

**Pro Periode läuft die Pipeline genau einmal.** Alle gewählten Produkte sind konsistente
`build_index`-Slices dieses einen Laufs.

```
für jede Periode:
    Snapshot bauen  →  run_selection_pipeline(...)  →  gm_complete
                                                        ├─ build_index(NX-GM-LM)
                                                        ├─ build_index(NX-EU-LM)
                                                        └─ ...
    Incumbent-State fortschreiben = investierbares Universe (Large + Mid + Small)
```

Konsequenzen:

- Ein Titel hat in **jeder** Periode genau **eine** Size-Klasse über alle Produkte hinweg.
- Die Identitäten `NX-GM-* = NX-DM-* + NX-EM-*`, `NX-*-AC = -L + -M + -S` und
  `NX-EU-LM ⊆ NX-DM-LM` gelten by construction.
- Deutlich schneller als ein Lauf je Produkt.

**Zweiter Lauf je Periode** nur, wenn ein Total-Markets-Produkt (`eumss_off`) gewählt ist:
identische Einstellungen, aber EUMSS-Floor aus, mit **eigenem** Incumbent-State.

**Incumbent-Matching** läuft über `_match_key`, also Perm ID mit ISIN-Fallback. Damit
überlebt der Bestand ISIN- und Ticker-Wechsel.

---

## 4. Bedienung

| Element | Bedeutung |
|---|---|
| Start-Periode (Seed) | Erste Periode. Keine Incumbents, alle Titel laufen durch die Entry-Schwellen. |
| End-Periode | Letzte Periode des Laufs. |
| Welche Indizes berechnen? | Mehrfachauswahl aus `INDEX_SERIES`, Default `NX-GM-LM`. |
| ▶️ Multi-Period Run starten | Startet den Lauf, Fortschrittsbalken je Periode. |

Alle übrigen Parameter kommen aus der **Sidebar** und gelten für den gesamten Lauf.

---

## 5. Puffer und Schalter (Sidebar), aktuelle Defaults

| Schalter | Default | Wirkung im Multi-Period |
|---|---|---|
| **Buffer Rules** (Maintenance) | **an** | Weichere Schwellen für Incumbents: Min FF **7,5 %**, Coverage **90 %**, ADTV DM **750k**. Erst ab Periode 2. |
| **Size Buffer** (Segment-Hysterese) | **an**, **±5 pp** | Incumbents halten ihr Segment im Band um 70 % und 85 %, also 65/75 und 80/90. Erst ab Periode 2. |
| **Small-Cap Coverage-Cut** (Solactive 99/99,5) | **an** | Kappt Small bei 99 % Länder-Coverage, Incumbent bis 99,5 %. Betrifft nur Small und All Cap, Standard bleibt unberührt. |
| **Capping** (UCITS 5/10/40) | aus | Nur für die sechs Tech-Produkte mit `cap`-Flag. |
| **MSCI Logic (GIMI)** | aus | Full-MCap-Cutoffs, GMSR als IMI-Floor (EM = ½), Migrations-Buffer 2/3 und 1,5. Überschreibt den Coverage-Buffer. |
| **Asymmetrischer Size-Buffer** | aus | Mid wird bis 90 % gehalten, Small steigt ungepuffert auf. |
| **Labeling vor Liquidität** | aus | Coverage-Waterfall auf dem vollen post-EUMSS-Pool, Liquidität wirkt danach nur als Mitgliedschafts-Gate. |

**Rang-Band-Buffer** (Fixed-Count-Produkte, keine eigene Sidebar-Option): aktiv, wenn Buffer
Rules an sind und das Produkt `buffer_hard` / `buffer_exit` trägt. Gezählt wird auf
**Unternehmensebene** (Entity ID mit ISIN-Fallback). US-500 = 425/600, die 100er-Produkte
= 85/120, EU-T30 = 25/36.

> **Wichtig:** Alle Puffer greifen erst ab der **zweiten** Periode. Die Seed-Periode nutzt
> immer die glatten Schwellen.

### ATVR-Beine und Hochpreis-Regel (2026-08-25)

Der ATVR-Screen laeuft ab jetzt auf **3M und 6M**, synchron zu den ADTV-Beinen. Vorher waren es
3M und 12M. Solange die ATVR-Schwellen auf 0 stehen, ist die Umstellung verhaltensneutral
(`0 >= 0` ist wahr); mit Schwellen groesser 0 ist sie es nicht, deshalb steht sie explizit im
Code und in `test_atvr_dual_horizon`. `ATVR_12M` bleibt als Spalte im Export.

Hochpreis-Regel statt Preis-Ausschluss: Kurs ab 20.000 USD schliesst nicht mehr aus, verlangt
aber `min(ATVR 3M, ATVR 6M)` von **10 %** (neu) bzw. **5 %** (Bestand). Parameter
`max_price_atvr` und `m_max_price_atvr`. Der normale Ast (Kurs unter 20.000) hat weiterhin
Schwelle 0, also keine ATVR-Anforderung; Begruendung in der Index-Guideline (indische
BSE-Datenlage).

Sidebar: der Max-Price-Block hat eine Umschaltung "Ausschluss (bisher)" / "ATVR-Bedingung",
Default ATVR-Bedingung, dazu zwei Schwellenfelder. Alles im Settings-Stempel.

### Liquiditaets-Buffer, korrigiert am 2026-08-25

`apply_liquidity_new` erkannte Bestandstitel an der reinen ISIN, obwohl `incumbents_isin` aus
`_match_key` (Perm ID mit ISIN-Fallback) gefuellt wird. Da Perm ID im Master vollstaendig
gefuellt ist, traf die Bedingung nie: 0 von 28.580 Zeilen am 2026-08-19. Der ADTV-/ATVR-
Maintenance-Buffer war damit wirkungslos, jeder Bestandstitel lief gegen die Entry-Schwelle.

Nach dem Fix (Europe Pooled, 48 Perioden, asym 5 pp): NX-EU-LM 371 -> 373, NX-DM-LM
1.440 -> 1.443, NX-GM-LM 2.800 -> 2.823, Turnover faellt in allen drei Produkten
(GM 6,48 -> 6,19 %). Backtests vor diesem Datum sind nicht reproduzierbar.

### Spin-off-Aufnahme (Stand 2026-08-25)

Schalter `Spin-off-Aufnahme` in der Sidebar, Default **an**. Quelle ist `Spin-Off Data.xlsx`;
fehlt das File oder ist die Liste leer, ist der Schalter ein exakter No-op.

Wirkung: die Kinder des jeweiligen Termins werden vor dem Pipeline-Aufruf in den
Incumbent-State geschrieben (`seed_spinoff_incumbents` in `pipeline_core.py`). Damit behandelt
`run_selection_pipeline` sie wie Bestandstitel, ohne dass an der Engine etwas geaendert werden
muss: Bestandsschutz ist dort nur ein Set plus ein Dict, die die Run-Schleife uebergibt.

Geseedet wird in den **drei** Incumbent-States, die auf `run_selection_pipeline` laufen, jeweils
getrennt weil sie unabhaengig fortgeschrieben werden: Multi-Period Haupt, Multi-Period
Total-Markets (EUMSS aus) und Europe MP (Pooled).

OFFEN: **Helvetica MP ist noch nicht geseedet.** Es faehrt einen eigenen Pfad
(`build_helvetica_pipeline` statt `run_selection_pipeline`) und schluesselt seinen
Incumbent-State auf `Entity ID` statt auf Perm ID. `seed_spinoff_incumbents` nimmt dafuer den
Parameter `key_fn` und ist getestet, die Verdrahtung in der Helvetica-Schleife fehlt aber noch.
Ein Schweizer Spin-off wird dort also weiterhin als Neuzugang behandelt.

ADTV-Ausnahme je HORIZONT, abgeleitet aus dem Ex-Date (`spinoff_liquidity_exemptions` ->
`liquidity_exempt_missing`): ein Horizont wird uebersprungen, solange
`selection_date < ex_date + N Monate` gilt und der Wert leer oder 0 ist (N = 3 fuer das
3M-Bein, 6 fuer 6M, 12 fuer das 12M-ATVR-Bein). Bei Quartals-Rhythmus ist das 3M-Bein damit
meist nur am Seed-Termin offen, das **6M-Bein an den ersten zwei Terminen**.

Warum am Horizont und nicht am Seed: eine Ausnahme, die nur am Seed-Datum gilt, laesst das Kind
eine Periode spaeter an der 6M-Huerde scheitern, die es rechnerisch nicht erfuellen kann. Es
faellt dann aus `gm_complete`, verliert dadurch den geerbten Bestandsschutz (der Incumbent-State
der Folgeperiode wird aus `gm_complete` neu aufgebaut), kommt als Neuzugang gegen den glatten
Coverage-Schnitt und ist dauerhaft ausgesperrt. Nachgerechnet an Magnum (Ex-Date 2025-12-08,
Seed 2026-02-18): mit der Horizont-Ausnahme durchgehend Mid Cap und im Index (379 / 375 / 373
Titel), auch wenn am Seed-Termin alle ADTV-Spalten und am Folgetermin 6M und 12M leer sind.

Berechtigt ist nur ein Kind, das gerade geseedet wird oder schon Bestandstitel ist. Ein
verworfener Seed bekommt keine Liquiditaets-Erleichterung.

Wichtig: "fehlend" heisst NaN **oder <= 0**. `build_new_universe` macht
`pd.to_numeric(...).fillna(0)` auf alle vier ADTV-Spalten, im Screen kommen fehlende Werte also
als 0.0 an. Eine Pruefung nur auf NaN kann nie greifen (erste Version genau deshalb wirkungslos).
Ein vorhandener Wert oberhalb 0 aber unter der Schwelle schliesst weiter aus.

Ausgaben:
- Spalte `Spinoff_Seeded` auf den Konstituenten, sichtbar in Detailtabelle und Long-Export
- Spalte `Spin-off-Seeds` in der Summary je Periode
- Sheet `Spin-offs` im Long-Format-Export mit dem Protokoll je Eintrag (geseedet oder verworfen,
  jeweils mit Begruendung)
- Expander im Ergebnisblock mit demselben Protokoll
- Eintrag im Settings-Stempel, damit ein Export dokumentiert, ob die Regel aktiv war

Gemessene Wirkung, Europe MP (Pooled), 48 Perioden 2014-11-19 bis 2026-08-19, asymmetrischer
Size Buffer 5 pp, Liste mit drei Eintraegen: NX-EU-LM **370 -> 371** Titel. Nur Magnum Ice Cream
(Unilever-Abspaltung, Seed 2026-02-18) kommt tatsaechlich dazu, es liegt beim ersten Auftauchen
bei Coverage 88,73 % und wird von der Hysterese gehalten. Italgas (Snam-Abspaltung 2016) wird
geseedet, bleibt aber wirkungslos, weil seine Coverage danach durchgehend jenseits der 90er-Kante
liegt. Sandoz (Novartis-Abspaltung 2023) hatte die Entry-Schwellen ohnehin selbst geschafft und
war bereits ab 2023-11-15 im Index. Ein "geseedet" im Protokoll heisst also, dass der Seed
angewandt wurde, nicht dass er noetig war.

### Bekannte Asymmetrie beim Newcomer-Schnitt

`_size_segment` schneidet **Neuzugänge** am glatten 70/85, während Incumbents im Band 65/75
bzw. 80/90 gehalten werden. Ein Neuzugang bei 82 % Coverage wird damit Mid, ein Small-Incumbent
an derselben Position bleibt Small. Solactive ordnet Neuzugänge dem oberen Buffer zu, dort wäre
der Neuzugang ebenfalls Small. Der Unterschied ist bekannt und **bewusst nicht geändert**, weil
es eine Methodikänderung wäre. Siehe `pipeline_core.py` `_size_segment`, Newcomer-Zweig.

---

## 6. Ausgaben

**Summary je Periode und Produkt:** Konstituenten, Incumbents der Vorperiode, davon gehalten,
davon gefallen, Neueinsteiger, Buffer-Saldo, Index-Größe Δ, Held by Size Buffer,
Kept in Standard (Buffer).

**Detail-Ansicht** (Picker Index × Periode):
- Konstituenten mit FOL-Aufschlüsselung, on-screen Top 50, vollständig im Export
- Country Breakdown DM und EM getrennt
- Gewichtsgrafiken nach Land (Top 30 plus „Others") und nach FactSet Economy
- DM/EM-Gesamtanteil
- Index Characteristics je Periode (Anzahl, Mkt-Cap-Kennzahlen, EUMSS Full/FF)

**Tenure-Ansicht:** Perioden im Index, längste ununterbrochene Serie, aktuell drin.

### Exporte

Die leichten Anzeigematrizen (Wide, Segment) entstehen direkt nach dem Lauf. Die **schweren
Excel-Exporte werden erst auf Klick „Downloads vorbereiten"** erzeugt, damit der Lauf schlank
bleibt. Vier Dateien:

| Export | Inhalt |
|---|---|
| Long | alle Perioden gestapelt, ein Blatt je Produkt, volle Feldliste inkl. FOL, IF, Adj-FF-MCap |
| Wide | Gewichtsmatrix Aktie × Periode, Prozentformat auf Spaltenebene |
| Segment | Segmentmatrix Aktie × Periode |
| Backtest | Backtest-Matrix je Produkt |

Ein neuer Lauf verwirft die Export-Bytes des vorherigen.

---

## 7. Optional: Europe MP (Pooled)

Eigener Tab **🇪🇺 Europe MP (Pooled)**. Rechnet denselben Multi-Period-Ablauf, aber mit
`europe_pool=True`: der Coverage-Waterfall läuft für **alle DM-Europa-Titel unter einem
gemeinsamen Nenner** statt je Land. Alle übrigen Märkte bleiben unberührt je Land.

Hintergrund: MSCI behandelt Developed Europe laut GIMI-Fußnote als einen Markt
(„Developed Markets Europe, Baltic States and WAEMU are treated as single markets for the
purpose of index construction"). Solactive GBS und unsere publizierte Methodik segmentieren
je Land.

### Bedienung

| Element | Default | Bedeutung |
|---|---|---|
| Start- / End-Periode | erste / letzte | wie im regulären Tab |
| Länder-Mindestbesetzung | **0 (aus)** | Fällt ein Europa-Land unter diese Zahl Standard-Titel, werden seine größten Small Caps zu Mid Cap hochgezogen. Audit-Flag `Country_Floor_Promoted`. |
| Welche Europe-Produkte | `NX-EU-LM` | Auswahl aus den Produkten mit `region == "EU"` |

> Die Länder-Mindestbesetzung ist eine **eigene Konstruktion, keine MSCI-Regel**. MSCIs Index
> Continuity Rule (min. 5 DM / 3 EM / 1 FM) greift pro **Markt**, und DM Europa ist dort ein
> einziger Markt. Sie schützt europäische Einzelländer also nicht. 0 = reiner Pooling-Effekt.

### Ausgaben zusätzlich zum regulären Tab

- **Pool-Cutoff je Periode** (Total MCap des kleinsten Standard-Titels im Pool), als Spalte
  in der Summary und als Zeitreihen-Chart
- **Konstituenten je Land über alle Perioden** als Matrix, mit Excel-Download
- Detailansicht inklusive `Country_Floor_Promoted`

### Isolation

Der Tab startet einen **eigenen** Pipeline-Lauf mit **eigenem** Incumbent-State. GIMI-Tab und
regulärer Multi-Period-Tab bleiben unverändert auf der Baseline. Session-State-Keys sind mit
`eupool_` präfixiert.

### Gemessene Wirkung (Snapshot 2026-05-20, ohne Buffer)

| | NX-EU-LM | NX-DM-LM | NX-GM-LM | Pool-Cutoff |
|---|---|---|---|---|
| Baseline, je Land | 342 | 1185 | 2427 | — |
| Europa gepoolt | **303** | 1146 | 2388 | 14,20 Mrd USD |
| gepoolt + Mindestbesetzung 5 | 306 | 1149 | 2391 | 14,20 Mrd USD |

Umverteilung zwischen den Ländern: Deutschland +9, Schweiz +7, Frankreich +7, Niederlande +6,
Spanien +5 gegen Schweden −16, Norwegen −14, UK −14, Polen −10, Belgien −8.

Zeitreihe über 13 gesampelte Perioden 2014 bis 2026: Pooling schneidet in **jeder** Periode,
Mittelwert Baseline 318,4 gegen gepoolt 288,5. Der Trim wächst über die Zeit, weil der gepoolte
Cutoff von 7,9 Mrd (2016) auf 14,2 Mrd (2026) gewandert ist.

> **Nicht die publizierte Methodik.** Der Tab ist ein Research-Werkzeug. Da
> `NX-EU-LM ⊆ NX-DM-LM ⊆ NX-GM-LM` gilt, verschiebt Pooling auch DM und GM: Was Europa
> verliert, fehlt dort ebenfalls.

---

## 8. Einschränkungen

- Der Lauf ist **nicht** resume-fähig. Ein Abbruch verwirft den Zwischenstand.
- Laufzeit skaliert linear mit der Zahl der Perioden. Ein Total-Markets-Produkt verdoppelt
  die Pipeline-Läufe je Periode.
- Der Europe-MP-Tab braucht einen eigenen vollen Lauf, ein direkter Baseline-Vergleich im
  selben Tab ist nicht implementiert. Vergleich erfolgt gegen den regulären Multi-Period-Lauf.
- `Country_Floor_Promoted` greift nur bei aktivem `europe_pool`.
