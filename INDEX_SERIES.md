# NaroIX Index Series

> The product catalogue for the NaroIX benchmark family. "ACWI" / "World" are MSCI brands,
> so NaroIX ships its own series with generic, trademark-safe names (Global / Developed /
> Emerging / Europe Markets). All products are derived from one pipeline — see `SELECTION.md`
> for the construction process and `HANDOVER.md` §2 for the methodology decisions.
>
> Single source of truth in code: the `INDEX_SERIES` constant + `build_index()` helper in
> `pipeline_core.py`. Last updated: 2026-06-11.

---

## 1. The products (20)

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
| **NX-US-500** | NaroIX US 500 Index | US | Top 500 | by Total MCap | S&P 500 |
| **NX-US-T100** | NaroIX US Tech 100 Index | US, Tech industries | Top 100 | by Total MCap | Nasdaq-100 |
| NX-US-T | NaroIX US Tech Index | US, Tech industries | Large + Mid + Small | — | — |
| **NX-WL-100** | NaroIX World 100 Index | GM (DM+EM) | Top 100 | by Total MCap | FTSE All-World 100 |

The **Standard** products (Large + Mid, suffix `-LM`) are the regional flagships: **NX-DM-LM**, **NX-EM-LM**, **NX-GM-LM**, **NX-EU-LM**.

### Thematic / fixed-count products (added 2026-06-11)

The last four are **not** coverage-segmented; they are **fixed-count / filtered** baskets drawn from the same pipeline output:
- **NX-US-500** — the 500 largest US-listed **companies** by **Total MCap** (US = **Exchange Country** United States — includes US-listed foreign-domiciled names like ARM/Linde/Chubb/NXP, closer to the real S&P/Nasdaq membership). **Count is at the company level (Entity ID); all share lines of the selected companies are then included** (S&P/Solactive step 6) → 500 companies ≈ **505 securities** (Alphabet A+C, Fox A+B, HEICO, Lennar, Liberty Media …).
- **NX-US-T / NX-US-T100** — US **Technology** via *FactSet Industry* (Kern + Internet Retail: Internet Software/Services, Semiconductors, Packaged Software, Telecom Equipment, IT Services, Computer Peripherals/Processing Hardware, Electronic Components/Equipment/Production Equipment, Data Processing, Internet Retail). **Aerospace & Defense is deliberately excluded** (it sits in the Electronic Technology *sector* but is not tech). `NX-US-T` = **all** US tech Large+Mid+Small (no fixed count, ~367 on 2026-05-20); `NX-US-T100` = its **top 100 by Total MCap** (a strict subset of NX-US-T).
- **NX-WL-100** — the 100 largest global (DM+EM) constituents by **Total MCap**.
- **Selection is by Total MCap; weighting is by Adj-FF-MCap** (like every other product). Amazon/Netflix are captured (Internet Retail / Internet Software/Services); Tesla is **not** (FactSet "Motor Vehicles" — would pull in GM/Ford), so a rules-based Nasdaq-100 clone is intentionally approximate.

**Company-level count.** `top_n` counts **companies** (Entity ID), not share lines; once a company is in, *all* its listings come along. So `top_n=500` → exactly 500 companies, ~505 securities. Ranking is by Total MCap (company-wide, identical across a company's lines).

**Rank-band buffer (turnover control, Solactive-GBS style).** The fixed-count products (`NX-US-500`, `NX-US-T100`, `NX-WL-100`) carry `buffer_hard` / `buffer_exit` ranks (in **company** ranks): top `buffer_hard` companies are hard-included, current incumbent companies ranked up to `buffer_exit` fill the remaining slots to `top_n`, then the highest-ranked new companies top it up. US 500 = **425 / 600** (Solactive GBS US 500 1:1); the 100-products = **85 / 120** (proportional). Active only in the **Multi-Period** run (needs prior-period membership) and only when the Buffer toggle is on; the seed period and the single-period GIMI table use a plain top-N cut. Empirically (NX-US-500, consecutive periods) it cut turnover **54 → 14 name changes (~−74%)**. `NX-US-T` (variable count) has no rank band — it inherits the standard coverage/maintenance buffers.

## 2. Naming & code scheme

- **Region**: `DM` Developed · `EM` Emerging · `GM` Global (= DM + EM) · `EU` Europe (DM ∩ European countries) · `US` United States (**Exchange Country** = US-listed). Note: EU uses *Mapping* Country, US uses *Exchange* Country (listing-based, matches S&P/Nasdaq).
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

- Defined once as `INDEX_SERIES` in **`pipeline_core.py`** (list of `{code, name, region, segments, coverage, vs}`, plus optional `industries` / `top_n` for thematic products) with `INDEX_BY_CODE` / `INDEX_BY_NAME` lookups.
- `build_index(gm_complete, region, segments, industries=None, top_n=None, rank_col="Total MCap Y2025", incumbents_isin=None, buffer_hard=None, buffer_exit=None)` scopes one pipeline result to a product (filter by region + segments [+ industries], optional top-N by Total MCap with an optional rank-band buffer, re-normalise weights to 100%). Single source of truth for **all** consumers (GIMI-tab product table, Multi-Period tab).
- **Multi-Period (Option Y):** the pipeline runs **once per period** (global incumbent/buffer state = prior period's investable universe L+M+S); every selected product is a consistent `build_index` slice of that one run. This guarantees a stock has exactly **one** size class across all products and is far faster than per-product runs. See `SELECTION.md` §2/§5.
- Internal keys/sheet names use the **code** (stable, short); UI labels show the **name**.

---

*See also: `SELECTION.md` (selection process), `HANDOVER.md` §2 (methodology decisions), §2.11 (liquidity exclusion).*
