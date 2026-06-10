# NaroIX Index Series

> The product catalogue for the NaroIX benchmark family. "ACWI" / "World" are MSCI brands,
> so NaroIX ships its own series with generic, trademark-safe names (Global / Developed /
> Emerging / Europe Markets). All products are derived from one pipeline — see `SELECTION.md`
> for the construction process and `HANDOVER.md` §2 for the methodology decisions.
>
> Single source of truth in code: the `INDEX_SERIES` constant + `build_index()` helper in
> `naroix_benchmark.py`. Last updated: 2026-06-09.

---

## 1. The products (16)

Coverage = cumulative Adj-FF-MCap coverage band, **per country** (Option B, HANDOVER §2.2). Approximate (per-country + liquidity exclusion mean it's never exact).

| Code | Index | Region | Size segments | Coverage | Comparable to |
|---|---|---|---|---|---|
| **NX-EU-LM** | NaroIX Europe Markets Index | EU (DM ∩ Europe) | Large + Mid | 0–85% | MSCI Europe |
| **NX-DM-LM** | NaroIX Developed Markets Index | DM | Large + Mid | 0–85% | MSCI World |
| NX-DM-L | NaroIX Developed Markets Large Cap Index | DM | Large | 0–70% | MSCI World Large Cap |
| NX-DM-M | NaroIX Developed Markets Mid Cap Index | DM | Mid | 70–85% | MSCI World Mid Cap |
| NX-DM-S | NaroIX Developed Markets Small Cap Index | DM | Small | 85–99% | MSCI World Small Cap |
| NX-DM-AC | NaroIX Developed Markets All Cap Index | DM | Large + Mid + Small | 0–99% | MSCI World IMI |
| **NX-EM-LM** | NaroIX Emerging Markets Index | EM | Large + Mid | 0–85% | MSCI EM |
| NX-EM-L | NaroIX Emerging Markets Large Cap Index | EM | Large | 0–70% | MSCI EM Large Cap |
| NX-EM-M | NaroIX Emerging Markets Mid Cap Index | EM | Mid | 70–85% | MSCI EM Mid Cap |
| NX-EM-S | NaroIX Emerging Markets Small Cap Index | EM | Small | 85–99% | MSCI EM Small Cap |
| NX-EM-AC | NaroIX Emerging Markets All Cap Index | EM | Large + Mid + Small | 0–99% | MSCI EM IMI |
| **NX-GM-LM** | NaroIX Global Markets Index | GM (DM+EM) | Large + Mid | 0–85% | MSCI ACWI |
| NX-GM-L | NaroIX Global Markets Large Cap Index | GM | Large | 0–70% | MSCI ACWI Large Cap |
| NX-GM-M | NaroIX Global Markets Mid Cap Index | GM | Mid | 70–85% | MSCI ACWI Mid Cap |
| NX-GM-S | NaroIX Global Markets Small Cap Index | GM | Small | 85–99% | MSCI ACWI Small Cap |
| NX-GM-AC | NaroIX Global Markets All Cap Index | GM | Large + Mid + Small | 0–99% | MSCI ACWI IMI |

The **Standard** products (Large + Mid, suffix `-LM`) are the flagships: **NX-DM-LM**, **NX-EM-LM**, **NX-GM-LM**, **NX-EU-LM**.

## 2. Naming & code scheme

- **Region**: `DM` Developed · `EM` Emerging · `GM` Global (= DM + EM) · `EU` Europe (DM ∩ European countries).
- **Size suffix**: `-LM` Standard (Large+Mid) · `-L` Large · `-M` Mid · `-S` Small · `-AC` All Cap (Large+Mid+Small).
- **No MSCI terms**: "Global Markets" not "ACWI", "All Cap" not "IMI", "Developed/Emerging Markets" as generic descriptors. The `NaroIX` prefix is the brand.

## 3. Structure — 9 atomic sleeves, the rest are aggregations

Only **9 atomic region×size sleeves** are fundamental: {DM, EM} × {Large, Mid, Small}. Everything else is an aggregation:
- **Standard** = Large + Mid · **All Cap** = Large + Mid + Small
- **GM** = DM + EM (every size level) · **EU** = the European subset of DM

These identities hold exactly by construction (verified on real data): `NX-GM-* = NX-DM-* + NX-EM-*`, `NX-*-AC = -L + -M + -S`, `NX-*-LM = -L + -M`, `NX-EU-LM ⊆ NX-DM-LM`.

## 4. Scope rules

- **Frontier Markets (FM) are always excluded.** Global = DM + EM only (like MSCI ACWI). FM is out of scope (possible future addition).
- **Europe** is currently only shipped as Standard (`NX-EU-LM`). The full Europe family (Large/Mid/Small/All Cap) is a deferred addition — same template when needed. Country-level indices (Switzerland, Germany) and the custom Helvetica index are separate and not part of this series.
- **Liquidity-fails are excluded entirely** (Variante A, HANDOVER §2.11) — they are not in any product, including All Cap.

## 5. How it's computed

- Defined once as `INDEX_SERIES` (list of `{code, name, region, segments, coverage, vs}`) with `INDEX_BY_CODE` / `INDEX_BY_NAME` lookups.
- `build_index(gm_complete, region, segments)` scopes one pipeline result to a product (filter by region + segments, re-normalise weights to 100%). Single source of truth for **all** consumers (GIMI-tab product table, Multi-Period tab).
- **Multi-Period (Option Y):** the pipeline runs **once per period** (global incumbent/buffer state = prior period's investable universe L+M+S); every selected product is a consistent `build_index` slice of that one run. This guarantees a stock has exactly **one** size class across all products and is far faster than per-product runs. See `SELECTION.md` §2/§5.
- Internal keys/sheet names use the **code** (stable, short); UI labels show the **name**.

---

*See also: `SELECTION.md` (selection process), `HANDOVER.md` §2 (methodology decisions), §2.11 (liquidity exclusion).*
