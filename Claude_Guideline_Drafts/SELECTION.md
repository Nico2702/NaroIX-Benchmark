# NaroIX — Selection Process (Detailed)

> **Purpose:** Authoritative, step-by-step description of the constituent selection pipeline.
> Reflects the actual implementation of `run_selection_pipeline()` in `naroix_benchmark.py`
> (the canonical pipeline used by the Multi-Period Run and, mirrored inline, by the GIMI tab).
> Read together with `HANDOVER.md` §2 (methodology decisions) and §3 (filter chain).
>
> Last updated: 2026-06-06. Line numbers are approximate — search by symbol.

---

## 0. The single most important distinction

There are **two different cumulative-coverage computations on two different market-cap metrics**. Confusing them is the #1 source of misunderstanding:

| Cut | Cumulation metric | Scope | Produces |
|---|---|---|---|
| **EUMSS "99 %"** | **raw Free Float MCap** | DM-Primary, **global** | an absolute size floor (Total-MCap + FF-MCap threshold) |
| **Size cuts "70 % / 85 %"** | **Adj_FF_MCap** (Free Float × Inclusion Factor) | **per country** (`Mapping Country`) | the Large / Mid / Small split |

`Adj_FF_MCap = Free Float MCap × IF` is the **investable** free float and is the basis for both the 70/85 segmentation (Step 5) **and** the final index weights (Step 8) — they are intentionally consistent. See §2.2 / §A below for why.

---

## 1. Inputs — prepared once per Selection Date

In the Multi-Period loop, before the pipeline runs:

- **Classification** — `get_classification_dict(hc_df, date)` → DM / EM / FM per country, point-in-time from `Historical Classification.xlsx`.
- **China Inclusion Factor** — historical value for the date (`china_if_map`), default 0.20.
- **Snapshot** — `build_snapshot_from_master(master_data, date_iso)` → a single-period DataFrame (static fields + the period's dynamic columns, with Float-% normalisation etc., structurally identical to the old single-snapshot format).

The snapshot contains **all listings** (Primary **and** Secondary) — see §6 (Variante B).

---

## 2. The pipeline — `run_selection_pipeline()`

### Step 1 — Universe & Exclusions + FOL (`build_new_universe`)

Global exclusions (applied to all listings):
- `Closing Price < 20,000 USD`
- `Listing Status ≠ 1` (inactive / delisted removed)
- **Thailand** SHARE→NVDR mode (qualification on SHARE, liquidity/index on NVDR)
- **HK** stocks with Trading Currency **CNY**
- `Country of Risk = @NA`
- **NAICS** open-end investment funds
- Exchange **Euro MTF / @NA**
- Name contains **"ETF" / "SICAV" / "%"**
- `Classification` (DM/EM/FM) must be set via `Mapping Country`

Then **FOL / Inclusion Factor**:
- `IF = min(1, FOL / Free Float %)`; FOL lookup fallback chain **Industry (exact) → Industry (normalized, whitespace/case-tolerant) → Sector (strictest) → Country default → 1.0**. The normalized step absorbs YAML-vs-FactSet spelling differences (e.g. `Cruiselines` vs `Cruise lines`) so an existing matrix entry isn't missed and wrongly fall through to an unrelated restricted industry.
- **China A-shares**: China Inclusion Factor (≈ 0.20)
- **`Adj_FF_MCap = Free Float MCap × IF`** — the investable size, basis for almost everything downstream.

**Output:** `gm_u` (eligible universe with `IF`, `Adj_FF_MCap`).

### Step 2 — EUMSS calibration (the "99 %") — basis: **raw FF MCap**, scope: **DM-Primary, global**

- Take **DM + Listing = Primary** only; sort by **Total MCap** desc (tiebreaker: `Adj_FF_MCap` desc).
- Cumulate **raw `Free Float MCap`** (not adjusted): `_cum_ff_pct = cumsum(FF) / Σ FF × 100`.
- At the **99 %** point (`small_thr`), take that stock's **`Total MCap`** as **`eumss_full`**; set **`eumss_ff = eumss_full × eumss_ff_ratio`** (default 0.50).
- Result: an **absolute size floor** (a Total-MCap threshold and an FF-MCap threshold) applied **globally** (DM **and** EM) in Step 3.

Calibrated on DM-Primary, before liquidity, per MSCI §2.2.3 (otherwise multi-listings / the liquidity filter would distort the calibration).

### Step 3 — EUMSS filter (buffer-aware Min FF%)

Keep a stock only if **all** hold:
- `Total MCap ≥ eumss_full` **and**
- `Free Float MCap ≥ eumss_ff` **and**
- `Free Float % ≥ Min FF%` (incumbents get the relaxed `buffer_min_ff`, e.g. 7.5 %, when the maintenance buffer is on)

**Key asymmetry — calibration vs. filter:** the *calibration* (Step 2) uses **DM-Primary only** (to avoid double-counting multi-listings in the 99 % point), but this *filter* runs on the **entire universe — DM + EM, Primary + Secondary**. A secondary is therefore checked on **its own values**: `Total MCap` is company-level (identical across the company's share classes) and `Free Float MCap` / `Free Float %` are the listing's own. So a secondary clears EUMSS independently — it is never "added back" (see §6).

**Stocks failing EUMSS → `Micro`** (`gm_micro`). **Output:** `gm_eumss`.

### Step 4 — Liquidity filter (buffer-aware)

ADTV / ATVR, DM/EM differentiated:
- DM: 3M ADTV ≥ $2M; EM: ≥ $1M (+ optional ATVR minimum). Incumbents get relaxed maintenance thresholds.
- **ATVR** = annualized traded value ratio = `ADTV × 252 / MCap` (1.0 = 100% of the float turns over per year). Denominator is Free Float MCap (MSCI-conform, default) or Total MCap (conservative), a sidebar toggle. Screened **MSCI-style on two horizons**: a name must clear the threshold on **both** the 3M **and** the 12M ATVR (each falls back to the next-shorter ADTV window on a data gap). Default threshold 0 (screen off). Note: this is a mean-based approximation of MSCI's median-based ATVR, since the master file carries pre-aggregated ADTV windows, not daily traded values.

**Variante A (HANDOVER §2.11): stocks that pass EUMSS but FAIL liquidity are excluded entirely** — not Small, not Micro, not in IMI. The liquidity bar applies to all tiers; failing it means the stock is not investable, so it is out. They are returned as `gm_liq_excluded` (audit only). **Output:** `gm_liq` (the only stocks that proceed to the coverage waterfall).

*Impact (2026-05-20, ACWI): −1,083 names from the IMI universe (9,763 → 8,680), −1.26 % by weight; Standard unaffected.*

### Step 5 — Coverage waterfall (the "70 / 85") — basis: **Adj_FF_MCap**, scope: **per country**

For each `Mapping Country` group (sorted by Total MCap desc, `Adj_FF_MCap` tiebreaker):
- `_c_before = cumsum(Adj_FF_MCap).shift(1).fillna(0) / Σ Adj_FF_MCap × 100` — cumulative coverage **before** the stock's own FF (the **straddle rule**, HANDOVER §2.3).
- Classify on one scale (Option B, HANDOVER §2.2):
  - `_c_before < 70 %` → **Large Cap**
  - `70 % ≤ _c_before < 85 %` → **Mid Cap**
  - `_c_before ≥ 85 %` → **Small Cap** (coverage-Small)
- **Size buffer** (optional, Multi-Period only) — for incumbents, hysteresis bands ±`size_buffer_pp` (default 5) around the 70 % and 85 % boundaries, keyed on the prior-period segment (see §5.1).

`if_cum_col = "Adj_FF_MCap"` in the default "Selektion" mode (MSCI-conform). A toggle (`if_selection_mode = "Gewichtung"`) switches cumulation to raw FF, but that is an explicitly non-MSCI research mode.

### Step 6 — Combine + dedup

`gm_complete = concat(Large/Mid, coverage-Small, Micro)`, then `drop_duplicates(subset=["Symbol"])`. *(Liquidity-fails are NOT included — Variante A, Step 4.)*

- Dedup is on **`Symbol`** (security-unique — verified: 0 duplicate Symbols in real data), **not** ISIN / Entity ID. This **protects Variante B**: multi-class lines share Entity ID / sometimes ISIN but have distinct Symbols, so both survive.
- The three buckets are mutually exclusive by Symbol-set construction, so the dedup **removes nothing in practice** — it is a defensive backstop. The "larger" segment wins ties (concat order Large/Mid → Small → Micro).

### Step 7 — Ineligible filter

Apply `In-Eligible.xlsx` for the Selection Date — stocks with a matching ISIN are removed at the end; weights are redistributed proportionally.

### Step 8 — Index weights

`Index_Weight = Adj_FF_MCap / Σ Adj_FF_MCap × 100`, normalised to exactly 100.000000 (floating-point remainder assigned to the largest stock); sorted descending.

---

## 3. Segments produced

| Segment | Condition |
|---|---|
| **Large Cap** | coverage waterfall, `_c_before < 70 %` |
| **Mid Cap** | `70 % ≤ _c_before < 85 %` |
| **Small Cap** | passed liquidity **and** coverage `≥ 85 %` (coverage-based only — Variante A) |
| **Micro Cap** | failed EUMSS |
| *(excluded)* | passed EUMSS but **failed liquidity** → out entirely (`gm_liq_excluded`, Variante A) |

---

## 4. Index products — the NaroIX Index Series

The pipeline assigns segments to the full universe; each **product** is then a scope of that result via `build_index(gm_complete, region, segments, industries=None, top_n=None)`, re-normalised to 100%. The full 22-product catalogue (16 region×size + 6 thematic/filtered: US 500, US Tech 100, US Tech, Europe Tech, Europe Tech 30, World 100) with codes, names and MSCI equivalents is documented in **`INDEX_SERIES.md`** — defined once as the `INDEX_SERIES` constant (single source of truth).

Scope dimensions:
- **Region**: `DM` · `EM` · `GM` (= DM+EM) · `EU` (DM ∩ Europe countries). **FM always excluded.**
- **Size segments**: Large (`<70%`), Mid (`70–85%`), Small (`85–99%`); Standard = Large+Mid, All Cap = Large+Mid+Small.

**Multi-Period (Option Y):** the pipeline runs **once per period** with a single global incumbent/buffer state (prior period's investable universe, L+M+S); every selected product is a consistent slice of that one run. A stock therefore has exactly one size class across all products, and `NX-GM-* = NX-DM-* + NX-EM-*` etc. hold by construction.

---

## 5. The two buffers (do not conflate)

### 5.1 Maintenance buffer — *membership* (in/out of the index)
Relaxes entry thresholds for **incumbents** (stocks in the prior period's index):
- Min FF% → `buffer_min_ff` (e.g. 7.5 % vs 10 %)
- ADTV / ATVR → relaxed maintenance values
- (legacy path only) Standard coverage cutoff → `buffer_coverage` (e.g. 90 % vs 85 %)

### 5.2 Size buffer — *segment* (Large ↔ Mid ↔ Small)
Hysteresis so companies don't flip-flop between size buckets each rebalancing. Bands ±`size_buffer_pp` (default 5) around 70 % and 85 %, keyed on the **prior-period segment** (`incumbent_segments`, a `{ISIN → segment}` map carried per index). Multi-Period only (needs a prior segment). Transition function `_size_segment(prior, _c_before, large_thr, mid_thr, bw)`:

| Prior | stays | rises | falls |
|---|---|---|---|
| **Large** | `_c_before ≤ 75` | — | → Mid if `> 75`, → Small if `> 90` |
| **Mid** | `65 ≤ _c_before ≤ 90` | → Large if `< 65` | → Small if `> 90` |
| **Small** | `_c_before ≥ 80` | → Large if `< 65`, → Mid if `< 80` | — |
| **newcomer / none** | plain cut-offs: `< 70` Large, `< 85` Mid, else Small | | |

When the size buffer is ON, the 85→90 % "stay in Standard" effect comes from `mid_thr + size_buffer_pp` (not from `buffer_coverage`). Audit flags: `Size_Buffer_Held` (held in prior segment vs. plain cut-off) and `Kept_In_Standard_By_Buffer` (incumbent kept as Large/Mid although plain cut-off → Small).

**Verified impact (ACWI, last 8 periods):** size buffer ON cut Large↔Mid segment switches from 1041 → 345 (−67 %), with Standard membership and DM/EM split unchanged.

---

## 6. Secondaries — Variante B (no re-add step)

Both Primary and Secondary listings of the same entity run through the pipeline as **separate securities** and are included if they individually pass the filters (HANDOVER §2.4). Consequences:
- Secondaries are in the universe from Step 1 onward and pass EUMSS / liquidity / coverage alongside primaries. **There is no separate "re-add secondaries" step.**
- Only the **EUMSS calibration** (Step 2) is computed on DM-Primary-only to avoid double-counting multi-listings in the threshold; the calibrated thresholds (and all other filters) are then applied to the full listing universe.
- **Worked example — Alphabet (2026-05-20):** GOOGL (Primary, ISIN …3059) and GOOG (Secondary, ISIN …1079) share one Entity ID and an **identical company-level `Total MCap`** (≈ $4.69T), but have distinct Symbols/ISINs and their **own `Free Float MCap`** (GOOGL ≈ $2.23T, GOOG ≈ $1.94T). The EUMSS filter checks GOOG on its own Total (= company Total) + own FF → it clears the threshold independently and ends up as a separate **Large Cap** constituent with its own weight (GOOGL ≈ 1.94 %, GOOG ≈ 1.68 %). No re-add step is involved.
- `add_secondary_listings()` exists in the code but is **never called** — dead code from the pre-Variante-B era (Primary-only + re-add). Candidate for cleanup (HANDOVER §6).

---

## 7. Sort & tiebreaker (everywhere)

Sort by **`Total MCap` desc**, with **`Adj_FF_MCap` desc** as secondary tiebreaker (HANDOVER §2.5). This makes the ordering deterministic when multi-class listings share an identical company-level Total MCap (the more tradable share class — higher Adj_FF — comes first).

---

## A. Why Adj_FF_MCap for the 70/85 cuts (not raw FF)

The index is **weighted** on `Adj_FF_MCap` (Step 8), so a stock's **size segment** must be set on the same investable basis — otherwise its size class is decoupled from its actual index weight. A stock only ~20 % investable to foreigners (China A-shares, CIF ≈ 0.20) is sized by its *investable* free float.

Measured impact (2026-05-20, ACWI): switching the coverage basis to raw FF would push **~360 stocks** into the Standard tier that Adj_FF excludes — **357 of them China, 307 with IF < 1.0** — inflating EM Standard by +353 while DM is essentially unchanged. These would enter at near-zero index weight (the "zombie constituent" problem). Adj_FF coverage avoids this. See HANDOVER §2.2.

---

## Field names (internal standard, post Master-Loader rename)

`Mapping Country`, `Classification` (DM/EM/FM), `FactSet Econ Sector`, `FactSet Industry`, `FactSet Economy`, `Exchange Ticker`, `Symbol` (security-unique), `ISIN`, `Entity ID`, `Listing` (Primary/Secondary), `Total MCap Y2025`, `Free Float MCap Y2025`, `Free Float Percent` (0–1 decimal), `Adj_FF_MCap`, `IF`, `Closing Price`, `1M/3M/6M/12M ADTV Y2025`, `Listing Status` (0 active / 1 inactive), `Segment_New`, `Index_Weight`.
