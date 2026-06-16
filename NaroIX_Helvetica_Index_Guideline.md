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
| Gold | PPFB-XEX 7,5 % + SGLD.EUR-SWX 7,5 % | 15,0 % |
| **Summe** | | **45,0 %** |

Diese Sleeves sind feste Zielgewichte — keine Titelselektion, kein Buffer, keine Coverage-Cuts.

---

## 3. Selektierter Teil (55 %) — Zielgewichte

| Sleeve | Auswahl | Ziel-Gewicht | Gewicht je Titel |
|--------|---------|--------------|------------------|
| Large Cap | Top 10 des Large-Segments (Fallback: aus Mid auffüllen) | 10 % | 1,0 % |
| Mid Cap | Top 10 des Mid-Segments (Fallback: aus Small auffüllen) | 15 % | 1,5 % |
| Small Cap | Top 10 des Small-Segments (Fallback: aus Micro auffüllen) | 15 % | 1,5 % |
| Real Estate | **alle** qualifizierten (inkl. Micro) | 15 % | 15 % / n |
| **Summe** | | **55 %** | |

Die Equity-Sleeves sind auf **feste 10/10/10** ausgelegt (siehe Schritt 5). Rangkriterium ist die
Größe (Total MCap, Adj_FF_MCap als Tiebreaker — derselbe Schlüssel wie der Coverage-Cut).

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
- **3M ADTV ≥ Schwelle**, fester Wert (kein Buffer).
- Standard: **$1,0 Mio.**; umschaltbar auf $0,5 Mio. / $0,25 Mio. (inklusiver, mehr Kleintitel/RE).

### Schritt 3b — Company-Level-Dedup (vor dem Coverage-Cut)
- Pro Unternehmen (**Entity ID**) bleibt nur die **liquideste Linie** (höchstes 3M-ADTV).
- Verhindert Doppelzählung von Mehrfach-Listings (Variante B) in der Coverage-Kumulation —
  jedes Unternehmen zählt **genau einmal**, mit derselben Linie, die später im Sleeve landet.
- Für echte Paare = die Primary-Linie (Roche ROP, Swatch UHR, Schindler SCHP); hält aber z. B.
  Lindt korrekt über LISP, falls die Primary (LISN) per Preis-Filter rausfällt.

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

### Schritt 5 — Sleeve-Zusammenstellung (feste 10/10/10)
- **Equity je Sleeve (Large/Mid/Small):** Jeder Sleeve nimmt die **Top 10 seines EIGENEN
  Coverage-Segments** (Rang nach Total MCap, Adj_FF_MCap als Tiebreaker). Gewicht = Sleeve-Gewicht / n.
  - **Auffüllen = reine Fallback-Lösung:** Hat ein Segment **weniger als 10** qualifizierte Titel,
    rücken die nächstgrößten aus den **kleineren** Segmenten auf (Mid → Large, Small → Mid,
    Micro → Small). Solche Titel werden als **„Aufrücker"** markiert; ihre echte Coverage-Klasse
    (`True_Segment`) bleibt im Reporting erhalten.
  - **Kein Übertrag nach unten:** Größere Segmente sind als Auffüll-Kandidaten **ausgeschlossen**.
    Hat ein Segment **mehr als 10** Titel, behält es seine Top 10; der **Überschuss wird verworfen**
    (nicht in den kleineren Sleeve verschoben).
  - **Inkumbenten-Schutz:** Im Multi-Period läuft der **Rang-Band-Buffer (8 / 13)** über die
    Kandidatenliste je Sleeve (eigenes Segment + Fallback), sodass auch der Auffüll-Rand stabil ist.
  - **Status je Titel:** `Kern` (echte Klasse = Sleeve) oder `Aufrücker` (aus kleinerer Klasse
    aufgefüllt) — beides in der Index-Anzeige und im Excel-Export ausgewiesen.
- **Real Estate:** **alle** qualifizierten CH-RE-Titel (FactSet Industry *Real Estate Development*
  oder *Real Estate Investment Trusts*, **inkl. Micro**, kein Coverage-Cut). Gewicht = 15 % / n.

### Swiss Size Sub-Indizes (Zwei-Schichten-Logik)

Der Equity-Teil ist konzeptionell ein **Zwei-Schichten-Modell**:

**Schicht 1 — drei eigenständige Swiss Size Sub-Indizes** (Large / Mid / Small Cap):
- gleiches CH-Universe wie oben (Exchange Country = CH, FF % ≥ 10 %, 3M-ADTV ≥ Schwelle, Preis < 20k);
- **Variante B:** *alle* Share Lines dürfen vertreten sein (z. B. Roche ROP **und** RO);
- Segment = firmen-interner Coverage-Cut (Schritt 4, inkl. ±5/±0,5-Hysterese); jede Linie erbt das
  Segment **ihrer Firma**;
- **Float-MCap-gewichtet** (Adj_FF_MCap), je Sub-Index auf 100 % normiert;
- Real Estate ausgeschlossen (eigenes Sleeve).

**Schicht 2 — Helvetica** zieht je Sub-Index die **Top 10 Firmen** (bei Mehrfach-Listing nur die
**liquideste Linie**), **gleichgewichtet** auf die SAA (Large 10 % / Mid 15 % / Small 15 %), mit
Rang-Band-Buffer (8/13) und Fallback-Auffüllen (Schritt 5).

Damit sind die Größenklassen familien-konsistent (gleiche Logik wie die NaroIX-Coverage-Indizes), und
Helvetica ist als „Top-10 je Sub-Index, gleichgewichtet" sauber definiert. Die cap-gewichteten
Sub-Indizes werden im Tool als eigene Sicht/Export ausgewiesen (ohne eigene ISINs).

---

## 5. Größenmaße: Total MCap, Adj_FF_MCap & FOL/IF

- **Größen-Rang (Coverage-Cut + Sleeve-Tranchen):** **Total MCap** absteigend, **Adj_FF_MCap** als
  Tiebreaker. Die Coverage-Grenzen (70/85/99 %) werden auf der **kumulierten Adj_FF_MCap** gezogen.
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

- **Closing Price < 20.000** (USD). Default an. → filtert z. B. Lindt-Namen (~121k) heraus,
  Lindt-PS (~12k) bleibt.
- **Ausschlüsse:** HK (CNY), Country of Risk = @NA, NAICS Investment Funds, Exchange Euro MTF/@NA,
  Name enthält ETF/SICAV.
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
| **Coverage-Cuts (Segment)** | **±5/±0,5-Hysterese pro Firma**: eine Bestands-Firma bleibt in ihrem Segment (Large < 75 %, Mid 65–90 %, Small 84,5–99,5 %); neue Firmen werden hart geschnitten (70/85/99 %). |

- Inkumbenten = die selektierten Konstituenten (55 %) der **Vorperiode**.
- Rebalancing-Termine sind frei wählbar (Quartalsweise / Halbjährlich / Jährlich / eigene Monate),
  abhängig von den im Master vorhandenen Stichtagen.

---

## 8. Designprinzipien (zusammengefasst)

1. **Multi-Asset, fix:** 45 % statische ETF-/Cash-Sleeves + 55 % selektiert.
2. **Schweiz über Exchange Country** (Listing), nicht Domizil.
3. **Zwei Schichten:** Sub-Indizes = Variante B (alle Share Lines, cap-gewichtet); **Helvetica** nimmt
   pro Firma nur die **liquideste Linie** (Top-10, gleichgewichtet) — keine Doppelgewichte, kein
   Doppelzählen in der Coverage.
4. **Gleichgewichtung** je Sleeve; feste 10/10/10 (Top 10 je Segment + Fallback-Auffüllen),
   RE alle qualifizierten.
5. **Eigenständige CH-Pipeline** (kein EUMSS, kein DM/EM-Split).
6. **Inkumbenten-Buffer** (Rang-Band Equity 8/13, FF-Buffer RE 7,5 %) nur im Multi-Period.

---

## 9. Hinweise zur Größenklassen-Logik

- **Konzentration im Large-Cap-Segment:** Der Schweizer Large-Cap-Markt wird von wenigen Giganten
  dominiert (Nestlé/Novartis/Roche), sodass der Coverage-Cut (Large = erste 70 % der CH-Adj-FF-MCap)
  historisch teils **weniger als 10** echte Large Caps liefert (z. B. 2014: nur 5). Das feste
  10/10/10-Design löst das per **Fallback-Auffüllen**: fehlende Slots werden mit den nächstgrößten
  Titeln aus dem Mid-Segment besetzt (als „Aufrücker" markiert). So bleibt der Large-Cap-Sleeve
  stets mit 10 Titeln (je 1 %) besetzt, ohne die echte MSCI-Klassifikation zu verlieren.
- **Bezug zu MSCI:** Die Coverage-Schwellen (70/85/99 %) entsprechen exakt der MSCI-GIMI-Logik
  (Large 70 %, Standard 85 %, IMI 99 %). MSCI verzichtet bewusst auf feste Titelzahlen je Klasse;
  Helvetica ergänzt das feste 10/10/10 als Kunden-Anforderung über das Fallback-Auffüllen — die
  Klassifikation selbst bleibt MSCI-konform, der Überschuss großer Segmente wird **nicht** abgestuft,
  sondern verworfen (kein „Übertrag").
