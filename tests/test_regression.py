"""Regression / determinism tests for the NaroIX selection engine.

Locks in the invariants established during the methodology audit so that future
changes that break them fail loudly. Two tiers:

  * PURE tests   - operate on synthetic data, always runnable (no master file).
  * INTEGRATION  - need the ~165 MB master file + repo data; skipped cleanly if
                   absent (e.g. fresh checkout / CI without data).

Run:  ./venv/Scripts/python.exe tests/test_regression.py
Exit code 0 = all run tests passed; 1 = at least one failure.
(Plain-assert style, no pytest dependency — but functions are pytest-compatible.)
"""
import sys
import os
import glob

# ── Streamlit stub (engine imports must not require a running Streamlit) ──────
class _Stub:
    def __init__(self): self.session_state = {}; self.secrets = {}
    def cache_data(self, *a, **k):
        if len(a) == 1 and callable(a[0]) and not k:
            return a[0]
        return lambda fn: fn
    def __getattr__(self, n): return lambda *a, **k: None

sys.modules.setdefault("streamlit", _Stub())

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)  # repo-relative data files (FOL yaml, classification, master)

import numpy as np
import pandas as pd
import pipeline_core as C

# ── Tiny test harness ─────────────────────────────────────────────────────────
_RESULTS = []  # (status, name, detail)

def check(name, cond, detail=""):
    _RESULTS.append((("PASS" if cond else "FAIL"), name, "" if cond else detail))

def skip(name, detail=""):
    _RESULTS.append(("SKIP", name, detail))


# ══════════════════════════════════════════════════════════════════════════════
# PURE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_index_series_integrity():
    codes = [ix["code"] for ix in C.INDEX_SERIES]
    check("index_series: 16 products", len(C.INDEX_SERIES) == 16, f"got {len(C.INDEX_SERIES)}")
    check("index_series: codes unique", len(set(codes)) == len(codes), "duplicate code")
    check("index_series: BY_CODE consistent", set(C.INDEX_BY_CODE) == set(codes))
    valid = {"Large Cap", "Mid Cap", "Small Cap"}
    seg_ok = all(set(ix["segments"]) <= valid for ix in C.INDEX_SERIES)
    check("index_series: segments subset of L/M/S", seg_ok)
    regions = {ix["region"] for ix in C.INDEX_SERIES}
    check("index_series: regions in {DM,EM,GM,EU}", regions <= {"DM", "EM", "GM", "EU"}, str(regions))


def test_clean_export_cols():
    df = pd.DataFrame({"Total MCap Y2025": [1], "Free Float MCap Y2025": [2],
                       "3M ADTV Y2025": [3], "Adj_FF_MCap": [4], "Index_Weight": [5]})
    out = list(C.clean_export_cols(df).columns)
    check("clean_export_cols: renames Y2025", "Total MCap" in out and "Free Float MCap" in out and "3M ADTV" in out)
    check("clean_export_cols: leaves others", "Adj_FF_MCap" in out and "Index_Weight" in out)
    check("clean_export_cols: no Y2025 remains", not any("Y2025" in c for c in out))


def test_excel_no_y2025_leak():
    import io, openpyxl
    df = pd.DataFrame({"Total MCap Y2025": [1.0], "Free Float MCap Y2025": [2.0], "Adj_FF_MCap": [3.0]})
    for label, blob in [("to_excel_multi", C.to_excel_multi({"S": df})),
                        ("to_excel_multi+one-sheet", C.to_excel_multi({"A": df, "B": df}))]:
        wb = openpyxl.load_workbook(io.BytesIO(blob))
        leak = any("Y2025" in str(c.value) for ws in wb.worksheets for c in ws[1])
        check(f"export: no Y2025 header ({label})", not leak)


def test_norm_fol_key():
    a = C._norm_fol_key("Consumer Services", "Hotels/Resorts/Cruise lines")
    b = C._norm_fol_key("Consumer Services", "Hotels/Resorts/Cruiselines")
    check("norm_fol_key: 'Cruise lines' == 'Cruiselines'", a == b, f"{a} != {b}")
    c = C._norm_fol_key("Consumer Services", "Casinos/Gaming")
    check("norm_fol_key: distinct industries stay distinct", a != c)


def test_size_segment():
    valid = {"Large Cap", "Mid Cap", "Small Cap"}
    # newcomer -> plain cuts (bw irrelevant)
    check("size_segment: newcomer <70 -> Large", C._size_segment(None, 50) == "Large Cap")
    check("size_segment: newcomer 70-85 -> Mid", C._size_segment(None, 80) == "Mid Cap")
    check("size_segment: newcomer >=85 -> Small", C._size_segment(None, 90) == "Small Cap")
    # hysteresis: a Large incumbent at 73% (within 70+5 band) stays Large
    check("size_segment: Large incumbent sticky in band", C._size_segment("Large Cap", 73) == "Large Cap")
    # but a newcomer at 73% would be Mid -> proves the buffer changed the outcome
    check("size_segment: newcomer 73 -> Mid (contrast)", C._size_segment(None, 73) == "Mid Cap")
    # vocabulary always valid
    outs = {C._size_segment(p, cb) for p in (None, "Large Cap", "Mid Cap", "Small Cap")
            for cb in (10, 67, 72, 80, 88, 95)}
    check("size_segment: vocabulary valid", outs <= valid, str(outs - valid))


def test_normalize_index_weight():
    df = pd.DataFrame({"Adj_FF_MCap": [100.0, 50.0, 25.0, 25.0]})
    out = C.normalize_index_weight(df)
    check("normalize: sums to exactly 100", round(out["Index_Weight"].sum(), 6) == 100.0,
          str(out["Index_Weight"].sum()))
    z = C.normalize_index_weight(pd.DataFrame({"Adj_FF_MCap": [0.0, 0.0]}))
    check("normalize: all-zero -> 0 weights, no crash", (z["Index_Weight"] == 0).all())
    e = C.normalize_index_weight(pd.DataFrame({"Adj_FF_MCap": []}))
    check("normalize: empty -> no crash", len(e) == 0)


def _synthetic_gm_complete():
    rows = [
        # ISIN, Classification, Mapping Country, Segment_New, Adj_FF_MCap
        ("D1", "DM", "GERMANY", "Large Cap", 1000.0),
        ("D2", "DM", "GERMANY", "Mid Cap",    400.0),
        ("D3", "DM", "FRANCE",  "Small Cap",  100.0),
        ("D4", "DM", "JAPAN",   "Large Cap",  800.0),   # DM non-Europe
        ("E1", "EM", "BRAZIL",  "Large Cap",  600.0),
        ("E2", "EM", "INDIA",   "Mid Cap",    300.0),
        ("Z1", "EM", "QATAR",   "Non-Investable", 0.0),  # carved out
        ("M1", "DM", "GERMANY", "Micro Cap",   10.0),    # not in any index
    ]
    return pd.DataFrame(rows, columns=["ISIN", "Classification", "Mapping Country",
                                       "Segment_New", "Adj_FF_MCap"])


def test_build_index():
    gm = _synthetic_gm_complete()
    std = C.build_index(gm, "GM", ["Large Cap", "Mid Cap"])
    check("build_index: GM Standard sums 100", round(std["Index_Weight"].sum(), 6) == 100.0)
    check("build_index: excludes Small/Micro/Non-Investable",
          set(std["Segment_New"]) <= {"Large Cap", "Mid Cap"})
    # D1,D2,D4 (DM L/M) + E1,E2 (EM L/M) = 5; D3 Small, Z1 Non-Inv, M1 Micro excluded
    check("build_index: GM Standard count", len(std) == 5, f"got {len(std)}")
    eu = C.build_index(gm, "EU", ["Large Cap", "Mid Cap"])
    check("build_index: EU only DM-Europe", set(eu["Mapping Country"]) <= C.EUROPE_COUNTRIES)
    check("build_index: EU excludes Japan(DM non-EU)", "JAPAN" not in set(eu["Mapping Country"]))
    ac = C.build_index(gm, "GM", ["Large Cap", "Mid Cap", "Small Cap"])
    check("build_index: All-Cap has no Non-Investable", "Non-Investable" not in set(ac["Segment_New"]))
    check("build_index: All-Cap has no Micro", "Micro Cap" not in set(ac["Segment_New"]))


def test_validate_factset_data():
    n = 5
    clean = pd.DataFrame({
        "Free Float MCap Y2025": [100.0] * n, "Total MCap Y2025": [200.0] * n,
        "Free Float Percent": [0.5] * n, "Closing Price": [10.0] * n,
        "3M ADTV Y2025": [1e6] * n, "6M ADTV Y2025": [1e6] * n,
        "Listing": ["Primary"] * n, "Listing Status": ["0"] * n,
    })
    an = C.validate_factset_data(clean)
    check("validate: clean data -> no error anomalies", not any(s == "error" for s, _, _ in an), str(an))
    bad = clean.copy(); bad.loc[0, "Free Float Percent"] = 0.0
    an2 = C.validate_factset_data(bad)
    check("validate: FF>0 & FF%=0 -> error flagged", any(s == "error" for s, _, _ in an2))


def _minimal_universe_row(symbol, listing_status):
    return {
        "Symbol": symbol, "ISIN": symbol, "Name": symbol, "Sec Type": "SHARE",
        "Listing": "Primary", "Exchange Ticker": symbol + "-XE", "Trading Currency": "EUR",
        "Exchange Name": "XETRA", "NAICS": "",
        "Exchange Country Name": "GERMANY", "Country of Incorp": "GERMANY", "Country of Risk": "GERMANY",
        "FactSet Econ Sector": "Finance", "FactSet Industry": "Banks",
        "Total MCap Y2025": "1000", "Free Float MCap Y2025": "500", "Free Float Percent": "0.5",
        "Closing Price": "10", "1M ADTV Y2025": "1", "3M ADTV Y2025": "1",
        "6M ADTV Y2025": "1", "12M ADTV Y2025": "1",
        "Listing Status": listing_status,
    }


def test_delisted_filter_numeric():
    df = pd.DataFrame([
        _minimal_universe_row("ACTIVE", "0"),
        _minimal_universe_row("DELISTED_STR", "1"),
        _minimal_universe_row("DELISTED_FLOAT", "1.0"),   # the hardening target
    ])
    gm = C.build_new_universe(df, {"GERMANY": "DM"}, "SHARE only", None,
                              False, False, False, False, False, 0.20,
                              excl_delisted=True, fol_enabled=False)
    syms = set(gm["Symbol"])
    check("delisted: active kept", "ACTIVE" in syms)
    check("delisted: '1' excluded", "DELISTED_STR" not in syms)
    check("delisted: '1.0' (float) excluded", "DELISTED_FLOAT" not in syms,
          "float-formatted Listing Status leaked through")


def test_with_fol_breakdown():
    import io, openpyxl
    df = pd.DataFrame({"Name": ["A"], "Free Float MCap Y2025": [100.0], "FOL_Value": [0.49],
                       "IF": [0.6], "Adj_FF_MCap": [60.0], "IF_Source": ["Industry"], "Index_Weight": [100.0]})
    out = list(C.with_fol_breakdown(df).columns)
    check("fol_breakdown: FOL renamed + before Adj_FF_MCap",
          "FOL" in out and out.index("FOL") < out.index("Adj_FF_MCap"))
    check("fol_breakdown: IF before Adj_FF_MCap", out.index("IF") < out.index("Adj_FF_MCap"))
    # propagates through to_excel_multi (the central export path)
    hdr = [c.value for c in openpyxl.load_workbook(io.BytesIO(C.to_excel_multi({"S": df})))["S"][1]]
    check("fol_breakdown: survives Excel export",
          "FOL" in hdr and hdr.index("FOL") < hdr.index("Adj_FF_MCap") and hdr.index("IF") < hdr.index("Adj_FF_MCap"))
    # no-op when the table is not a constituent table (no Index_Weight)
    nodf = df.drop(columns=["Index_Weight"])
    check("fol_breakdown: no-op without Index_Weight", list(C.with_fol_breakdown(nodf).columns) == list(nodf.columns))


def test_fol_matrix_consistency():
    """Validate the active FOL YAML — catches the data-quality issues found during
    the v1.x audits (auto>max logical violations, out-of-range values, duplicate
    industries, capped-flag drift) and the Taiwan-style gap where a YAML country
    has no FOL_COUNTRY_CODE_MAP entry (so its limits would be silently ignored)."""
    fol, version, dbg = C.load_fol_matrix()
    if not fol:
        skip("fol consistency", "no FOL YAML found")
        return
    check("fol: version string present", bool(version), "no version in YAML")

    bad_range, bad_auto_max, bad_capped = [], [], []
    iso_in_matrix = set()
    for yr, ys in fol.items():
        for cc, cd in ys.items():
            iso_in_matrix.add(cc)
            d = cd.get("default_fol")
            if d is None or not (0.0 <= float(d) <= 1.0):
                bad_range.append((yr, cc, "default_fol", d))
            for (sec, ind), v in cd["industries"].items():
                a, m, cap = v["fol_automatic"], v["fol_max_with_approval"], v["capped"]
                if not (0.0 <= a <= 1.0):
                    bad_range.append((yr, cc, ind, a))
                if a > m + 1e-9:                       # auto must never exceed with-approval ceiling
                    bad_auto_max.append((yr, cc, ind, a, m))
                if (cap and a >= 1.0) or ((not cap) and a < 1.0):  # capped flag must match the value
                    bad_capped.append((yr, cc, ind, a, cap))
    check("fol: all values in [0,1]", not bad_range, str(bad_range[:3]))
    check("fol: fol_automatic <= fol_max_with_approval", not bad_auto_max, str(bad_auto_max[:3]))
    check("fol: capped flag consistent with value", not bad_capped, str(bad_capped[:3]))

    # Every country present in the YAML must have a name->ISO entry, else its FOL
    # is silently ignored (the Taiwan gap). FOL_COUNTRY_CODE_MAP maps name->ISO.
    iso_in_map = set(C.FOL_COUNTRY_CODE_MAP.values())
    missing = iso_in_matrix - iso_in_map
    check("fol: every matrix country has a FOL_COUNTRY_CODE_MAP entry", not missing,
          f"YAML ISO codes without a name->ISO mapping: {sorted(missing)}")

    # Duplicate (sector, industry) within a country/year collapse silently in the
    # parsed dict (last-wins) -> check the raw YAML list.
    import yaml as _yaml
    path = dbg.get("used_path")
    dups = []
    if path and os.path.exists(path):
        raw = _yaml.safe_load(open(path, encoding="utf-8"))
        for yr, ys in raw["naroix_pit_fol_master"]["snapshots"].items():
            for cc, cd in (ys.get("countries", {}) or {}).items():
                seen = set()
                for i in (cd.get("industries", []) or []):
                    k = (i.get("factset_sector", ""), i.get("factset_industry", ""))
                    if k in seen:
                        dups.append((yr, cc, k))
                    seen.add(k)
    check("fol: no duplicate (sector,industry) per country/year", not dups, str(dups[:3]))


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS (need master file + repo data)
# ══════════════════════════════════════════════════════════════════════════════

def _load_real_context():
    """Return (snapshot_df, country_cls, china_if, year, fol, fsb) for the last
    period, or None if the master file / data is unavailable."""
    masters = glob.glob(os.path.join(_ROOT, "*Master*.xlsx"))
    if not masters:
        return None
    from datetime import date
    src = open(os.path.join(_ROOT, "naroix_benchmark.py"), encoding="utf-8").read()
    marker = "hc_df, selection_dates, china_if_map = load_historical_data()"
    if marker not in src:
        return None
    ns = {"__name__": "_probe"}
    exec(src[:src.index(marker)], ns)
    hc_df, seld, china = ns["load_historical_data"]()
    md = C.load_master_excel(masters[0], {d.isoformat() for d in seld})
    if md.get("error") or not md.get("detected_dates"):
        return None
    fol, _, _ = C.load_fol_matrix()
    fsb = C.build_sector_fallback_table(fol)
    sd = md["detected_dates"][-1]
    sdd = date.fromisoformat(sd)
    snap = C.build_snapshot_from_master(md, sd)
    cc = C.get_classification_dict(hc_df, sdd)
    return snap, cc, float(china.get(sdd, 0.20)), sdd.year, fol, fsb


def _run(snap, cc, china_if, year, fol, fsb):
    return C.run_selection_pipeline(
        snap.copy(), cc, china_if, year,
        "SHARE -> NVDR", 20000.0, True, True, True, True, True,
        70, 85, 99, 0.10, 0.50,
        2_000_000.0, 1_000_000.0, 0.0, 0.0,
        fol, fsb, True,
        "Adj_FF_MCap", "Free Float MCap Y2025",
        excl_delisted=True, apply_size_buffer=False,
    )


def integration_tests():
    ctx = _load_real_context()
    if ctx is None:
        for nm in ["determinism", "weights sum 100 (all 16 products)", "no zombie constituents",
                   "Variante A (liq-fails out of IMI)", "Non-Investable excluded from indices",
                   "FOL normalized match active"]:
            skip("integration: " + nm, "master file / data not available")
        return
    snap, cc, china_if, year, fol, fsb = ctx

    r1 = _run(snap, cc, china_if, year, fol, fsb)
    r2 = _run(snap, cc, china_if, year, fol, fsb)
    gc1, gc2 = r1["gm_complete"], r2["gm_complete"]

    # Determinism: identical constituents + segments + weights across two runs
    key = ["Symbol", "Segment_New", "Adj_FF_MCap", "Index_Weight"]
    a = gc1[key].sort_values("Symbol").reset_index(drop=True)
    b = gc2[key].sort_values("Symbol").reset_index(drop=True)
    check("integration: determinism (two runs identical)", a.equals(b),
          f"shapes {a.shape} vs {b.shape}")

    # Every product sums to exactly 100 (or is empty)
    all_ok = True; bad = []
    for ix in C.INDEX_SERIES:
        p = C.build_index(gc1, ix["region"], ix["segments"])
        if len(p) == 0:
            continue
        s = round(p["Index_Weight"].sum(), 6)
        if s != 100.0:
            all_ok = False; bad.append(f"{ix['code']}={s}")
    check("integration: weights sum 100 (all 16 products)", all_ok, ", ".join(bad))
    check("integration: gm_index_only sums 100",
          round(r1["gm_index_only"]["Index_Weight"].sum(), 6) == 100.0)

    # No zombie constituents: every IMI member has Adj_FF > 0
    imi = gc1[gc1["Segment_New"].isin(["Large Cap", "Mid Cap", "Small Cap"])]
    n_zero = int((pd.to_numeric(imi["Adj_FF_MCap"], errors="coerce").fillna(0) <= 0).sum())
    check("integration: no zombie constituents (IMI Adj_FF>0)", n_zero == 0, f"{n_zero} zeros")

    # Non-Investable is excluded from every product
    noninv_syms = set(gc1[gc1["Segment_New"] == "Non-Investable"]["Symbol"])
    leaked = False
    for ix in C.INDEX_SERIES:
        p = C.build_index(gc1, ix["region"], ix["segments"])
        if "Symbol" in p.columns and noninv_syms & set(p["Symbol"]):
            leaked = True; break
    check("integration: Non-Investable excluded from indices", not leaked)

    # Variante A: stocks that passed EUMSS but failed liquidity are NOT in the IMI
    liq_excl = set(r1["gm_liq_excluded"]["Symbol"].dropna())
    imi_syms = set(imi["Symbol"].dropna())
    check("integration: Variante A (liq-fails out of IMI)", not (liq_excl & imi_syms),
          f"{len(liq_excl & imi_syms)} liq-fails leaked into IMI")

    # FOL normalized match recovered the 'Cruise lines' stocks (>0 and no longer zeroed)
    src = pd.Series(gc1.get("IF_Source", pd.Series([], dtype=str)))
    n_norm = int((src == "Industry (normalisiert)").sum())
    check("integration: FOL normalized match active (>0 stocks)", n_norm > 0, f"n={n_norm}")


# ══════════════════════════════════════════════════════════════════════════════
def main():
    pure = [test_index_series_integrity, test_clean_export_cols, test_excel_no_y2025_leak,
            test_norm_fol_key, test_size_segment, test_normalize_index_weight,
            test_build_index, test_validate_factset_data, test_delisted_filter_numeric,
            test_with_fol_breakdown, test_fol_matrix_consistency]
    for t in pure:
        try:
            t()
        except Exception as e:  # a crash in a test counts as a failure, not a skip
            check(t.__name__, False, f"EXCEPTION: {e!r}")
    try:
        integration_tests()
    except Exception as e:
        check("integration", False, f"EXCEPTION: {e!r}")

    n_pass = sum(1 for s, _, _ in _RESULTS if s == "PASS")
    n_fail = sum(1 for s, _, _ in _RESULTS if s == "FAIL")
    n_skip = sum(1 for s, _, _ in _RESULTS if s == "SKIP")
    for status, name, detail in _RESULTS:
        line = f"[{status}] {name}"
        if detail:
            line += f"  -- {detail}"
        print(line)
    print("-" * 60)
    print(f"PASS={n_pass}  FAIL={n_fail}  SKIP={n_skip}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
