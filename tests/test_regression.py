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
import datetime as _dt
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
    check("index_series: 25 products", len(C.INDEX_SERIES) == 25, f"got {len(C.INDEX_SERIES)}")
    check("index_series: codes unique", len(set(codes)) == len(codes), "duplicate code")
    check("index_series: BY_CODE consistent", set(C.INDEX_BY_CODE) == set(codes))
    valid = {"Large Cap", "Mid Cap", "Small Cap"}
    seg_ok = all(set(ix["segments"]) <= valid for ix in C.INDEX_SERIES)
    check("index_series: segments subset of L/M/S", seg_ok)
    regions = {ix["region"] for ix in C.INDEX_SERIES}
    check("index_series: regions in {DM,EM,GM,EU,US}", regions <= {"DM", "EM", "GM", "EU", "US"}, str(regions))
    # thematic products carry top_n / industries
    check("index_series: US 500 has top_n=500", C.INDEX_BY_CODE["NX-US-500"].get("top_n") == 500)
    check("index_series: US Tech has industries", bool(C.INDEX_BY_CODE["NX-US-T"].get("industries")))


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


def test_to_excel_pct_date_cols():
    # pct_date_cols=True: date-headed columns (YYYY-MM-DD) written as real Excel percent
    # (value/100 + '%' number format at column level); other columns untouched.
    import io, openpyxl
    df = pd.DataFrame({"ISIN": ["A", "B"], "Name": ["x", "y"],
                       "2026-05-20": [1.5, 40.0], "Total MCap Y2025": [100.0, 200.0]})
    wb = openpyxl.load_workbook(io.BytesIO(C.to_excel_multi({"S": df}, pct_date_cols=True)))
    ws = wb.active
    hdr = [c.value for c in ws[1]]
    dci = hdr.index("2026-05-20") + 1                        # 1-based date column
    tci = next(i for i, h in enumerate(hdr, start=1) if h and "Total MCap" in str(h))
    check("pct_date: value divided by 100", abs(ws.cell(row=2, column=dci).value - 0.015) < 1e-9,
          str(ws.cell(row=2, column=dci).value))
    check("pct_date: percent number format", "%" in ws.cell(row=2, column=dci).number_format,
          ws.cell(row=2, column=dci).number_format)
    check("pct_date: non-date value untouched", abs(ws.cell(row=2, column=tci).value - 100.0) < 1e-9)
    check("pct_date: non-date no percent format", "%" not in ws.cell(row=2, column=tci).number_format)
    # default (flag off): date column stays as-is (no /100, no percent)
    wb0 = openpyxl.load_workbook(io.BytesIO(C.to_excel_multi({"S": df})))
    ws0 = wb0.active
    dci0 = [c.value for c in ws0[1]].index("2026-05-20") + 1
    check("pct_date default off: value unchanged", abs(ws0.cell(row=2, column=dci0).value - 1.5) < 1e-9)


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


_SEG_RANK = {"Large Cap": 3, "Mid Cap": 2, "Small Cap": 1}


def test_size_segment_entry_at_cut():
    """Aufstieg am Cut-off: Bandbreite wirkt nur auf der Halteseite (FTSE-Prinzip)."""
    f = C._size_segment_entry
    # Aufstieg an den glatten Cut-offs, unabhaengig vom Vorsegment
    check("entry: War Mid -> Large bei <70", f("Mid Cap", 69.9, 70, 85, 5) == "Large Cap")
    check("entry: War Mid bleibt Mid bei 70.0", f("Mid Cap", 70.0, 70, 85, 5) == "Mid Cap")
    check("entry: War Small -> Mid bei <85", f("Small Cap", 84.9, 70, 85, 5) == "Mid Cap")
    check("entry: War Small bleibt Small bei 85.0", f("Small Cap", 85.0, 70, 85, 5) == "Small Cap")
    check("entry: War Small -> Large bei <70 (Doppelsprung)",
          f("Small Cap", 69.9, 70, 85, 5) == "Large Cap")
    # Verbleib im Band
    check("entry: War Large haelt bis 75", f("Large Cap", 75.0, 70, 85, 5) == "Large Cap")
    check("entry: War Large faellt ab 75.1", f("Large Cap", 75.1, 70, 85, 5) == "Mid Cap")
    check("entry: War Mid haelt bis 90", f("Mid Cap", 90.0, 70, 85, 5) == "Mid Cap")
    check("entry: War Mid faellt ab 90.1", f("Mid Cap", 90.1, 70, 85, 5) == "Small Cap")
    # Neuzugang = glatte Cut-offs (unveraendert gegenueber Legacy)
    check("entry: Neuzugang <70 Large", f(None, 69.9, 70, 85, 5) == "Large Cap")
    check("entry: Neuzugang 85.0 Small", f(None, 85.0, 70, 85, 5) == "Small Cap")
    # Getrennte Bandbreite je Kante
    check("entry: bw_ms setzt die Mid-Kante separat",
          f("Mid Cap", 91.0, 70, 85, 5, 6) == "Mid Cap"
          and f("Mid Cap", 91.1, 70, 85, 5, 6) == "Small Cap")
    check("entry: bw_ms beruehrt die Large-Kante nicht",
          f("Large Cap", 75.0, 70, 85, 5, 6) == "Large Cap"
          and f("Large Cap", 75.1, 70, 85, 5, 6) == "Mid Cap")

    # Kerninvariante: kein Bestandstitel wird schlechter eingestuft als ein Neuzugang
    grid = [x / 10.0 for x in range(500, 1000)]
    bad = [(pr, c) for c in grid for pr in ("Large Cap", "Mid Cap", "Small Cap")
           if _SEG_RANK[f(pr, c, 70, 85, 5)] < _SEG_RANK[f(None, c, 70, 85, 5)]]
    check("entry: kein Incumbent schlechter als ein Neuzugang", not bad,
          f"{len(bad)} Faelle, z.B. {bad[:3]}")
    # Gegenprobe: im symmetrischen Buffer existieren genau solche Faelle (= das Problem)
    bad_sym = [(pr, c) for c in grid for pr in ("Mid Cap", "Small Cap")
               if _SEG_RANK[C._size_segment(pr, c, 70, 85, 5)]
               < _SEG_RANK[C._size_segment(None, c, 70, 85, 5)]]
    check("entry: Gegenprobe - symmetrischer Buffer benachteiligt Bestandstitel",
          len(bad_sym) > 0, "keine gefunden, Annahme pruefen")


def _load_helvetica():
    """Helvetica-Funktionsblock aus naroix_benchmark.py laden (ohne Streamlit-UI-Code)."""
    src = open(os.path.join(_ROOT, "naroix_benchmark.py"), encoding="utf-8").read()
    lines = src.split("\n")
    a = next(i for i, l in enumerate(lines) if l.startswith("def build_helvetica_pipeline"))
    b = next(i for i, l in enumerate(lines) if l.startswith("def render_helvetica_tab"))
    ns = {"np": np, "pd": pd, "_norm_isin": C._norm_isin, "_match_key": C._match_key,
          "_rank_band_select": C._rank_band_select, "format_bn": C.format_bn,
          "normalize_index_weight": C.normalize_index_weight,
          "apply_ucits_5_10_40": C.apply_ucits_5_10_40, "clean_export_cols": C.clean_export_cols,
          "apply_ineligible_filter": C.apply_ineligible_filter}
    exec(compile("\n".join(lines[a:b]), "<helvetica>", "exec"), ns)
    return ns


def _ch_frame(adj):
    """Minimaler CH-Frame; adj = Adj_FF_MCap je Titel, steuert _c_before."""
    n = len(adj)
    return pd.DataFrame({
        "Exchange Country Name": ["SWITZERLAND"] * n,
        "Name": [f"T{i}" for i in range(n)],
        "ISIN": [f"CH000000000{i}" for i in range(n)],
        "Entity ID": [f"E{i}" for i in range(n)],
        "Listing": ["Primary"] * n,
        "FactSet Industry": ["Major Banks"] * n,
        "Free Float MCap Y2025": [float(x) for x in adj],
        "Free Float Percent": [0.90] * n,
        "Total MCap Y2025": [float(x) * 1.2 for x in adj],
        "Adj_FF_MCap": [float(x) for x in adj],
        "3M ADTV Y2025": [1e7] * n,
    })


def test_helvetica_entry_at_cutoff():
    """Helvetica-Hysterese: Umschalten der Aufstiegsschwellen auf den glatten Cut-off."""
    ns = _load_helvetica()
    f = ns["build_helvetica_pipeline"]
    # Large/Mid-Kante: zweiter Titel landet bei _c_before = 67 % (zwischen 65 und 70)
    df = _ch_frame([67e9, 33e9])
    kw = dict(adtv_thr=1.0, incumbents_isin={"CH0000000000", "CH0000000001"},
              prior_segments={"E0": "Large Cap", "E1": "Mid Cap"})
    a = dict(zip(f(df, **kw)[0]["Entity ID"], f(df, **kw)[0]["Segment_New"]))
    b_df = f(df, entry_at_cutoff=True, **kw)[0]
    b = dict(zip(b_df["Entity ID"], b_df["Segment_New"]))
    check("helvetica: symmetrisch haelt Mid-Incumbent bei 67 %", a.get("E1") == "Mid Cap",
          str(a))
    check("helvetica: Cut-off laesst Mid-Incumbent bei 67 % nach Large auf",
          b.get("E1") == "Large Cap", str(b))
    # Mid/Small-Kante: dritter Titel bei _c_before = 84,7 % (zwischen 84,5 und 85)
    df2 = _ch_frame([60e9, 24.7e9, 15.3e9])
    kw2 = dict(adtv_thr=1.0,
               incumbents_isin={f"CH000000000{i}" for i in range(3)},
               prior_segments={"E0": "Large Cap", "E1": "Mid Cap", "E2": "Small Cap"})
    a2 = f(df2, **kw2)[0]
    b2 = f(df2, entry_at_cutoff=True, **kw2)[0]
    cb = float(a2[a2["Entity ID"] == "E2"]["_c_before"].iloc[0])
    check("helvetica: Testaufbau trifft 84,5-85 %", 84.5 <= cb < 85.0, f"_c_before={cb:.2f}")
    sa = dict(zip(a2["Entity ID"], a2["Segment_New"]))
    sb = dict(zip(b2["Entity ID"], b2["Segment_New"]))
    check("helvetica: symmetrisch haelt Small-Incumbent bei 84,7 %", sa.get("E2") == "Small Cap",
          str(sa))
    check("helvetica: Cut-off laesst Small-Incumbent bei 84,7 % nach Mid auf",
          sb.get("E2") == "Mid Cap", str(sb))
    # Halteseiten unveraendert: Mid-Incumbent bei 88 % bleibt in beiden Varianten Mid
    df3 = _ch_frame([88e9, 12e9])
    kw3 = dict(adtv_thr=1.0, incumbents_isin={"CH0000000000", "CH0000000001"},
               prior_segments={"E0": "Large Cap", "E1": "Mid Cap"})
    for tag, res in (("symmetrisch", f(df3, **kw3)[0]),
                     ("Cut-off", f(df3, entry_at_cutoff=True, **kw3)[0])):
        seg = dict(zip(res["Entity ID"], res["Segment_New"]))
        check(f"helvetica: Halteseite unveraendert ({tag}), Mid bei 88 %",
              seg.get("E1") == "Mid Cap", str(seg))


def test_helvetica_adtv_maintenance():
    """3M-ADTV hat Entry- und Maintenance-Schwelle (Guideline Schritt 3).

    Bis 2026-08-28 war die Liquiditaet Helveticas EINZIGE Schwelle ohne Bestandsschutz,
    waehrend FF % und Coverage laengst einen hatten.
    """
    ns = _load_helvetica()
    df = _ch_frame([60e9, 40e9])
    df["3M ADTV Y2025"] = [8e5, 8e5]          # zwischen Maintenance 750k und Entry 1,0 Mio
    kw = dict(adtv_thr=1_000_000, adtv_maint_thr=750_000)

    out_new = ns["build_helvetica_pipeline"](df, **kw)[1]
    check("helvetica adtv: Neuzugang unter der Entry-Schwelle faellt raus",
          len(out_new) == 0, f"n={len(out_new)}")

    out_inc = ns["build_helvetica_pipeline"](df, incumbents_isin={"CH0000000000"}, **kw)[1]
    check("helvetica adtv: Bestandstitel wird von der Maintenance-Schwelle gehalten",
          set(out_inc["ISIN"]) == {"CH0000000000"}, sorted(out_inc["ISIN"]))

    df2 = df.copy(); df2["3M ADTV Y2025"] = [7e5, 7e5]   # unter BEIDEN Schwellen
    out_low = ns["build_helvetica_pipeline"](df2, incumbents_isin={"CH0000000000"}, **kw)[1]
    check("helvetica adtv: unter der Maintenance-Schwelle faellt auch der Bestand",
          len(out_low) == 0, f"n={len(out_low)}")


def test_helvetica_high_price_rule():
    """Hochpreis-Regel als ATVR-Bedingung statt hartem Cut (wie apply_liquidity_new)."""
    ns = _load_helvetica()

    def frame(atvr):
        d = _ch_frame([60e9, 40e9])
        d["Closing Price"] = [50_000.0, 100.0]        # Titel 0 ueber der Preisgrenze
        d["ATVR_3M"] = [atvr, 1.0]
        d["ATVR_6M"] = [atvr, 1.0]
        return d

    kw = dict(adtv_thr=1.0, max_price=20_000.0, max_price_atvr=0.10)
    keep = ns["build_helvetica_pipeline"](frame(0.20), **kw)[1]
    check("helvetica preis: Hochpreis-Titel bleibt bei ausreichender ATVR",
          "CH0000000000" in set(keep["ISIN"]), sorted(keep["ISIN"]))
    drop = ns["build_helvetica_pipeline"](frame(0.05), **kw)[1]
    check("helvetica preis: Hochpreis-Titel faellt bei zu geringer ATVR",
          "CH0000000000" not in set(drop["ISIN"]), sorted(drop["ISIN"]))

    # Maintenance-Schwelle: Bestandstitel darf unter die Entry-ATVR fallen
    kw_m = dict(kw, m_max_price_atvr=0.05, incumbents_isin={"CH0000000000"})
    hold = ns["build_helvetica_pipeline"](frame(0.07), **kw_m)[1]
    check("helvetica preis: Bestandstitel haelt ueber die Maintenance-ATVR",
          "CH0000000000" in set(hold["ISIN"]), sorted(hold["ISIN"]))

    # Ohne max_price_atvr passiert hier nichts (harter Cut sitzt in build_new_universe)
    off = ns["build_helvetica_pipeline"](frame(0.0), adtv_thr=1.0, max_price=20_000.0)[1]
    check("helvetica preis: ohne ATVR-Modus greift die Regel hier nicht",
          "CH0000000000" in set(off["ISIN"]), sorted(off["ISIN"]))


def test_helvetica_ineligible():
    """In-Eligible entfernt NACH der Segmentierung; das Equity-Sleeve rueckt nach."""
    ns = _load_helvetica()
    df = _ch_frame([100e9 / (i + 1) for i in range(14)])
    ie = pd.DataFrame([{"ISIN": "CH0000000000", "Company Name": "T0", "Country Mapping": "",
                        "From": pd.Timestamp("2000-01-01"), "To": pd.Timestamp("9999-12-31"),
                        "Reason": "Test"}])
    kw = dict(adtv_thr=1.0)
    base = ns["build_helvetica_pipeline"](df, **kw)[1]
    cut = ns["build_helvetica_pipeline"](df, ineligible_df=ie, apply_ineligible=True,
                                         selection_date=_dt.date(2026, 5, 20), **kw)[1]
    check("helvetica ineligible: Titel ist aus dem Pool entfernt",
          "CH0000000000" in set(base["ISIN"]) and "CH0000000000" not in set(cut["ISIN"]),
          f"vorher {len(base)}, nachher {len(cut)}")
    check("helvetica ineligible: genau ein Titel weniger", len(cut) == len(base) - 1,
          f"{len(base)} -> {len(cut)}")

    _re = {"Real Estate Development"}
    helv = ns["build_helvetica_pipeline"](df, ineligible_df=ie, apply_ineligible=True,
                                          selection_date=_dt.date(2026, 5, 20), **kw)[0]
    comp = ns["build_helvetica_composite"](helv, cut, _re)[0]
    check("helvetica ineligible: taucht auch in der Komposition nicht auf",
          "CH0000000000" not in set(comp["ISIN"]), "gefunden")


def test_helvetica_dedup_most_liquid():
    """Pro Firma nur die liquideste Linie — sonst Doppelgewichte bei Mehrfach-Listings."""
    ns = _load_helvetica()
    df = _ch_frame([60e9, 40e9])
    df["Entity ID"] = ["E-SAME", "E-SAME"]            # eine Firma, zwei Linien
    df["3M ADTV Y2025"] = [1e6, 5e6]                  # die ZWEITE ist liquider
    out = ns["build_helvetica_pipeline"](df, adtv_thr=1.0)[1]
    check("helvetica dedup: nur eine Linie je Firma", len(out) == 1, f"n={len(out)}")
    check("helvetica dedup: es ueberlebt die liquidere Linie",
          set(out["ISIN"]) == {"CH0000000001"}, sorted(out["ISIN"]))

    # Fehlende Entity ID darf NICHT kollabieren (Fallback auf ISIN)
    df2 = df.copy(); df2["Entity ID"] = ["", ""]
    out2 = ns["build_helvetica_pipeline"](df2, adtv_thr=1.0)[1]
    check("helvetica dedup: ohne Entity ID kein faelschliches Kollabieren",
          len(out2) == 2, f"n={len(out2)}")


def test_helvetica_micro_fillup():
    """Micro Cap ist Fill-up-Quelle fuer das Small-Sleeve (Guideline 4.2.1).

    Historisch nie eingetreten (Small hat im CH-Universe nie unter 37 eigene Titel), der Pfad
    laeuft also nur hier. Vor dem Fix war er toter Code: der Kaskaden-Pool kam aus `helv`
    (nur L/M/S), der Eintrag "Micro Cap" in _SEG_RANK konnte nie greifen und ein kurzes
    Small-Sleeve blieb LEER, statt aufzufuellen.
    """
    ns = _load_helvetica()
    # Streng fallende Groessen, damit die Coverage-Treppe monoton ist. Der Small-Cut liegt
    # bei 90 % statt 99 %, sonst faellt Small strukturell nie unter 10 Titel — genau deshalb
    # ist der Pfad in der Praxis nie gelaufen.
    adj = [8e9] * 10 + [1.5e9] * 10 + [0.25e9] * 6 + [0.02e9] * 12
    rules = {"min_ff": 0.10, "min_ff_maint": 0.075, "large": 70.0, "std": 85.0, "small": 90.0,
             "hold_large_pp": 5.0, "hold_std_pp": 5.0, "hold_small_pp": 0.5}
    helv, full, _ = ns["build_helvetica_pipeline"](_ch_frame(adj), adtv_thr=1.0, rules=rules)

    _seg = full["Segment_New"].value_counts().to_dict()
    n_small, n_micro = _seg.get("Small Cap", 0), _seg.get("Micro Cap", 0)
    check("helvetica micro: Testaufbau hat kurzes Small-Sleeve",
          0 < n_small < ns["HELVETICA_TOPN"], f"Small={n_small}")
    check("helvetica micro: Testaufbau hat Micro Caps zum Auffuellen", n_micro > 0,
          f"Micro={n_micro}")

    _re = {"Real Estate Development"}
    eq = ns["build_helvetica_composite"](helv, full, _re)[0].query("Type == 'Equity'")
    sm = eq[eq["Sleeve"] == "Small Cap"]
    check("helvetica micro: Small-Sleeve fuellt auf top_n auf",
          len(sm) == ns["HELVETICA_TOPN"], f"n={len(sm)}")
    check("helvetica micro: nachgezogene Titel sind als Aufruecker markiert",
          (sm["Status"] == "Aufrücker").sum() >= ns["HELVETICA_TOPN"] - n_small, str(sm["Status"].tolist()))
    check("helvetica micro: echte Groessenklasse bleibt erhalten",
          "Micro Cap" in set(sm["True_Segment"]), str(sorted(set(sm["True_Segment"]))))
    check("helvetica micro: Sleeve-Gewicht bleibt auf Ziel",
          abs(sm["Index_Weight"].sum() - 15.0) < 1e-9, f"{sm['Index_Weight'].sum():.4f}")

    # Gegenprobe: ohne Micro im Quellpool bleibt das Sleeve leer (= der Zustand vor dem Fix)
    sm_old = ns["build_helvetica_composite"](helv, helv, _re)[0].query(
        "Type == 'Equity' and Sleeve == 'Small Cap'")
    check("helvetica micro: Gegenprobe - ohne Micro bleibt das Sleeve unterbesetzt",
          len(sm_old) < ns["HELVETICA_TOPN"], f"n={len(sm_old)}")


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


def test_build_index_thematic():
    # region US + industry filter + top_n (US 500 / US Tech / World 100 mechanics)
    SEG = ["Large Cap", "Mid Cap", "Small Cap"]
    rows = [
        # ISIN, Class, Exchange Country, Mapping Country, Segment, Industry, Total MCap, Adj_FF
        ("U1", "DM", "UNITED STATES", "UNITED STATES", "Large Cap", "Semiconductors",    3000.0, 2900.0),
        ("U2", "DM", "UNITED STATES", "UNITED STATES", "Large Cap", "Packaged Software", 2000.0, 1900.0),
        ("U3", "DM", "UNITED STATES", "UNITED STATES", "Mid Cap",   "Internet Retail",   1500.0, 1400.0),
        ("U4", "DM", "UNITED STATES", "UNITED STATES", "Large Cap", "Major Banks",       2900.0, 2800.0),  # US non-tech
        ("U5", "DM", "UNITED STATES", "UNITED STATES", "Small Cap", "Semiconductors",     300.0,  280.0),
        ("A1", "DM", "UNITED STATES", "UNITED KINGDOM","Large Cap", "Internet Software/Services", 2800.0, 2700.0),  # US-listed, foreign-domiciled (ADR-like)
        ("X1", "DM", "GERMANY",       "GERMANY",       "Large Cap", "Semiconductors",    5000.0, 4800.0),  # non-US-listed
    ]
    gm = pd.DataFrame(rows, columns=["ISIN", "Classification", "Exchange Country Name", "Mapping Country",
                                     "Segment_New", "FactSet Industry", "Total MCap Y2025", "Adj_FF_MCap"])
    us = C.build_index(gm, "US", SEG)
    check("build_index US: only US-listed (Exchange Country)", set(us["Exchange Country Name"]) == {"UNITED STATES"})
    check("build_index US: includes US-listed foreign-domiciled (A1)", "A1" in set(us["ISIN"]))
    check("build_index US: excludes non-US listing (X1)", "X1" not in set(us["ISIN"]))
    tech = C.build_index(gm, "US", SEG, industries=C.TECH_INDUSTRIES)
    check("build_index US+tech: excludes Major Banks", "U4" not in set(tech["ISIN"]))
    check("build_index US+tech: keeps tech (incl. A1)", {"U1", "U2", "U3", "U5", "A1"} == set(tech["ISIN"]))
    topn = C.build_index(gm, "US", SEG, top_n=2)
    check("build_index top_n: largest 2 by Total MCap", set(topn["ISIN"]) == {"U1", "U4"}, str(set(topn["ISIN"])))
    techtop = C.build_index(gm, "US", SEG, industries=C.TECH_INDUSTRIES, top_n=2)
    check("build_index tech+top_n: top-2 US tech", set(techtop["ISIN"]) == {"U1", "A1"}, str(set(techtop["ISIN"])))
    check("build_index thematic: weights sum 100", round(techtop["Index_Weight"].sum(), 6) == 100.0)


def test_atvr_dual_horizon():
    # apply_liquidity_new screens ATVR on BOTH horizons: a name must clear the threshold on
    # the 3M AND the 6M ATVR, not just one. Bis 2026-08-25 waren die Beine 3M und 12M; sie
    # laufen jetzt synchron zu den ADTV-Beinen (3M/6M). ADTV weit ueber dem $1M-Gate, damit
    # nur die ATVR-Bedingung bindet.
    big = 10_000_000.0
    rows = [
        # ISIN, Class, 3M ADTV, 6M ADTV, ATVR_3M, ATVR_6M, ATVR_12M
        ("L1", "DM", big, big, 0.50, 0.50, 0.01),   # both clear -> in (12M egal)
        ("L2", "DM", big, big, 0.05, 0.50, 0.50),   # 3M fails    -> out
        ("L3", "DM", big, big, 0.50, 0.05, 0.50),   # 6M fails    -> out
        ("L4", "DM", big, big, 0.05, 0.05, 0.50),   # both fail   -> out
        ("E1", "EM", big, big, 0.50, 0.50, 0.01),   # EM both clear -> in
    ]
    df = pd.DataFrame(rows, columns=["ISIN", "Classification", "3M ADTV Y2025",
                                     "6M ADTV Y2025", "ATVR_3M", "ATVR_6M", "ATVR_12M"])
    keep = set(C.apply_liquidity_new(df, 1_000_000.0, 1_000_000.0, 0.20, 0.20)["ISIN"])
    check("atvr dual: both horizons clear -> kept", {"L1", "E1"} <= keep, str(keep))
    check("atvr dual: 3M-only fail -> excluded", "L2" not in keep, str(keep))
    check("atvr dual: 6M-only fail -> excluded", "L3" not in keep, str(keep))
    check("atvr dual: both fail -> excluded", "L4" not in keep, str(keep))
    check("atvr dual: 12M spielt keine Rolle mehr", {"L1", "E1"} <= keep, str(keep))
    # threshold 0 keeps everyone (default screen is a no-op -> default selection unchanged)
    keep0 = C.apply_liquidity_new(df, 1_000_000.0, 1_000_000.0, 0.0, 0.0)
    check("atvr dual: threshold 0 keeps all", len(keep0) == len(df), f"{len(keep0)}/{len(df)}")


def test_rank_band_buffer():
    # df pre-sorted best-first (rank = row position); A..J = ranks 1..10. N=5, hard=3, exit=7.
    df = pd.DataFrame({"ISIN": list("ABCDEFGHIJ")})
    out = C._rank_band_select(df, top_n=5, incumbents={"E", "G", "H"}, buffer_hard=3, buffer_exit=7)
    got = list(out["ISIN"])
    check("rank_band: count == N", len(got) == 5, str(got))
    check("rank_band: hard top (A,B,C) always in", set("ABC") <= set(got))
    check("rank_band: band incumbents kept (E r5, G r7)", {"E", "G"} <= set(got))
    check("rank_band: newcomer in band dropped (D r4)", "D" not in got, str(got))
    check("rank_band: incumbent beyond exit excluded (H r8)", "H" not in got, str(got))
    # too few band incumbents -> fill remaining slot with highest-ranked newcomer (D)
    out2 = C._rank_band_select(df, top_n=5, incumbents={"G"}, buffer_hard=3, buffer_exit=7)
    check("rank_band: fill newcomer when incumbents short", set(out2["ISIN"]) == {"A", "B", "C", "D", "G"}, str(list(out2["ISIN"])))
    # plain top-N (no incumbents) for contrast = A..E
    plain = C._rank_band_select(df, top_n=5, incumbents=set(), buffer_hard=3, buffer_exit=7)
    check("rank_band: no incumbents -> {A..C}+fill", set("ABC") <= set(plain["ISIN"]) and len(plain) == 5)


def test_build_index_company_count():
    # top_n counts COMPANIES (Entity ID), then keeps ALL share lines of the selected ones.
    SEG = ["Large Cap", "Mid Cap", "Small Cap"]
    rows = [
        # ISIN, Class, Exchange, Mapping, Segment, Industry, Total MCap, Adj_FF, Entity ID
        ("C1A", "DM", "UNITED STATES", "UNITED STATES", "Large Cap", "Packaged Software", 3000.0, 2900.0, "E_ALPHA"),
        ("C1B", "DM", "UNITED STATES", "UNITED STATES", "Large Cap", "Packaged Software", 3000.0, 1500.0, "E_ALPHA"),  # 2nd class, same company
        ("C2",  "DM", "UNITED STATES", "UNITED STATES", "Large Cap", "Semiconductors",    2000.0, 1900.0, "E_BETA"),
        ("C3",  "DM", "UNITED STATES", "UNITED STATES", "Mid Cap",   "Internet Retail",   1000.0,  900.0, "E_GAMMA"),
    ]
    gm = pd.DataFrame(rows, columns=["ISIN", "Classification", "Exchange Country Name", "Mapping Country",
                                     "Segment_New", "FactSet Industry", "Total MCap Y2025", "Adj_FF_MCap", "Entity ID"])
    p = C.build_index(gm, "US", SEG, top_n=2)   # top 2 COMPANIES
    check("company-count: 2 companies", p["Entity ID"].nunique() == 2, str(set(p["Entity ID"])))
    check("company-count: both share lines of top company kept", {"C1A", "C1B"} <= set(p["ISIN"]), str(set(p["ISIN"])))
    check("company-count: 3 securities for 2 companies", len(p) == 3, str(len(p)))
    check("company-count: 3rd company excluded", "C3" not in set(p["ISIN"]))
    check("company-count: weights sum 100", round(p["Index_Weight"].sum(), 6) == 100.0)


def _issuer_weights(df):
    # aggregate line weights to the issuer level (Entity ID, ISIN fallback) like the cap does
    ck = df["Entity ID"].fillna("").astype(str).str.strip()
    ck = ck.where(ck != "", df["ISIN"].astype(str))
    return df.assign(_k=ck.to_numpy()).groupby("_k")["Index_Weight"].sum()


def test_ucits_cap():
    # top-heavy issuer set; one issuer (E_GOOG) has two share lines that must be
    # aggregated before the cap, else it dodges the 10% ceiling across two listings.
    SEG = ["Large Cap", "Mid Cap", "Small Cap"]
    rows = [
        ("E1",  "E1",     30.0),
        ("E2",  "E2",     25.0),
        ("E3",  "E3",     15.0),
        ("E4",  "E4",     12.0),
        ("E5",  "E5",      8.0),
        ("G_A", "E_GOOG",  6.0),   # Alphabet line 1
        ("G_C", "E_GOOG",  6.0),   # Alphabet line 2 (same Entity ID) -> issuer 12% pre-cap
    ] + [(f"T{i}", f"E_T{i}", 1.0) for i in range(10)]   # sub-5% tail to absorb redistribution
    gm = pd.DataFrame(
        [(isin, "DM", "UNITED STATES", "UNITED STATES", "Large Cap", "Semiconductors",
          ff * 10.0, ff, ent) for isin, ent, ff in rows],
        columns=["ISIN", "Classification", "Exchange Country Name", "Mapping Country",
                 "Segment_New", "FactSet Industry", "Total MCap Y2025", "Adj_FF_MCap", "Entity ID"],
    )

    # uncapped: at least one issuer breaches 10% (sanity that the fixture is top-heavy)
    raw = C.build_index(gm, "US", SEG, cap="5/10/40", apply_cap=False)
    check("ucits: uncapped breaches 10% (fixture is top-heavy)", _issuer_weights(raw).max() > 10.0 + 1e-6)

    cap = C.build_index(gm, "US", SEG, cap="5/10/40", apply_cap=True)
    iss = _issuer_weights(cap)
    big = iss[iss > 5.0 + 1e-9]
    check("ucits: weights sum 100", round(cap["Index_Weight"].sum(), 6) == 100.0)
    check("ucits: no issuer > 10%", iss.max() <= 10.0 + 1e-6, f"max {iss.max():.4f}")
    check("ucits: sum of >5% issuers <= 40%", big.sum() <= 40.0 + 1e-6, f"sum>5% {big.sum():.4f}")
    check("ucits: dual-line issuer aggregated <= 10%", iss.get("E_GOOG", 0.0) <= 10.0 + 1e-6,
          f"E_GOOG {iss.get('E_GOOG', 0.0):.4f}")
    check("ucits: no line weight is negative", (cap["Index_Weight"] >= -1e-9).all())

    # every catalogued tech index carries the 5/10/40 flag
    capped = [ix["code"] for ix in C.INDEX_SERIES if ix.get("cap")]
    check("ucits: 6 tech indices flagged", len(capped) == 6, str(capped))
    check("ucits: all flags are 5/10/40",
          all(C.INDEX_BY_CODE[c]["cap"] == "5/10/40" for c in capped))


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
                              False, False, False, False, 0.20,
                              excl_delisted=True, fol_enabled=False)
    syms = set(gm["Symbol"])
    check("delisted: active kept", "ACTIVE" in syms)
    check("delisted: '1' excluded", "DELISTED_STR" not in syms)
    check("delisted: '1.0' (float) excluded", "DELISTED_FLOAT" not in syms,
          "float-formatted Listing Status leaked through")


def test_with_fol_breakdown():
    import io, openpyxl
    df = pd.DataFrame({"Name": ["A"], "Total MCap Y2025": [200.0], "Share MCap Y2025": [150.0],
                       "Free Float MCap Y2025": [100.0], "FOL_Value": [0.49], "IF": [0.6],
                       "Adj_FF_MCap": [60.0], "IF_Source": ["Industry"], "Index_Weight": [100.0]})
    out = list(C.with_fol_breakdown(df).columns)
    check("fol_breakdown: FOL renamed + before Adj_FF_MCap",
          "FOL" in out and out.index("FOL") < out.index("Adj_FF_MCap"))
    check("fol_breakdown: IF before Adj_FF_MCap", out.index("IF") < out.index("Adj_FF_MCap"))
    # full export column order through the central path (FOL/IF + Share MCap placement + rename)
    hdr = [c.value for c in openpyxl.load_workbook(io.BytesIO(C.to_excel_multi({"S": df})))["S"][1]]
    check("export: FOL/IF before Adj_FF_MCap",
          "FOL" in hdr and hdr.index("FOL") < hdr.index("Adj_FF_MCap") and hdr.index("IF") < hdr.index("Adj_FF_MCap"))
    check("export: Share MCap between Total and Free Float MCap",
          hdr.index("Total MCap") < hdr.index("Share MCap") < hdr.index("Free Float MCap"),
          str(hdr))
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

def _liq_row(pid, adtv3, adtv6, atvr3=0.5, atvr6=None, cls="DM"):
    # atvr6 default = atvr3, damit die Alt-Faelle unveraendert lesen
    _a6 = atvr3 if atvr6 is None else atvr6
    return {"Perm ID": pid, "ISIN": "XX" + pid, "Classification": cls,
            "3M ADTV Y2025": adtv3, "6M ADTV Y2025": adtv6,
            "ATVR_3M": atvr3, "ATVR_6M": _a6, "ATVR_12M": atvr3}


def test_liquidity_exempt_missing():
    """ADTV-Ausnahme fuer geseedete Spin-off-Kinder: FEHLENDE Werte gelten als bestanden,
    vorhandene Werte unter der Schwelle weiterhin nicht."""
    nan = float("nan")
    df = pd.DataFrame([
        _liq_row("P-MISS", nan, nan, nan, nan),      # Kind ohne Handelshistorie
        _liq_row("P-LOW", 100_000.0, 100_000.0),     # Kind, aber Wert VORHANDEN und zu klein
        _liq_row("P-OK", 5_000_000.0, 5_000_000.0),  # normal liquide
        _liq_row("P-OTHER", nan, nan, nan, nan),     # kein Kind, fehlende Werte
    ])
    ex = {"P-MISS", "P-LOW"}
    out = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0,
                                exempt_missing_keys=ex)
    keys = set(out["Perm ID"])
    check("liq-exempt: fehlender Wert gilt als bestanden", "P-MISS" in keys, sorted(keys))
    check("liq-exempt: vorhandener Wert unter Schwelle scheitert weiter",
          "P-LOW" not in keys, sorted(keys))
    check("liq-exempt: normal liquider Titel unberuehrt", "P-OK" in keys, sorted(keys))
    check("liq-exempt: Nicht-Kind mit fehlendem Wert scheitert",
          "P-OTHER" not in keys, sorted(keys))
    # build_new_universe macht fillna(0): im Screen kommt ein fehlender Wert als 0.0 an.
    # Die Ausnahme MUSS deshalb auch auf 0 greifen, sonst kann sie real nie feuern.
    df0 = pd.DataFrame([
        _liq_row("P-ZERO", 0.0, 0.0, 0.0, 0.0),
        _liq_row("P-ZERO2", 0.0, 0.0, 0.0, 0.0),
    ])
    out0 = C.apply_liquidity_new(df0, 1_000_000, 1_000_000, 0.0, 0.0,
                                 exempt_missing_keys={"P-ZERO"})
    k0 = set(out0["Perm ID"])
    check("liq-exempt: 0.0 gilt als fehlend (nach fillna(0))", "P-ZERO" in k0, sorted(k0))
    check("liq-exempt: 0.0 ohne Ausnahme scheitert", "P-ZERO2" not in k0, sorted(k0))


def test_liquidity_exempt_neutral():
    """Ohne Ausnahme-Menge muss das Ergebnis bit-identisch zum Verhalten ohne den
    Parameter sein. Das ist die Zusage, dass die Ausnahme nichts sonst beruehrt."""
    nan = float("nan")
    df = pd.DataFrame([
        _liq_row("P-A", 5_000_000.0, 5_000_000.0),
        _liq_row("P-B", 900_000.0, 900_000.0),
        _liq_row("P-C", nan, nan, nan, nan),
        _liq_row("P-D", 2_000_000.0, 500_000.0),
        _liq_row("P-E", 5_000_000.0, 5_000_000.0, cls="EM"),
    ])
    for ex in (None, set(), frozenset()):
        a = C.apply_liquidity_new(df, 1_000_000, 500_000, 0.0, 0.0, exempt_missing_keys=ex)
        b = C.apply_liquidity_new(df, 1_000_000, 500_000, 0.0, 0.0)
        check(f"liq-exempt: neutral bei {ex!r}", set(a["Perm ID"]) == set(b["Perm ID"]),
              (sorted(a["Perm ID"]), sorted(b["Perm ID"])))
    # und die Ausnahme darf einen Titel mit nur EINEM fehlenden Horizont nicht durchwinken,
    # wenn der andere vorhanden und zu klein ist
    df2 = pd.DataFrame([_liq_row("P-HALF", nan, 100_000.0, nan, 0.5)])
    out = C.apply_liquidity_new(df2, 1_000_000, 1_000_000, 0.0, 0.0,
                                exempt_missing_keys={"P-HALF"})
    check("liq-exempt: ein fehlender + ein zu kleiner Horizont scheitert", len(out) == 0,
          out.to_dict("records"))


def _hz_list(ex="2025-12-08", sd="2026-02-18"):
    return pd.DataFrame([{
        "Selection Date": pd.Timestamp(sd), "Event Type": "Spin-off", "Aktiv": "JA",
        "Parent ISIN": "XXP-PARENT", "Parent Ticker": "PAR-X", "Parent Name": "Parent",
        "Child ISIN": "XXP-CHILD", "Child Ticker": "CHI-X", "Child Name": "Child",
        "Segment Override": "", "Quelle": "PM", "Ex-Date": pd.Timestamp(ex),
        "Erfasst am": pd.Timestamp(ex), "Kommentar": "", "_Aktiv": True, "_SD": sd,
    }])


def _hz_snap():
    return pd.DataFrame([
        {"Perm ID": "P-PARENT", "ISIN": "XXP-PARENT", "Total MCap Y2025": 50e9},
        {"Perm ID": "P-CHILD", "ISIN": "XXP-CHILD", "Total MCap Y2025": 8e9},
    ])


def test_spinoff_horizon_windows():
    """Die Ausnahme haengt am Ex-Date, nicht am Seed-Termin: das 6M-Bein muss auch am
    Folgetermin noch offen sein, sonst scheitert das Kind dort an einer Huerde, die es
    rechnerisch nicht erfuellen kann."""
    snap, sl = _hz_snap(), _hz_list()          # Ex-Date 2025-12-08
    inc, seeded = {"P-PARENT"}, {"P-CHILD"}
    cases = [
        ("2026-02-18", {"3M", "6M", "12M"}),   # 2,4 Monate danach: alles offen
        ("2026-05-20", {"6M", "12M"}),         # 5,4 Monate: 3M zu, 6M offen
        ("2026-08-19", {"12M"}),               # 8,4 Monate: nur 12M offen
        ("2026-11-18", {"12M"}),               # 11,4 Monate: 12M noch offen
        ("2027-02-17", set()),                 # 14 Monate: nichts mehr offen
    ]
    for sd, exp in cases:
        ex = C.spinoff_liquidity_exemptions(sl, sd, snap, incumbent_keys=inc,
                                            seeded_keys=seeded)
        got = {h for h, k in ex.items() if "P-CHILD" in k}
        check(f"spinoff-horizon: offene Horizonte am {sd}", got == exp, (sorted(got), sorted(exp)))
    # Grenzen exakt: genau 3 bzw. 6 Monate nach Ex-Date ist der Horizont ZU
    for sd, closed in (("2026-03-08", "3M"), ("2026-06-08", "6M")):
        ex = C.spinoff_liquidity_exemptions(sl, sd, snap, incumbent_keys=inc,
                                            seeded_keys=seeded)
        check(f"spinoff-horizon: {closed} genau {sd} geschlossen",
              "P-CHILD" not in ex[closed], sorted(ex[closed]))


def test_spinoff_horizon_entitlement():
    """Nur ein Kind, das geseedet wird oder schon Bestandstitel ist, bekommt die
    Ausnahme. Ein verworfener Seed darf sich keine Liquiditaets-Erleichterung erschleichen."""
    snap, sl = _hz_snap(), _hz_list()
    ex = C.spinoff_liquidity_exemptions(sl, "2026-02-18", snap,
                                        incumbent_keys={"P-PARENT"}, seeded_keys=set())
    check("spinoff-horizon: ohne Seed und ohne Bestand keine Ausnahme",
          all("P-CHILD" not in k for k in ex.values()), {h: sorted(k) for h, k in ex.items()})
    ex2 = C.spinoff_liquidity_exemptions(sl, "2026-05-20", snap,
                                         incumbent_keys={"P-PARENT", "P-CHILD"},
                                         seeded_keys=set())
    check("spinoff-horizon: als Bestandstitel weiter berechtigt",
          "P-CHILD" in ex2["6M"], sorted(ex2["6M"]))
    # vor dem Seed-Termin: gar nichts
    ex3 = C.spinoff_liquidity_exemptions(sl, "2025-11-19", snap,
                                         incumbent_keys={"P-PARENT"}, seeded_keys={"P-CHILD"})
    check("spinoff-horizon: vor dem Seed-Termin keine Ausnahme",
          all("P-CHILD" not in k for k in ex3.values()), {h: sorted(k) for h, k in ex3.items()})
    # leere Liste
    ex4 = C.spinoff_liquidity_exemptions(None, "2026-02-18", snap, {"P-PARENT"}, {"P-CHILD"})
    check("spinoff-horizon: leere Liste -> leere Mengen",
          all(len(k) == 0 for k in ex4.values()), ex4)


def test_liquidity_exempt_per_horizon():
    """Dict-Form: die Ausnahme darf NUR das Bein oeffnen, dessen Horizont offen ist."""
    df = pd.DataFrame([_liq_row("P-K", 0.0, 0.0, 0.0, 0.0)])
    # nur 6M offen -> das 3M-Bein blockt weiter
    out = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0,
                                exempt_missing_keys={"3M": set(), "6M": {"P-K"},
                                                     "12M": {"P-K"}})
    check("liq-horizon: 3M zu -> Titel scheitert", len(out) == 0, out.to_dict("records"))
    # 3M und 6M offen -> kommt durch
    out2 = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0,
                                 exempt_missing_keys={"3M": {"P-K"}, "6M": {"P-K"},
                                                      "12M": {"P-K"}})
    check("liq-horizon: 3M+6M offen -> Titel kommt durch", len(out2) == 1,
          out2.to_dict("records"))
    # realistischer Folgetermin: 3M vorhanden und ausreichend, 6M fehlt und ist offen
    df2 = pd.DataFrame([_liq_row("P-K", 5_000_000.0, 0.0, 0.9, 0.0)])
    out3 = C.apply_liquidity_new(df2, 1_000_000, 1_000_000, 0.0, 0.0,
                                 exempt_missing_keys={"3M": set(), "6M": {"P-K"},
                                                      "12M": {"P-K"}})
    check("liq-horizon: Folgetermin 3M ok + 6M offen -> durch", len(out3) == 1,
          out3.to_dict("records"))
    # gleicher Fall, aber 6M-Horizont zu -> raus
    out4 = C.apply_liquidity_new(df2, 1_000_000, 1_000_000, 0.0, 0.0,
                                 exempt_missing_keys={"3M": set(), "6M": set(),
                                                      "12M": {"P-K"}})
    check("liq-horizon: Folgetermin mit geschlossenem 6M -> raus", len(out4) == 0,
          out4.to_dict("records"))


def _hp_row(pid, px, atvr3, atvr6, adtv=5_000_000.0, cls="DM"):
    return {"Perm ID": pid, "ISIN": "XX" + pid, "Classification": cls,
            "3M ADTV Y2025": adtv, "6M ADTV Y2025": adtv,
            "ATVR_3M": atvr3, "ATVR_6M": atvr6, "ATVR_12M": max(atvr3, atvr6),
            "Closing Price": px}


def _cell_row(pid, px, atvr, cls="DM"):
    """Titel mit gegebenem Kurs und gegebener ATVR (auf beiden Beinen), ADTV unkritisch."""
    return {"Perm ID": pid, "ISIN": "XX" + pid, "Classification": cls,
            "3M ADTV Y2025": 5_000_000.0, "6M ADTV Y2025": 5_000_000.0,
            "ATVR_3M": atvr, "ATVR_6M": atvr, "ATVR_12M": atvr, "Closing Price": px}


_CELLS = dict(adtv_dm=1_000_000, adtv_em=1_000_000, atvr_dm=0.020, atvr_em=0.020,
              m_adtv_dm=750_000, m_adtv_em=750_000, m_atvr_dm=0.015, m_atvr_em=0.015,
              max_price=20_000, max_price_atvr=0.10, m_max_price_atvr=0.05)


def _run_cells(df, incumbents=None):
    k = dict(_CELLS)
    return C.apply_liquidity_new(df, k.pop("adtv_dm"), k.pop("adtv_em"),
                                 k.pop("atvr_dm"), k.pop("atvr_em"),
                                 incumbents_isin=incumbents, **k)


def test_atvr_four_cells():
    """Vier-Zellen-Matrix: New 2,0 / 1,5 Current bei normalem Kurs, 10,0 / 5,0 ab 20.000."""
    df = pd.DataFrame([
        _cell_row("P-N-LO-OK", 100.0, 0.025),     # neu, guenstig, 2,5 % -> ueber 2,0
        _cell_row("P-N-LO-NO", 100.0, 0.018),     # neu, guenstig, 1,8 % -> unter 2,0
        _cell_row("P-C-LO-OK", 100.0, 0.018),     # Bestand, guenstig, 1,8 % -> ueber 1,5
        _cell_row("P-C-LO-NO", 100.0, 0.012),     # Bestand, guenstig, 1,2 % -> unter 1,5
        _cell_row("P-N-HI-OK", 50_000.0, 0.12),   # neu, teuer, 12 % -> ueber 10
        _cell_row("P-N-HI-NO", 50_000.0, 0.08),   # neu, teuer, 8 % -> unter 10
        _cell_row("P-C-HI-OK", 50_000.0, 0.08),   # Bestand, teuer, 8 % -> ueber 5
        _cell_row("P-C-HI-NO", 50_000.0, 0.03),   # Bestand, teuer, 3 % -> unter 5
    ])
    inc = {"P-C-LO-OK", "P-C-LO-NO", "P-C-HI-OK", "P-C-HI-NO"}
    keys = set(_run_cells(df, incumbents=inc)["Perm ID"])
    for pid, soll in (("P-N-LO-OK", True), ("P-N-LO-NO", False),
                      ("P-C-LO-OK", True), ("P-C-LO-NO", False),
                      ("P-N-HI-OK", True), ("P-N-HI-NO", False),
                      ("P-C-HI-OK", True), ("P-C-HI-NO", False)):
        check(f"atvr-cells: {pid} {'bleibt' if soll else 'raus'}",
              (pid in keys) == soll, sorted(keys))
    # Kein Ausschluss wegen des Kurses allein: teuer + liquide bleibt drin
    check("atvr-cells: teuer schliesst nie allein aus", "P-N-HI-OK" in keys, sorted(keys))


def test_atvr_india_protection():
    """Der Grund fuer New = 2,0 statt 2,5: Indiens illiquidester Standard-Titel liegt bei
    2,494 % (BSE-Datenlage, vgl. Analyse 2026-08-19). 2,5 % wuerde ihn treffen."""
    df = pd.DataFrame([_cell_row("P-GRASIM", 100.0, 0.02494, cls="EM")])
    # als Bestandstitel gegen 1,5 %
    check("atvr-india: Grasim besteht Current 1,5 %",
          len(_run_cells(df, incumbents={"P-GRASIM"})) == 1)
    # als Neuzugang gegen 2,0 %
    check("atvr-india: Grasim besteht New 2,0 %", len(_run_cells(df)) == 1)
    # gegen 2,5 % wuerde er scheitern — genau deshalb 2,0
    k = dict(_CELLS); k["atvr_dm"] = k["atvr_em"] = 0.025
    out = C.apply_liquidity_new(df, k.pop("adtv_dm"), k.pop("adtv_em"),
                                k.pop("atvr_dm"), k.pop("atvr_em"), **k)
    check("atvr-india: bei 2,5 % wuerde Grasim scheitern", len(out) == 0, out.to_dict("records"))


def test_atvr_real_high_price_titles():
    """Echte Zahlen vom Snapshot 2026-08-19."""
    df = pd.DataFrame([
        _cell_row("P-BRKA", 750_170.0, 0.1410),   # Berkshire A
        _cell_row("P-LISN", 117_398.0, 0.3211),   # Lindt Namenaktie
        _cell_row("P-GOLF", 23_932.0, 0.0000),    # Club de Golf Santiago
        _cell_row("P-BRKB", 500.0, 0.8034),       # Berkshire B, guenstig
        _cell_row("P-LISP", 11_390.0, 0.7794),    # Lindt Partizipationsschein
    ])
    keys = set(_run_cells(df)["Perm ID"])
    check("atvr-real: Berkshire A bleibt (14,1 % > 10 %)", "P-BRKA" in keys, sorted(keys))
    check("atvr-real: Lindt Namenaktie bleibt", "P-LISN" in keys, sorted(keys))
    check("atvr-real: Golfclub raus (0 %)", "P-GOLF" not in keys, sorted(keys))
    check("atvr-real: Berkshire B unberuehrt", "P-BRKB" in keys, sorted(keys))
    check("atvr-real: Lindt Partizipationsschein unberuehrt", "P-LISP" in keys, sorted(keys))


def test_atvr_legs_3m_6m():
    """Der Screen prueft 3M und 6M. ATVR_12M darf das Ergebnis nicht mehr beeinflussen."""
    good = _cell_row("P-A", 100.0, 0.05)
    good["ATVR_12M"] = 0.0                      # 12M auf null -> muss egal sein
    bad = _cell_row("P-B", 100.0, 0.05)
    bad["ATVR_6M"] = 0.001                      # 6M reisst die Schwelle
    out = _run_cells(pd.DataFrame([good, bad]))
    keys = set(out["Perm ID"])
    check("atvr-legs: ATVR_12M ohne Wirkung", "P-A" in keys, sorted(keys))
    check("atvr-legs: 6M-Bein bindet", "P-B" not in keys, sorted(keys))


def test_atvr_zero_thresholds_neutral():
    """Mit Schwellen 0 und ohne Hochpreis-Regel darf nichts an der ATVR scheitern."""
    df = pd.DataFrame([_cell_row("P-X", 750_170.0, 0.0), _cell_row("P-Y", 100.0, 0.0)])
    out = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0)
    check("atvr-neutral: Schwelle 0 laesst alles durch",
          set(out["Perm ID"]) == {"P-X", "P-Y"}, sorted(out["Perm ID"]))


def test_high_price_atvr_rule():
    """Hochpreis-Regel: Kurs >= max_price schliesst nicht mehr aus, verlangt aber
    min(ATVR_3M, ATVR_6M) >= Schwelle. Zahlen aus dem echten Snapshot 2026-08-19."""
    df = pd.DataFrame([
        _hp_row("P-BRK", 750_170.0, 0.14621, 0.14102),   # Berkshire A: hochliquide
        _hp_row("P-LISN", 117_398.0, 0.32107, 0.37807),  # Lindt Namenaktie
        _hp_row("P-ISATR", 92_933.0, 0.0, 0.0),          # unhandelbar
        _hp_row("P-ISKUR", 86_050.0, 0.00055, 0.00057),  # 0,055 % — knapp
        _hp_row("P-GOLF", 23_932.0, 0.0, 0.00067),       # min = 0
        _hp_row("P-NORMAL", 120.0, 0.0, 0.0),            # guenstig: Regel greift nicht
    ])
    out = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0,
                                max_price=20_000, max_price_atvr=0.003)
    keys = set(out["Perm ID"])
    check("high-price: Berkshire A bleibt", "P-BRK" in keys, sorted(keys))
    check("high-price: Lindt bleibt", "P-LISN" in keys, sorted(keys))
    check("high-price: unhandelbar raus", "P-ISATR" not in keys, sorted(keys))
    check("high-price: 0,055 % unter 0,3 % raus", "P-ISKUR" not in keys, sorted(keys))
    check("high-price: min(3M,6M)=0 raus", "P-GOLF" not in keys, sorted(keys))
    check("high-price: guenstiger Titel unberuehrt", "P-NORMAL" in keys, sorted(keys))

    # Schwelle 0,03 % laesst ISKUR (0,055 %) durch
    out2 = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0,
                                 max_price=20_000, max_price_atvr=0.0003)
    check("high-price: bei 0,03 % kommt ISKUR durch", "P-ISKUR" in set(out2["Perm ID"]),
          sorted(out2["Perm ID"]))
    check("high-price: bei 0,03 % bleiben die Nuller draussen",
          not {"P-ISATR", "P-GOLF"} & set(out2["Perm ID"]), sorted(out2["Perm ID"]))

    # Die Schwelle gilt fuer NEUE UND BESTEHENDE gleich: Incumbent-Status darf nichts aendern
    out3 = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0,
                                 incumbents_isin={"P-ISKUR", "P-ISATR"},
                                 m_adtv_dm=750_000, m_adtv_em=750_000,
                                 m_atvr_dm=0.0, m_atvr_em=0.0,
                                 max_price=20_000, max_price_atvr=0.003)
    check("high-price: kein Maintenance-Rabatt fuer Bestandstitel",
          not {"P-ISKUR", "P-ISATR"} & set(out3["Perm ID"]), sorted(out3["Perm ID"]))


def test_high_price_neutral():
    """Ohne die neuen Argumente muss sich nichts aendern, und der alte harte Cut in
    apply_universe_exclusions muss weiter funktionieren."""
    df = pd.DataFrame([
        _hp_row("P-HI", 750_170.0, 0.0, 0.0),
        _hp_row("P-LO", 120.0, 0.0, 0.0),
    ])
    out = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0)
    check("high-price: ohne Argumente bleibt der Hochpreis-Titel drin",
          set(out["Perm ID"]) == {"P-HI", "P-LO"}, sorted(out["Perm ID"]))
    # max_price ohne Schwelle -> Regel inaktiv
    out2 = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0, max_price=20_000)
    check("high-price: max_price ohne ATVR-Schwelle ist inaktiv",
          set(out2["Perm ID"]) == {"P-HI", "P-LO"}, sorted(out2["Perm ID"]))
    # alter harter Cut
    uni = pd.DataFrame([
        {"Free Float MCap Y2025": 1e9, "Closing Price": 750_170.0, "Exchange Ticker": "A-USA",
         "Trading Currency": "USD", "Listing": "Primary", "Country of Risk": "US",
         "Exchange Name": "NYSE", "Sec Type": "SHARE", "Name": "Hoch"},
        {"Free Float MCap Y2025": 1e9, "Closing Price": 120.0, "Exchange Ticker": "B-USA",
         "Trading Currency": "USD", "Listing": "Primary", "Country of Risk": "US",
         "Exchange Name": "NYSE", "Sec Type": "SHARE", "Name": "Guenstig"},
    ])
    kept = C.apply_universe_exclusions(uni, max_price=20_000, excl_delisted=False)
    check("high-price: harter Cut in den Exclusions unveraendert",
          set(kept["Name"]) == {"Guenstig"}, sorted(kept["Name"]))
    kept2 = C.apply_universe_exclusions(uni, max_price=None, excl_delisted=False)
    check("high-price: max_price=None laesst beide drin",
          set(kept2["Name"]) == {"Hoch", "Guenstig"}, sorted(kept2["Name"]))


def test_atvr_6m_column():
    """ATVR_6M muss existieren und dieselbe Fallback-Kette nutzen wie die anderen."""
    import inspect
    src = inspect.getsource(C.run_selection_pipeline.__module__ and C)
    check("atvr6m: Spalte wird gesetzt", 'df["ATVR_6M"]' in src)
    check("atvr6m: Fallback 6M -> 3M", "_adtv6  = _a6.where(_a6 > 0, _adtv3)" in src)


def test_liquidity_incumbent_key():
    """Der ADTV-/ATVR-Maintenance-Buffer muss auf _match_key greifen (Perm ID mit
    ISIN-Fallback), nicht auf die reine ISIN. Vorher traf er nie, weil die Run-Schleifen
    Perm IDs in incumbents_isin legen und Perm ID im Master immer gefuellt ist."""
    df = pd.DataFrame([
        # Bestandstitel, ADTV 800k: unter Entry (1 Mio), ueber Maintenance (750k)
        {"Perm ID": "P-INC", "ISIN": "XX0000000INC", "Classification": "DM",
         "3M ADTV Y2025": 800_000.0, "6M ADTV Y2025": 800_000.0,
         "ATVR_3M": 0.5, "ATVR_6M": 0.5, "ATVR_12M": 0.5},
        # Neuzugang mit identischen Zahlen: muss an der Entry-Schwelle scheitern
        {"Perm ID": "P-NEW", "ISIN": "XX0000000NEW", "Classification": "DM",
         "3M ADTV Y2025": 800_000.0, "6M ADTV Y2025": 800_000.0,
         "ATVR_3M": 0.5, "ATVR_6M": 0.5, "ATVR_12M": 0.5},
    ])
    out = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0,
                                incumbents_isin={"P-INC"},
                                m_adtv_dm=750_000, m_adtv_em=750_000,
                                m_atvr_dm=0.0, m_atvr_em=0.0)
    keys = set(out["Perm ID"])
    check("liquidity: Incumbent per Perm ID erkannt", "P-INC" in keys, sorted(keys))
    check("liquidity: Neuzugang scheitert an Entry", "P-NEW" not in keys, sorted(keys))
    # Ohne Buffer muessen beide fallen
    out2 = C.apply_liquidity_new(df, 1_000_000, 1_000_000, 0.0, 0.0, incumbents_isin=None)
    check("liquidity: ohne Buffer fallen beide", len(out2) == 0, len(out2))
    # ISIN-Fallback muss weiter funktionieren, wenn keine Perm-ID-Spalte da ist
    df2 = df.drop(columns=["Perm ID"])
    out3 = C.apply_liquidity_new(df2, 1_000_000, 1_000_000, 0.0, 0.0,
                                 incumbents_isin={"XX0000000INC"},
                                 m_adtv_dm=750_000, m_adtv_em=750_000,
                                 m_atvr_dm=0.0, m_atvr_em=0.0)
    check("liquidity: ISIN-Fallback ohne Perm ID", set(out3["ISIN"]) == {"XX0000000INC"},
          sorted(out3["ISIN"]))


def _spin_snapshot():
    """Minimaler Snapshot: Mutter + Kind + ein Dritter. Perm ID vorhanden, damit der
    Matching-Key derselbe Pfad ist wie in der echten Pipeline (_match_key)."""
    return pd.DataFrame([
        {"Perm ID": "P-PARENT", "ISIN": "XX0000PARENT", "Exchange Ticker": "PAR-X",
         "Total MCap Y2025": 50e9},
        {"Perm ID": "P-CHILD", "ISIN": "XX0000CHILD0", "Exchange Ticker": "CHI-X",
         "Total MCap Y2025": 8e9},
        {"Perm ID": "P-OTHER", "ISIN": "XX0000OTHER0", "Exchange Ticker": "OTH-X",
         "Total MCap Y2025": 12e9},
        # Kind, das an diesem Termin noch keine Daten hat (Panel-Padding im Master)
        {"Perm ID": "P-UNBORN", "ISIN": "XX0000UNBORN", "Exchange Ticker": "UNB-X",
         "Total MCap Y2025": None},
    ])


def _spin_list(**over):
    row = {"Selection Date": pd.Timestamp("2026-02-18"), "Event Type": "Spin-off",
           "Aktiv": "JA", "Parent ISIN": "XX0000PARENT", "Parent Ticker": "PAR-X",
           "Parent Name": "Parent", "Child ISIN": "XX0000CHILD0", "Child Ticker": "CHI-X",
           "Child Name": "Child", "Segment Override": "", "Quelle": "Pressemitteilung",
           "Ex-Date": pd.Timestamp("2026-01-05"), "Erfasst am": pd.Timestamp("2026-01-06"),
           "Kommentar": "", "_Aktiv": True, "_SD": "2026-02-18"}
    row.update(over)
    return pd.DataFrame([row])


def test_spinoff_seed_basic():
    snap = _spin_snapshot()
    prev_keys = {"P-PARENT", "P-OTHER"}
    prev_segs = {"P-PARENT": "Large Cap", "P-OTHER": "Mid Cap"}
    keys, segs, log = C.seed_spinoff_incumbents(prev_keys, prev_segs, "2026-02-18", snap,
                                                _spin_list())
    check("spinoff: Kind wird Incumbent", "P-CHILD" in keys, sorted(keys))
    check("spinoff: erbt Segment der Mutter", segs.get("P-CHILD") == "Large Cap",
          segs.get("P-CHILD"))
    check("spinoff: Status geseedet", len(log) == 1 and log.iloc[0]["Status"] == "geseedet",
          log.to_dict("records"))
    # Eingaben duerfen NICHT mutiert werden (die Run-Schleife reicht denselben State weiter)
    check("spinoff: Eingabe-Set unveraendert", prev_keys == {"P-PARENT", "P-OTHER"}, prev_keys)
    check("spinoff: Eingabe-Dict unveraendert", "P-CHILD" not in prev_segs, prev_segs)


def test_spinoff_segment_override():
    snap = _spin_snapshot()
    keys, segs, log = C.seed_spinoff_incumbents(
        {"P-PARENT"}, {"P-PARENT": "Large Cap"}, "2026-02-18", snap,
        _spin_list(**{"Segment Override": "Mid Cap"}))
    check("spinoff: Segment Override schlaegt Vererbung", segs.get("P-CHILD") == "Mid Cap",
          segs.get("P-CHILD"))


def test_spinoff_rejects():
    snap = _spin_snapshot()
    # (a) Mutter war nicht im investierbaren Universum
    keys, segs, log = C.seed_spinoff_incumbents({"P-OTHER"}, {"P-OTHER": "Mid Cap"},
                                                "2026-02-18", snap, _spin_list())
    check("spinoff: Mutter nicht im Bestand -> verworfen",
          "P-CHILD" not in keys and log.iloc[0]["Status"] == "verworfen",
          log.iloc[0].to_dict())
    # (b) Kind ohne Daten an diesem Termin (Panel-Padding)
    keys, segs, log = C.seed_spinoff_incumbents(
        {"P-PARENT"}, {"P-PARENT": "Large Cap"}, "2026-02-18", snap,
        _spin_list(**{"Child ISIN": "XX0000UNBORN", "Child Ticker": "UNB-X"}))
    check("spinoff: Kind ohne MCap -> verworfen",
          "P-UNBORN" not in keys and "ohne Total MCap" in str(log.iloc[0]["Begruendung"]),
          log.iloc[0].to_dict())
    # (c) Kind ist schon Bestandstitel -> wirkungslos
    keys, segs, log = C.seed_spinoff_incumbents(
        {"P-PARENT", "P-CHILD"}, {"P-PARENT": "Large Cap", "P-CHILD": "Small Cap"},
        "2026-02-18", snap, _spin_list())
    check("spinoff: schon Bestandstitel -> wirkungslos",
          log.iloc[0]["Status"] == "verworfen" and segs["P-CHILD"] == "Small Cap",
          log.iloc[0].to_dict())
    # (d) Kind nicht im Snapshot
    keys, segs, log = C.seed_spinoff_incumbents(
        {"P-PARENT"}, {"P-PARENT": "Large Cap"}, "2026-02-18", snap,
        _spin_list(**{"Child ISIN": "XX0000GHOST0"}))
    check("spinoff: unbekanntes Kind -> verworfen",
          len(keys) == 1 and log.iloc[0]["Status"] == "verworfen", log.iloc[0].to_dict())


def test_spinoff_neutral_when_empty():
    """Leere/fremde Liste muss den State BIT-IDENTISCH lassen. Das ist die Zusage,
    dass bestehende Backtests durch die Regel nicht kippen."""
    snap = _spin_snapshot()
    pk, ps = {"P-PARENT", "P-OTHER"}, {"P-PARENT": "Large Cap", "P-OTHER": "Mid Cap"}
    for label, sl in (("None", None),
                      ("leer", pd.DataFrame(columns=C.SPINOFF_COLS)),
                      ("anderer Termin", _spin_list(_SD="2025-11-19"))):
        keys, segs, log = C.seed_spinoff_incumbents(pk, ps, "2026-02-18", snap, sl)
        check(f"spinoff: neutral bei Liste '{label}'", keys == pk and segs == ps and len(log) == 0,
              (sorted(keys), segs, len(log)))


def test_spinoff_other_key_fn():
    """Helvetica faehrt den Incumbent-State auf Entity ID, nicht auf Perm ID."""
    snap = _spin_snapshot()
    snap["Entity ID"] = ["E-PARENT", "E-CHILD", "E-OTHER", "E-UNBORN"]
    kf = lambda df: df["Entity ID"].fillna("").astype(str).str.strip()
    keys, segs, log = C.seed_spinoff_incumbents({"E-PARENT"}, {"E-PARENT": "Mid Cap"},
                                                "2026-02-18", snap, _spin_list(), key_fn=kf)
    check("spinoff: key_fn Entity ID", "E-CHILD" in keys and segs["E-CHILD"] == "Mid Cap",
          sorted(keys))


def test_spinoff_loader_validation():
    """load_spinoff_list() gegen das echte File im Repo-Root, falls vorhanden."""
    import datetime as _dt
    try:
        sd = pd.read_excel(os.path.join(_ROOT, "Selection Dates.xlsx"), usecols=[0])
    except Exception:
        skip("spinoff: Loader gegen echtes File", "Selection Dates.xlsx nicht lesbar")
        return
    sd.columns = ["d"]
    SEL = set(pd.to_datetime(sd["d"]).dt.strftime("%Y-%m-%d").dropna())
    _cwd = os.getcwd()
    try:
        os.chdir(_ROOT)
        df, probs = C.load_spinoff_list(SEL)
    finally:
        os.chdir(_cwd)
    if df is None:
        check("spinoff: Loader liefert DataFrame", False, "None")
        return
    check("spinoff: Loader liefert DataFrame", isinstance(df, pd.DataFrame))
    if len(df) == 0:
        skip("spinoff: Eintraege im File", "Liste leer oder File fehlt")
        return
    check("spinoff: _SD gesetzt", df["_SD"].notna().all())
    check("spinoff: nur bekannte Termine", set(df["_SD"]) <= SEL, set(df["_SD"]) - SEL)
    check("spinoff: Ex-Date nie nach dem Seed-Termin",
          (df["Ex-Date"] <= df["Selection Date"]).all())
    check("spinoff: keine Dubletten Kind+Termin",
          not df.duplicated(subset=["Child ISIN", "_SD"]).any())
    check("spinoff: Kind != Mutter", (df["Child ISIN"] != df["Parent ISIN"]).all())
    check("spinoff: Probleme sind Tripel",
          all(isinstance(p, tuple) and len(p) == 3 for p in probs), probs[:3])


def _load_real_context():
    """Return (snapshot_df, country_cls, china_if, year, fol, fsb) for the last
    period, or None if the master file / data is unavailable."""
    # Neuesten Universe-Master nehmen, nicht den alphabetisch ersten: im Repo liegen mehrere
    # Staende nebeneinander und glob()[0] traf den aeltesten. Das Namensmuster deckt die
    # aktuelle Datei (NaroIX_Universe_Selection_Master_Final_08_2026_Complete.xlsx) und die
    # frueheren ACWI-Staende ab; der Helvetica-Master ist ein anderes Universum und faellt raus.
    # '~$...' sind Office-Sperrdateien: sie entstehen, sobald der Master in Excel offen ist,
    # matchen das Muster, sind per mtime die neuesten und lassen sich nicht lesen. Ohne den
    # Filter waeren die Integrationstests still weggeskippt, solange die Datei offen ist.
    masters = sorted((f for f in glob.glob(os.path.join(_ROOT, "*Selection_Master*.xlsx"))
                      if "helvetica" not in os.path.basename(f).lower()
                      and not os.path.basename(f).startswith("~$")),
                     key=os.path.getmtime, reverse=True)
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
    # Ueber die Kandidaten laufen: ein gesperrtes oder kaputtes File soll den Lauf nicht
    # abschalten, solange ein aelterer, lesbarer Stand daneben liegt.
    md = None
    for _m in masters:
        _md = C.load_master_excel(_m, {d.isoformat() for d in seld})
        if not _md.get("error") and _md.get("detected_dates"):
            md = _md
            break
    if md is None:
        return None
    fol, _, _ = C.load_fol_matrix()
    fsb = C.build_sector_fallback_table(fol)
    sd = md["detected_dates"][-1]
    sdd = date.fromisoformat(sd)
    snap = C.build_snapshot_from_master(md, sd)
    cc = C.get_classification_dict(hc_df, sdd)
    return snap, cc, float(china.get(sdd, 0.20)), sdd.year, fol, fsb


def _run(snap, cc, china_if, year, fol, fsb, **kw):
    kw.setdefault("apply_size_buffer", False)
    return C.run_selection_pipeline(
        snap.copy(), cc, china_if, year,
        "SHARE -> NVDR", 20000.0, True, True, True, True,
        70, 85, 99, 0.10, 0.50,
        2_000_000.0, 1_000_000.0, 0.0, 0.0,
        fol, fsb, True,
        "Adj_FF_MCap", "Free Float MCap Y2025",
        excl_delisted=True, **kw,
    )


def _segmap(gc):
    """{Symbol: Segment_New} fuer Mengenvergleiche zwischen Laeufen."""
    return dict(zip(gc["Symbol"], gc["Segment_New"]))


def integration_size_integrity(ctx, baseline):
    """Size-Integrity-Auffuellung: additiv, ast-unabhaengig, ohne Doppelzaehlung."""
    snap, cc, china_if, year, fol, fsb = ctx
    base = _segmap(baseline)

    r_si = _run(snap, cc, china_if, year, fol, fsb,
                apply_size_integrity=True, si_k=1.00, si_edge_pp=90.0)
    gc = r_si["gm_complete"]
    seg = _segmap(gc)
    T, T_em = r_si["si_threshold"], r_si["si_threshold_em"]

    check("size-integrity: T > 0 kalibriert", T > 0, f"T={T}")
    check("size-integrity: EM-Schwelle = 1/2 DM", abs(T_em - 0.5 * T) < 1e-6,
          f"{T_em} vs {0.5*T}")

    # Nur Small -> Mid. Keine andere Segmentbewegung gegenueber der Baseline.
    moved = {s: (base[s], seg[s]) for s in set(base) & set(seg) if base[s] != seg[s]}
    bad = {s: v for s, v in moved.items() if v != ("Small Cap", "Mid Cap")}
    check("size-integrity: ausschliesslich Small -> Mid", not bad,
          f"{len(bad)} andere Wechsel, z.B. {list(bad.items())[:3]}")
    check("size-integrity: bewegt ueberhaupt Titel", len(moved) > 0, "keine Auffuellung")

    # All Cap und Large unveraendert (die Regel ist additiv im Standard, nicht im Universum).
    imi = lambda m: {s for s, v in m.items() if v in ("Large Cap", "Mid Cap", "Small Cap")}
    lg = lambda m: {s for s, v in m.items() if v == "Large Cap"}
    check("size-integrity: All Cap konstant", imi(base) == imi(seg),
          f"delta {len(imi(base) ^ imi(seg))}")
    check("size-integrity: Large konstant", lg(base) == lg(seg),
          f"delta {len(lg(base) ^ lg(seg))}")

    # Flags konsistent mit der tatsaechlichen Bewegung.
    filled = set(gc.loc[gc["Size_Integrity_Filled"].fillna(False), "Symbol"])
    check("size-integrity: Flag == bewegte Titel", filled == set(moved),
          f"Flag {len(filled)} vs bewegt {len(moved)}")

    # Keine Doppelzaehlung mit den Buffer-Flags.
    dbl = int((gc["Size_Integrity_Filled"].fillna(False)
               & gc["Kept_In_Standard_By_Buffer"].fillna(False)).sum())
    check("size-integrity: keine Doppelzaehlung mit Buffer-Flag", dbl == 0, f"{dbl} doppelt")

    # Kante: jeder aufgefuellte Titel liegt unter der Kante, Regel vollstaendig angewandt.
    fl = gc[gc["Size_Integrity_Filled"].fillna(False)]
    check("size-integrity: Kante haelt (_c_before < 90)",
          bool((pd.to_numeric(fl["_c_before"], errors="coerce") < 90.0).all()) if len(fl) else True)
    rest = gc[(gc["Segment_New"] == "Small Cap")
              & (pd.to_numeric(gc["Total MCap Y2025"], errors="coerce").fillna(0) >= T)
              & (pd.to_numeric(gc["_c_before"], errors="coerce") < 90.0)
              & (gc["Classification"] == "DM")]
    check("size-integrity: kein qualifizierter DM-Titel uebersehen", len(rest) == 0,
          f"{len(rest)} Small-Titel >= T unter der Kante")

    # Ohne Kante: nichts blockiert, und mindestens so viele Fills wie mit Kante.
    r_open = _run(snap, cc, china_if, year, fol, fsb,
                  apply_size_integrity=True, si_k=1.00, si_edge_pp=None)
    check("size-integrity: ohne Kante keine Blockierungen", r_open["si_blocked_n"] == 0,
          f"{r_open['si_blocked_n']} blockiert")
    check("size-integrity: ohne Kante >= Fills mit Kante",
          r_open["si_filled_n"] >= r_si["si_filled_n"],
          f"{r_open['si_filled_n']} vs {r_si['si_filled_n']}")

    # Ast-Unabhaengigkeit: mit aktivem Size Buffer (anderer Waterfall-Ast) muss die Regel
    # genauso vollstaendig greifen — kein qualifizierter Small-Titel bleibt liegen.
    r_buf = _run(snap, cc, china_if, year, fol, fsb,
                 apply_size_integrity=True, si_k=1.00, si_edge_pp=90.0,
                 apply_size_buffer=True, incumbent_segments=base, size_buffer_pp=5.0)
    gb = r_buf["gm_complete"]
    left = gb[(gb["Segment_New"] == "Small Cap")
              & (pd.to_numeric(gb["Total MCap Y2025"], errors="coerce").fillna(0)
                 >= r_buf["si_threshold"])
              & (pd.to_numeric(gb["_c_before"], errors="coerce") < 90.0)
              & (gb["Classification"] == "DM")]
    check("size-integrity: greift auch im Size-Buffer-Ast", len(left) == 0,
          f"{len(left)} Titel liegen geblieben")
    check("size-integrity: Size-Buffer-Ast fuellt auf", r_buf["si_filled_n"] > 0)

    # MSCI Logic hat Vorrang: Regel muss stillgelegt sein.
    r_msci = _run(snap, cc, china_if, year, fol, fsb,
                  apply_size_integrity=True, si_k=1.00, msci_logic=True)
    check("size-integrity: von MSCI Logic deaktiviert", r_msci["si_filled_n"] == 0,
          f"{r_msci['si_filled_n']} Fills trotz GIMI")

    # Guard: ohne DM-Basis waere T = 0 und wuerde JEDEN Small Cap anheben.
    cc_em = {k: "EM" for k in cc}
    r_nodm = _run(snap, cc_em, china_if, year, fol, fsb,
                  apply_size_integrity=True, si_k=1.00, si_edge_pp=90.0)
    check("size-integrity: kein DM-Pool -> Regel still aus",
          r_nodm["si_filled_n"] == 0 and r_nodm["si_threshold"] == 0.0,
          f"fills={r_nodm['si_filled_n']} T={r_nodm['si_threshold']}")


def integration_tests():
    ctx = _load_real_context()
    if ctx is None:
        for nm in ["determinism", "weights sum 100 (all 16 products)", "no zombie constituents",
                   "Variante A (liq-fails out of IMI)", "Non-Investable excluded from indices",
                   "FOL normalized match active"]:
            skip("integration: " + nm, "master file / data not available")
        skip("size-integrity: alle Checks", "master file / data not available")
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

    # Aufstieg am Cut-off gegen symmetrischen Buffer, gleiche Vorperioden-Segmente
    _IMI3 = ["Large Cap", "Mid Cap", "Small Cap"]
    _base = _segmap(gc1)
    _sym = _run(snap, cc, china_if, year, fol, fsb, apply_size_buffer=True,
                incumbent_segments=_base, size_buffer_pp=5.0)["gm_complete"]
    _ent = _run(snap, cc, china_if, year, fol, fsb, apply_size_buffer=True,
                incumbent_segments=_base, size_buffer_pp=5.0,
                entry_at_cutoff=True)["gm_complete"]
    _ms, _me = _segmap(_sym), _segmap(_ent)
    _imi = lambda m: {s for s, v in m.items() if v in _IMI3}
    check("entry_at_cutoff: All Cap unveraendert", _imi(_ms) == _imi(_me),
          f"delta {len(_imi(_ms) ^ _imi(_me))}")
    _down = [s for s in set(_ms) & set(_me) if _SEG_RANK.get(_me[s], 0) < _SEG_RANK.get(_ms[s], 0)]
    check("entry_at_cutoff: kein Titel wird tiefer eingestuft als symmetrisch", not _down,
          f"{len(_down)} Titel, z.B. {_down[:3]}")
    _std = lambda m: sum(1 for v in m.values() if v in ("Large Cap", "Mid Cap"))
    check("entry_at_cutoff: Standard-Segment nicht kleiner", _std(_me) >= _std(_ms),
          f"{_std(_me)} vs {_std(_ms)}")
    check("entry_at_cutoff: von MSCI Logic deaktiviert",
          _segmap(_run(snap, cc, china_if, year, fol, fsb, apply_size_buffer=True,
                       incumbent_segments=_base, entry_at_cutoff=True, msci_logic=True)
                  ["gm_complete"])
          == _segmap(_run(snap, cc, china_if, year, fol, fsb, apply_size_buffer=True,
                          incumbent_segments=_base, msci_logic=True)["gm_complete"]))

    # Investable Universe je Produkt-Scope (Basis der Multi-Period-Summary-Spalte
    # und des zweiten Tabs im Detail-Download).
    bad_sub, bad_n = [], []
    for ix in C.INDEX_SERIES:
        cons = C.build_index(gc1, ix["region"], ix["segments"],
                             industries=ix.get("industries"), top_n=ix.get("top_n"))
        iu = C.build_index(gc1, ix["region"], C._SEG_AC,
                           industries=ix.get("industries"), apply_cap=False)
        if len(cons) == 0:
            continue
        if not set(cons["Symbol"]) <= set(iu["Symbol"]):
            bad_sub.append(ix["code"])
        if len(iu) < len(cons):
            bad_n.append(f"{ix['code']} {len(iu)}<{len(cons)}")
    check("investable universe: Konstituenten Teilmenge des Universe", not bad_sub,
          ", ".join(bad_sub))
    check("investable universe: Universe nie kleiner als der Index", not bad_n, ", ".join(bad_n))

    iu_eu = C.build_index(gc1, "EU", C._SEG_AC, apply_cap=False)
    non_eu = set(iu_eu["Mapping Country"].fillna("").astype(str).str.upper()) - C.EUROPE_COUNTRIES
    check("investable universe: EU-Scope enthaelt nur Europa", not non_eu, str(sorted(non_eu))[:80])
    check("investable universe: EU-Scope enthaelt nur DM",
          set(iu_eu["Classification"].dropna()) <= {"DM"})
    check("investable universe: EU-Scope nur IMI-Segmente",
          set(iu_eu["Segment_New"].dropna()) <= set(C._SEG_AC))

    # Coverage-Treppe (_cum_cov / _c_after): die beiden Spalten, mit denen der Export den
    # Cut nachvollziehbar macht. Eigenschaften je Segmentierungsmarkt: monoton, verkettet
    # mit _c_before der Folgezeile, Endwert exakt 100 %. Zeilen ohne Waterfall (Micro aus
    # EUMSS/Liquiditaet, Non-Investable) tragen NaN wie _c_before und bleiben aussen vor.
    check("coverage-treppe: Spalten vorhanden",
          {"_c_before", "_cum_cov", "_c_after"} <= set(gc1.columns))
    _wf = gc1[pd.to_numeric(gc1["_c_before"], errors="coerce").notna()]
    _bad_mono, _bad_link, _bad_end = [], [], []
    for _ctry, _grp in _wf.groupby("Mapping Country"):
        _grp = _grp.sort_values(["Total MCap Y2025", "Adj_FF_MCap"], ascending=[False, False])
        _ca = pd.to_numeric(_grp["_c_after"], errors="coerce").to_numpy()
        _cb = pd.to_numeric(_grp["_c_before"], errors="coerce").to_numpy()
        if not bool((np.diff(_ca) >= -1e-9).all()):
            _bad_mono.append(_ctry)
        if len(_ca) > 1 and not bool(np.allclose(_cb[1:], _ca[:-1], atol=1e-9)):
            _bad_link.append(_ctry)
        if abs(float(_ca[-1]) - 100.0) > 1e-6:
            _bad_end.append(f"{_ctry} {_ca[-1]:.4f}")
    check("coverage-treppe: monoton je Markt", not _bad_mono, str(_bad_mono[:3]))
    check("coverage-treppe: _c_before(n+1) == _c_after(n)", not _bad_link, str(_bad_link[:3]))
    check("coverage-treppe: Endwert 100 % je Markt", not _bad_end, str(_bad_end[:3]))
    # Der Cut liegt genau auf den Schwellen, die die Segmentregel testet (70 / 85, Lauf ohne Buffer).
    _cbs = lambda seg: pd.to_numeric(gc1.loc[gc1["Segment_New"] == seg, "_c_before"], errors="coerce")
    check("coverage-treppe: Large unter 70 %", float(_cbs("Large Cap").max()) < 70.0 + 1e-9)
    check("coverage-treppe: Mid zwischen 70 % und 85 %",
          float(_cbs("Mid Cap").min()) >= 70.0 - 1e-9 and float(_cbs("Mid Cap").max()) < 85.0 + 1e-9)
    check("coverage-treppe: Small ab 85 %", float(_cbs("Small Cap").min()) >= 85.0 - 1e-9)

    # Size-Integrity-Auffuellung gegen denselben Baseline-Lauf
    integration_size_integrity(ctx, gc1)


# ══════════════════════════════════════════════════════════════════════════════
def main():
    pure = [test_index_series_integrity, test_clean_export_cols, test_excel_no_y2025_leak,
            test_to_excel_pct_date_cols,
            test_norm_fol_key, test_size_segment, test_normalize_index_weight,
            test_size_segment_entry_at_cut, test_helvetica_entry_at_cutoff, test_helvetica_micro_fillup,
            test_helvetica_adtv_maintenance, test_helvetica_high_price_rule,
            test_helvetica_ineligible, test_helvetica_dedup_most_liquid, test_build_index, test_build_index_thematic, test_atvr_dual_horizon, test_rank_band_buffer,
            test_build_index_company_count, test_ucits_cap, test_validate_factset_data, test_delisted_filter_numeric,
            test_with_fol_breakdown, test_fol_matrix_consistency,
            test_spinoff_seed_basic, test_spinoff_segment_override, test_spinoff_rejects,
            test_spinoff_neutral_when_empty, test_spinoff_other_key_fn,
            test_liquidity_incumbent_key, test_liquidity_exempt_missing,
            test_high_price_atvr_rule, test_high_price_neutral,
            test_atvr_four_cells, test_atvr_india_protection,
            test_atvr_real_high_price_titles, test_atvr_legs_3m_6m,
            test_atvr_zero_thresholds_neutral,
            test_atvr_6m_column,
            test_spinoff_horizon_windows, test_spinoff_horizon_entitlement,
            test_liquidity_exempt_per_horizon,
            test_liquidity_exempt_neutral,
            test_spinoff_loader_validation]
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
