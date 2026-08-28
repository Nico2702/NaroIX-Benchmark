# Helvetica — Selektionsprozess (Automatisierungs-Spezifikation)

**Zweck:** Vollständige, implementierungsfertige Beschreibung des Helvetica-Selektions-
und Kompositionsprozesses, sodass er unabhängig vom Streamlit-Tool automatisiert werden
kann. Referenz-Implementierung: `naroix_benchmark.py` →
`build_helvetica_pipeline`, `build_helvetica_composite`, `build_swiss_size_subindices`,
`_helv_dedup_most_liquid`. Engine-Universum: `pipeline_core.build_new_universe`.

> Helvetica = kundenspezifischer **Schweizer Multi-Asset-Index** („All-Swiss Asset Strategy
> Index", NTR/EUR). Aufbau: **45 % statische Sleeves** (Cash + Anleihen-/Gold-ETFs, NICHT
> vom Tool selektiert) + **55 % tool-selektierte** Aktien/Immobilien. Rebalancing = zu den
> NaroIX-Selection-Dates.

---

## 0. Gesamtüberblick (Sleeves & Zielgewichte)

| Sleeve | Typ | Zielgewicht | Selektion |
|---|---|---|---|
| Cash (CHF) | statisch | 5 % | fix |
| Government Bonds (2 ETFs) | statisch | 10 % | fix |
| Corporate Bonds (1 ETF) | statisch | 15 % | fix |
| Gold (2 ETCs) | statisch | 15 % | fix |
| **Large Cap Equity** | selektiert | **10 %** | Top-10, equal-weight |
| **Mid Cap Equity** | selektiert | **15 %** | Top-10, equal-weight |
| **Small Cap Equity** | selektiert | **15 %** | Top-10, equal-weight |
| **Real Estate** | selektiert | **15 %** | ALLE qualifizierten, equal-weight |
| **Summe** | | **100 %** | (45 % statisch + 55 % selektiert) |

- Equity equal-weight: Large **1,0 %/Titel** (10 %/10), Mid & Small **1,5 %/Titel** (15 %/10).
- Real Estate equal-weight: **15 % / n_RE** je Titel (alle qualifizierten, inkl. Micro Cap).
- Bei < 10 Titeln in einem Equity-Sleeve → Zielgewicht wird auf die vorhandenen n Titel
  gleichverteilt (Sleeve-Gewicht bleibt konstant, siehe Kaskade in §5).

### Statische Instrumente (Live-Index — maßgeblich für die Automatisierung)

| Sleeve | Instrument | Kennung | Gewicht |
|---|---|---|---|
| Cash | Cash (CHF) | CASH-CHF | 5,0 % |
| Government Bonds | iShares Swiss Domestic Government Bond 3-7 | CSBGC7-SWX | 5,0 % |
| Government Bonds | iShares Swiss Domestic Government Bond 7-15 | CSBGC0-SWX | 5,0 % |
| Corporate Bonds | iShares Core CHF Corporate Bond ETF | CHCORP-SWX | 15,0 % |
| **Gold** | **Amundi Physical Gold ETC** | **FR0013416716** | **7,5 %** |
| **Gold** | **Xtrackers Physical Gold ETC** | **DE000A1E0HR8** | **7,5 %** |

Alle statischen Sleeves sind feste Zielgewichte — keine Titelselektion, kein Buffer, kein
Coverage-Cut.

> **Gold — maßgebliche Instrumente (Live-Index, von Nico 2026-07-01 bestätigt):**
> **Amundi Physical Gold ETC (FR0013416716) + Xtrackers Physical Gold ETC (DE000A1E0HR8)**,
> je 7,5 %. Diese sind für die Automatisierung des publizierten „All-Swiss Asset Strategy
> Index" zu verwenden.
>
> **Nicht verwechseln:** Der **Tool-Backtest** (`HELVETICA_STATIC` in `naroix_benchmark.py`)
> nutzt bewusst **PPFB-XEX (iShares) + XAD5-XEX (Xtrackers)** als **Proxy** (längere
> Historie). Das ist eine reine Backtest-Entscheidung und bleibt im Tool unverändert — es
> ist **nicht** das Live-Instrument.

---

## 1. Eingangs-Universum (Vorstufe, gemeinsam mit allen NaroIX-Indizes)

Helvetica setzt auf dem **Pipeline-Universum** auf = Output von `build_new_universe`
(vor EUMSS-Größen-Floor — der EUMSS-Floor wird für Helvetica **NICHT** angewandt):

1. **Investability-Exclusions** (`apply_universe_exclusions`): FF MCap > 0, Max Price,
   HK(CNY), LON(USD)-Secondary, Country-of-Risk=@NA, Euro-MTF, ETF/SICAV,
   Listing-Status. (Der NAICS-Fondsausschluss ist am 2026-08-23 entfallen, Begründung in
   `PIPELINE_IST.md`.)
2. **Mapping Country + Classification** (DM/EM/FM) — für Helvetica selbst irrelevant, da
   es später über **Exchange Country = SWITZERLAND** filtert (nicht über Mapping Country).
3. **FOL/FIF + China-IF** → `IF`, und daraus:
   **`Adj_FF_MCap = Free Float MCap × IF`** (die zentrale Gewichtungs-/Coverage-Größe).
4. Thailand-SHARE/NVDR-Handling.

**Wichtig:** Helvetica nutzt **`Adj_FF_MCap`** (Float-MCap nach IF) für Gewichtung/Ranking
und **`Total MCap`** für die Größenklassen-Grenzen (Coverage).

---

## 2. Helvetica-Selektions-Pipeline (`build_helvetica_pipeline`)

Erzeugt aus dem Universum die Größensegmente. Reihenfolge:

**Step 1 — Hard-Filter (Schweiz):**
```
Exchange Country Name == "SWITZERLAND"  AND  Free Float MCap > 0
```

**Step 2 — Min Free-Float-% (per Titel):**
```
Free Float Percent >= 10.0 %   (Entry / Neukandidat)
Free Float Percent >=  7.5 %   (Maintenance / Bestandstitel)
```
Maintenance gilt, wenn der Titel Inkumbent ist (`incumbents_isin`, Multi-Period) **oder**
`use_buffer=True` (globaler Vergleichsmodus im Single-Snapshot).

**Step 3 — Liquidität (3M-ADTV, ein fester Schwellenwert, KEIN Buffer):**
```
3M ADTV >= adtv_thr        (Default-Toggle im Tool: $1.0M; Optionen: $0.25M / $0.5M / $1.0M)
```
Reihenfolge-Toggle `label_before_liquidity` (Default **False**):
- **False (Default):** Liquiditäts-Filter **vor** dem Coverage-Cut (Coverage läuft auf dem
  liquiden Pool).
- **True:** Coverage-Labeling erst auf dem vollen CH-Pool, Liquidität danach nur als
  Mitgliedschafts-Gate.

**Step 3b — Company-Dedup vor dem Coverage-Cut (`_helv_dedup_most_liquid`):**
Pro **Entity ID** (Firma) nur die **liquideste Linie** (höchstes 3M-ADTV) behalten. Fehlt die
Entity ID → Fallback auf ISIN (Zeilen kollabieren dann nicht fälschlich). Verhindert
Doppelzählung von Mehrfach-Listings (Roche RO/ROP, Swatch UHR/UHRN, Schindler SCHN/SCHP,
Lindt LISN/LISP) in der Coverage-Kumulation.

**Step 4 — Sortierung + Coverage-Basis:**
```
Sortiere absteigend nach [Total MCap, Adj_FF_MCap (Tiebreaker)]
tot        = Σ Adj_FF_MCap
_c_before  = (kumulierte Adj_FF_MCap VOR dieser Zeile) / tot × 100      # Straddle-Coverage
```

**Step 5 — Coverage-Cuts → Segment** (siehe §3).

Rückgabe: `helv` (nur Large/Mid/Small = Konstituenten i.e.S.) und
`helv_full_pool` (inkl. Micro Cap — Basis für den Real-Estate-Sleeve).

---

## 3. Größensegmentierung (Coverage-Cuts + Hysterese)

Zuteilung anhand `_c_before` (kumulative Adj-FF-Coverage, Firma sortiert nach Total MCap):

| Segment | Entry-Cut | Maintenance-Cut |
|---|---|---|
| Large Cap | `_c_before < 70 %` | `< 75 %` |
| Mid Cap | `< 85 %` | `< 90 %` |
| Small Cap | `< 99 %` | `< 99,5 %` |
| Micro Cap | Rest (≥ 99 % / ≥ 99,5 %) | — (nicht in Equity-Sleeves; nur RE) |

**Welcher Cut gilt?**
- **Single-Snapshot:** `use_buffer=False` → **Entry** (70/85/99); `use_buffer=True` → **Maintenance**.
- **Multi-Period:** `use_buffer=False`, stattdessen **firmen-interne Hysterese** über
  `prior_segments` (dict `{Entity ID → Segment der Vorperiode}`):

```
Neue Firma:                         harter Entry-Cut (70/85/99)
War Large  → bleibt Large,  wenn _c_before < 75            (70 + 5)
War Mid    → bleibt Mid,    wenn 65   <= _c_before < 90     (70 - 5  …  85 + 5)
War Small  → bleibt Small,  wenn 84,5 <= _c_before < 99,5   (85 - 0,5 … 99 + 0,5)
```

Diese Hysterese hält Helveticas Größenklassen **deckungsgleich mit den Swiss-Size-Sub-Indizes**
und reduziert Segment-Wechsel. Die selektierten 30 Titel ändern sich dadurch praktisch nicht
(Top-10 ist rein rang-basiert) — nur die Kern/Aufrücker-Labels.

---

## 4. Multi-Asset-Komposition (`build_helvetica_composite`)

Baut den finalen Index für einen Snapshot: 45 % statische Sleeves (feste Gewichte aus
`HELVETICA_STATIC`) + 55 % selektiert (§5 Equity + §6 Real Estate).

Jede Ausgabe-Zeile trägt: `Sleeve, Type, Exchange Ticker, Name, ISIN, Mapping Country,
FactSet Industry, Adj_FF_MCap, Index_Weight (% des Gesamtindex), True_Segment, Status`.

---

## 5. Equity-Selektion — sequenzielle Top-Down-Kaskade (Large → Mid → Small)

Basis: `helv` (nur L/M/S), **ohne Real Estate**, company-dedupliziert, sortiert nach
**`[Adj_FF_MCap, Total MCap]` absteigend** (Rang = Free-Float-MCap).

Für jedes Segment in Reihenfolge **Large → Mid → Small** (Zielanzahl je Sleeve = **10**):

1. **Eigene Titel** des Segments (aus dem verbleibenden Restbestand) nach Adj_FF_MCap ranken.
2. **Top-10 wählen:**
   - Ohne Inkumbenten: schlicht `head(10)`.
   - Mit Inkumbenten (Multi-Period): **Rang-Band-Buffer** (`_rank_band_select`, §7).
3. **Kaskade bei < 10 eigenen Titeln:** die **besten** Titel des **nächstkleineren** Segments
   nachziehen (Large←Mid, Mid←Small, Small←Micro), markiert als **„Aufrücker"** (True_Segment
   = echte Größenklasse bleibt erhalten). Größere Segmente sind als Quelle **ausgeschlossen**
   → kein Übertrag nach unten.
4. Gewählte Titel aus dem Restbestand **entfernen** → das nächste Segment prüft „≥ 10" auf dem
   **reduzierten** Bestand (Kaskade propagiert: knappes Large drückt evtl. Mid unter 10 usw.).
5. **Überschuss** (Segment mit > 10 Titeln): nur Top-10, Rest wird verworfen.

**Gewicht je Equity-Titel** = `Sleeve-Zielgewicht / n` (n = tatsächliche Titelzahl, ≤ 10):
Large 10 %/n, Mid 15 %/n, Small 15 %/n.

**Status-Feld:** `Kern` (Titel in seinem eigenen Segment) vs. `Aufrücker` (aus kleinerem
Segment nachgezogen).

---

## 6. Real-Estate-Sleeve

- Basis: `helv_full_pool` (inkl. Micro Cap), gefiltert auf
  **`FactSet Industry ∈ {"Real Estate Development", "Real Estate Investment Trusts"}`**.
- Company-Dedup (liquideste Linie), Sortierung nach Adj_FF_MCap.
- **ALLE** qualifizierten Titel werden aufgenommen (kein Top-N).
- **Gewicht je Titel** = `15 % / n_RE` (equal-weight).
- Real Estate ist aus den Equity-Sleeves ausgeschlossen (eigener Korb).

---

## 7. Rang-Band-Buffer (Turnover-Kontrolle, nur Multi-Period)

Stabilisiert die „Rang-10"-Kante je Equity-Sleeve (`_rank_band_select` über die eigenen
Segment-Mitglieder, Rang nach Adj_FF_MCap):

```
Neuer Titel:   kommt rein, wenn Rang <= 8      (HELVETICA_BUFFER_HARD)
Inkumbent:     bleibt drin, wenn Rang <= 13     (HELVETICA_BUFFER_EXIT)
```
Ein Bestandstitel (Vorperioden-Konstituent) auf Rang 9–13 verdrängt einen Neuling
> Rang 8 → weniger Fluktuation an der Grenze. `incumbents_isin` = selektierte Konstituenten
der Vorperiode. Der Real-Estate-Buffer ist implizit (RE = alle qualifizierten) und liegt über
die FF%-Maintenance in der Pipeline.

---

## 8. Swiss-Size-Sub-Indizes (`build_swiss_size_subindices`, optional/Referenz)

Drei eigenständige Float-MCap-gewichtete Sub-Indizes (Large/Mid/Small), aus denen Helvetica
die Top-10 zieht. Für die Automatisierung des Helvetica-Index selbst **nicht zwingend nötig**,
aber nützlich als Kontroll-/Reporting-Größe:
- Universum: CH-gelistet, FF MCap > 0, FF% ≥ 10 % (Inkumbent/use_buffer ≥ 7,5 %), 3M-ADTV ≥ adtv_thr.
- **Variante B:** ALLE Share-Lines (KEIN Dedup) — Mehrfach-Listings dürfen vertreten sein.
- Segment: jede Linie **erbt das Segment ihrer Firma** (firmen-interner Cut aus der Pipeline).
- Gewicht: Adj_FF_MCap, je Sub-Index auf 100 % normiert. Real Estate ausgeschlossen.

---

## 9. Multi-Period-Ablauf (Rebalancing über mehrere Selection Dates)

Pro Periode (chronologisch, mit globalem Incumbent-/Segment-State):
1. Snapshot bauen (`build_snapshot_from_master`) + `build_new_universe` (Universum inkl.
   Adj_FF_MCap) für dieses Datum.
2. Seed-Periode (erste): keine Incumbents → Entry-Schwellen, harter Cut.
3. Folgeperioden: `incumbents_isin` = **selektierte Konstituenten der Vorperiode**,
   `prior_segments` = **Segmente der Vorperiode je Entity ID** → aktiviert FF%-Maintenance
   (7,5 %), Segment-Hysterese und Rang-Band-Buffer.
4. `build_helvetica_pipeline` → `build_helvetica_composite` → Composition dieser Periode.
5. Incumbent-State für die nächste Periode fortschreiben (selektierte Titel + deren Segmente).

**Matching-Schlüssel** für „Inkumbent": im Tool über ISIN/`_norm_isin` bzw. Entity ID (Segmente).
Für Live-Betrieb ggf. auf **Perm ID** umstellen (robust gegen ISIN-/Ticker-Wechsel) —
konsistent zur übrigen NaroIX-Pipeline.

---

## 10. Parameter- & Konstanten-Referenz

| Konstante | Wert | Bedeutung |
|---|---|---|
| Min FF % (Entry / Maint) | 10 % / 7,5 % | Streubesitz-Mindestschwelle |
| Coverage-Cuts Entry | 70 / 85 / 99 % | Large / Mid / Small |
| Coverage-Cuts Maint | 75 / 90 / 99,5 % | Bestandstitel / use_buffer |
| Hysterese-Bänder | L<75 · M∈[65,90) · S∈[84,5;99,5) | firmen-intern (Multi-Period) |
| 3M-ADTV-Schwelle | $1.0M (Default) · $0.25M / $0.5M / $1.0M | fester Wert, kein Buffer |
| `HELVETICA_EQUITY_SLEEVES` | Large 10 %, Mid 15 %, Small 15 % | Sleeve-Zielgewichte |
| `HELVETICA_TOPN` | 10 | Titel je Equity-Sleeve |
| `HELVETICA_RE_WEIGHT` | 15 % | Real-Estate-Sleeve gesamt |
| `HELVETICA_RE_INDUSTRIES` | RE Development, REITs | FactSet-Industrien |
| `HELVETICA_BUFFER_HARD` / `_EXIT` | 8 / 13 | Rang-Band-Buffer (Equity) |
| `HELVETICA_STATIC` | 45 % (Cash 5, GovB 10, CorpB 15, Gold 15) | feste Sleeves |
| Rang-Schlüssel Equity | `Adj_FF_MCap`, dann `Total MCap` | Selektions-/Gewichts-Rang |
| Größenklassen-Schlüssel | `Total MCap` (via `_c_before`) | Coverage-Cut |

---

## 11. Benötigte Datenfelder je Wertpapier (pro Selection Date)

`Exchange Country Name`, `Total MCap`, `Free Float MCap`, `Free Float Percent`,
`3M ADTV`, `FactSet Industry`, `Entity ID`, `ISIN`, `Exchange Ticker`, `Name`,
`Mapping Country`, `Listing`, `Trading Currency` — plus alle für FOL/IF/China-IF nötigen
Felder (siehe `build_new_universe`), da `Adj_FF_MCap = Free Float MCap × IF`.

---

## 12. Edge Cases & Determinismus

- **Leeres CH-Universum** → leere Segmente/Composition (kein Fehler).
- **Segment mit < 10 Titeln** → Kaskade zieht aus kleinerem Segment nach; reicht das nicht,
  bleibt der Sleeve mit < 10 Titeln (Gewicht auf n verteilt).
- **Mehrfach-Listings (Variante B):** in der Selektion/Gewichtung immer nur die **liquideste
  Linie** je Firma (Dedup) → nie Doppelgewichte; in den Sub-Indizes dagegen alle Linien.
- **Deterministisch:** feste Sortierschlüssel (Total MCap, dann Adj_FF_MCap) + fester
  Incumbent-State → gleicher Input ⇒ gleicher Output.
- **Reihenfolge-Toggle** `label_before_liquidity` beeinflusst, ob illiquide Titel die
  Größengrenzen mitdefinieren (Default: nein).

---

## 13. Ablauf-Kurzfassung (Pseudocode, eine Periode)

```
universe   = build_new_universe(snapshot, ...)          # inkl. Adj_FF_MCap
helv, full = build_helvetica_pipeline(universe,
                 use_buffer=False, adtv_thr=1_000_000,
                 incumbents_isin=prev_selected,          # None in Seed-Periode
                 prior_segments=prev_segments_by_entity) # None in Seed-Periode
comp, summ = build_helvetica_composite(helv, full, RE_INDUSTRIES,
                 incumbents_isin=prev_selected)
# comp = 45% statisch + Equity(10/10/10-Kaskade) + RealEstate(alle) ; Index_Weight in % gesamt
prev_selected      = { ISIN der selektierten Equity/RE-Titel }
prev_segments      = { Entity ID -> Segment_New } aus `full`
```

---

*Referenz-Code: `naroix_benchmark.py` (Funktionen s. o.). Diese Datei beschreibt den Stand
der Tool-Logik; bei Abweichungen ist der Code die maßgebliche Quelle.*
