# NaroIX Pipeline: Ist-Zustand der Codebase

**Referenzdokument für Spec- und Guideline-Anpassungen**
**Stand:** 2026-08-15 · Basis-Commit `971940e` · `pipeline_core.py` (2093 Zeilen), `naroix_benchmark.py` (3804 Zeilen)

> Dieses Dokument beschreibt, was der Code heute **tut**, nicht was er tun soll. Es ist die
> Vorlage, gegen die Methodik-Specs geprüft und angepasst werden. Alle Zeilenangaben beziehen
> sich auf den oben genannten Stand.
> Verwandt: `HANDOVER.md` (Architektur, teils veraltet), `SELECTION.md`, `MULTI_PERIOD.md`.

---

## 1. Architektur in einem Satz

Es gibt **genau eine** Selektions-Engine, `run_selection_pipeline()` in `pipeline_core.py:1653`.
Sie ist Streamlit-frei. `naroix_benchmark.py` ist reine UI und ruft die Engine an fünf Stellen auf.
Ein Patch an der Engine wirkt automatisch in allen fünf Kontexten.

### 1.1 Die fünf Call-Sites

| Zeile (`naroix_benchmark.py`) | Kontext | Besonderheit |
|---|---|---|
| 1784 | Single-Snapshot-Tab | `apply_size_buffer=False` fest verdrahtet (keine Vorperiode) |
| 1810 | Single-Snapshot, zweiter Lauf | nur wenn Total-Markets-Produkt gewählt, `eumss_enabled=False` |
| 2993 | Multi-Period-Loop | ein Lauf je Periode, globaler Incumbent-State |
| 3026 | Multi-Period, Total-Markets | eigener Incumbent-State, `eumss_enabled=False` |
| 3663 | Erweiterter Perioden-Lauf | analog 2993 |

**Wichtig für Spec-Autoren:** Es existiert **kein** zweiter Coverage-Waterfall für die NaroIX-Serie.
Der zweite `_c_before`-Block in `naroix_benchmark.py:2262` gehört zu `build_helvetica_pipeline()`,
also zum kundenspezifischen Schweizer Index (Swiss-Made Portfolio Index), einer eigenständigen
Pipeline mit eigenen Schwellen (Entry 70/85/99, Maintenance 75/90/99,5). Sie hat mit der
NaroIX-Serie nichts zu tun.

---

## 2. Die Engine, Schritt für Schritt

### Schritt 0: Vorbereitung (`pipeline_core.py:1725-1741`)

- Bei `msci_logic=True` werden `apply_size_buffer` und `asym_buffer` **hart auf False gesetzt**.
  Das ist das etablierte Muster für "Modus schließt Modus aus".
- Maintenance-Schwellen fallen auf Entry zurück, wo sie nicht gesetzt sind
  (`buffer_min_ff`, `buffer_adtv_*`, `buffer_atvr_*`).

### Schritt 1: Universe (`build_new_universe`, `pipeline_core.py:1512`)

Optional übersprungen, wenn `prebuilt_universe` übergeben wird (Performance, nur bei identischen
Universe-Parametern zulässig).

1. Numerische Coercion aller MCap-, ADTV- und Preis-Spalten.
2. **Thailand-Modus**: `NVDR only` / `SHARE only` / `SHARE → NVDR` (letzterer qualifiziert auf der
   SHARE-Linie und überträgt FF MCap, FF %, Total MCap und Preis auf die NVDR).
3. **Kein Listing-Filter.** Primary und Secondary laufen gemeinsam durch alle Filter (Variante B).
4. **Exclusions** über `apply_universe_exclusions` (`pipeline_core.py:689`), eine gemeinsame Quelle
   für Engine und UI-Diagnostik:
   - `Free Float MCap > 0` (immer, nicht abschaltbar)
   - Closing Price < `max_price`
   - HKG-gelistet mit Trading Currency CNY
   - London-gelistete USD-Secondaries (ADR/GDR-Doppelzählung)
   - `Country of Risk == "@NA"`
   - Exchange Name in `["Euro MTF", "@NA"]`
   - Name matcht `\bETF\b | \bSICAV\b | %`
   - `Listing Status == 1` (delisted)

   > **Entfallen am 2026-08-23:** der Fondsausschluss über `NAICS` ("Open-End Investment Fund").
   > Das FactSet-Feld markierte überwiegend operative Asset Manager als Fonds. Von 16 Treffern im
   > Master 05/2026 waren 10 operative Gesellschaften (WisdomTree, Jupiter Fund Management,
   > IntegraFin, Strive, Groww, City of London Investment Group, U.S. Global Investors, Y.D. More,
   > Marygold, Pengana Capital). `Sec Type` trennt nicht (alle 16 = SHARE), ein Name-Regex auch
   > nicht. Die 6 echten Fondsvehikel liegen alle in Micro Cap, also außerhalb der IMI-Segmente.
5. **Klassifikation**: `Mapping Country` über `derive_mapping_country` (primär das File-Feld
   `Country Mapping`, Fallback Risk-First), dann `Classification` aus der PIT-Klassifikationstabelle.
   **Titel ohne Klassifikation fallen hier raus** (`Classification.notna()`), das betrifft auch FM.
6. **Inclusion Factor** über `apply_fol_matrix` (`pipeline_core.py:1424`):
   - FIF-Formel `IF = min(1, FOL / Free Float Percent)`
   - Override China: `IF = china_if` (PIT, Default 0,20)
   - Override Thailand bei NVDR-Modi: `IF = 1,0`
   - `pre_investable` aus dem Resolver: `IF = 0`
   - **`Adj_FF_MCap = Free Float MCap × IF`**
7. **ATVR** in zwei Horizonten, mit Fallback-Kaskade bei Datenlücken:
   - `ATVR_3M = ADTV_3M × 252 / MCap`, ADTV-Fallback 3M → 1M
   - `ATVR_12M = ADTV_12M × 252 / MCap`, ADTV-Fallback 12M → 6M → 3M → 1M
   - `ATVR = min(ATVR_3M, ATVR_12M)` (nur Anzeige)
   - Bezugs-MCap steuerbar über `atvr_mcap_col` (Default Free Float MCap)

### Schritt 2: EUMSS-Kalibrierung (`pipeline_core.py:1762-1790`)

```
Pool    = gm_u[Classification == "DM" AND Listing == "Primary"]
Sort    = Total MCap desc, Tiebreak Adj_FF_MCap desc
Kumuliert: Free Float MCap Y2025   (ROH, nicht Adj_FF_MCap)
eumss_full = Total MCap der ersten Firma mit kumuliertem FF-Anteil >= small_thr (99 %)
eumss_ff   = eumss_full × eumss_ff_ratio   (Default 0,50)
```

Drei Punkte, die in Specs regelmäßig falsch stehen:

- **Primary-only** ist Absicht (Multi-Class-Doppelzählung vermeiden). Fehlt die Spalte oder ist sie
  abweichend geschrieben, greift ein Fallback auf alle DM-Listings und setzt
  `eumss_calib_fallback=True`, damit die UI warnen kann.
- Kumuliert wird **rohes Free Float MCap**, nicht `Adj_FF_MCap`. Der spätere Coverage-Waterfall
  kumuliert dagegen `if_cum_col` (= `Adj_FF_MCap` im Default-Modus "Selektion"). Die beiden
  Kalibrierungen laufen also auf unterschiedlichen Nennern.
- Bei `eumss_enabled=False` (Total-Markets-Produkt) werden beide Schwellen auf 0 gesetzt.

### Schritt 3: EUMSS-Filter (`pipeline_core.py:1792-1799`)

Angewendet auf **alle** Listings (Primary + Secondary), Security-Level:

```
Total MCap        >= eumss_full
Free Float MCap   >= eumss_ff
Free Float Percent >= (buffer_min_ff wenn Incumbent, sonst min_ff_pct)
```

Incumbent-Erkennung hier über `_match_key` (Perm ID, ISIN-Fallback).

### Schritt 4: Liquidität (`apply_liquidity_new`, `pipeline_core.py:1609`)

Je Titel vier Bedingungen, alle müssen erfüllt sein, Schwellen getrennt nach DM und EM:

```
3M ADTV   >= adtv_thr
6M ADTV   >= adtv_thr        (gleiche Schwelle wie 3M)
ATVR_3M   >= atvr_thr
ATVR_12M  >= atvr_thr
```

Incumbents bekommen die Maintenance-Schwellen. Titel, die weder DM noch EM sind, fallen hier
komplett raus (die Maske ist `mask_dm | mask_em`).

> **Befund, bitte prüfen:** Diese Funktion matcht Incumbents über `_norm_isin(df["ISIN"])`
> (Zeile 1629), während der State im Multi-Period-Loop als **Perm-ID**-Menge geführt wird
> (`naroix_benchmark.py:3099-3101`) und der Master-Loader eine `Perm ID`-Spalte anlegt
> (`pipeline_core.py:997`). Wo Perm ID gefüllt ist und von der ISIN abweicht, läuft der
> Liquiditäts-Maintenance-Buffer damit ins Leere. Dasselbe gilt für die Buffer-Statistik
> in Zeile 2048. Alle anderen Buffer-Pfade nutzen korrekt `_match_key`.

### Schritt 5: Coverage-Waterfall (`pipeline_core.py:1809-1918`)

Das Kernstück. Reihenfolge:

**5a. Non-Investable abtrennen.** Titel aus `gm_liq` mit `Adj_FF_MCap <= 0` (IF = 0, also explizites
FOL = 0 oder `pre_investable`) bekommen `Segment_New = "Non-Investable"` und laufen **nicht** in den
Waterfall. Sie sind in keinem Index, aber im Audit sichtbar.

**5b. Pool wählen.**

```
_seg_pool = gm_eumss   wenn label_before_liquidity=True
          = gm_liq     sonst (Default)
gm_liq_cov = _seg_pool[Adj_FF_MCap > 0]
```

**5c. Nur bei `msci_logic`:** GMSR-Kalibrierung über `_coverage_cutoffs()` auf `gm_liq_cov[DM]`.
Achtung: **ohne** Primary-Filter, anders als die EUMSS-Kalibrierung in Schritt 2.

**5d. Segmentierungs-Markt bestimmen.** Normalfall `Mapping Country`. Bei `europe_pool=True` laufen
alle DM-Europa-Titel unter einem gemeinsamen Schlüssel, teilen sich also Nenner und Cutoff.

**5e. Je Markt:**

```
Sort:      Total MCap desc, Tiebreak Adj_FF_MCap desc
tot      = Summe(if_cum_col)          # Default Adj_FF_MCap
_c_before = cumsum(if_cum_col).shift(1).fillna(0) / tot × 100
```

`_c_before` ist die Straddle-Coverage, also der Wert **vor** der eigenen Zeile. Ein Titel, der die
Grenze überspannt, landet im größeren Segment.

**5f. Vier alternative Segmentierungs-Äste.** Das ist die Stelle, an der Specs am häufigsten
danebengreifen. Es gibt keinen gemeinsamen `in_std`-Ausdruck.

| # | Bedingung | Mechanik | Zeilen |
|---|---|---|---|
| 1 | `msci_logic` | Full-MCap-Cutoffs per Markt, IMI-Floor aus GMSR (EM = ½), optional Migrations-Buffer −33 % / +50 % | 1865-1875 |
| 2 | `apply_size_buffer AND incumbent_segments` | Python-Loop über `_size_segment()` bzw. `_size_segment_asym()`, Hysterese je Vorperioden-Segment | 1876-1882 |
| 3 | Legacy mit `apply_buffer` und Incumbents | `thr_per_stock = np.where(is_inc, buffer_coverage, mid_thr)`, dann `_c_before < thr` | 1886-1897 |
| 4 | Legacy ohne Buffer | harter Cut an `mid_thr` | 1890-1897 |

Nur **Ast 3** enthält die aus Specs bekannte Konstruktion `cov_thr = np.where(incumbent, 90, 85)`.
Die Default-Sidebar mit aktivem Size Buffer läuft durch **Ast 2**, wo das Segment aus der
Übergangsfunktion kommt und keine solche Maske existiert.

Die Übergangsfunktionen (`pipeline_core.py:366` und `:397`), `bw` = `size_buffer_pp`, Default 5:

```
_size_segment (symmetrisch)
  prior Large:  <=75 Large  |  <=90 Mid  |  sonst Small
  prior Mid:    <65  Large  |  <=90 Mid  |  sonst Small
  prior Small:  <65  Large  |  <80  Mid  |  sonst Small
  Newcomer:     <70  Large  |  <85  Mid  |  sonst Small

_size_segment_asym (einseitig)
  wie oben, aber prior Small: <85 Mid  (kein 80er-Abwärtshalt)
```

**5g. Optional `apply_small_buffer`** (nicht bei `msci_logic`): kappt Small nach Micro an der
99-%-Kante, Incumbents des IMI erst bei `small_thr + small_buffer_pp` (Default 99,5).

**5h. Nach dem Loop, in dieser Reihenfolge:**

- Bei `label_before_liquidity`: Filter auf liquide Symbole (Liquidität als Mitgliedschafts-Gate).
- `europe_pool_cutoff` messen (kleinste Standard-Total-MCap im EU-Pool, vor allen Korrekturen).
- **Size-Integrity-Auffüllung** (Post-Step, nur bei `apply_size_integrity`): `Segment_New ==
  "Small Cap"` und Full MCap >= T wird zu `"Mid Cap"`. T = `si_k × R85`, R85 aus
  `_coverage_cutoffs(gm_liq_cov[DM])["standard"]`, für EM halbiert (`_EM_SIZE_FACTOR`).
  `si_edge_pp` begrenzt auf `_c_before < si_edge_pp`. Greift in allen vier Ästen gleich, weil
  er nur auf `Segment_New` und Full MCap schaut. Ohne DM-Pool bliebe T = 0, deshalb schaltet
  sich die Regel dort selbst ab.
- `Country_Floor_Promoted`: nur bei `europe_pool` und `min_per_country > 0`, zieht die größten
  Small Caps eines unterbesetzten Europa-Landes nach Mid. Eigene Konstruktion, keine MSCI-Regel.
  Läuft **nach** der Auffüllung, damit er auf dem finalen Segment prüft.

### Schritt 6: Segment-Mengen (`pipeline_core.py:2001-2030`)

```
gm_std      = Segment_New in {Large Cap, Mid Cap}
gm_above85  = Segment_New NICHT in {Large Cap, Mid Cap}   (Small, ggf. Micro aus 5g)
gm_micro    = gm_u ohne gm_eumss                          (EUMSS gerissen) -> "Micro Cap"
gm_noninv   = aus 5a                                      -> "Non-Investable"
gm_complete = concat(gm_std, gm_above85, gm_micro, gm_noninv), dedup auf Symbol
```

**Variante A:** Wer EUMSS besteht, aber an der Liquidität scheitert, ist **komplett raus**, nicht
Small und nicht Micro. Die Liquiditätshürde gilt für alle Tiers.

Der Code kennt keinen Begriff "Standard-Index". Was Specs so nennen, ist
`Segment_New in {Large Cap, Mid Cap}`.

### Schritt 7 und 8

- Ineligible-Filter (PIT-Liste), wenn aktiviert.
- `normalize_index_weight` auf `gm_complete` (Basis `Adj_FF_MCap`, Summe exakt 100,0).
- `gm_index_only` = Large + Mid, **eigenständig renormiert**.

---

## 3. Audit-Flags im Bestand

| Flag | Bedingung |
|---|---|
| `Size_Buffer_Held` | Segment weicht vom reinen Cut ab **und** entspricht dem Vorperioden-Segment. Nur bei aktivem Size Buffer, sonst False |
| `Kept_In_Standard_By_Buffer` | Incumbent **und** `_c_before >= mid_thr` **und** Segment in {Large, Mid}. Bei `msci_logic` immer False |
| `Country_Floor_Promoted` | Small nach Mid gezogen wegen `min_per_country` |
| `Size_Integrity_Filled` | Small nach Mid gehoben, weil Full MCap >= T (Size-Integrity-Auffüllung) |
| `Size_Integrity_Blocked` | Full MCap >= T, aber `_c_before >= si_edge_pp`, daher nicht gehoben |

`Size_Integrity_Filled` hat Vorrang: wo es gesetzt ist, werden `Kept_In_Standard_By_Buffer` und
`Size_Buffer_Held` zurückgesetzt, damit derselbe Titel nicht doppelt gezählt wird.

Alle drei werden für `gm_micro` auf False aufgefüllt (Zeile 2026-2030).

**Für neue Flags relevant:** `Kept_In_Standard_By_Buffer` fängt jede Konstellation mit
`_c_before >= 85` und Standard-Segment ein. Eine neue Regel, die Titel oberhalb von 85 % in den
Standard hebt, überlappt damit zwangsläufig. Die Präzedenz muss explizit definiert werden,
sonst wird derselbe Titel doppelt gezählt.

---

## 4. Rückgabe-Dict (`pipeline_core.py:2075-2091`)

`gm_complete`, `gm_index_only`, `gm_universe`, `gm_eumss`, `gm_liq`, `gm_liq_excluded`, `gm_std`,
`gm_final`, `gm_noninv`, `gm_ie_removed`, `eumss_full`, `eumss_ff`, `eumss_calib_fallback`,
`buffer_breakdown`, `europe_pool_cutoff`.

Neue Kalibrierungsgrößen (Schwellen, Zählwerte je Periode) gehören hier hinein, damit die UI sie
ohne Neuberechnung anzeigen kann. Vorbild: `europe_pool_cutoff`.

---

## 5. Produkt-Slicing (`build_index`, `pipeline_core.py:205`)

Ein Pipeline-Lauf, daraus alle Produkte als konsistente Slices (Option Y). Ein Titel hat genau
eine Size-Klasse über alle Produkte hinweg.

- **Region**: `DM` / `EM` / `GM` (= DM + EM) / `EU` (DM ∩ `EUROPE_COUNTRIES`) / `US`
  (Exchange Country Name = United States). FM ist nie enthalten.
- **Segmente**: `_SEG_STD` = Large + Mid, `_SEG_AC` = Large + Mid + Small.
- Optional Industrie-Filter (`TECH_INDUSTRIES`).
- Optional `top_n`, gezählt auf **Company-Ebene** (Entity ID): die Top-N Firmen nach Total MCap,
  dann alle ihre Aktienlinien. Ein 500er-Index hält daher etwa 505 Wertpapiere.
- Optional Rang-Band-Buffer (`_rank_band_select`, Solactive-Stil): hart drin bis `buffer_hard`,
  Bestandstitel füllen aus dem Band bis `buffer_exit` auf, dann Newcomer nach Rang.
- Gewichtung immer `Adj_FF_MCap`, unabhängig vom Ranking. Optional UCITS 5/10/40.

Die 24 Produkte stehen in `INDEX_SERIES` (`pipeline_core.py:145`), das ist die einzige Quelle.

**Konsequenz für Size-Regeln:** Wer ein Segment-Label ändert, verschiebt einen Titel zwischen
Produkten. Ein Titel von Small nach Mid verlässt NX-\*-S und betritt NX-\*-LM und NX-\*-M.
NX-\*-AC bleibt unberührt. Das ist ein brauchbarer Verifikationstest: **All Cap muss konstant
bleiben**, sonst greift die Regel an der falschen Stelle.

---

## 6. Multi-Period-Loop (`naroix_benchmark.py:2984-3107`)

Pro Periode ein globaler Pipeline-Lauf, danach die Produkt-Slices.

**State-Fortschreibung (Zeile 3096-3101):**

```python
_inv     = gm_complete[Segment_New in {Large Cap, Mid Cap, Small Cap}]
prev_isin = set(_match_key(_inv))                    # Membership-Incumbents
prev_seg  = {key: Segment_New}                       # Segment-Incumbents (Size Buffer)
```

Der Incumbent-State ist also das **investierbare Universe inklusive Small**, nicht der
Standard-Index. Ein Small-Cap-Titel der Vorperiode ist Incumbent.

- **Seed-Periode**: `is_seed = (len(prev_isin) == 0)`, dort sind `apply_buffer` und
  `apply_size_buffer` deaktiviert. Alle Buffer-Effekte beginnen ab Periode 2.
- **Total Markets** läuft als zweiter Pipeline-Aufruf mit eigenem State
  (`prev_isin_tm`, `prev_seg_tm`) und `eumss_enabled=False`.
- **Rang-Band-Buffer** hält je Produkt einen eigenen Company-Key-State (`prev_prod_ckey`).
- Matching-Key ist durchgehend `_match_key` (Perm ID mit ISIN-Fallback), außer an den beiden
  in Abschnitt 2 / Schritt 4 genannten Stellen.

---

## 7. Parameter-Referenz der Engine

Signatur ab `pipeline_core.py:1653`. Gruppiert, mit Defaults.

| Gruppe | Parameter |
|---|---|
| Universe | `thailand_mode`, `max_price`, `exclude_hk_cny`, `exclude_country_risk_na`, `exclude_naics_funds`, `exclude_euro_mtf`, `exclude_etf_sicav`, `excl_delisted=True`, `exclude_lon_usd_sec=True` |
| Size & Liquidität | `large_thr` (70), `mid_thr` (85), `small_thr` (99), `min_ff_pct`, `eumss_ff_ratio` (0,50), `adtv_dm`, `adtv_em`, `atvr_dm`, `atvr_em` |
| IF / FOL | `fol_matrix`, `fol_sector_fb`, `fol_enabled`, `if_cum_col`, `atvr_mcap_col` |
| Membership-Buffer | `incumbents_isin`, `apply_buffer=False`, `buffer_min_ff`, `buffer_coverage=90`, `buffer_adtv_*`, `buffer_atvr_*` |
| Size-Buffer | `apply_size_buffer=False`, `incumbent_segments`, `size_buffer_pp=5.0`, `asym_buffer=False` |
| Small-Buffer | `apply_small_buffer=False`, `small_buffer_pp=0.5` |
| Size-Integrity | `apply_size_integrity=False`, `si_k=1.00`, `si_edge_pp=90.0` (None = keine Coverage-Grenze) |
| Modi | `eumss_enabled=True`, `msci_logic=False`, `label_before_liquidity=False`, `europe_pool=False`, `min_per_country=0` |
| Sonstiges | `ineligible_df`, `apply_ineligible`, `selection_date`, `prebuilt_universe` |

**Konvention für neue Optionen:** ein `bool`-Schalter plus die Wert-Parameter, alle mit Default
"kein Verhaltenswechsel", Vorbild `apply_small_buffer` / `small_buffer_pp`. Durchreichen an allen
fünf Call-Sites, sonst wirkt die Option im jeweiligen Tab nicht.

---

## 8. Vorhandene Bausteine, die Specs oft neu erfinden

| Gesucht | Existiert bereits |
|---|---|
| Full MCap an einem Coverage-Punkt | `_coverage_cutoffs(pool, if_col, large, mid, small)` (`:444`), liefert `{"large","standard","imi"}`. `["standard"]` ist die Full MCap am 85-%-Punkt |
| Halte- / Eintrittsfaktoren | `_MIG_DOWN = 2/3`, `_MIG_UP = 1.5` (`:441`) |
| GMSR-Floor mit EM-Halbierung | `_imi_floor(gmsr_dm, classification)` (`:468`) |
| Incumbent-Matching | `_match_key(df)` (`:354`) |
| Gewichtsnormierung auf exakt 100 | `normalize_index_weight` (`:106`) |
| Rang-Band-Buffer | `_rank_band_select` (`:180`) |
| Europa-Länderliste | `EUROPE_COUNTRIES` |

---

## 9. Checkliste für Methodik-Specs

Wer eine Regel spezifiziert, sollte diese Punkte explizit beantworten:

1. **In welchem der vier Segmentierungs-Äste greift die Regel?** Bei "in allen" muss sie als
   Post-Step auf `Segment_New` formuliert sein, nicht als Maske innerhalb eines Astes.
2. **Verhalten bei `msci_logic`?** Der etablierte Umgang ist harte Deaktivierung in Schritt 0
   plus UI-Sperre.
3. **Welcher Pool, welcher Nenner?** `gm_u` / `gm_eumss` / `gm_liq` / `gm_liq_cov`, und
   `Free Float MCap` oder `Adj_FF_MCap` (`if_cum_col`). Primary-only oder alle Listings.
4. **Verhalten bei `label_before_liquidity=True`?** Dort wechselt der Waterfall-Pool auf
   `gm_eumss`. Soll eine Kalibrierung trotzdem auf `gm_liq` laufen, muss sie explizit aus einem
   anderen Frame gezogen werden.
5. **Welche Segment-Labels ändern sich?** Daraus folgt direkt, welche Produkte betroffen sind
   (Abschnitt 5).
6. **Gibt es einen Exit, der zum Eintritt symmetrisch ist?** Regeln, die nur den Eintritt
   definieren und den Verbleib dem Coverage-Buffer überlassen, wirken als Ratsche.
7. **Kollidiert das Audit-Flag mit `Kept_In_Standard_By_Buffer`?**
8. **Seed-Periode:** greift die Regel dort, und ist das gewollt?
9. **Rückgabewerte** für die UI ergänzt (Abschnitt 4)?
10. **Alle fünf Call-Sites** bedient?

---

*Erstellt aus dem Code, nicht aus vorhandener Dokumentation. Bei Abweichungen zwischen diesem
Dokument und `HANDOVER.md` gilt dieses hier, solange der Basis-Commit stimmt.*
