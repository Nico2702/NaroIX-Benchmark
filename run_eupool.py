"""Europe-Pooled 48-Periodenlauf ohne Streamlit — App-Defaults + Mid/Small-Kante frei setzbar.

Aufruf:  python run_eupool.py <master.xlsx> <out_prefix> [ms_pp]
Schreibt <out_prefix>.pkl mit {periode: {isin: segment}} und der Summary-Tabelle.
"""
import sys, os, time, pickle
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class _Stub:
    def __init__(self): self.session_state = {}; self.secrets = {}
    def cache_data(self, *a, **k):
        if len(a) == 1 and callable(a[0]) and not k:
            return a[0]
        return lambda fn: fn
    def __getattr__(self, n): return lambda *a, **k: None


sys.modules.setdefault("streamlit", _Stub())
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import pandas as pd
import pipeline_core as C

MASTER = sys.argv[1]
OUT = sys.argv[2]
MS_PP = float(sys.argv[3]) if len(sys.argv) > 3 else 7.0
LIMIT = int(sys.argv[4]) if len(sys.argv) > 4 else 0
DUMP = len(sys.argv) > 5 and sys.argv[5] == 'dump'

# ── Referenzdaten (wie load_historical_data in der App) ───────────────────────
hc = pd.read_excel("Historical Classification.xlsx")
cols = ["Country"]
for c in hc.columns[1:]:
    try:
        cols.append(pd.to_datetime(c).date())
    except Exception:
        cols.append(c)
hc.columns = cols
hc["Country"] = hc["Country"].astype(str).str.upper().str.strip()

sd = pd.read_excel("Selection Dates.xlsx", usecols=[0])
sd.columns = ["Selection Date"]
selection_dates = sorted(pd.to_datetime(sd["Selection Date"]).dt.date.dropna().unique())

ci = pd.read_excel("China Inclusion Factor.xlsx")
ci["Selection Date"] = pd.to_datetime(ci["Selection Date"]).dt.date
china_if_map = dict(zip(ci["Selection Date"], ci["China Inclusion Factor"].astype(float)))

fol_matrix, fol_version, _ = C.load_fol_matrix()
fol_sector_fb = C.build_sector_fallback_table(fol_matrix)
ineligible_df = C.load_ineligible_list()
valid_iso = {d.isoformat() for d in selection_dates}
spinoff_df, _so_problems = C.load_spinoff_list(valid_iso)

t0 = time.time()
master_data = C.load_master_excel(MASTER, valid_iso)
if master_data.get("error"):
    sys.exit("Master-Fehler: " + str(master_data["error"]))
dates = master_data["detected_dates"]
print(f"master geladen: {len(dates)} Perioden ({dates[0]}..{dates[-1]})  {time.time()-t0:.0f}s",
      flush=True)
for w in master_data.get("warnings", [])[:10]:
    print("  warn:", w, flush=True)

# ── App-Defaults (Sidebar) ───────────────────────────────────────────────────
P = dict(
    thailand_mode="SHARE → NVDR", max_price=20000.0,
    exclude_hk_cny=True, exclude_country_risk_na=True,
    exclude_euro_mtf=True, exclude_etf_sicav=True,
    large_thr=70, mid_thr=85, small_thr=99, min_ff_pct=0.10, eumss_ff_ratio=0.50,
    adtv_dm=1_000_000.0, adtv_em=1_000_000.0, atvr_dm=0.0, atvr_em=0.0,
    if_cum_col="Adj_FF_MCap", atvr_mcap_col="Free Float MCap Y2025",
    max_price_atvr=0.10, m_max_price_atvr=0.05,
    buffer_min_ff=0.075, buffer_coverage=90,
    buffer_adtv_dm=750_000.0, buffer_adtv_em=750_000.0,
    buffer_atvr_dm=0.0, buffer_atvr_em=0.0,
    size_buffer_pp=5.0, asym_buffer=False, entry_at_cutoff=True,
    size_buffer_pp_ms=MS_PP,
    msci_logic=False, apply_small_buffer=True, small_buffer_pp=0.5,
    apply_size_integrity=False, si_k=1.00, si_edge_pp=90.0,
    excl_delisted=True, exclude_lon_usd_sec=True,
    label_before_liquidity=False,
    europe_pool=True, min_per_country=0,
)
CODE = "NX-EU-LM"
IX = C.INDEX_BY_CODE[CODE]

prev_keys, prev_seg = set(), {}
out = {}
rows = []
if LIMIT:
    dates = dates[:LIMIT]
for i, sd_iso in enumerate(dates):
    sd_dt = pd.Timestamp(sd_iso).date()
    cc = C.get_classification_dict(hc, sd_dt)
    cif = float(china_if_map.get(sd_dt, 0.20))
    snap = C.build_snapshot_from_master(master_data, sd_iso)
    is_seed = (len(prev_keys) == 0)

    so_keys, so_segs, so_log = C.seed_spinoff_incumbents(
        prev_keys, prev_seg, sd_iso, snap, spinoff_df)
    so_seeded = so_keys - set(prev_keys)
    so_exempt = C.spinoff_liquidity_exemptions(
        spinoff_df, sd_iso, snap, incumbent_keys=prev_keys, seeded_keys=so_seeded)

    res = C.run_selection_pipeline(
        snap.copy(), cc, cif, sd_dt.year,
        P["thailand_mode"], P["max_price"],
        P["exclude_hk_cny"], P["exclude_country_risk_na"],
        P["exclude_euro_mtf"], P["exclude_etf_sicav"],
        P["large_thr"], P["mid_thr"], P["small_thr"], P["min_ff_pct"], P["eumss_ff_ratio"],
        P["adtv_dm"], P["adtv_em"], P["atvr_dm"], P["atvr_em"],
        fol_matrix, fol_sector_fb, True,
        P["if_cum_col"], P["atvr_mcap_col"],
        max_price_atvr=P["max_price_atvr"], m_max_price_atvr=P["m_max_price_atvr"],
        incumbents_isin=so_keys, liquidity_exempt_missing=so_exempt,
        apply_buffer=(not is_seed),
        buffer_min_ff=P["buffer_min_ff"], buffer_coverage=P["buffer_coverage"],
        buffer_adtv_dm=P["buffer_adtv_dm"], buffer_adtv_em=P["buffer_adtv_em"],
        buffer_atvr_dm=P["buffer_atvr_dm"], buffer_atvr_em=P["buffer_atvr_em"],
        apply_size_buffer=(not is_seed), incumbent_segments=so_segs,
        size_buffer_pp=P["size_buffer_pp"], asym_buffer=P["asym_buffer"],
        entry_at_cutoff=P["entry_at_cutoff"], size_buffer_pp_ms=P["size_buffer_pp_ms"],
        msci_logic=P["msci_logic"],
        apply_small_buffer=P["apply_small_buffer"], small_buffer_pp=P["small_buffer_pp"],
        apply_size_integrity=P["apply_size_integrity"], si_k=P["si_k"], si_edge_pp=P["si_edge_pp"],
        exclude_lon_usd_sec=P["exclude_lon_usd_sec"],
        ineligible_df=ineligible_df, apply_ineligible=(not ineligible_df.empty),
        selection_date=sd_dt,
        label_before_liquidity=P["label_before_liquidity"],
        europe_pool=P["europe_pool"], min_per_country=P["min_per_country"],
    )
    gmc = res["gm_complete"]
    if DUMP and sd_iso == dates[-1]:
        _eu = gmc[gmc["Mapping Country"].fillna("").astype(str).str.upper().isin(C.EUROPE_COUNTRIES)
                  & (gmc["Classification"] == "DM")].copy()
        with open(OUT + "_dump.pkl", "wb") as _f:
            pickle.dump({"gm_complete_eu": _eu,
                         "incumbent_segments": dict(so_segs),
                         "incumbent_keys": set(so_keys),
                         "snapshot": snap,
                         "pool_symbols": set(res["gm_liq_cov"]["Symbol"].dropna()),
                         "pool_eu": res["gm_liq_cov"][
                             res["gm_liq_cov"]["Mapping Country"].fillna("").astype(str).str.upper()
                             .isin(C.EUROPE_COUNTRIES)].copy(),
                         "date": sd_iso}, _f)
        print("  dump geschrieben: %s_dump.pkl (EU-Zeilen %d)" % (OUT, len(_eu)), flush=True)
    cons = C.build_index(gmc, IX["region"], IX["segments"],
                         industries=IX.get("industries"), top_n=IX.get("top_n"),
                         cap=IX.get("cap"), apply_cap=False)

    keys = C._match_key(cons)
    out[sd_iso] = {
        "n": len(cons),
        "isin": set(cons["ISIN"].fillna("").astype(str).str.strip().str.upper()) - {""},
        "keys": set(keys) - {""},
        "cutoff": float(res.get("europe_pool_cutoff") or 0.0),
        "detail": cons[[c for c in ["ISIN", "Symbol", "Name", "Mapping Country", "Segment_New",
                                    "Total MCap Y2025", "Free Float MCap Y2025", "Adj_FF_MCap",
                                    "_c_before"] if c in cons.columns]].copy(),
        "pool_n": int(len(res["gm_liq_cov"])),
    }
    rows.append((sd_iso, len(cons), out[sd_iso]["cutoff"]))
    print(f"  {sd_iso}  n={len(cons):4d}  pool={out[sd_iso]['pool_n']:6d} "
          f"cutoff={out[sd_iso]['cutoff']/1e9:8.2f} bn  ({time.time()-t0:.0f}s)", flush=True)

    # Incumbent-State fortschreiben (wie der Tab: aus gm_complete)
    imi = gmc[gmc["Segment_New"].isin(["Large Cap", "Mid Cap", "Small Cap"])]
    k_imi = C._match_key(imi)
    prev_keys = set(k_imi)
    prev_seg = {i: s for i, s in zip(k_imi.values, imi["Segment_New"].values) if i}

with open(OUT + ".pkl", "wb") as f:
    pickle.dump({"rows": rows, "out": out, "master": MASTER, "ms_pp": MS_PP}, f)
print(f"\nfertig in {time.time()-t0:.0f}s -> {OUT}.pkl", flush=True)
