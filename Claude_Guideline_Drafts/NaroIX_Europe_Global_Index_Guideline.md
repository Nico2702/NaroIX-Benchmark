# NaroIX Europe Markets & Global Markets Index — Selection Methodology

> **Purpose of this document.** A complete, self-contained description of how the
> **NaroIX Europe Markets Index** (code `NX-EU-LM`) and the **NaroIX Global Markets
> Index** (code `NX-GM-LM`) are constructed, so that the formal Index Guideline can be
> written from it and the selection can be reproduced independently. Both indices use
> the **identical** selection process; they differ **only** in the final universe scope
> (Step 8). Methodology basis: MSCI-GIMI-style, point-in-time. Status: 2026-06-15.
>
> *Companion docs in this repo: `SELECTION.md` (process), `INDEX_SERIES.md` (full product
> catalogue), `HANDOVER.md` (design decisions). Where they differ, this document governs
> for these two products.*

---

## 0. The two indices

| | NaroIX Europe Markets Index | NaroIX Global Markets Index |
|---|---|---|
| Code | `NX-EU-LM` | `NX-GM-LM` |
| Universe scope | Developed Markets **listed in Europe** | Developed **+** Emerging Markets (global) |
| Size segments | **Standard** = Large + Mid Cap | **Standard** = Large + Mid Cap |
| Comparable to | MSCI Europe | MSCI ACWI |
| Weighting | Free-float + foreign-ownership-adjusted market cap | same |

Both are **Standard** (Large + Mid Cap) indices. Frontier Markets (FM) are always
excluded. "ACWI"/"World" are MSCI trademarks and are deliberately **not** used.

---

## 1. Required input data (per security, per selection date)

Point-in-time values **as of each selection date** (the index is rebalanced per date):

| Field | Use |
|---|---|
| Security ID (Symbol / Exchange Ticker) | identity, display |
| ISIN | membership / matching key |
| Entity ID (company) | company-level identity (multi-class grouping) |
| Listing (Primary / Secondary) | EUMSS calibration basis |
| Sec Type (SHARE / NVDR / …) | Thailand handling |
| Exchange Country Name | listing venue (China A-share & Europe scope) |
| Country of Incorporation, Country of Risk | classification mapping |
| FactSet Econ Sector, FactSet Industry | foreign-ownership lookup |
| **Total MCap** | size ranking, EUMSS, segmentation sort |
| **Free Float MCap** | investable size base |
| **Free Float %** | foreign-ownership inclusion factor |
| Closing Price | exclusions, listing-status proxy |
| 3M / 6M / 12M ADTV (avg. daily traded value, USD) | liquidity screen |
| Listing Status (0 active / 1 delisted) | exclude delisted |

> All monetary values in **USD**. "Free Float %" is a decimal 0–1.

### Reference data
- **FOL Matrix** (`NaroIX_FOL_Master_Aggregated_v1.9.yaml`) — point-in-time foreign-ownership
  limits by country × FactSet industry × year (12 jurisdictions; see §3.3).
- **Country classification** (Developed / Emerging / Frontier) **per selection date**.
- **Selection-dates calendar** (rebalancing dates).
- **China Inclusion Factor** per date (currently ≈ 20%).
- *(optional)* **Ineligible list** — ISINs excluded for a stated period (e.g. sanctions).

---

## 2. Selection process — overview

```
Raw securities (per selection date)
  → 1. Universe construction (listings, exclusions)
  → 2. Classification (DM / EM / FM)            → drop FM & unclassified
  → 3. Foreign Ownership → Inclusion Factor (IF)
  → 4. Investable size  Adj_FF_MCap = Free Float MCap × IF
  → 5. EUMSS size calibration & filter          → below = Micro (out)
  → 6. Liquidity screen                          → fail = excluded entirely (Variante A)
  → 7. Per-country size segmentation             → Large / Mid / Small
  → 8. Index scoping + weighting                 → NX-EU-LM / NX-GM-LM (Large+Mid)
```

Each step is detailed below.

---

## 3. Selection process — detail

### Step 1 — Universe construction
- **Both listings flow through (Variante B).** Primary *and* Secondary listings of a company
  are treated as **separate securities** and pass every filter individually (consistent with
  MSCI "applied at individual security level"). Both can be index members (e.g. Roche common +
  Genussschein). They are re-aggregated only for company-level counts, never for weighting.
- **Thailand (mode "SHARE → NVDR"):** qualify the company on its local **SHARE** line
  (Free Float MCap, FF%), but represent it in the index by its **NVDR** (the foreign-investable
  line); the SHARE's FF MCap / FF% / Total MCap / price are transferred to the NVDR.
- **Exclusions** (a security is dropped if any apply):
  - Free Float MCap ≤ 0
  - Closing Price ≥ **20,000** (price filter, configurable)
  - Hong-Kong-listed line trading in CNY (HK-CNY)
  - Country of Risk = `@NA`
  - NAICS = open-end investment fund
  - Exchange = `Euro MTF` / `@NA`
  - Name contains `ETF`, `SICAV`, or `%`
  - Listing Status = 1 (delisted) — *disable for historical snapshots where the name was still
    trading at that date.*

### Step 2 — Classification (DM / EM / FM)
- **Mapping Country rule:** if `Exchange Country == Country of Incorporation` → use Country of
  Incorporation, else use **Country of Risk**.
- Map the Mapping Country to **Developed / Emerging / Frontier** using the point-in-time
  classification table for that selection date.
- **Drop** Frontier Markets and any security whose Mapping Country has no classification at
  that date.

### Step 3 — Foreign Ownership Limit → Inclusion Factor (IF)
The **Foreign Inclusion Factor** reflects the share of the free float actually accessible to
foreign investors:

```
IF = min( 1 , FOL / Free Float % )          (when Free Float % > 0, else IF = 1)
```

- **FOL** (Foreign Ownership Limit) is looked up in the FOL matrix by **(Mapping Country,
  FactSet Industry, year)** with this fallback chain:
  1. exact industry match → 2. normalized industry match (whitespace/case-tolerant) →
  3. strictest `fol_automatic` within the sector → 4. country default → 5. 1.0 (no limit).
  The `fol_automatic` (no-approval) limit is used — the conservative, mechanically-investable level.
- **Overrides:**
  - **China A-shares** (Exchange Country = China) → IF = **China Inclusion Factor** (≈ 20%),
    regardless of FOL (Stock-Connect partial inclusion). China H-shares (listed Hong Kong) are
    unrestricted (IF = 1).
  - **Thailand NVDR** → IF = 1 (the NVDR is the foreign-investable vehicle).
  - **pre-investable** market/year (e.g. Saudi Arabia 2014) → IF = 0.
- **Interpretation:** if FOL ≥ Free Float % the limit does not bind → IF = 1; if FOL < Free Float %
  it binds → IF = FOL / Free Float % < 1. *Example:* FAB (UAE bank) FOL 40 %, free float 44.2 %
  → IF = 0.40/0.442 = 0.906. QNB (Qatar) FOL 49 %, free float 48.3 % → IF = 1 (does not bind).

### Step 4 — Investable size
```
Adj_FF_MCap = Free Float MCap × IF
```
This **foreign-ownership-adjusted free-float market cap** is the basis for segmentation and
weighting. A security with **IF = 0 → Adj_FF_MCap = 0** is **not investable**: it is set to
segment **"Non-Investable"** and excluded from every index (kept visible for audit only).

### Step 5 — EUMSS size calibration & filter
EUMSS = the global minimum-size standard, **calibrated once** and applied to all markets.
- **Calibration basis:** Developed-Markets **Primary** listings only (avoids double-counting
  multi-class companies). Sort by Total MCap descending; cumulate Free Float MCap as a % of the
  DM-Primary total. The **Total MCap at the 99 % cumulative-coverage point** = `EUMSS_full`.
- `EUMSS_ff = EUMSS_full × 50 %` (the EUMSS FF ratio).
- A security **passes EUMSS** (is "investable size") iff:
  ```
  Total MCap ≥ EUMSS_full   AND   Free Float MCap ≥ EUMSS_ff   AND   Free Float % ≥ 10 %
  ```
- Securities failing EUMSS are labelled **Micro Cap** and are **not** index-eligible.

### Step 6 — Liquidity screen (Variante A)
Applied to the EUMSS-passing set, differentiated by classification:

| | 3-month ADTV | 6-month ADTV | ATVR (annualized traded value ratio) |
|---|---|---|---|
| Developed | ≥ **$2,000,000** | ≥ **$2,000,000** | ≥ 0 % (off by default) |
| Emerging | ≥ **$1,000,000** | ≥ **$1,000,000** | ≥ 0 % (off by default) |

- **Variante A (decisive):** a security that passes EUMSS but **fails liquidity is excluded
  entirely** — it is **not** demoted to Small/Micro and is in **no** index. The single liquidity
  bar therefore applies to **all** size tiers.

### Step 7 — Per-country size segmentation (coverage waterfall)
Computed **per Mapping Country over that country's entire investable, liquid universe**
(all sectors) — *not* relative to Europe or to any sub-index.
- Sort the country's securities by **Total MCap** descending.
- For each security, `_c_before` = cumulative **Adj_FF_MCap** of all **larger** securities of the
  country, as a % of the country's total Adj_FF_MCap (the security's own float is **not yet**
  counted — "straddle rule").
- Assign the size segment:

  | `_c_before` | Segment |
  |---|---|
  | < **70 %** | Large Cap |
  | 70 % – < **85 %** | Mid Cap |
  | ≥ **85 %** | Small Cap |

  (Securities that failed EUMSS are **Micro Cap**; IF = 0 are **Non-Investable**. Neither is
  index-eligible.)
- **Consequence to communicate:** a security is "Large" if it is among the top-70%-coverage of
  its **whole home market**, across all sectors — segmentation is country-relative, not
  index-relative.

### Step 8 — Index scoping & weighting *(the only step that differs between the two indices)*

**Scope (Standard = Large + Mid Cap of the relevant universe):**
- **NX-EU-LM (Europe Markets):** Classification = **DM** **and** Mapping Country ∈ the European
  country list (§4) **and** Segment ∈ {Large, Mid}.
- **NX-GM-LM (Global Markets):** Classification ∈ {**DM**, **EM**} **and** Segment ∈ {Large, Mid}.

**Weighting** (identical for both):
```
Index_Weight(i) = Adj_FF_MCap(i) / Σ Adj_FF_MCap (over the product's members) × 100
```
normalized to sum to exactly 100.0000 % (rounding remainder assigned to the largest constituent).

---

## 4. Parameters (current defaults)

| Parameter | Value | Where |
|---|---|---|
| Large/Mid cut | **70 %** coverage | Step 7 |
| Mid/Small cut | **85 %** coverage | Step 7 |
| EUMSS calibration coverage | **99 %** | Step 5 |
| EUMSS FF ratio | **50 %** | Step 5 |
| Minimum Free Float % | **10 %** | Step 5 |
| Liquidity ADTV — DM (3M & 6M) | **$2,000,000** | Step 6 |
| Liquidity ADTV — EM (3M & 6M) | **$1,000,000** | Step 6 |
| Liquidity ATVR — DM / EM | 0 % / 0 % (off) | Step 6 |
| China Inclusion Factor | **≈ 20 %** (per date) | Step 3 |
| Max closing price | **20,000** | Step 1 |

### Optional buffers (turnover control — applied across rebalancings)
| Buffer | Default | Effect |
|---|---|---|
| **Maintenance buffer** (membership) | Min FF **7.5 %**, ADTV DM **$1.0M** / EM **$0.5M**, coverage **90 %** | Current constituents face *softer* Step-5/6/7 thresholds, so they aren't dropped on marginal misses. |
| **Size buffer** (segment hysteresis) | **±5 pp** around the 70 % and 85 % cuts | Incumbents keep their size segment within the band instead of flipping each rebalance. The Small↔Micro lower bound stays governed by EUMSS. |

Both are optional and, when enabled, apply only from the **second** rebalancing onward (they need
a prior-period membership). The seed period uses plain cut-offs.

---

## 5. Rebalancing & point-in-time logic
- The index is rebalanced on each **selection date**; every value (MCap, float, FOL, classification,
  liquidity) is the point-in-time value **as of that date**.
- **One pipeline run per date** produces the full segmented universe; both NX-EU-LM and NX-GM-LM are
  consistent **slices** of that one run, so a security has exactly **one** size class across all
  NaroIX products, and `NX-GM-* = NX-DM-* + NX-EM-*` holds by construction.
- **Incumbents** for the buffers = the prior period's investable universe (Large + Mid + Small).

---

## 6. Country scope

**European countries** (for NX-EU-LM; the Developed-Markets requirement removes the currently-EM
ones such as Greece/Hungary/Czechia automatically):

> Austria, Belgium, Denmark, Finland, France, Germany, Ireland, Italy, Netherlands, Norway,
> Portugal, Spain, Sweden, Switzerland, United Kingdom, Poland *(DM from 2024)*, Greece, Hungary,
> Czech Republic.

**Developed / Emerging / Frontier** assignment comes from the point-in-time classification table
(it changes over time — e.g. country promotions/demotions are respected per selection date).
Frontier is always out of scope.

---

## 7. Output / index composition
Per selection date, each index delivers its constituents with at least:
`ISIN · Name · Mapping Country · Classification · Segment · Free Float % · Total MCap · Free Float
MCap · FOL · IF · Adj_FF_MCap · Index_Weight`. Weights sum to 100 %.

---

## 8. Glossary
- **Free Float** — shares available to the general investing public (excludes strategic/locked
  holdings).
- **FOL** — Foreign Ownership Limit: maximum % of a company foreigners may own.
- **IF / Foreign Inclusion Factor** — `min(1, FOL / Free Float %)`; the foreign-accessible
  fraction of the free float.
- **Adj_FF_MCap** — Free Float MCap × IF; the investable size, basis for segmentation & weighting.
- **EUMSS** — the calibrated global minimum-size standard (full + FF thresholds).
- **Coverage / `_c_before`** — cumulative Adj_FF_MCap of larger securities of the same country, as
  % of the country total (straddle rule).
- **Standard** — Large + Mid Cap (the `-LM` products).
- **Variante A** — EUMSS-pass but liquidity-fail ⇒ excluded entirely (not Small, not Micro).
- **Variante B** — Primary and Secondary listings handled as separate securities.

---

## Appendix — worked examples

**Inclusion Factor**
- *First Abu Dhabi Bank (UAE):* FOL 0.40, Free Float % 0.442 → `min(1, 0.40/0.442)` = **0.906**;
  Adj_FF_MCap = Free Float MCap × 0.906.
- *Qatar National Bank:* FOL 0.49, Free Float % 0.483 → `min(1, 0.49/0.483)` = **1.000** (limit
  does not bind, since the float is below the cap) → Adj_FF_MCap = Free Float MCap.

**Segmentation (per-country coverage)**
- A Dutch security with `_c_before` = 0 % (largest in the Netherlands) → **Large Cap**; a Dutch
  security at `_c_before` = 88 % → **Small Cap** (hence not in the Standard / `-LM` index).

**Scope difference (only Step 8)**
- A large German bank: DM, Mapping Country Germany ∈ Europe, Large → **in both** NX-EU-LM and
  NX-GM-LM.
- A large Brazilian miner: EM, Large → **in NX-GM-LM only** (not European).
