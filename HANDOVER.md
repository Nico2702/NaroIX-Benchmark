# NaroIX Benchmark — Handover Documentation

> **Purpose:** Context document for continuing work on the NaroIX Benchmark / Helvetica Index project in Cursor. Reflects the state as of June 2026, after multi-week iterative development with Claude in claude.ai.
>
> **Read this first** before making any code changes. It encodes hard-won methodology decisions and bug fixes that aren't obvious from the code alone.

---

## 0. Status Update — 2026-06-04 (read before §1)

This document was written before the latest local work. The **methodology sections (§2–§5) remain valid**, but several structural/infra claims are now outdated. Corrected facts:

- **`pipeline_core.py` now EXISTS** (extracted 2026-06-10, behaviour-preserving). The Streamlit-free selection engine (`run_selection_pipeline`, `build_new_universe`, FOL, EUMSS, `build_index`, the matrix builders, the pure loaders incl. `load_master_excel`/`load_fol_matrix`, constants `INDEX_SERIES`/`EUROPE_COUNTRIES`/…) lives in `pipeline_core.py` and is importable headless (no Streamlit). `naroix_benchmark.py` is the UI: `from pipeline_core import *`, re-wraps the file loaders with `@st.cache_data`, keeps `set_page_config`, `render_*`, `load_excel`/`load_historical_data` (these use `st`). Verified: `pipeline_core` output is bit-identical to the pre-split baseline (3 periods) and the app boots clean. The "`pipeline_core.py` mirror (~line X)" references in §2 still have stale line numbers — search by symbol.
- **`auth.py` removed.** GitHub-OAuth login was deleted; the app runs open on localhost with no secrets/`secrets.toml` needed. Run with `streamlit run naroix_benchmark.py` (see `README.md`).
- **Caching IS applied** (contradicts §8): `@st.cache_data` decorates `load_master_excel`, `load_fol_matrix`, `load_historical_data`, etc.
- **Excel loading sped up** (partially closes §8 I/O backlog): `load_master_excel` now reads the file **once** with the `python-calamine` engine (was up to 11× openpyxl passes via the header-probe loop). Parquet caching still NOT implemented ("wir lassen es erstmal so").
- **Multi-Period buffer rules (§6 Priority 1) ARE implemented**: the "Multi-Period Run" tab runs the pipeline chronologically per index with incumbent state + maintenance buffer. Added on top: a Country Breakdown (Land×Periode matrix + GIMI-style per-period table) and a vectorized `build_wide_matrix()` (~239× faster than the old per-cell loop); heavy export artifacts are now built once and cached in `session_state`.
- **NaroIX Index Series** — own trademark-safe product family (Developed / Emerging / Global / Europe Markets × Large / Mid / Small / Standard / All Cap = 16, plus 6 thematic/filtered: US 500, US Tech 100, US Tech, Europe Tech, Europe Tech 30, World 100 = **22 products**) defined declaratively as `INDEX_SERIES` + `build_index()` (the latter supports optional `industries` filter + `top_n` by Total MCap). The GIMI-tab product table and the Multi-Period tab both run off it. Multi-Period uses **Option Y** (one pipeline run/period, products = consistent slices). Full catalogue + codes in **`INDEX_SERIES.md`**; construction in **`SELECTION.md`**.
- **Line numbers throughout are approximate** and have shifted. Use symbol search, not line numbers.

---

## 1. Project Overview

### What this is

**NaroIX Benchmark** is a Python/Streamlit tool that builds and analyzes equity indices following an MSCI-GIMI-like methodology. It supports:

- **Global indices**: NaroIX ACWI, World (DM), Emerging Markets (EM), ACWI IMI, World IMI
- **Country indices**: Switzerland, Germany, plus other DM/EM countries via the Country-Tab
- **Custom indices**: Helvetica (Swiss-focused multi-asset index with separate methodology)

The tool ingests FactSet snapshots (or a multi-period master file) and produces:
- Constituent lists per size segment (Large/Mid/Small/Micro)
- Excel exports per index and segment
- Validation reports
- Buffer-rule simulations (still maturing)

### Architecture (current — single file)

```
┌─────────────────────────────────────────────────────┐
│ pipeline_core.py  (Streamlit-FREE selection engine)  │
│  - load_master_excel(), build_snapshot_from_master() │
│  - load_fol_matrix(), build_sector_fallback_table()  │
│  - build_new_universe() / liquidity / FOL / EUMSS    │
│  - run_selection_pipeline(), build_index()           │
│  - normalize_index_weight(), build_wide/segment_*()  │
│  - constants: INDEX_SERIES, EUROPE_COUNTRIES, FOL_*  │
│  → importable headless (backtesting, tests)          │
└─────────────────────────────────────────────────────┘
              ▲  from pipeline_core import *
              │  (file loaders re-wrapped with @st.cache_data)
┌─────────────────────────────────────────────────────┐
│ naroix_benchmark.py  (Streamlit UI)                  │
│  - set_page_config + CSS, sidebar, all tabs          │
│  - render_new_tab(), render_*_tab()                  │
│  - load_excel(), load_historical_data() (use st)     │
│  - Helvetica pipeline (build_helvetica_pipeline)     │
└─────────────────────────────────────────────────────┘

Supporting Excel files (read-only inputs):
  - China Inclusion Factor.xlsx
  - Country_Classification.xlsx
  - Historical Classification.xlsx
  - In-Eligible.xlsx
  - NaroIX_FOL_Master_Aggregated_v1.9.yaml  (the only / active FOL matrix, internal version "1.9-redteam-corrected", 12 jurisdictions incl. Taiwan; older v1.3/v1.6 files were removed — no fallback)
  - Selection Dates.xlsx
```

> **Done (2026-06-10):** the Streamlit-free core was extracted into `pipeline_core.py`
> (behaviour-preserving; verified bit-identical to the pre-split baseline). Still inline in
> the UI: `build_helvetica_pipeline` (pure, but only used by the Helvetica tab) and the
> `st`-using loaders `load_excel` / `load_historical_data`. See §6 "Code Tasks" for the
> remaining dedupe (GIMI inline pipeline, dead `add_secondary_listings`).

### Repository

GitHub: `Nico2702/NaroIX-Benchmark`

Files in repo:
- `naroix_benchmark.py` (main app — contains everything)
- `requirements.txt` (now includes `python-calamine` for fast Excel reads)
- `README.md` (Windows-only local run instructions)
- `HANDOVER.md` (this file)
- Excel reference files (Historical Classification, FOL Matrix, etc.)

Removed / never added:
- `auth.py` — **deleted** (login removed)
- `secrets.toml.template` — not needed (no auth)
- `pipeline_core.py` — does not exist (planned split, see Architecture note)

Local setup is recommended over Streamlit Cloud due to RAM constraints (the master file is 458 columns × 52,764 stocks ≈ 200 MB in RAM, which exceeds the 1 GB Cloud limit).

---

## 2. Methodology — Core Decisions

This section documents **the why** behind code structure. Decisions were made deliberately and should not be reverted without explicit user confirmation.

### 2.1 Index Construction — Three Layers

The methodology follows a three-layer construction:

1. **Strategic Asset Allocation (SAA)** — fixed target weights per asset class block
2. **Size Bucket Classification** — eligible universe partitioned into Large/Mid/Small Cap based on cumulative Free Float Market Capitalization (FF MCAP) Coverage
3. **Constituent Selection & Weighting** — per bucket, the constituents are selected (Top 10 for equity) and weighted (equal weight within bucket)

### 2.2 Coverage Logic — Option B (Pool-Based)

**DECISION**: Cumulative Coverage is computed on the **eligible pool total** (single scale), not on a "Standard Pool" re-normalization.

This was a deliberate change from an earlier MSCI-style approach. The current logic is:

```python
# One cumulative series, one scale, three thresholds
_c_before = cumsum(Adj_FF_MCap).shift(1).fillna(0) / pool_total * 100

# Classification thresholds (all on the same Pool scale)
Large Cap:  _c_before < 70%
Mid Cap:    70% ≤ _c_before < 85%
Small Cap:  85% ≤ _c_before < 99%
Micro Cap:  _c_before ≥ 99%
```

This is **methodologically more elegant** than MSCI's two-step approach (first define Standard Pool, then re-normalize Large/Mid threshold). Effects:
- Each stock has one well-defined Pool Weight visible in the UI
- Section weights add up across all size segments naturally
- Straddle rule (see 2.3) applies uniformly to all three thresholds

**Implementation locations**:
- `run_selection_pipeline()` in `naroix_benchmark.py` (~line 1295)
- GIMI-Tab inline code (~line 2680)
- `build_helvetica_pipeline()` (~line 3178)
- `pipeline_core.py` mirror (~line 595)

**Effect vs old logic**: ~427 stocks globally shifted from Mid to Large in ACWI. Total Standard count unchanged. Country breakdowns shift:
- Germany: 12 Large + 20 Mid → 18 Large + 14 Mid
- Switzerland: 8 Large + 16 Mid → 12 Large + 14 Mid (now 26 total in Switzerland-Tab)

**Coverage basis = Adj_FF_MCap (IF-adjusted), NOT raw Free Float MCap** — deliberate, MSCI-conform.

The per-country coverage cumulation (`_c_before`) runs on **`Adj_FF_MCap` = Free Float MCap × Inclusion Factor** (`if_cum_col` in "Selektion" mode, the default). A toggle (`if_selection_mode` = "Gewichtung") switches it to raw FF, but that is explicitly a non-MSCI research mode.

**Why Adj_FF and not raw FF:** the index is *weighted* on Adj_FF_MCap (Step 8), so a stock's size-segment must be set on the same investable basis — otherwise its size class is decoupled from its actual index weight. A stock only 20 % investable to foreigners (e.g. China A-shares, CIF ≈ 0.20) must be sized by its *investable* free float, not its full free float.

**Impact measured on real data (2026-05-20, ACWI, headless run):**

| Coverage basis | Large | Mid | Small | Standard (L+M) | DM | EM |
|---|---|---|---|---|---|---|
| **Adj_FF (default)** | 1080 | 1323 | 7354 | **2403** | 1178 | **1225** |
| raw FF (alt) | 1368 | 1389 | 7000 | 2757 | 1179 | 1578 |

- 664 stocks change segment between the two bases.
- **360 stocks land in Standard under raw FF but not under Adj_FF — 357 of them China, 307 with IF < 1.0.** DM Standard barely moves (1178↔1179, IF≈1 there); **EM Standard inflates +353**, almost entirely China A-shares.
- Raw FF would push ~360 barely-investable (FOL/China-capped) stocks into the Standard tier at near-zero index weight — the "zombie constituent" problem at scale. Adj_FF avoids this and keeps segmentation consistent with weighting.

### 2.3 Straddle Rule (uniform across all thresholds)

A stock that crosses a size-segment cutoff is **assigned to the segment with the lower threshold** (i.e., the larger size bucket).

Mechanism: classification uses `_c_before` (cumulative coverage *before* including the stock's own FF MCAP), not `_c_after`. This makes the rule deterministic and applies uniformly to all three cuts (70/85/99).

Example: If Lonza's `_c_before = 69.02%` and `_c_after = 71.13%`, Lonza is Large Cap (because 69.02% < 70%).

### 2.4 Variante B — Both Primary and Secondary Listings Included

**DECISION**: Multi-class securities of the same entity (e.g., Roche common shares + Genussschein, Schindler common + preference, Swatch bearer + registered) all run through the pipeline as **separate securities**. Both can be included if they pass investability filters individually.

This applies to:
- ACWI/World/EM/Country-Tabs (always Variante B since the recent migration)
- **Helvetica** (migrated from Primary-only-with-fallback to Variante B in the latest iteration)

**Methodological justification**:
- MSCI Section 2.2.2: "Some of the investability requirements are applied at the individual security level"
- Solactive since 2025-04 methodology change: explicit allowance for multi-share-lines
- Both listings are genuinely tradable with separate order books

**Impact on Helvetica** (snapshot 03-2026 Pool):
- Pool grows from 132 → 135 stocks
- Pool Adj_FF total grows from $2,024.52B → $2,044.73B
- Standard count grows from 24 → 26 (12 Large + 14 Mid)
- Roche-Konzern weight increases from 15.74% → 16.16% (ROP-SWX Genussschein 15.58% + RO-SWX Common 0.58%)

**Edge case — Lindt**: Lindt has only LISP-SWX (participation certificate, listed as Secondary) available in CH. Variante B handles this correctly — Lindt PS stays in the index because there's no Primary alternative.

**Final dedup is on `Symbol` (security-unique) — protects Variante B.** Step 6 of `run_selection_pipeline` ends with `gm_complete.drop_duplicates(subset=["Symbol"])`. Verified on real data (2026-05-20, 52,764 rows): `Symbol` and `Exchange Ticker` are **unique per row** (0 duplicates), while `ISIN` has 151 and `Entity ID` 2,263 duplicates (= the multi-class securities). So:
- The dedup is **deliberately on `Symbol`, NOT ISIN/Entity ID** — multi-class lines (e.g. Roche common + Genussschein) share Entity ID / sometimes ISIN but have **distinct Symbols**, so both survive. Dedup on ISIN or Entity ID would wrongly collapse Variante B secondaries.
- Since `Symbol` is unique and the four segment buckets (Large/Mid, coverage-Small, liquidity-Small, Micro) are mutually exclusive by Symbol-set construction, the dedup **removes nothing in practice** — it is a defensive backstop, not an active filter.

### 2.5 Sort Tiebreaker

**DECISION**: Sort by Total MCap descending, with Adj_FF_MCap descending as secondary tiebreaker.

```python
.sort_values(["Total MCap Y2025", "Adj_FF_MCap"], ascending=[False, False])
```

**Why**: Multi-class listings of the same company often have identical Total MCap (both report company-level Total). Without a tiebreaker, the order would be non-deterministic (depends on FactSet's row order). With the tiebreaker, the listing with higher Adj_FF_MCap (= more tradable share class) consistently appears first.

Example: BMW Common ($24.49B Adj_FF) always before BMW3 Preference ($4.75B Adj_FF) at identical $55.33B Total MCap.

**Implementation locations** (all 7 places):
- `naroix_benchmark.py` lines ~1270, 1301, 2639, 2677, 3193
- `pipeline_core.py` lines ~566, 594

### 2.6 EUMSS Calibration

**DECISION**: Calibrate EUMSS on DM Primary-only stocks, apply globally to both DM and EM.

```python
dm_only = gm_u[(gm_u["Classification"] == "DM") & (gm_u["Listing"] == "Primary")]
dm_only = dm_only.sort_values(["Total MCap Y2025", "Adj_FF_MCap"], ascending=[False, False])
dm_total_ff = dm_only["Free Float MCap Y2025"].sum()
dm_only["_cum_ff_pct"] = dm_only["Free Float MCap Y2025"].cumsum() / dm_total_ff * 100
eumss_pos = dm_only[dm_only["_cum_ff_pct"] >= 99].index
eumss_full = dm_only.loc[eumss_pos[0], "Total MCap Y2025"]  # threshold
eumss_ff = eumss_full * eumss_ff_ratio  # ~0.5 ratio
```

**Methodologically correct** — MSCI Section 2.2.3 mandates this exact approach. EUMSS must come **before** liquidity filter (otherwise calibration would shift).

**Recently verified scenarios**:
- ACWI Standard without EUMSS would have 2,640 instead of 2,429 stocks (+211). Most additions in China (+64), Japan (+12). DE and CH unchanged.
- Decision: keep EUMSS, methodologically standard-conforming.

### 2.7 Country Mapping — Two Sources

Country mapping was originally computed in code:

```python
df["Mapping Country"] = np.where(_ecn == _coi, _coi, _cor)
```

**RECENT CHANGE**: The user now maintains Country Mapping **directly in the Excel file** (column T, header "Country Mapping"). Reasons:
- Auditable and reviewable by humans
- Edge cases (Amrize, Bunge, etc.) handled explicitly
- Decoupling from code logic improvements

**Current code behavior**:
- If "Country Mapping" exists in input Excel → use directly (preferred)
- If not → fall back to old code logic (`ECN==COI ? COI : COR`)

**Note**: This is implemented in the master-file loader. The single-snapshot loader still uses code logic. Both should work correctly because both arrive at the same `Mapping Country` column name internally.

### 2.8 Helvetica-Specific Methodology

Helvetica is a Swiss-focused custom index with **different filters** from the ACWI pipeline:

| Filter | Helvetica | ACWI |
|---|---|---|
| Country Filter | Exchange Country = Switzerland (fixed) | Mapping Country + Classification = DM/EM |
| EUMSS | Not applied | Applied globally |
| Min FF % | ≥ 10% (Buffer 7.5%) | ≥ 10% (Buffer 7.5%) |
| Min ADTV (3M) | ≥ $0.5M (Toggle: $0.25M) | DM ≥ $2M, EM ≥ $1M |
| Variante B | Yes (recently migrated) | Yes |
| Coverage cuts | 70/85/99% (Buffer 75/90/99.5%) | Same |
| Real Estate handling | Two separate sections (Constituents + Universe incl. Micro) | Combined in size segments |

**Why Helvetica = Exchange Country instead of Mapping**: Verified with MSCI Switzerland Index — MSCI uses similar restrictive country definition (40 constituents, all classic SIX-listings, no On Holding/Chubb/Amrize). Solactive is more inclusive (uses Mapping OR Exchange). NaroIX/Helvetica deliberately follows MSCI's narrower approach.

**Helvetica Sections (UI display)**:
1. Standard Index (Large + Mid, excl. Real Estate)
2. Large Cap (excl. Real Estate)
3. Mid Cap (excl. Real Estate)
4. Small Cap (excl. Real Estate)
5. Real Estate (Helvetica Constituents — Coverage < 99%)
6. Real Estate Universe (incl. Micro Cap — no Coverage cut)

**Consolidated Export** at the end of Helvetica tab: One Excel with `Section`-column listing Top 10 Large + Top 10 Mid + Top 10 Small + all Real Estate Universe stocks.

**Real Estate Treatment** (important methodologically):
- Real Estate Development stocks **remain in the pool** for Cumulative Coverage calculation
- They are **removed AFTER** size bucket assignment
- This means: the size-bucket thresholds (70/85/99) are calculated on the FULL pool including Real Estate. Real Estate is only excluded from the displayed Large/Mid/Small sections, and shown separately in section 5/6.

### 2.9 Two Real Estate Sections — Methodology

Real Estate (Helvetica Constituents) has Coverage cut < 99%. Real Estate Universe has NO coverage cut.

**Per user decision**: The Index Guideline (Section 4.2.2) refers to **all eligible Swiss REITs** (incl. Micro Cap, no coverage cut). So the "Real Estate Universe" table IS the methodological basis for the Swiss REIT exposure in the index.

The "Helvetica Constituents" table is an additional view for users curious about which REITs also fall within the Standard universe coverage range.

### 2.10 SAA Block Allocations

| Block | SAA Weight | Constituents | Weight per Constituent |
|---|---|---|---|
| Swiss Large Caps | 10.0% | 10 | 1.00% |
| Swiss Mid Caps | 15.0% | 10 | 1.50% |
| Swiss Small Caps | 15.0% | 10 | 1.50% |
| **Swiss Equity total** | **40.0%** | 30 | — |
| Swiss REITs | 15.0% | all eligible (N) | 15.0% / N |
| Swiss Government Bonds 3-7y | 5.0% | 1 ETF | 5.0% |
| Swiss Government Bonds 7-15y | 5.0% | 1 ETF | 5.0% |
| Swiss Corporate Bonds | 15.0% | 1 ETF | 15.0% |
| **Swiss Fixed Income total** | **25.0%** | — | — |
| Gold | (not yet specified) | 1 ETC | — |
| Cash (CHF) | (not yet specified) | — | — |

The Equity Block weights are **deliberately asymmetric** (10/15/15 instead of 20/10/10) to avoid Large Cap concentration — Roche/Novartis/Nestlé would otherwise dominate.

### 2.11 Liquidity-Fail Exclusion — Variante A (decided 2026-06-06)

**DECISION:** A stock that passes EUMSS but **fails the liquidity filter is excluded entirely** — it is NOT demoted to Small Cap and does NOT enter the IMI. The single liquidity bar (DM 3M ADTV ≥ $2M / EM ≥ $1M) thus applies to **all** size tiers.

**Rationale:** previously liquidity-fails were labelled Small Cap ("MSCI-style"), which in practice gave Small Cap **no liquidity floor at all** — illiquid names entered the IMI. That is too lax. (The fully MSCI-proper alternative would be a *second, looser* liquidity bar for Small Cap; we deliberately chose the simpler Variante A — one bar, fail = out — see code comments.)

**Impact (2026-05-20, ACWI):** removes **1,083** names from the IMI universe (ACWI IMI 9,763 → 8,680), but only **−1.26 % by weight** (these are small, illiquid). **ACWI Standard (Large+Mid) is unaffected** (liquidity-fails were never Large/Mid). Small Cap is now **coverage-based only** (6,275 vs. 7,358 before).

**Implementation:** `run_selection_pipeline` Step 5/6 (the `gm_small` bucket is gone) and the GIMI-tab inline mirror, kept in sync. Excluded names are returned as `gm_liq_excluded` for audit.

---

## 3. Universe Construction — Filter Chain

> **See `SELECTION.md` for the full, detailed step-by-step selection process** (all 8 steps of `run_selection_pipeline`, the two cumulative-coverage bases, both buffers, Variante B, segment/scope definitions). This section is the condensed version.

The universe is built in `build_new_universe()` (inline in `naroix_benchmark.py`; the planned `pipeline_core.py` does not exist yet). Steps in order:

### Step 1 — Inheritance from NaroIX Equity Universe (global exclusions)
- `Closing Price < $20,000` (extreme high-priced stocks excluded — Lindt Common ~$150k gets cut, but Lindt PS LISP-SWX at ~$13k stays)
- `Listing Status ≠ 1` (inactive/delisted stocks excluded)
- Thailand SHARE→NVDR mode (default: keep NVDR over SHARE for foreign-investable A-Shares)
- HK stocks with Trading Currency CNY excluded
- `Country of Risk ≠ @NA`
- NAICS-based exclusions (Open-End Investment Funds)
- Exchange Name exclusions (Euro MTF, @NA)
- Name contains "ETF", "SICAV", "%" → excluded
- `Classification` (DM/EM/FM) must be set (via `country_cls.map(Mapping Country)`)

### Step 2 — FOL Matrix Application
- **Active matrix (switched 2026-06-11):** `NaroIX_FOL_Master_Aggregated_v1.9.yaml`, internal version **`1.9-redteam-corrected`** — **12 jurisdictions** (added **Taiwan**), Qatar banks & insurers fixed to 49%, and all logical `auto>max` violations resolved (India pharma `fol_automatic` 1.0→0.74, internet retail max 0→1). v1.9 is now the **only** FOL matrix in the repo (the older v1.3/v1.6 files were deleted — `load_fol_matrix` looks for v1.9 only, no fallback). **Taiwan requires `"TAIWAN":"TW"` in `FOL_COUNTRY_CODE_MAP`** (added) — without it Taiwan's FOL is loaded but never matched. Lineage: 1.3→1.6 = point-in-time corrections (IN insurers 26→49→74%, AE/ID/KW/TH finance & telecom); 1.6→1.9 = +Taiwan +Qatar-financials +auto>max fixes. **Index impact** (simulated, ACWI 2026): tiny — EM weight ~−0.03pp vs v1.1 (Qatar financials + Taiwan telecom/transport; Taiwan megacaps are tech = 100% open), a few small India pharma IFs drop. Historical years (2014-2020) shift more. NOTE: some corrections legitimately end before 2026 (real liberalization, documented in the YAML changelog with legal bases).
- Looks up `FOL_Value` per stock based on `(Mapping Country, FactSet Industry, year)`
- Fallback chain in `_resolve_fol_row`: **(1)** exact industry match → **(2)** normalized industry match (whitespace/case-tolerant, `_norm_fol_key`) → **(3)** sector fallback (strictest `fol_automatic` in the sector) → **(4)** country `default_fol` → **(5)** 1.0
  - Step (2) added to fix a YAML-vs-FactSet spelling mismatch: matrix wrote `Hotels/Resorts/Cruiselines` while FactSet data has `Hotels/Resorts/Cruise lines`. The exact match failed and the sector fallback grabbed an *unrelated* restricted industry (SA: Casinos 0; KR: Broadcasting 0) → IF=0 → no weight. Affected **71 stocks across 8 countries** (IN/ID/TH/KR/MY/PH/SA/AE), incl. 4250-SAU and 180640-KRX. Normalization recovers the *already-present* correct matrix entry without touching the YAML; verified **0 collisions** (no two distinct industries with differing FOL collapse to the same normalized key), Adj_FF==0 in the universe dropped 73 → 15.
- Computes `IF = min(1.0, FOL_Value / Free Float Percent)`
- China A-Shares get the China Inclusion Factor (CIF, currently ~20%)
- `Adj_FF_MCap = Free Float MCap × IF`

### Step 3 — EUMSS Calibration (Equity Universe Minimum Size)
- Calibrated on DM Primary-only stocks
- Threshold at 99% Cumulative FF MCAP Coverage of sorted DM pool
- Applied globally to all stocks (DM + EM)
- `eumss_full` (Total MCap threshold) and `eumss_ff` (FF MCap threshold, ~50% ratio of eumss_full)

### Step 4 — Liquidity Filter (DM/EM differentiated)
- DM: 3M ADTV ≥ $2M AND 6M ADTV ≥ $2M
- EM: 3M ADTV ≥ $1M AND 6M ADTV ≥ $1M
- **Variante A (decided 2026-06-06): stocks passing EUMSS but failing liquidity are EXCLUDED entirely** — not Small, not Micro, not in IMI. The liquidity bar therefore applies to **all** tiers (Standard *and* Small); a stock that doesn't meet it isn't investable, so it's out. *(Previously these were demoted to Small Cap — "MSCI-style" — which effectively gave Small Cap no liquidity floor. See §2.11.)*
- Stocks failing EUMSS → **Micro Cap**
- Excluded liquidity-fails are returned as `gm_liq_excluded` for audit (not in `gm_complete`).

### Step 5 — Per-Country Coverage Cuts (Option B Logic)
- **Non-Investable carve-out (decided 2026-06-10):** before the waterfall, stocks with `Adj_FF_MCap == 0` (i.e. `IF == 0` — explicit industry FOL=0, `pre_investable`, or FF=0) are split off into segment **`Non-Investable`**. MSCI excludes FIF=0 securities, so these enter **no** index (Large/Mid/Small/IMI) but stay visible in `gm_complete`/exports for audit (returned as `gm_noninv`). Only `Adj_FF_MCap > 0` runs the waterfall — which also means a country block can no longer be silently skipped on `tot == 0`. *(Impact 2026-05-20 ACWI: IMI 8,680 → 8,679; Standard unchanged. Pre-fix these were 0-weight "zombie" constituents.)*
- Group by `Mapping Country`
- Sort by Total MCap desc, Adj_FF_MCap desc (tiebreaker)
- Compute `_c_before` per stock on Adj_FF_MCap
- Classify: < 70% Large, 70-85% Mid, ≥ 85% becomes Small Cap. **Small Cap is now coverage-based only** (all of it passed liquidity); liquidity-fails are no longer added here (Variante A).
- EUMSS calibration robustness: if no DM **Primary** listings exist (malformed `Listing` column), calibration falls back to all DM listings and sets `eumss_calib_fallback=True` (UI warns) instead of silently yielding `eumss_full=0`.

The Helvetica pipeline (`build_helvetica_pipeline()`) is **structurally simpler** — no EUMSS, simpler liquidity, narrower country definition.

---

## 4. Master File Format

The new multi-period Master File is the upcoming standard input format.

### Structure
- **Sheet name**: "Master"
- **Rows**: 52,764 stocks (full FactSet universe)
- **Columns**: 458 total
  - 26 metadata columns (A-Z)
  - 432 periodic data columns (48 periods × 9 fields)

### Metadata columns (static)
A. Symbol
B. Name
C. Listing
D. Sec Type
E. Sec Type Inclusion
F. Public Company
G. NAICS
H. SIC
I. FactSet Economy
J. FactSet Sector
K. FactSet Industry *(typo "Inudstry" fixed in latest version)*
L. Perm ID (Security)
M. Entity ID (Company)
N. ISIN
O. Exchange Ticker
P. Trading Exchange
Q. Exchange Name
R. Trading Currency
S. Exchange Country *(renamed from "Exchange Country Name")*
**T. Country Mapping** *(NEW — user maintains this manually)*
U. Country of Incorp
V. Country of Risk
W. Country of Rev_Risk *(not used in pipeline)*
X. Country HQ *(not used in pipeline)*
Y. Region by Exchange *(not used in pipeline)*
Z. Region by Primary Listing *(not used in pipeline)*

### Periodic columns (9 fields × 48 dates)

Format: `<Field> YYYY-MM-DD` (e.g., `Closing Price 2026-05-20`)

Per period:
1. Closing Price
2. Total MCap
3. Share MCap *(informational, not used in pipeline)*
4. **Float MCap** *(latest naming — was "FloatMCap" zusammengeschrieben, now "Float MCap" getrennt)*
5. Float PCT *(WARNING: stored as 0-100 percent, NOT 0-1 decimal — see Bug Fix #2)*
6. 1M ADTV
7. 3M ADTV
8. 6M ADTV
9. 12M ADTV

### Selection Dates Coverage
- First: 2014-11-19
- Last: 2026-05-20
- 48 quarterly periods (Feb / May / Aug / Nov)

`Selection Dates.xlsx` was recently updated to include 2026-05-20 (was missing).

### Listing Status Derivation

The Master File **does not** include `Listing Status` per period. We derive it:

```python
combined["Listing Status"] = np.where(
    pd.to_numeric(combined["Closing Price"], errors="coerce").fillna(0) > 0,
    0,  # active
    1   # delisted or pre-IPO
)
```

This is methodologically sound: if a stock has a closing price on the selection date, it's tradable.

### Loader Logic

`load_master_excel()` and `build_snapshot_from_master()` in `naroix_benchmark.py` handle the format:

1. Read full Excel (memory-intensive, ~200 MB in RAM)
2. Detect static vs periodic columns via regex on header
3. Build a `master_data` dict: `{"static_df": ..., "periods": {date_iso: period_df}}`
4. UI selectbox lets user pick a period
5. `build_snapshot_from_master(master_data, selection_date_iso)` produces a snapshot DataFrame structurally identical to old single-snapshot format

**Default period**: Most recent (2026-05-20).

---

## 5. Critical Bug Fixes (do not undo)

### Bug Fix #1 — Sort Tiebreaker (Multi-Class Listings)

**Symptom**: BMW Common and BMW Pref had identical Total MCap, ordering depended on FactSet's row order — Coverage Cuts could shift unpredictably between snapshots.

**Fix**: Added `Adj_FF_MCap` as secondary sort key everywhere. See Section 2.5.

### Bug Fix #2 — Float PCT Format Mismatch (Master File)

**Symptom**: Master File reports `Float PCT` as `99.879` (percent, 0-100). Single-snapshot reports `Free Float Percent` as `0.99879` (decimal, 0-1). Code assumes decimal.

**Effect before fix**: In Master File mode, the FOL calculation `IF = min(1.0, FOL_Value / Free Float Percent)` divided by ~100x larger value → all IFs ≈ 0.01 → Apple Adj_FF dropped from $3,980B to $39B → China weight inflated from ~3% to ~30% in ACWI.

**Fix** in `build_snapshot_from_master()`:

```python
if "Free Float Percent" in combined.columns:
    _ffp_num = pd.to_numeric(combined["Free Float Percent"], errors="coerce")
    _ffp_med = _ffp_num.dropna().median() if _ffp_num.notna().any() else 0
    if _ffp_med > 1:  # Auto-detect percent format
        combined["Free Float Percent"] = _ffp_num / 100.0
```

**After fix**: China weight ~2.77% in ACWI, USA ~61.61%, in line with MSCI ACWI.

### Bug Fix #3 — Selection Dates Missing 2026-05-20

**Symptom**: Master File contains 48 periods, but `Selection Dates.xlsx` only had 47 (latest 2026-02-18). Loader filtered out 2026-05-20 as "invalid".

**Fix**: User added 2026-05-20 to `Selection Dates.xlsx`. No code change.

### Bug Fix #4 — Validation Warning False-Positive

**Symptom**: Pipeline validation showed "fehlende Pflichtfelder ['Free Float MCap']" for all 48 periods even though pipeline worked. Validation hardcoded `"Free Float MCap"` but Master File uses `"Float MCap"` (different prefix).

**Fix**: Validation now accepts any of three aliases (`Float MCap`, `FloatMCap`, `Free Float MCap`).

### Bug Fix #5 — Helvetica Multi-Listings (Variante B Migration)

**Earlier behavior**: Helvetica used Primary-only with Secondary fallback. Roche Common (RO-SWX) was excluded since Genussschein (ROP-SWX) is Primary.

**Recent change**: Variante B activated for Helvetica. Both listings now included. See Section 2.4.

---

## 6. Open Backlog — Multi-Period Work

Multi-period data is now available (48 periods, 2014-11-19 to 2026-05-20). This unlocks several long-pending methodological additions:

### Priority 1 — Maintenance Buffer Rules over Time — ✅ DONE

Implemented in the **"Multi-Period Run"** tab (`naroix_benchmark.py`, `with tab_multi:`):
- Pipeline iterates over the selected period range chronologically, per selected index.
- Incumbents (previous period's constituents, by ISIN) are tracked per index (`incumbents_per_index`).
- Maintenance buffer is applied against incumbent status (`apply_buffer and not is_seed`); the first period is the seed (no incumbents).
- Summary table reports per period/index: constituents, held / dropped / new entrants, buffer balance.
- Outputs: Long-format export (sheet per index×period), Wide "Gewichtsmatrix" (stock×period weights), and a Country Breakdown (Land×Periode matrix + GIMI-style per-period table).

**Turnover statistics** are surfaced in the Multi-Period Summary (held / dropped / new entrants per period). Empirical buffer calibration is **not pursued** (buffers fixed by choice, aligned with peer providers).

### Priority 2 — Size Buffer (Large↔Mid, Mid↔Small) — ✅ DONE (2026-06-05)

Implemented as a coverage-percentage-point hysteresis (Nico's concept, not MSCI's ±50/−33 market-size buffers):
- `_size_segment(prior, _c_before, large_thr, mid_thr, bw)` transition function; bands ±`bw` pp (default 5) around the 70 % (Large/Mid) and 85 % (Mid/Small) boundaries. Incumbents are sticky within the band; newcomers classified at the plain cut-offs (= legacy behaviour). Verified against the concept (796 combos, 0 mismatches).
- New `run_selection_pipeline` params: `apply_size_buffer`, `incumbent_segments` ({ISIN→segment}), `size_buffer_pp`. Default off → byte-identical legacy path. Adds a `Size_Buffer_Held` audit column.
- Multi-Period loop carries per-index `{ISIN→Segment}` state; summary shows "Held by Size Buffer". `Size_Buffer_Held` (per-stock bool: did the hysteresis hold this stock in its prior segment?) is also included in the Long-format Excel export.
- Sidebar toggle (default ON in Master mode). Multi-Period only.

**Deliberate scope decisions** (Nico, 2026-06-05): buffer applies ONLY at the 70 & 85 boundaries — the Small↔Micro lower bound stays governed by **EUMSS** (not a per-country 99 % percentile, §2.6 kept). Percentile = `_c_before` (straddle rule §2.3). Liquidity-driven Small is unaffected.

**Supporting views in the Multi-Period tab** (2026-06-06):
- **Segment-Wanderung** matrix (`build_segment_matrix`): stock × period → segment, colour-coded, sorted by most segment changes first; built once per run, cached, with Excel export. The primary visual check for the buffer effect (fewer colour changes per row = less segment churn).
- Detail-Ansicht (defaults to last period) shows DM/EM Country Breakdown tables + weight charts by Country, by Sector (`FactSet Economy`), and a DM-vs-EM total bar — all for the selected period/index.

**Verified on real data (2026-06-06)** — headless run of the ACWI multi-period loop (last 8 periods of `NaroIX_ACWI_Selection_Master_05_2026_Final.xlsx`), size buffer OFF vs ON (±5pp):
- **Segment switches (Large↔Mid) dropped from 1041 → 345 (−67 %)** across the 7 transitions. Buffer works as intended.
- **Standard count (Large+Mid) and DM/EM split identical** OFF vs ON every period; Standard entries (908) / exits (331) identical → membership invariant. (Expected: the buffer only relabels Large↔Mid, and the Mid↔Small membership edge is already governed identically by the maintenance buffer's 90 % coverage.)
- "Held by Size Buffer" plausible and growing (221→561/period, 3145 total).

**P2 fully closed.**

### Priority 3 — Length-of-Trading Filter (20 Days) — out of scope

Handled in Nico's **external backtesting tool** (it concerns trading-day history within the backtest), not in this selection engine.

### Priority 4-N — status (2026-06-09)

- Historical Index-Performance simulation — **out of scope** (external backtesting tool).
- Sector / Country drift over time — ✅ **DONE** — Country-Gewichte- and Sector-Gewichte-über-Zeit matrices in the Multi-Period tab (each with Excel export).
- Constituent movement (longest tenure, chronic cap-class shifters) — ✅ **DONE** — Segment-Wanderung matrix + Tenure ranking (each with Excel export).
- Empirical buffer calibration — **not pursued** (buffers fixed by choice, aligned with peer providers).
- EUMSS threshold evolution over time — ✅ **DONE** — EUMSS Full/FF columns per period in the Index Characteristics table.
- China Inclusion Factor evolution validation — **not needed** (Nico).

### Code Tasks (cleanups)

- ✅ **DONE (2026-06-10)** — `pipeline_core.py` extracted (Streamlit-free single source of truth). Verified bit-identical to the pre-split baseline; app boots clean. UI does `from pipeline_core import *` and re-wraps the file loaders with `@st.cache_data`.
- ✅ **DONE (2026-06-10)** — the GIMI-Tab inline pipeline was replaced by a single `run_selection_pipeline(...)` call (with a new `excl_delisted` param so it honours the UI toggle, default True). Verified headless: identical constituents + segments for `excl_delisted` True and False. One intentional harmonisation: GIMI weights now use `normalize_index_weight` (exact-100, sorted) like every other tab, instead of plain division (≤1e-6 weight diff; same names/segments). Dead `add_secondary_listings()` deleted. → the selection logic now lives in **one** place (`pipeline_core.run_selection_pipeline`).
- ✅ **DONE (2026-06-09)** — "Real Estate Investment Trusts" added to the RE filter (Helvetica pipeline): `RE_INDUSTRIES = {"Real Estate Development", "Real Estate Investment Trusts"}`, matched via `.isin`. Verified: 18 CH "Real Estate Development", 0 CH REITs → currently a no-op on the data, but now methodologically complete (900 REITs exist globally).

---

## 7. Index Guideline (External Document — Draft)

User is writing a methodology guideline document. Currently working on Section 4 (Index Selection and Construction).

### Section 4 — Index Construction (introduction)

Current draft (approved):

> "The Index is constructed in three layers. At the top layer, a fixed Strategic Asset Allocation (SAA) determines the target weight of each asset class block. At the second layer, the eligible Swiss equity universe is classified into Large, Mid and Small Cap size buckets based on cumulative Free Float Market Capitalization (FF MCAP) Coverage. At the third layer, the constituents of each size bucket are selected from the resulting pools in accordance with the criteria set out in this Section, and weighted as described in Section 4.5."

### Section 4.1 — Index Universe Definition

Approved version:

> The Index Universe comprises all eligible Swiss equities, Swiss listed real estate companies (REITs), and exchange-traded products (ETFs and ETCs) providing Swiss fixed income and gold exposure that meet the eligibility criteria specified in this Section. In addition, the Index holds a CHF cash position.
>
> 1. **Equity universe** — all equity securities of companies listed on the SIX Swiss Exchange and meeting the investability requirements set out in Section 4.2.1.
> 2. **Real estate universe** — all Swiss-listed real estate companies classified under the FactSet Industry classification as Real Estate (e.g. "Real Estate Development" or "Real Estate Investment Trusts" within the FactSet Sector "Finance"), meeting the requirements set out in Section 4.2.2.
> 3. **Fixed Income universe** — CHF-denominated, UCITS-compliant ETFs that provide exposure to Swiss government and Swiss corporate bond markets, listed on the SIX Swiss Exchange. The specific ETFs included in the Index are set out in Section 4.2.3.
> 4. **Gold universe** — physically-backed Gold ETCs (Exchange-Traded Commodities), listed on an Eligible Exchange. The specific ETCs included in the Index are set out in Section 4.2.4.
> 5. **Cash Exposure** — a CHF cash position held directly within the Index, as set out in Section 4.2.5.

### Section 4.2.1 — Swiss Equities (in progress, key paragraphs approved)

Filters (bullets):
- Exchange Country: Switzerland
- Closing Price: < USD 20,000
- Free Float Percent: ≥ 10% (Maintenance Buffer: ≥ 7.5%)
- 3-month Average Daily Value Traded (ADTV): ≥ USD 0.5M

Subsequent paragraphs include:
- Sort and Cumulative Coverage description
- **Straddle Rule** (bold-headed): "Each security is assigned to a size bucket based on its cumulative coverage immediately before including its own FF MCAP..."
- **Maintenance Buffer logic** (bold-headed)
- Real Estate treatment (stays in pool for coverage, separated after classification)
- Top 10 selection per bucket, equal weight
- SAA table (10/15/15)
- Edge case: < 10 eligible non-Real-Estate securities

### Section 4.2.2 — Swiss REITs (approved)

Filter list identical to 4.2.1 plus FactSet Industry restriction.

Key sentence (recently agreed): "Unlike the Swiss Equity selection (Section 4.2.1), no Coverage-based size segmentation applies to the Swiss REIT exposure. All Swiss-listed Real Estate securities meeting these criteria on the Selection Day are included as Index Components, regardless of size."

Maintenance Buffer paragraph references Section 4.2.1 ("applies analogously").

### Section 4.2.3 — Swiss Bonds (concrete ISINs)

| Exposure | ISIN | Name | Weight |
|---|---|---|---|
| Swiss Government Bonds 3-7y | CH0016999846 | iShares Swiss Domestic Government Bond 3-7 ETF (CH) | 5.0% |
| Swiss Government Bonds 7-15y | CH0016999861 | iShares Swiss Domestic Government Bond 7-15 ETF (CH) | 5.0% |
| Swiss Corporate Bonds | CH0226976816 | iShares Core CHF Corporate Bond ETF (CH) | 15.0% |

### Definitions Section

Approved definition:

> **Cumulative FF MCAP Coverage** — the cumulative sum of Free Float-Adjusted Market Capitalization across the eligible Swiss equity universe (sorted in descending order by Total Market Capitalization, with FF MCAP as tiebreaker), expressed as a percentage of the total FF MCAP of the eligible universe. For each security, the cumulative coverage is evaluated immediately before including its own FF MCAP, and is used to assign the security to a size bucket as described in Section 4.2.1.

---

## 8. Coding Style & Conventions

### Internal Field Names (post-rename)
After Master Loader rename, the code expects these field names:
- `Mapping Country` (not "Country Mapping")
- `Exchange Country Name` (not "Exchange Country")
- `FactSet Industry`
- `FactSet Econ Sector`
- `Perm ID` (not "Perm ID (Security)")
- `Entity ID` (not "Entity ID (Company)")
- `Total MCap Y2025`
- `Free Float MCap Y2025`
- `Free Float Percent` (always 0-1 decimal)
- `Closing Price`
- `1M/3M/6M/12M ADTV Y2025`
- `Listing Status` (0 = active, 1 = inactive)
- `Adj_FF_MCap` (computed in `build_new_universe()`)
- `IF` (Foreign Inclusion Factor)
- `Classification` (DM/EM/FM)

### Pipeline Decorator Patterns
Streamlit caching **is** applied to the heavy loaders: `@st.cache_data` decorates `load_master_excel()`, `load_fol_matrix()`, `load_historical_data()`, etc. `run_selection_pipeline()` is **not** cached (it takes many scalar args + DataFrames; caching is impractical and it only runs on explicit button press anyway).

### File I/O Optimization — partially done
- `load_master_excel()` now reads the workbook **once** with the `python-calamine` engine. Previously a header-probe loop called `pd.read_excel` up to 11× (each call re-parsed the whole ~200 MB file with openpyxl). Calamine is ~5–20× faster than openpyxl; there is an automatic fallback to openpyxl if calamine is missing.
- In the Multi-Period tab, the wide weight-matrix build was vectorized (`build_wide_matrix()`, ~239× faster) and the two Excel exports are now generated once after a run and cached in `session_state` (previously rebuilt on every widget interaction).
- **Still open**: Parquet caching of the parsed master (could cut cold-start reload to <1s across app restarts). Not implemented per user decision ("wir lassen es erstmal so wie es ist").

---

## 9. Communication Style with User (Nico)

- **Language**: Primary German for casual discussion, English for formal deliverables (ticket descriptions, methodology paper)
- **Approach**: User asks for clarifying questions BEFORE Claude jumps to coding. Claude should ask 1-3 focused questions when there are open methodological decisions, then implement.
- **Iteration style**: Many small iterations preferred over one large refactor. User reviews each step.
- **Critical**: Never silently change methodology. Always surface trade-offs and let user decide.
- **Verification**: Code changes are tested against the 03-2026 snapshot (and now the Master File 2026-05-20 period) before being declared complete. Run actual pipeline, check expected outputs.

### Phrases the user often uses
- "kannst du das prüfen" = please check/verify
- "wir lassen es so" = leave as-is, decision final
- "lass uns step-by-step" = walk through one item at a time
- "wir kommen später darauf zurück" = backlog item, defer

---

## 10. Quick Start for Cursor

If you're continuing work in Cursor on this codebase:

1. Read this file (`HANDOVER.md`) completely first.
2. Familiarize with `naroix_benchmark.py` and `pipeline_core.py` structure.
3. Verify local setup (Windows): `.\venv\Scripts\Activate.ps1`, then `streamlit run naroix_benchmark.py`. First-time only: `python -m venv venv` + `pip install -r requirements.txt`. See `README.md`. No auth/secrets needed.
4. Maintenance Buffer over time (old Priority 1) is **done**. Likely next topics: **Size Buffer** (Large↔Mid / Mid↔Small, MSCI §3.1.5.1), Length-of-Trading filter, turnover statistics, or the `pipeline_core.py` extraction. Ask which before starting.
5. **DO NOT** make breaking methodology changes without explicit confirmation. The decisions in Section 2 are deliberate and were reached over multi-week discussions.

### Files in current state
- `naroix_benchmark.py` — main Streamlit app, contains ALL logic (universe, pipeline, Helvetica, all tabs)
- `README.md` — Windows local-run instructions
- `requirements.txt` — includes `python-calamine`
- `pipeline_core.py` — **does not exist** (planned extraction, see §1 / §6)
- Multi-period Master File (user-uploaded via UI): `NaroIX_..._Master_..._WITH_FLOAT.xlsx`, ~458 cols × 52,764 rows, "Float MCap" naming

### Recent fixes
**This session (2026-06-04):**
- Removed GitHub-OAuth auth (`auth.py` deleted, no secrets required); app runs open on localhost
- Replaced `use_container_width=True` → `width='stretch'` (28×, Streamlit deprecation)
- Fixed Arrow serialization warning in the GIMI index-products table (DM/EM mixed int/"—" cast to str)
- `load_master_excel`: single read + `python-calamine` engine (was up to 11× openpyxl passes)
- Multi-Period tab: vectorized `build_wide_matrix()` (~239×), build/cache exports once in `session_state`, added Country Breakdown (Land×Periode matrix + GIMI-style per-period table)
- Added `README.md`

**Earlier (claude.ai, last ~2 weeks):**
- Float PCT format auto-detection in Master Loader
- Selection Dates updated to include 2026-05-20
- Helvetica migrated to Variante B (both Primary and Secondary listings)
- Tiebreaker sort key added everywhere
- Real Estate Universe (incl. Micro Cap) added as separate section
- Consolidated Helvetica Excel export at end of tab

---

*End of Handover Document. Last substantive update: 2026-06-04.*
