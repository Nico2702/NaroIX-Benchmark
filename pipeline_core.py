"""pipeline_core.py — Streamlit-free NaroIX selection engine.
Pure logic extracted from naroix_benchmark.py (behaviour-preserving). Importable
headless (backtesting, tests). The Streamlit UI lives in naroix_benchmark.py."""
import re
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import date as _date

def format_bn(val):
    if val >= 1e12: return f"{val/1e12:.2f}T"
    if val >= 1e9:  return f"{val/1e9:.2f}B"
    if val >= 1e6:  return f"{val/1e6:.2f}M"
    return f"{val:.0f}"

# Internal canonical column names carry a legacy "Y2025" suffix (set in
# build_snapshot_from_master so the pipeline stays period-agnostic). That suffix is
# NOT a data year — each period holds its own snapshot values — so it must never
# surface in a user-facing table or export. clean_export_cols() strips it to a
# year-agnostic label; to_excel_multi() applies it to every sheet centrally, so no
# export can leak the internal name regardless of which call site builds the frame.
EXPORT_COL_RENAME = {
    "Total MCap Y2025":      "Total MCap",
    "Share MCap Y2025":      "Share MCap",
    "Free Float MCap Y2025": "Free Float MCap",
    "1M ADTV Y2025":         "1M ADTV",
    "3M ADTV Y2025":         "3M ADTV",
    "6M ADTV Y2025":         "6M ADTV",
    "12M ADTV Y2025":        "12M ADTV",
}

def _place_share_mcap(df):
    """Position 'Share MCap' directly between 'Total MCap' and 'Free Float MCap'
    (operates on the clean export labels). No-op if any of the three is absent."""
    cols = list(df.columns)
    if not ({"Share MCap", "Total MCap", "Free Float MCap"} <= set(cols)):
        return df
    cols = [c for c in cols if c != "Share MCap"]
    i = cols.index("Total MCap")
    return df[cols[:i + 1] + ["Share MCap"] + cols[i + 1:]]

def clean_export_cols(df):
    """Rename internal canonical '* Y2025' columns to clean, year-agnostic labels
    for display/export. Non-mutating (returns a renamed view/copy)."""
    return df.rename(columns={k: v for k, v in EXPORT_COL_RENAME.items() if k in df.columns})

def with_fol_breakdown(df):
    """For constituent-level tables/exports (those carrying both Adj_FF_MCap and
    Index_Weight), surface the FOL limit and the Inclusion Factor immediately BEFORE
    Adj_FF_MCap, so the computation `Adj_FF_MCap = Free Float MCap × IF`
    (IF = min(1, FOL / Free Float %), or the China CIF) is transparent in the output.
    `FOL_Value` is shown as `FOL`. No-op if the relevant columns are absent. Non-mutating."""
    if "Adj_FF_MCap" not in df.columns or "Index_Weight" not in df.columns:
        return df
    out = df.rename(columns={"FOL_Value": "FOL"}) if "FOL_Value" in df.columns else df.copy()
    block = [c for c in ("FOL", "IF") if c in out.columns]
    if not block:
        return out
    cols = [c for c in out.columns if c not in block]
    pos = cols.index("Adj_FF_MCap")
    return out[cols[:pos] + block + cols[pos:]]

def to_excel_multi(sheets: dict):
    """Export multiple DataFrames as sheets. sheets = {sheet_name: df}.
    Uses xlsxwriter (markedly faster than openpyxl when writing many sheets);
    falls back to openpyxl if xlsxwriter is unavailable.
    Per sheet: FOL/IF are surfaced before Adj_FF_MCap (with_fol_breakdown), the
    internal 'Y2025' suffix is stripped (clean_export_cols), and Share MCap is placed
    between Total MCap and Free Float MCap (_place_share_mcap)."""
    try:
        import xlsxwriter  # noqa: F401
        _engine = "xlsxwriter"
    except Exception:
        _engine = "openpyxl"
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine=_engine) as writer:
        for sheet_name, df in sheets.items():
            _place_share_mcap(clean_export_cols(with_fol_breakdown(df))).to_excel(
                writer, sheet_name=sheet_name[:31], index=False)
    return buf.getvalue()

def normalize_index_weight(df, adj_col="Adj_FF_MCap"):
    """Recalculate Index_Weight based on the sheet's own Adj_FF_MCap total, sorted descending.
    Weights sum to exactly 100.0000 by assigning the floating-point remainder to the largest stock.
    """
    df = df.copy()
    tot = df[adj_col].sum() if adj_col in df.columns else 0
    if tot > 0:
        df["Index_Weight"] = (df[adj_col] / tot * 100).round(6)
        # Assign floating-point remainder to the largest stock so sum = exactly 100.000000
        _diff = round(100.0 - df["Index_Weight"].sum(), 6)
        if _diff != 0:
            _top_idx = df[adj_col].idxmax()
            df.loc[_top_idx, "Index_Weight"] = round(df.loc[_top_idx, "Index_Weight"] + _diff, 6)
    else:
        df["Index_Weight"] = 0.0
    return df.sort_values("Index_Weight", ascending=False)

_SEG_STD = ["Large Cap", "Mid Cap"]

_SEG_AC  = ["Large Cap", "Mid Cap", "Small Cap"]

# "Tech" universe via FactSet Industry (granular — deliberately excludes Aerospace &
# Defense, which sits in the Electronic Technology *sector* but is not tech). Region-agnostic:
# used by the US Tech AND Europe Tech products. Kern (echte Tech-Industrien) + Internet Retail.
TECH_INDUSTRIES = [
    "Internet Software/Services",     # Alphabet, Meta, Netflix
    "Semiconductors",                 # Nvidia, Broadcom, AMD, Micron, Intel
    "Packaged Software",              # Microsoft, Oracle
    "Telecommunications Equipment",   # Apple, Cisco
    "Information Technology Services",
    "Computer Peripherals",
    "Computer Processing Hardware",
    "Electronic Components",
    "Electronic Equipment/Instruments",
    "Electronic Production Equipment",
    "Data Processing Services",
    "Internet Retail",                # Amazon, MercadoLibre, PDD
]

INDEX_SERIES = [
    {"code": "NX-EU-LM", "name": "NaroIX Europe Markets Index",               "region": "EU", "segments": _SEG_STD,        "coverage": "0–85%",  "vs": "MSCI Europe"},
    {"code": "NX-DM-LM", "name": "NaroIX Developed Markets Index",            "region": "DM", "segments": _SEG_STD,        "coverage": "0–85%",  "vs": "MSCI World"},
    {"code": "NX-DM-L",  "name": "NaroIX Developed Markets Large Cap Index",  "region": "DM", "segments": ["Large Cap"],   "coverage": "0–70%",  "vs": "MSCI World Large Cap"},
    {"code": "NX-DM-M",  "name": "NaroIX Developed Markets Mid Cap Index",    "region": "DM", "segments": ["Mid Cap"],     "coverage": "70–85%", "vs": "MSCI World Mid Cap"},
    {"code": "NX-DM-S",  "name": "NaroIX Developed Markets Small Cap Index",  "region": "DM", "segments": ["Small Cap"],   "coverage": "85–99%", "vs": "MSCI World Small Cap"},
    {"code": "NX-DM-AC", "name": "NaroIX Developed Markets All Cap Index",    "region": "DM", "segments": _SEG_AC,         "coverage": "0–99%",  "vs": "MSCI World IMI"},
    {"code": "NX-EM-LM", "name": "NaroIX Emerging Markets Index",             "region": "EM", "segments": _SEG_STD,        "coverage": "0–85%",  "vs": "MSCI EM"},
    {"code": "NX-EM-L",  "name": "NaroIX Emerging Markets Large Cap Index",   "region": "EM", "segments": ["Large Cap"],   "coverage": "0–70%",  "vs": "MSCI EM Large Cap"},
    {"code": "NX-EM-M",  "name": "NaroIX Emerging Markets Mid Cap Index",     "region": "EM", "segments": ["Mid Cap"],     "coverage": "70–85%", "vs": "MSCI EM Mid Cap"},
    {"code": "NX-EM-S",  "name": "NaroIX Emerging Markets Small Cap Index",   "region": "EM", "segments": ["Small Cap"],   "coverage": "85–99%", "vs": "MSCI EM Small Cap"},
    {"code": "NX-EM-AC", "name": "NaroIX Emerging Markets All Cap Index",     "region": "EM", "segments": _SEG_AC,         "coverage": "0–99%",  "vs": "MSCI EM IMI"},
    {"code": "NX-GM-LM", "name": "NaroIX Global Markets Index",               "region": "GM", "segments": _SEG_STD,        "coverage": "0–85%",  "vs": "MSCI ACWI"},
    {"code": "NX-GM-L",  "name": "NaroIX Global Markets Large Cap Index",     "region": "GM", "segments": ["Large Cap"],   "coverage": "0–70%",  "vs": "MSCI ACWI Large Cap"},
    {"code": "NX-GM-M",  "name": "NaroIX Global Markets Mid Cap Index",       "region": "GM", "segments": ["Mid Cap"],     "coverage": "70–85%", "vs": "MSCI ACWI Mid Cap"},
    {"code": "NX-GM-S",  "name": "NaroIX Global Markets Small Cap Index",     "region": "GM", "segments": ["Small Cap"],   "coverage": "85–99%", "vs": "MSCI ACWI Small Cap"},
    {"code": "NX-GM-AC", "name": "NaroIX Global Markets All Cap Index",       "region": "GM", "segments": _SEG_AC,         "coverage": "0–99%",  "vs": "MSCI ACWI IMI"},
    # Thematische / Fixed-Count-Produkte (Top-N nach Total MCap, cap-gewichtet nach Adj_FF).
    # buffer_hard/buffer_exit = Rang-Band-Buffer (Solactive-Stil): hart drin ≤ buffer_hard,
    # Bestandstitel bis Rang buffer_exit füllen auf top_n auf (nur Multi-Period mit Vorperiode).
    {"code": "NX-US-500",  "name": "NaroIX US 500 Index",      "region": "US", "segments": _SEG_AC, "top_n": 500, "buffer_hard": 425, "buffer_exit": 600, "coverage": "Top 500",      "vs": "S&P 500"},
    {"code": "NX-US-T100", "name": "NaroIX US Tech 100 Index", "region": "US", "segments": _SEG_AC, "top_n": 100, "buffer_hard": 85, "buffer_exit": 120, "industries": TECH_INDUSTRIES, "coverage": "Top 100 Tech", "vs": "Nasdaq-100"},
    {"code": "NX-US-T",    "name": "NaroIX US Tech Index",     "region": "US", "segments": _SEG_AC,               "industries": TECH_INDUSTRIES, "coverage": "Tech (All Cap)", "vs": "—"},
    {"code": "NX-EU-T",    "name": "NaroIX Europe Tech Index", "region": "EU", "segments": _SEG_AC,               "industries": TECH_INDUSTRIES, "coverage": "Tech (All Cap)", "vs": "—"},
    {"code": "NX-EU-T30",  "name": "NaroIX Europe Tech 30 Index", "region": "EU", "segments": _SEG_AC, "top_n": 30, "buffer_hard": 25, "buffer_exit": 36, "industries": TECH_INDUSTRIES, "coverage": "Top 30 Tech", "vs": "—"},
    {"code": "NX-WL-100",  "name": "NaroIX World 100 Index",   "region": "GM", "segments": _SEG_AC, "top_n": 100, "buffer_hard": 85, "buffer_exit": 120, "coverage": "Top 100",      "vs": "FTSE All-World 100"},
]

INDEX_BY_CODE = {ix["code"]: ix for ix in INDEX_SERIES}

INDEX_BY_NAME = {ix["name"]: ix for ix in INDEX_SERIES}

def _rank_band_select(df, top_n, incumbents, buffer_hard, buffer_exit, id_col="ISIN"):
    """Solactive-GBS-style rank-band buffer for a fixed-count index (df already sorted
    by rank, best first; 1-based rank = row position). `id_col` identifies each row
    (security ISIN, or a company key) and is matched against `incumbents`.
      1. ranks ≤ buffer_hard       → hard-included (anyone).
      2. remaining slots up to top_n → current incumbents ranked (buffer_hard, buffer_exit], by rank.
      3. if still short            → highest-ranked remaining names (newcomers), by rank.
    Returns the selected sub-DataFrame (≤ top_n rows). The hard cut MUST be < top_n,
    otherwise no slots are reserved and the buffer is vacuous (= plain top-N)."""
    n = int(top_n)
    rank = np.arange(len(df)) + 1                       # 1-based rank by row order
    ids = df[id_col].astype(str).to_numpy() if id_col in df.columns else np.array([""] * len(df))
    inc = np.isin(ids, list(incumbents))
    keep = list(np.where(rank <= int(buffer_hard))[0])  # step 1: hard top
    remaining = n - len(keep)
    if remaining > 0:
        band_inc = np.where((rank > int(buffer_hard)) & (rank <= int(buffer_exit)) & inc)[0]  # step 2
        keep += list(band_inc[:remaining])
        still = n - len(keep)
        if still > 0:                                   # step 3: fill with highest-ranked remaining
            kept = set(keep)
            fill = [p for p in range(len(df)) if p >= int(buffer_hard) and p not in kept]
            keep += fill[:still]
    return df.iloc[sorted(keep)[:n]]

def build_index(gm_complete, region, segments, industries=None, top_n=None,
                rank_col="Total MCap Y2025", incumbents_isin=None,
                buffer_hard=None, buffer_exit=None):
    """Scope a pipeline result to ONE index product and re-normalise weights to 100%.

    region: 'DM' | 'EM' | 'GM' (=DM+EM) | 'EU' (DM ∩ Europe countries) | 'US' (Exchange
            Country = United States, i.e. US-listed). FM is never included.
    segments: size buckets to draw from (the eligible pool).
    industries: optional iterable of FactSet Industry names to restrict to (e.g. US Tech).
    top_n: optional fixed constituent count — keep the largest `top_n` by `rank_col`
           (Total MCap by default), e.g. US 500 / World 100 / US Tech 100.
    incumbents_isin + buffer_hard/buffer_exit: optional Solactive-style rank-band buffer
           (only with top_n). `incumbents_isin` holds prior-period COMPANY keys (Entity IDs).
           When given, prior members are retained inside the band to cut turnover.
    top_n counts at the COMPANY level (Entity ID): the top_n *companies* by Total MCap are
           selected, then ALL their share lines are included (S&P/Solactive step 6) — so a
           500-company index holds ~505 securities (Alphabet A+C, Fox A+B, …).
    Weighting always = Adj_FF_MCap (normalize_index_weight), independent of the ranking.
    Single source of truth together with INDEX_SERIES."""
    if region == "EU":
        region_mask = (
            (gm_complete["Classification"] == "DM")
            & gm_complete["Mapping Country"].fillna("").astype(str).str.upper().isin(EUROPE_COUNTRIES)
        )
    elif region == "US":
        region_mask = gm_complete["Exchange Country Name"].fillna("").astype(str).str.upper() == "UNITED STATES"
    else:
        region_cls = {"DM": ["DM"], "EM": ["EM"], "GM": ["DM", "EM"]}[region]
        region_mask = gm_complete["Classification"].isin(region_cls)
    mask = region_mask & gm_complete["Segment_New"].isin(segments)
    if industries:
        mask = mask & gm_complete["FactSet Industry"].isin(list(industries))
    df = gm_complete[mask].copy()
    if top_n:
        # Rank securities by rank_col (Total MCap), Adj_FF_MCap as tiebreaker — best first.
        _rank = pd.to_numeric(df.get(rank_col), errors="coerce").fillna(0)
        df = (df.assign(_rank=_rank, _tb=pd.to_numeric(df.get("Adj_FF_MCap"), errors="coerce").fillna(0))
                .sort_values(["_rank", "_tb"], ascending=[False, False])
                .reset_index(drop=True))
        # Company key (Entity ID, fallback ISIN). Total MCap is company-wide, so a company's
        # rank is its best line's position. Count to top_n COMPANIES, then keep ALL their lines.
        if "Entity ID" in df.columns:
            _ck = df["Entity ID"].fillna("").astype(str).str.strip()
            _ck = _ck.where(_ck != "", _norm_isin(df["ISIN"]))
        else:
            _ck = _norm_isin(df["ISIN"])
        df = df.assign(_ckey=_ck)
        comp = df.drop_duplicates("_ckey", keep="first").reset_index(drop=True)  # one row/company, rank order
        if incumbents_isin and buffer_hard and buffer_exit:
            keys = set(_rank_band_select(comp, top_n, incumbents_isin, buffer_hard, buffer_exit, id_col="_ckey")["_ckey"])
        else:
            keys = set(comp["_ckey"].head(int(top_n)))   # plain top-N companies (seed / buffer off)
        df = df[df["_ckey"].isin(keys)].drop(columns=["_rank", "_tb", "_ckey"])
    return normalize_index_weight(df)

def _norm_isin(s):
    """Normalisiere eine ISIN- (oder Key-)Series: NaN→'', str, getrimmt, GROSS.
    Eine Stelle für das überall wiederholte fillna("").astype(str).str.strip().str.upper()."""
    return s.fillna("").astype(str).str.strip().str.upper()


def _size_segment(prior, c_before, large_thr=70.0, mid_thr=85.0, bw=5.0):
    """Map (prior segment, _c_before coverage %) → size segment with hysteresis.

    Size Buffer: incumbents are 'sticky' within a ±bw band around the Large/Mid
    (large_thr) and Mid/Small (mid_thr) boundaries, so companies don't flip-flop
    between size buckets at each rebalancing. Newcomers (prior None/unknown) are
    classified at the plain cut-offs — identical to the legacy hard-cut behaviour.

    Operates on _c_before (coverage BEFORE the stock's own FF MCap — the straddle
    rule, HANDOVER §2.3). The Small↔Micro lower bound stays governed by EUMSS and
    is NOT handled here (HANDOVER §2.6).
    """
    lo_lm, hi_lm = large_thr - bw, large_thr + bw   # e.g. 65 / 75
    lo_ms, hi_ms = mid_thr - bw, mid_thr + bw        # e.g. 80 / 90
    if prior == "Large Cap":
        if c_before <= hi_lm: return "Large Cap"     # ≤75 → stays Large
        if c_before <= hi_ms: return "Mid Cap"       # ≤90 → drops to Mid
        return "Small Cap"                           # >90 → drops to Small
    if prior == "Mid Cap":
        if c_before < lo_lm:  return "Large Cap"      # <65 → rises to Large
        if c_before <= hi_ms: return "Mid Cap"        # ≤90 → stays Mid
        return "Small Cap"                            # >90 → drops to Small
    if prior == "Small Cap":
        if c_before < lo_lm:  return "Large Cap"      # <65 → rises to Large
        if c_before < lo_ms:  return "Mid Cap"        # <80 → rises to Mid
        return "Small Cap"                            # ≥80 → stays Small
    # newcomer / unknown / Micro → plain cut-offs (= legacy behaviour)
    if c_before < large_thr:  return "Large Cap"      # <70
    if c_before < mid_thr:    return "Mid Cap"        # <85
    return "Small Cap"

def build_wide_matrix(period_dict):
    """Baue die Gewichtsmatrix (Aktie × Periode) für eine Index-Serie — vektorisiert.

    period_dict: {selection_date_iso: DataFrame mit ISIN + Index_Weight + Statik}

    Ersetzt die alte O(Stocks×Perioden)-Doppelschleife (die pro Zelle die komplette
    ISIN-Spalte neu normalisierte + maskierte) durch ein einziges groupby/concat/join.

    Returns: (wide_df, present_periods) oder (None, sorted_periods) wenn keine Daten.
    """
    sorted_periods = sorted(period_dict.keys())
    static_cols = ["Exchange Ticker", "Name", "ISIN", "Classification",
                   "Mapping Country", "Exchange Country Name", "Segment_New"]

    w_series = []     # eine Series pro Periode: index=ISIN, value=Index_Weight
    info_parts = []   # Statik je ISIN (aufgelöst aus der zuletzt vorhandenen Periode)
    for _ord, sd in enumerate(sorted_periods):
        df = period_dict[sd]
        if "ISIN" not in df.columns or "Index_Weight" not in df.columns or len(df) == 0:
            continue
        d = df.copy()
        d["ISIN"] = d["ISIN"].fillna("").astype(str).str.strip()
        d = d[d["ISIN"] != ""]
        if d.empty:
            continue
        s = d.groupby("ISIN")["Index_Weight"].first().round(6)
        s.name = sd
        w_series.append(s)
        present = [c for c in static_cols if c in d.columns]
        part = d[present].drop_duplicates("ISIN", keep="first").copy()
        part["_ord"] = _ord
        info_parts.append(part)

    if not w_series:
        return None, sorted_periods

    weight_mat = pd.concat(w_series, axis=1)  # index=ISIN, columns=Perioden
    present_periods = [c for c in sorted_periods if c in weight_mat.columns]

    # keep="last" → Statik (v.a. Segment) aus der ZULETZT vorhandenen Periode der Aktie
    # (sort_values("_ord") aufsteigend, also ist die letzte Zeile die jüngste Periode).
    # Passt zur Sortierung nach letztem Gewicht und zeigt den aktuellen Segment-Stand.
    info_all = (pd.concat(info_parts, ignore_index=True)
                  .sort_values("_ord")
                  .drop_duplicates("ISIN", keep="last")
                  .drop(columns=["_ord"])
                  .rename(columns={"Segment_New": "Segment"})
                  .set_index("ISIN"))

    wide = weight_mat.join(info_all, how="left")

    # Sortierung: Gewicht in der zuletzt vorhandenen Periode (letzter non-null Wert)
    _last_w = weight_mat[present_periods].ffill(axis=1).iloc[:, -1].fillna(0.0)
    wide = wide.loc[_last_w.sort_values(ascending=False).index].reset_index()

    static_order = [c for c in ["Exchange Ticker", "Name", "ISIN", "Classification",
                                "Mapping Country", "Exchange Country Name", "Segment"]
                    if c in wide.columns]
    wide = wide[static_order + present_periods]
    return wide, present_periods

def build_segment_matrix(period_dict):
    """Baue die Segment-Wanderungs-Matrix (Aktie × Periode) — analog build_wide_matrix,
    aber die Zellen enthalten das Size-Segment (Large/Mid/Small) statt des Gewichts.
    Leer = Aktie in dieser Periode nicht im Index. Sortiert: meiste Segment-Wechsel zuerst.

    Returns: (seg_df, present_periods) oder (None, sorted_periods) wenn keine Daten.
    """
    sorted_periods = sorted(period_dict.keys())
    static_cols = ["Exchange Ticker", "Name", "ISIN", "Classification",
                   "Mapping Country", "Exchange Country Name"]
    _short = {"Large Cap": "Large", "Mid Cap": "Mid", "Small Cap": "Small", "Micro Cap": "Micro"}

    seg_series = []
    info_parts = []
    for _ord, sd in enumerate(sorted_periods):
        df = period_dict[sd]
        if "ISIN" not in df.columns or "Segment_New" not in df.columns or len(df) == 0:
            continue
        d = df.copy()
        d["ISIN"] = d["ISIN"].fillna("").astype(str).str.strip()
        d = d[d["ISIN"] != ""]
        if d.empty:
            continue
        s = d.groupby("ISIN")["Segment_New"].first().map(lambda v: _short.get(v, v))
        s.name = sd
        seg_series.append(s)
        present = [c for c in static_cols if c in d.columns]
        part = d[present].drop_duplicates("ISIN", keep="first").copy()
        part["_ord"] = _ord
        info_parts.append(part)

    if not seg_series:
        return None, sorted_periods

    seg_mat = pd.concat(seg_series, axis=1)
    present_periods = [c for c in sorted_periods if c in seg_mat.columns]

    info_all = (pd.concat(info_parts, ignore_index=True)
                  .sort_values("_ord")
                  .drop_duplicates("ISIN", keep="last")
                  .drop(columns=["_ord"])
                  .set_index("ISIN"))

    wide = seg_mat.join(info_all, how="left")

    # Sortierung: meiste distinkte Segmente (= Wanderer) zuerst, dann meiste Perioden präsent
    _chg = seg_mat[present_periods].apply(lambda r: len(set(r.dropna())), axis=1)
    _pres = seg_mat[present_periods].notna().sum(axis=1)
    _order = pd.DataFrame({"chg": _chg, "pres": _pres}).sort_values(
        ["chg", "pres"], ascending=[False, False]).index
    wide = wide.loc[_order].reset_index()

    static_order = [c for c in ["Exchange Ticker", "Name", "ISIN", "Classification",
                                "Mapping Country", "Exchange Country Name"]
                    if c in wide.columns]
    wide = wide[static_order + present_periods]
    return wide, present_periods

EUROPE_COUNTRIES = {
    # Westeuropa / Nordeuropa (DM)
    "AUSTRIA", "BELGIUM", "DENMARK", "FINLAND", "FRANCE",
    "GERMANY", "IRELAND", "ITALY", "NETHERLANDS", "NORWAY",
    "PORTUGAL", "SPAIN", "SWEDEN", "SWITZERLAND", "UNITED KINGDOM",
    # Osteuropa / Südeuropa (Status wechselnd DM/EM)
    "POLAND",         # DM ab 2024-02-21
    "GREECE",         # aktuell EM
    "HUNGARY",        # aktuell EM
    "CZECH REPUBLIC", # aktuell EM
}

# Tax-Havens / Offshore-/Briefkasten-Domizile: in der Mapping-Fallback-Regel werden diese
# Laender als nicht-aussagekraeftig behandelt (Risk-First ueberspringt sie). Malta & Hongkong
# bewusst NICHT enthalten (echte Volkswirtschaften). Schreibvarianten (MACAU/MACAO,
# ST. LUCIA/SAINT LUCIA) bewusst doppelt. Identisch zur FactSet-Screener-Standardformel.
HAVENS = {
    "CAYMAN ISLANDS", "BERMUDA", "BAHAMAS", "JERSEY", "GUERNSEY", "BRITISH VIRGIN ISLANDS",
    "ISLE OF MAN", "GIBRALTAR", "LUXEMBOURG", "MARSHALL ISLANDS", "PANAMA", "MACAU", "MACAO",
    "CYPRUS", "MAURITIUS", "MONACO", "LIECHTENSTEIN", "CURACAO", "NETHERLANDS ANTILLES",
    "BARBADOS", "LIBERIA", "ANGUILLA", "TURKS AND CAICOS ISLANDS", "ST. LUCIA", "SAINT LUCIA",
    "ANTIGUA AND BARBUDA", "SEYCHELLES", "BELIZE", "SAMOA", "VANUATU", "COOK ISLANDS", "ARUBA",
    "SAN MARINO", "ANDORRA",
}

def derive_mapping_country(df):
    """Mapping Country bestimmen — EINE Quelle der Wahrheit fuer Pipeline UND UI.
    PRIMAER das Feld 'Mapping Country' (= 'Country Mapping' aus dem Master-File, falls befuellt).
    Fallback fuer leere Zeilen: Risk-First (Country of Risk -> Country of Incorp -> Exchange;
    Tax-Havens/leer werden uebersprungen) — identisch zur FactSet-Screener-Standardformel.
    Gibt eine Series (Index wie df) zurueck; robust gegen fehlende Spalten."""
    def _u(name):
        s = df[name] if name in df.columns else pd.Series("", index=df.index)
        return s.fillna("").astype(str).str.strip().str.upper()
    _ecn, _coi, _cor = _u("Exchange Country Name"), _u("Country of Incorp"), _u("Country of Risk")
    _risk_ok = (_cor != "") & (~_cor.isin(HAVENS))
    _inc_ok  = (_coi != "") & (~_coi.isin(HAVENS))
    _fallback = np.where(_risk_ok, _cor, np.where(_inc_ok, _coi, _ecn))
    if "Mapping Country" in df.columns:
        _mm = _u("Mapping Country")
        return pd.Series(np.where(_mm != "", _mm, _fallback), index=df.index)
    return pd.Series(_fallback, index=df.index)

def apply_universe_exclusions(df, max_price=None, excl_hk_cny=True, excl_cor_na=True,
                              excl_naics=True, excl_euro=True, excl_etf=True, excl_delisted=True):
    """Investability-Exclusions (Pipeline-Step 3) — EINE Quelle der Wahrheit fuer Engine UND
    UI-Diagnostik. FF MCap > 0 immer; alles andere per Flag. Behaltungstreu extrahiert aus
    build_new_universe. (Die UI ruft mit excl_delisted=False fuer ihr 'All-Listings'-df_raw_all.)"""
    import re as _re
    df = df.copy()
    # Defensiv: die beiden numerisch verglichenen Spalten sicher zu Zahlen coercen
    # (robust gegen String-/Arrow-Backends, unabhaengig vom Aufrufer).
    df["Free Float MCap Y2025"] = pd.to_numeric(df["Free Float MCap Y2025"], errors="coerce").fillna(0)
    if "Closing Price" in df.columns:
        df["Closing Price"] = pd.to_numeric(df["Closing Price"], errors="coerce").fillna(0)
    df = df[df["Free Float MCap Y2025"] > 0].copy()
    if max_price:
        df = df[df["Closing Price"].fillna(0) < max_price].copy()
    if excl_hk_cny:
        df = df[~(df["Exchange Ticker"].str.contains("HKG", na=False) & (df["Trading Currency"] == "CNY"))].copy()
    if excl_cor_na:
        df = df[df["Country of Risk"].fillna("") != "@NA"].copy()
    if excl_naics:
        df = df[~df["NAICS"].fillna("").str.contains("Open-End Investment Fund", case=False, na=False)].copy()
    if excl_euro:
        df = df[~df["Exchange Name"].fillna("").isin(["Euro MTF", "@NA"])].copy()
    if excl_etf:
        df = df[~df["Name"].fillna("").str.contains(_re.compile(r'\bETF\b|\bSICAV\b|%', _re.IGNORECASE))].copy()
    if excl_delisted and "Listing Status" in df.columns:
        _ls = pd.to_numeric(df["Listing Status"], errors="coerce").fillna(0)
        df = df[_ls != 1].copy()
    return df

def fif_inclusion_factor(fol_value, ff_pct):
    """FIF-Clamp: IF = min(1, FOL / Free-Float-%). Eine Formel-Definition fuer Engine + UI-Audit.
    Gibt 1.0 zurueck wenn FF<=0 oder Eingaben unbrauchbar (pre_investable/Thailand werden vom
    Aufrufer separat behandelt)."""
    try:
        f, ff = float(fol_value), float(ff_pct)
    except (TypeError, ValueError):
        return 1.0
    return min(1.0, f / ff) if ff > 0 else 1.0

FOL_COUNTRY_CODE_MAP = {
    "INDIA":              "IN",
    "VIETNAM":            "VN",
    "SAUDI ARABIA":       "SA",
    "QATAR":              "QA",
    "UNITED ARAB EMIRATES":"AE",
    "MALAYSIA":           "MY",
    "KUWAIT":             "KW",
    "INDONESIA":          "ID",
    "SOUTH KOREA":        "KR",
    "PHILIPPINES":        "PH",
    "THAILAND":           "TH",
    "TAIWAN":             "TW",   # ab FOL v1.7+ (12. Jurisdiktion); ohne diesen Eintrag bliebe Taiwans FOL wirkungslos
}

MASTER_DYNAMIC_PREFIXES = [
    "Total MCap",
    "Share MCap",          # informativ, derzeit nicht in der Pipeline genutzt
    "Float MCap",          # FF MCap (Master-File getrennt geschrieben)
    "FloatMCap",           # ältere zusammengeschriebene Variante (Rückwärtskompatibilität)
    "Free Float MCap",     # Single-Snapshot-Standard
    "Float PCT",
    "Free Float Percent",
    "Closing Price",
    "1M ADTV",
    "3M ADTV",
    "6M ADTV",
    "12M ADTV",
    "Listing Status",
]

MASTER_STATIC_REQUIRED = [
    "Symbol", "Name", "Listing", "Sec Type", "ISIN", "Entity ID", "NAICS",
    "Exchange Ticker", "Trading Currency", "Exchange Name",
    "Country of Incorp", "Country of Risk",
    # Klassifikations-Felder — werden im Loader auf normalisierte Namen gemappt
]

def validate_factset_data(df_raw):
    """
    Daten-Konsistenz-Check für FactSet-Snapshots.
    Wird nach dem Upload aufgerufen — zeigt Warnings bei methodisch
    inkonsistenten Datenpunkten.
    Anomalien sind nicht-blockierend; die Pipeline läuft trotzdem,
    aber der User wird auf potenzielle Daten-Drift aufmerksam gemacht.
    """
    anomalies = []  # list of (severity, label, mask)

    # Numerische Felder defensiv konvertieren (Snapshot kommt teils als str)
    def _num(col):
        if col not in df_raw.columns:
            return pd.Series([0.0]*len(df_raw), index=df_raw.index)
        return pd.to_numeric(df_raw[col], errors="coerce").fillna(0)

    ff_mcap   = _num("Free Float MCap Y2025")
    tot_mcap  = _num("Total MCap Y2025")
    ff_pct    = pd.to_numeric(df_raw.get("Free Float Percent"), errors="coerce") if "Free Float Percent" in df_raw.columns else pd.Series([float("nan")]*len(df_raw))
    price     = _num("Closing Price")
    adtv_3m   = _num("3M ADTV Y2025")
    adtv_6m   = _num("6M ADTV Y2025")

    # 1. FF MCap > 0 aber FF% = 0/NaN (Hauptcheck)
    mask1 = (ff_mcap > 0) & ((ff_pct.isna()) | (ff_pct == 0))
    if mask1.sum() > 0:
        anomalies.append(("error", "FF MCap > 0 aber FF% leer/0", mask1))

    # 2. Total MCap = 0/NaN aber FF MCap > 0 (umgekehrte Anomalie)
    mask2 = (ff_mcap > 0) & (tot_mcap <= 0)
    if mask2.sum() > 0:
        anomalies.append(("error", "FF MCap > 0 aber Total MCap = 0", mask2))

    # 3. ADTV negativ
    mask3 = (adtv_3m < 0) | (adtv_6m < 0)
    if mask3.sum() > 0:
        anomalies.append(("error", "ADTV negativ", mask3))

    # 4. FF% > 100% (theoretisch unmöglich)
    mask4 = ff_pct > 1.0
    if mask4.sum() > 0:
        anomalies.append(("warning", "FF% > 100%", mask4))

    # 5. Closing Price ≤ 0 bei aktiven Primary-Stocks mit substanzieller FF MCap
    # (OTC, delisted und Micro-Caps sind erwartbar ohne Preis-Daten — würden Pipeline
    # ohnehin nicht überleben, also bewusst ausgeschlossen aus diesem Check)
    listing       = df_raw.get("Listing", pd.Series([""]*len(df_raw))).fillna("")
    listing_stat  = df_raw.get("Listing Status", pd.Series(["0"]*len(df_raw))).fillna("0").astype(str).str.strip()
    mask5 = (ff_mcap > 100e6) & (price <= 0) & (listing == "Primary") & (listing_stat != "1")
    if mask5.sum() > 0:
        anomalies.append(("warning", "Closing Price ≤ 0 bei aktivem Primary-Stock (FF > $100M)", mask5))

    # 6. FF MCap > Total MCap (mathematisch unmöglich — schwerwiegende Datenanomalie)
    # Toleranzgrenzen:
    #  - Warning ab Ratio > 1.01 (kleine Stichtag-Drifts ~0.3% rausfiltern)
    #  - Error ab Ratio > 1.10 (echte Anomalien wie Roche/Tokio Marine: Ratio ~1.8-2.0)
    # Beide nur bei substanziellem Total MCap (>$10M) um Micro-Cap-Rauschen auszuschließen
    safe_tot = tot_mcap.where(tot_mcap > 0, 1)  # avoid div-by-zero
    ratio    = ff_mcap / safe_tot
    mask6_err  = (tot_mcap > 10e6) & (ratio > 1.10)
    mask6_warn = (tot_mcap > 10e6) & (ratio > 1.01) & (ratio <= 1.10)
    if mask6_err.sum() > 0:
        anomalies.append(("error",   "FF MCap > 110% von Total MCap (mathematisch unmöglich)", mask6_err))
    if mask6_warn.sum() > 0:
        anomalies.append(("warning", "FF MCap zwischen 101%-110% von Total MCap (Stichtag-Drift / leichte Anomalie)", mask6_warn))

    return anomalies

def load_master_excel(file, valid_selection_dates_iso):
    """Load Master-File with multi-period dynamic columns.

    Expected format:
        - Static columns (Symbol, Name, ISIN, Sector, Industry, ...) — no date suffix
        - Dynamic columns with YYYY-MM-DD suffix (e.g. "Total MCap 2024-02-21")
        - All dates in dynamic columns must match an entry in Selection_Dates.xlsx

    Args:
        file: Uploaded Excel file
        valid_selection_dates_iso: Set of ISO-format date strings from Selection_Dates.xlsx

    Returns dict with:
        - "static_df": DataFrame with static columns only
        - "periods": {date_iso_str: DataFrame with dynamic columns for that date (re-named to Y2025 suffix)}
        - "detected_dates": sorted list of date strings found in the file
        - "extra_static_cols": list of static column names beyond the required/standard set
        - "warnings": list of non-critical issues to display
        - "error": error message (if loading failed) or None
    """
    import re as _re
    warnings_list = []

    try:
        # Read the entire sheet ONCE, then detect the header row in-memory.
        # The old approach called pd.read_excel up to 11× (10 header probes +
        # the real read), and each call re-parses the WHOLE workbook — brutal for
        # a 165 MB file. We also prefer the calamine engine (Rust), which is
        # ~5-20× faster than the default openpyxl, and fall back if unavailable.
        try:
            raw_df = pd.read_excel(file, header=None, dtype=str, engine="calamine")
        except Exception:
            if hasattr(file, "seek"):
                file.seek(0)
            raw_df = pd.read_excel(file, header=None, dtype=str)

        header_row = 0
        for i in range(min(10, len(raw_df))):
            if (raw_df.iloc[i].astype(str).str.strip() == "Symbol").any():
                header_row = i
                break

        df = raw_df.iloc[header_row + 1:].reset_index(drop=True)
        df.columns = [str(c).strip() for c in raw_df.iloc[header_row].tolist()]

        if "Symbol" not in df.columns:
            return {"error": "Master-File enthält keine 'Symbol'-Spalte."}

        # Finde alle Spalten mit YYYY-MM-DD Suffix
        date_pattern = _re.compile(r'^(.+?)\s+(\d{4}-\d{2}-\d{2})$')
        dynamic_cols = {}    # {date_iso: {prefix: col_name}}
        static_cols = []
        unknown_prefixes = set()

        for col in df.columns:
            m = date_pattern.match(col.strip())
            if m:
                prefix, date_iso = m.group(1).strip(), m.group(2)
                # Prüfe ob Prefix erlaubt ist
                if prefix not in MASTER_DYNAMIC_PREFIXES:
                    unknown_prefixes.add(prefix)
                    continue
                dynamic_cols.setdefault(date_iso, {})[prefix] = col
            else:
                static_cols.append(col)

        if unknown_prefixes:
            warnings_list.append(
                f"Unbekannte dynamische Feld-Prefixe ignoriert: {sorted(unknown_prefixes)}"
            )

        if not dynamic_cols:
            return {"error": "Keine dynamischen Spalten mit YYYY-MM-DD-Suffix gefunden. "
                             "Erwartetes Format z.B.: 'Total MCap 2024-02-21'."}

        # Validiere Dates gegen Selection_Dates.xlsx
        detected_dates = sorted(dynamic_cols.keys())
        invalid_dates = [d for d in detected_dates if d not in valid_selection_dates_iso]
        if invalid_dates:
            warnings_list.append(
                f"{len(invalid_dates)} Date(s) im Master-File nicht in Selection_Dates.xlsx gefunden — werden ignoriert: "
                f"{invalid_dates[:5]}{'...' if len(invalid_dates) > 5 else ''}"
            )
            for d in invalid_dates:
                dynamic_cols.pop(d, None)
            detected_dates = sorted(dynamic_cols.keys())

        if not detected_dates:
            return {"error": "Keine Selection Dates aus dem Master-File stimmen mit Selection_Dates.xlsx überein."}

        # Prüfe pro Date: sind die Pflicht-Kernfelder da?
        # FF MCap kann unter verschiedenen Namen kommen (Float MCap / FloatMCap / Free Float MCap)
        # — wir prüfen ob mindestens einer der Aliase pro Periode vorhanden ist.
        ff_mcap_aliases = ["Float MCap", "FloatMCap", "Free Float MCap"]
        for d in detected_dates:
            present_prefixes = set(dynamic_cols[d].keys())
            missing = []
            if "Total MCap" not in present_prefixes:
                missing.append("Total MCap")
            if not any(alias in present_prefixes for alias in ff_mcap_aliases):
                missing.append("FF MCap (Float MCap / FloatMCap / Free Float MCap)")
            if "Closing Price" not in present_prefixes:
                missing.append("Closing Price")
            if missing:
                warnings_list.append(f"Selection Date {d}: fehlende Pflichtfelder {missing} — Stocks dieser Periode evtl. unvollständig")

        # Baue static_df
        static_df = df[static_cols].copy()

        # Normalisiere Spalten-Namen auf den internen Standard (analog load_excel)
        rename_static = {
            # Country-Felder
            "Country Name":              "Exchange Country Name",
            "Exchange Country":          "Exchange Country Name",   # Master-File
            "Country Mapping":           "Mapping Country",          # Master-File: Mapping direkt aus Excel
            # Sector/Industry
            "Sector":                    "FactSet Econ Sector",
            "FactSet Sector":            "FactSet Econ Sector",
            "Industry":                  "FactSet Industry",
            "Inudstry":                  "FactSet Industry",         # Typo-Toleranz (ältere Files)
            # IDs (Master-File-Format mit Klammer-Suffix)
            "Perm ID (Security)":        "Perm ID",
            "Entity ID (Company)":       "Entity ID",
        }
        static_df = static_df.rename(columns=rename_static)

        if "Exchange Country Name" not in static_df.columns:
            if "Country of Risk" in static_df.columns:
                static_df["Exchange Country Name"] = static_df["Country of Risk"].fillna("")
            else:
                static_df["Exchange Country Name"] = ""

        # Identifiziere extra statische Spalten (über die Standard-Felder hinaus)
        standard_static = set(MASTER_STATIC_REQUIRED) | {
            "Exchange Country Name", "FactSet Econ Sector", "FactSet Industry",
            "Sec Type Inclusion", "SIC", "Perm ID", "MSCI Ansatz", "BBG Ansatz",
            "Country HQ", "Region by Exchange", "Region by Primary Listing",
        }
        extra_static_cols = [c for c in static_df.columns if c not in standard_static]

        # Baue periods Dict: für jedes Date ein DataFrame mit dynamischen Spalten,
        # renamed auf internen Y2025-Standard
        periods = {}
        for d, prefix_map in dynamic_cols.items():
            period_df = pd.DataFrame(index=df.index)
            rename_map_dynamic = {
                "Total MCap":          "Total MCap Y2025",
                "Float MCap":          "Free Float MCap Y2025",   # Master-File-Standard (getrennt)
                "FloatMCap":           "Free Float MCap Y2025",   # legacy (zusammen)
                "Free Float MCap":     "Free Float MCap Y2025",   # Single-Snapshot-Standard
                "Float PCT":           "Free Float Percent",
                "Free Float Percent":  "Free Float Percent",
                "Closing Price":       "Closing Price",
                "1M ADTV":             "1M ADTV Y2025",
                "3M ADTV":             "3M ADTV Y2025",
                "6M ADTV":             "6M ADTV Y2025",
                "12M ADTV":            "12M ADTV Y2025",
                "Listing Status":      "Listing Status",
                "Share MCap":          "Share MCap Y2025",   # informativ: MCap der Anteilsklasse (Export, zwischen Total & Free Float)
            }
            for prefix, col_name in prefix_map.items():
                target = rename_map_dynamic.get(prefix)
                if target:
                    period_df[target] = df[col_name]
            periods[d] = period_df

        # Validierung: Duplikate
        # Strategie: (1) Exchange Ticker-Duplikate → echter Fehler, (2) ISIN-Duplikate klassifiziert
        # in harmlos (Primary+Secondary-Paar) vs. verdächtig (2x Primary oder 2x Secondary)
        # Exchange Ticker ist stock-level-eindeutig — @NA (FactSet-Platzhalter) wird als leer behandelt.
        if "Exchange Ticker" in static_df.columns:
            _et = static_df["Exchange Ticker"].fillna("").astype(str).str.strip()
            _et_valid = _et[(_et != "") & (_et != "@NA")]
            n_et_dup = _et_valid.duplicated().sum()
            if n_et_dup > 0:
                warnings_list.append(
                    f"⚠️ {n_et_dup} Zeile(n) mit dupliziertem Exchange Ticker — "
                    f"echter Datenfehler, bitte prüfen (Stocks würden doppelt gewichtet)."
                )

        if "ISIN" in static_df.columns and "Listing" in static_df.columns:
            _isin = _norm_isin(static_df["ISIN"])
            _listing = static_df["Listing"].fillna("").astype(str).str.strip()

            # Gruppiere pro ISIN: zähle Primary und Secondary Zeilen
            _isin_mask = _isin != ""
            _groups = pd.DataFrame({
                "ISIN": _isin[_isin_mask],
                "Listing": _listing[_isin_mask],
            }).groupby("ISIN")["Listing"].agg(list)

            # Nur Gruppen mit >1 Zeile sind Duplikate
            _dups = _groups[_groups.apply(len) > 1]

            benign_pairs = 0    # 1 Primary + N Secondary (beliebige N)
            suspicious = 0      # 2+ Primary ODER 0 Primary + 2+ Secondary (oder unklare Labels)
            suspicious_isins = []

            for isin, listings in _dups.items():
                n_prim = sum(1 for l in listings if l.lower() == "primary")
                n_sec  = sum(1 for l in listings if l.lower() == "secondary")
                # Muster: genau 1 Primary + ≥1 Secondary → harmlos
                if n_prim == 1 and n_sec == len(listings) - 1 and n_sec >= 1:
                    benign_pairs += 1
                else:
                    suspicious += 1
                    if len(suspicious_isins) < 5:
                        suspicious_isins.append(f"{isin} ({n_prim}× Primary, {n_sec}× Secondary)")

            if benign_pairs > 0 and suspicious == 0:
                warnings_list.append(
                    f"ℹ️ {benign_pairs} ISIN(s) mit Primary+Secondary-Paar — ist erwartet, kein Problem."
                )
            elif suspicious > 0:
                _sample = ", ".join(suspicious_isins)
                _rest = f" (+ {suspicious - 5} weitere)" if suspicious > 5 else ""
                warnings_list.append(
                    f"⚠️ {suspicious} ISIN(s) mit verdächtiger Duplikat-Struktur "
                    f"(mehrfach Primary oder keine Primary-Zeile): {_sample}{_rest}"
                    + (f" | zusätzlich {benign_pairs} harmlose Primary+Secondary-Paare." if benign_pairs > 0 else "")
                )

        return {
            "static_df": static_df,
            "periods": periods,
            "detected_dates": detected_dates,
            "extra_static_cols": extra_static_cols,
            "warnings": warnings_list,
            "error": None,
        }

    except Exception as e:
        return {"error": f"Fehler beim Laden des Master-Files: {e}"}

def build_snapshot_from_master(master_data, selection_date_iso):
    """Kombiniert static_df + dynamische Spalten für ein bestimmtes Selection Date
    zu einem DataFrame, der aussieht wie ein normaler FactSet-Export (Single-Snapshot).

    Listing Status Logik:
      - Falls "Listing Status" als dynamische Spalte im File vorhanden ist (im
        aktuellen Master-File für ALLE Perioden, als "0"/"1"), wird sie übernommen.
        Der Delisted-Filter (build_new_universe) vergleicht numerisch, ist also
        robust gegen "1" vs 1 vs 1.0.
      - Andernfalls aus Closing Price abgeleitet:
          Closing Price > 0  → Listing Status = 0 (aktiv/gelistet)
          Closing Price ≤ 0 oder NaN → Listing Status = 1 (delisted oder pre-IPO)
      Diese Heuristik ist methodisch sauber: solange eine Aktie zum Selection Date
      einen Preis hat, gilt sie als handelbar.

    Free Float Percent Normalisierung:
      Master-File liefert "Float PCT" als Prozent (0-100), Single-Snapshot als
      Dezimal (0-1). Der Rest des Codes erwartet Dezimal — daher hier konvertieren
      wenn Werte > 1 auftauchen.

    Returns: DataFrame mit allen Spalten (static + dynamic normalisiert auf Y2025)
    """
    if selection_date_iso not in master_data["periods"]:
        raise ValueError(f"Selection Date {selection_date_iso} nicht im Master-File vorhanden.")

    static_df = master_data["static_df"]
    period_df = master_data["periods"][selection_date_iso]

    # Concat auf Spalten-Ebene (beide haben gleichen Index)
    combined = pd.concat([static_df.reset_index(drop=True),
                          period_df.reset_index(drop=True)], axis=1)

    # Free Float Percent normalisieren: Master-File-Format ist Prozent (0-100),
    # Code erwartet Dezimal (0-1). Wenn Median > 1, dividieren durch 100.
    if "Free Float Percent" in combined.columns:
        _ffp_num = pd.to_numeric(combined["Free Float Percent"], errors="coerce")
        _ffp_med = _ffp_num.dropna().median() if _ffp_num.notna().any() else 0
        if _ffp_med > 1:  # Werte sind im Prozent-Format (z.B. 99.879)
            combined["Free Float Percent"] = _ffp_num / 100.0

    # Listing Status ableiten falls nicht im File
    if "Listing Status" not in combined.columns:
        if "Closing Price" in combined.columns:
            _cp = pd.to_numeric(combined["Closing Price"], errors="coerce").fillna(0)
            combined["Listing Status"] = np.where(_cp > 0, 0, 1)
        else:
            # Defensive: ohne Closing Price können wir nichts ableiten — alle aktiv
            combined["Listing Status"] = 0

    return combined

def get_selection_date_for_snapshot(snapshot_date, selection_dates):
    """Finde das letzte Selection Date, das ≤ snapshot_date ist.
    Liefert None wenn snapshot_date vor dem ersten Selection Date liegt.
    """
    eligible = [d for d in selection_dates if d <= snapshot_date]
    return max(eligible) if eligible else None

def get_classification_dict(hc_df, selection_date):
    """Erzeuge {Country: Classification} Dict für ein konkretes Selection Date.
    Länder mit NaN zu diesem Datum werden ausgeschlossen (nicht im Universum).
    """
    if hc_df.empty or selection_date not in hc_df.columns:
        return {}
    return hc_df.set_index("Country")[selection_date].dropna().to_dict()

def load_ineligible_list():
    """Load In-Eligible.xlsx — Liste von ISINs die zu bestimmten Zeiträumen vom Index ausgeschlossen werden.

    Schema: ISIN | Company Name | Country Mapping | From | To | Reason
    - Leeres To → Stock ist aktuell noch ineligible (wird als 9999-12-31 interpretiert)
    - Mehrere Einträge pro ISIN erlaubt (z.B. zwei separate Sperrzeiträume)

    Returns:
        DataFrame mit normalisierten From/To als pd.Timestamp, oder leerer DataFrame falls File fehlt.
    """
    from datetime import date as _date

    candidates = ["In-Eligible.xlsx", "In_Eligible.xlsx", "In Eligible.xlsx", "Ineligible.xlsx"]
    ie_df = None
    for name in candidates:
        try:
            ie_df = pd.read_excel(name)
            break
        except FileNotFoundError:
            continue

    if ie_df is None or ie_df.empty:
        return pd.DataFrame(columns=["ISIN","Company Name","Country Mapping","From","To","Reason"])

    # Normalize: strip whitespace, uppercase ISIN
    ie_df["ISIN"] = ie_df["ISIN"].astype(str).str.strip().str.upper()
    ie_df = ie_df[ie_df["ISIN"].notna() & (ie_df["ISIN"] != "") & (ie_df["ISIN"] != "NAN")].copy()

    # Parse dates
    ie_df["From"] = pd.to_datetime(ie_df["From"], errors="coerce")
    ie_df["To"]   = pd.to_datetime(ie_df["To"],   errors="coerce")
    # Leeres To → 9999-12-31 (noch ineligible)
    ie_df["To"]   = ie_df["To"].fillna(pd.Timestamp("9999-12-31"))
    # Leeres From → 1900-01-01 (sicherheitshalber, falls User vergisst)
    ie_df["From"] = ie_df["From"].fillna(pd.Timestamp("1900-01-01"))

    # Reason default
    if "Reason" not in ie_df.columns:
        ie_df["Reason"] = ""
    ie_df["Reason"] = ie_df["Reason"].fillna("").astype(str)

    return ie_df[["ISIN","Company Name","Country Mapping","From","To","Reason"]].reset_index(drop=True)

def apply_ineligible_filter(df_complete, ie_df, selection_date):
    """Entferne Stocks aus df_complete deren ISIN zum Selection Date auf der Ineligible-Liste steht.

    Args:
        df_complete: DataFrame mit Index-Konstituenten (muss Spalte "ISIN" enthalten)
        ie_df: Ineligible-Liste (from load_ineligible_list())
        selection_date: datetime.date

    Returns:
        (df_kept, df_removed, active_rules):
            df_kept:      gefilteter DataFrame
            df_removed:   entfernte Rows (inkl. neuer Spalten: Ineligible_Reason, Ineligible_From, Ineligible_To)
            active_rules: Teilmenge von ie_df die zum Selection Date aktiv ist (für UI-Anzeige)
    """
    if ie_df is None or ie_df.empty or "ISIN" not in df_complete.columns:
        return df_complete.copy(), df_complete.iloc[0:0].copy(), ie_df.iloc[0:0].copy() if ie_df is not None else pd.DataFrame()

    sd_ts = pd.Timestamp(selection_date)
    active_rules = ie_df[(ie_df["From"] <= sd_ts) & (sd_ts <= ie_df["To"])].copy()

    if active_rules.empty:
        return df_complete.copy(), df_complete.iloc[0:0].copy(), active_rules

    # Normalize ISINs on the data side for matching
    df = df_complete.copy()
    df["_ISIN_norm"] = df["ISIN"].astype(str).str.strip().str.upper()

    blocked_isins = set(active_rules["ISIN"].tolist())
    mask_blocked = df["_ISIN_norm"].isin(blocked_isins)

    df_removed = df[mask_blocked].copy()
    df_kept    = df[~mask_blocked].drop(columns=["_ISIN_norm"]).copy()

    # Annotate removed rows with reason / from / to (first matching rule per ISIN)
    if not df_removed.empty:
        rule_first = active_rules.drop_duplicates(subset=["ISIN"], keep="first").set_index("ISIN")
        df_removed["Ineligible_Reason"] = df_removed["_ISIN_norm"].map(rule_first["Reason"])
        df_removed["Ineligible_From"]   = df_removed["_ISIN_norm"].map(rule_first["From"])
        df_removed["Ineligible_To"]     = df_removed["_ISIN_norm"].map(rule_first["To"])
        df_removed = df_removed.drop(columns=["_ISIN_norm"])

    return df_kept, df_removed, active_rules

def load_fol_matrix():
    """Load FOL Matrix YAML from 'Historical FOL Register/'.

    Returns:
        fol_matrix: Dict[year][iso2] = {
            "default_fol": float,
            "investability_status": str,
            "industries": {(sector, industry): {"fol_automatic": float, ...}, ...}
        }
        version: Versionsstring aus YAML, oder None
        debug_info: Liste mit getesteten Pfaden (für Diagnostik)
    """
    import yaml as _yaml
    import os as _os

    # Script directory als Basis (Streamlit Cloud startet ggf. aus anderem CWD)
    _script_dir = _os.path.dirname(_os.path.abspath(__file__)) if "__file__" in globals() else _os.getcwd()

    # v1.9 (intern "1.9-redteam-corrected") ist die einzige/aktive Matrix — 12 Jurisdiktionen
    # inkl. Taiwan, Qatar-Finanzwerte 49%, alle logischen auto>max-Verstöße behoben.
    # (Alte Versionen 1.3/1.6 wurden bewusst entfernt; kein Fallback mehr.)
    _fname = "NaroIX_FOL_Master_Aggregated_v1.9.yaml"
    candidates_rel = [
        "Historical FOL Register/" + _fname,
        "Historical_FOL_Register/" + _fname,
        _fname,
    ]

    # Alle Pfade: relative (CWD) + absolute (Script-Dir)
    candidates = []
    for rel in candidates_rel:
        candidates.append(rel)
        candidates.append(_os.path.join(_script_dir, rel))

    raw = None
    tried = []
    used_path = None
    for name in candidates:
        tried.append(name)
        try:
            with open(name, "r", encoding="utf-8") as f:
                raw = _yaml.safe_load(f)
            used_path = name
            break
        except FileNotFoundError:
            continue

    debug_info = {
        "cwd": _os.getcwd(),
        "script_dir": _script_dir,
        "tried_paths": tried,
        "used_path": used_path,
    }

    if raw is None:
        return {}, None, debug_info

    root = raw.get("naroix_pit_fol_master", {})
    version = root.get("version")
    snapshots = root.get("snapshots", {})

    fol_matrix = {}
    for yr, ysnap in snapshots.items():
        yr_int = int(yr)
        fol_matrix[yr_int] = {}
        for cc, cd in ysnap.get("countries", {}).items():
            industries_lookup = {}
            for ind in cd.get("industries", []):
                key = (ind.get("factset_sector",""), ind.get("factset_industry",""))
                industries_lookup[key] = {
                    "fol_automatic": float(ind.get("fol_automatic", 1.0)),
                    "fol_max_with_approval": float(ind.get("fol_max_with_approval", 1.0)),
                    "capped": bool(ind.get("capped", False)),
                    "needs_company_override": bool(ind.get("needs_company_override", False)),
                }
            # Whitespace-/Case-tolerantes Sekundär-Mapping: gleicht Schreibweise-Differenzen
            # zwischen FOL-Matrix und FactSet-Daten aus (z.B. "Hotels/Resorts/Cruiselines"
            # in der Matrix vs. "Hotels/Resorts/Cruise lines" in den Daten). Wird in
            # _resolve_fol_row NACH dem exakten Match, aber VOR dem Sektor-Fallback genutzt.
            industries_norm = {_norm_fol_key(s, i): v for (s, i), v in industries_lookup.items()}
            fol_matrix[yr_int][cc] = {
                "default_fol": float(cd.get("default_fol", 1.0)),
                "investability_status": cd.get("investability_status", "investable"),
                "country_name": cd.get("country_name", cc),
                "industries": industries_lookup,
                "industries_norm": industries_norm,
            }

    return fol_matrix, version, debug_info

def build_sector_fallback_table(fol_matrix):
    """Precompute: für jeden (year, iso2, sector) den STRENGSTEN fol_automatic.

    Option (a) aus der Abstimmung — konservatives Fallback.
    """
    fb = {}
    for yr, ysnap in fol_matrix.items():
        fb[yr] = {}
        for cc, cd in ysnap.items():
            sec_min = {}
            for (sector, industry), vals in cd["industries"].items():
                fol_a = vals["fol_automatic"]
                if sector not in sec_min or fol_a < sec_min[sector]:
                    sec_min[sector] = fol_a
            fb[yr][cc] = sec_min
    return fb

def _norm_fol_key(sector, industry):
    """Normalisiert (sector, industry) für tolerantes Matching: lowercase + alle
    Whitespaces entfernt. Gleicht Schreibweise-Differenzen wie 'Cruise lines' vs
    'Cruiselines' aus, ohne unterschiedliche Industrien zu vermischen."""
    return ("".join(str(sector).lower().split()), "".join(str(industry).lower().split()))

# Cross-Call-Memo für FOL-Auflösung: pro Session werden dieselben (year, country, sector,
# industry)-Tripel über viele Perioden immer wieder aufgelöst. _resolve_fol_row ist rein
# (gegeben Matrix), daher cachebar. Schlüssel ist an die Matrix-OBJEKTIDENTITÄT gebunden:
# wechselt die Matrix (neuer Upload), wird der Cache verworfen → keine veralteten Treffer.
_FOL_ROW_CACHE = {"matrix": None, "rows": {}}


def _resolve_fol_row(ecn_upper, sector, industry, year, fol_matrix, sector_fallback):
    """Returns (fol_value, source_label) for a single stock.

    Fallback-Kette:
      1. Industry-Match (exakt) → "Industry"
      2. Industry-Match (normalisiert, Whitespace/Case) → "Industry (normalisiert)"
      3. Sector-Fallback (strengster Industry-Wert im Sector) → "Sector (strengster)"
      4. default_fol des Landes → "Country Default"
      5. 1.0 → "Kein FOL-Mapping"
    """
    iso2 = FOL_COUNTRY_CODE_MAP.get(ecn_upper)
    if iso2 is None:
        return 1.0, "Nicht in YAML"

    yr_data = fol_matrix.get(year)
    if yr_data is None:
        return 1.0, f"Jahr {year} fehlt"

    cdata = yr_data.get(iso2)
    if cdata is None:
        return 1.0, f"{iso2} fehlt in {year}"

    # Saudi pre_investable (nur 2014) → IF=0 damit das Gewicht 0 ist aber Stock diagnostisch sichtbar bleibt
    if cdata.get("investability_status") != "investable":
        return 0.0, f"pre_investable ({cdata.get('investability_status')})"

    # Industry-Match (exakt)
    ind_match = cdata["industries"].get((sector, industry))
    if ind_match is not None:
        return ind_match["fol_automatic"], "Industry"

    # Industry-Match (normalisiert) — fängt Schreibweise-Differenzen ab
    norm_match = cdata.get("industries_norm", {}).get(_norm_fol_key(sector, industry))
    if norm_match is not None:
        return norm_match["fol_automatic"], "Industry (normalisiert)"

    # Sector-Fallback (strengster)
    sec_min_table = sector_fallback.get(year, {}).get(iso2, {})
    if sector in sec_min_table:
        return sec_min_table[sector], "Sector (strengster)"

    # Country default_fol
    return cdata["default_fol"], "Country Default"

def apply_fol_matrix(df, fol_matrix, sector_fallback, year, thailand_mode,
                     fol_enabled=True, china_if=0.20):
    """Berechnet IF pro Stock nach FIF-Formel und setzt Adj_FF_MCap neu.

    FIF-Formel: IF = min(1.0, FOL / Free_Float_Pct) wenn FF>0, sonst 1.0

    Override-Kaskade (nach FOL-Lookup):
      - China         → IF = china_if (Stock Connect, nicht FOL)
      - Thailand NVDR only / SHARE → NVDR → IF = 1.0 (NVDR umgeht FOL)
      - Thailand SHARE only           → FOL-Resolver greift

    Wenn fol_enabled=False: IF = 1.0 für alle (außer China bleibt china_if).

    Returns: df mit neuen/überschriebenen Spalten IF, IF_Source, FOL_Value, Adj_FF_MCap
    """
    df = df.copy()
    ecn = df["Exchange Country Name"].fillna("").str.upper()

    if not fol_enabled:
        df["IF"] = 1.0
        df["IF_Source"] = "FOL deaktiviert"
        df["FOL_Value"] = np.nan
        # China bleibt trotz deaktivierter Matrix bei china_if
        mask_cn = ecn == "CHINA"
        df.loc[mask_cn, "IF"] = china_if
        df.loc[mask_cn, "IF_Source"] = f"China Stock Connect ({china_if*100:.0f}%)"
        df["Adj_FF_MCap"] = df["Free Float MCap Y2025"] * df["IF"]
        return df

    # Resolve FOL row-wise
    sectors = df.get("FactSet Econ Sector", pd.Series([""] * len(df))).fillna("")
    industries = df.get("FactSet Industry", pd.Series([""] * len(df))).fillna("")

    # Resolve FOL on UNIQUE (country, sector, industry) triples only. _resolve_fol_row is
    # a pure function of these (year + matrix fixed per call), so the ~28k rows collapse to
    # a few hundred unique combos. (Was: one _resolve_fol_row call per row → ~470ms/period.)
    _combo = pd.DataFrame({"e": ecn.values, "s": sectors.values, "i": industries.values})
    # Cross-Call-Memo: an Matrix-Identität gebunden, bei Matrixwechsel verwerfen.
    if _FOL_ROW_CACHE["matrix"] is not fol_matrix:
        _FOL_ROW_CACHE["matrix"] = fol_matrix
        _FOL_ROW_CACHE["rows"] = {}
    _rows = _FOL_ROW_CACHE["rows"]
    _fol_map = {}
    for r in _combo.drop_duplicates().itertuples(index=False):
        _ck = (year, r.e, r.s, r.i)
        if _ck not in _rows:
            _rows[_ck] = _resolve_fol_row(r.e, r.s, r.i, year, fol_matrix, sector_fallback)
        _fol_map[(r.e, r.s, r.i)] = _rows[_ck]
    _keys = list(zip(ecn.values, sectors.values, industries.values))
    df["FOL_Value"] = [_fol_map[k][0] for k in _keys]
    df["IF_Source"] = [_fol_map[k][1] for k in _keys]

    # FIF-Formel: IF = min(1.0, FOL / FF_Ratio)
    # Hinweis: "Free Float Percent" ist trotz des Namens im Code als Dezimalwert 0.0–1.0
    # gespeichert (so liefert es FactSet, so wird min_ff_pct in der Sidebar verglichen).
    # FOL_Value aus YAML ist ebenfalls 0.0–1.0 → direkte Division korrekt.
    ff_ratio = df["Free Float Percent"].astype(float)
    df["IF"] = np.where(
        ff_ratio > 0,
        np.minimum(1.0, df["FOL_Value"].astype(float) / ff_ratio.where(ff_ratio>0, np.nan)),
        1.0,
    )

    # Override: China (Stock Connect, nicht FOL)
    mask_cn = ecn == "CHINA"
    df.loc[mask_cn, "IF"] = china_if
    df.loc[mask_cn, "IF_Source"] = f"China Stock Connect ({china_if*100:.0f}%)"
    df.loc[mask_cn, "FOL_Value"] = np.nan

    # Override: Thailand je nach Modus
    mask_th = ecn == "THAILAND"
    if thailand_mode in ["NVDR only", "SHARE → NVDR"]:
        df.loc[mask_th, "IF"] = 1.0
        df.loc[mask_th, "IF_Source"] = f"Thailand {thailand_mode} (NVDR)"
        df.loc[mask_th, "FOL_Value"] = np.nan
    # "SHARE only" → FOL-Resolver greift bereits, kein Override

    # pre_investable-Fälle: IF ist bereits 0 aus Resolver, aber min(1, 0/FF) könnte NaN sein
    # Fix: Wo IF_Source mit "pre_investable" beginnt → IF=0 hart
    mask_preinv = df["IF_Source"].astype(str).str.startswith("pre_investable")
    df.loc[mask_preinv, "IF"] = 0.0

    # NaN-Schutz (z.B. wenn FF_Pct=0)
    df["IF"] = df["IF"].fillna(1.0).clip(0.0, 1.0)

    df["Adj_FF_MCap"] = df["Free Float MCap Y2025"] * df["IF"]
    return df

def build_new_universe(df_raw_orig, country_cls, thailand_mode, max_price,
                       excl_hk_cny, excl_cor_na, excl_naics, excl_euro, excl_etf,
                       china_if,
                       atvr_mcap_col="Free Float MCap Y2025",
                       excl_delisted=True,
                       fol_matrix=None, fol_sector_fb=None, fol_year=None, fol_enabled=True):
    """Build universe with Primary + Secondary listings, applying all investability
    filters (FF MCap > 0, exclusions, FOL/IF). EUMSS-Schwellen werden später im
    Pipeline-Schritt angewendet — auf Primary-only kalibriert, auf alle Listings appliziert."""
    import re as _re
    df = df_raw_orig.copy()
    for col in ["Total MCap Y2025","Free Float MCap Y2025","Free Float Percent",
                "1M ADTV Y2025","3M ADTV Y2025","6M ADTV Y2025","12M ADTV Y2025","Closing Price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    # Share MCap ist optional (rein informativ für den Export) — nur coercen wenn vorhanden
    if "Share MCap Y2025" in df.columns:
        df["Share MCap Y2025"] = pd.to_numeric(df["Share MCap Y2025"], errors="coerce").fillna(0)

    # Step 1: Thailand mode handling
    _th = df["Exchange Name"].fillna("").str.upper() == "THAILAND"

    if thailand_mode == "NVDR only":
        # Keep NVDRs (Secondary), remove Thai SHAREs
        df = df[~(_th & (df["Sec Type"].fillna("") == "SHARE"))].copy()

    elif thailand_mode == "SHARE only":
        # Keep SHAREs (Primary), remove Thai NVDRs
        df = df[~(_th & (df["Sec Type"].fillna("") == "NVDR"))].copy()

    elif thailand_mode == "SHARE → NVDR":
        # Qualify on SHARE (FF MCap/FF%), then switch to NVDR for index
        # 1. Get Thai SHAREs and NVDRs separately
        _th_shares = df[_th & (df["Sec Type"].fillna("") == "SHARE")].copy()
        _th_nvdrs  = df[_th & (df["Sec Type"].fillna("") == "NVDR")].copy()
        _non_thai  = df[~_th].copy()

        # 2. Qualify SHAREs on FF MCap + FF%
        _th_shares_qual = _th_shares[_th_shares["Free Float MCap Y2025"] > 0].copy()

        # 3. Only keep SHAREs that have a corresponding NVDR
        _nvdr_entities = set(_th_nvdrs["Entity ID"].dropna().unique())
        _th_shares_qual = _th_shares_qual[
            _th_shares_qual["Entity ID"].isin(_nvdr_entities)
        ].copy()

        # 4. Get the corresponding NVDRs
        _qual_entities = set(_th_shares_qual["Entity ID"].dropna().unique())
        _th_nvdrs_sel  = _th_nvdrs[_th_nvdrs["Entity ID"].isin(_qual_entities)].copy()

        # 5. Transfer FF MCap, FF%, Total MCap, Closing Price from SHARE to NVDR
        _ff_map = _th_shares_qual.set_index("Entity ID")
        for _fld in ["Free Float MCap Y2025","Free Float Percent","Total MCap Y2025","Closing Price"]:
            if _fld in _ff_map.columns:
                _th_nvdrs_sel[_fld] = _th_nvdrs_sel["Entity ID"].map(_ff_map[_fld])

        # 6. Rebuild df: non-Thai + enriched NVDRs (no Thai SHAREs)
        df = pd.concat([_non_thai, _th_nvdrs_sel], ignore_index=True)

    # Step 2: Listing-Universe — Primary + Secondary laufen konsistent durch alle Filter
    # (Variante B / MSCI-konform: EUMSS-Schwellen werden Security-Level auf alle Listings
    # angewendet. Thailand: in SHARE→NVDR-Modus wurden Thai SHAREs oben entfernt; NVDRs
    # (Secondary mit übernommenen Werten) bleiben drin.)
    # Kein Listing-Filter — alle Listings (Primary + Secondary) gehen weiter durch die Pipeline.

    # Step 3: Exclusions — zentral via apply_universe_exclusions (EINE Quelle; UI nutzt dieselbe).
    df = apply_universe_exclusions(df, max_price=max_price, excl_hk_cny=excl_hk_cny,
                                   excl_cor_na=excl_cor_na, excl_naics=excl_naics, excl_euro=excl_euro,
                                   excl_etf=excl_etf, excl_delisted=excl_delisted)

    # Step 4: Classification — Mapping Country via derive_mapping_country (primaer File-Feld
    # 'Country Mapping', Fallback Risk-First). Zentrale Quelle der Wahrheit (auch UI nutzt sie).
    df["Mapping Country"] = derive_mapping_country(df)
    df["Classification"] = df["Mapping Country"].map(country_cls)
    df = df[df["Classification"].notna()].copy()

    # Step 5: Inclusion Factors via FOL Matrix (Pflicht — Hard-Stop passiert bereits beim Laden)
    df = apply_fol_matrix(df, fol_matrix, fol_sector_fb, fol_year, thailand_mode,
                          fol_enabled=fol_enabled, china_if=china_if)

    # ADTV best for ATVR
    df["ADTV_Best"] = df["12M ADTV Y2025"].where(df["12M ADTV Y2025"]>0,
                      df["6M ADTV Y2025"].where(df["6M ADTV Y2025"]>0,
                      df["3M ADTV Y2025"].where(df["3M ADTV Y2025"]>0,
                      df["1M ADTV Y2025"])))
    df["ATVR"] = np.where(df[atvr_mcap_col]>0,
                          df["ADTV_Best"]*252/df[atvr_mcap_col], 0)
    return df

def apply_liquidity_new(df, adtv_dm, adtv_em, atvr_dm, atvr_em,
                         incumbents_isin=None,
                         m_adtv_dm=None, m_adtv_em=None, m_atvr_dm=None, m_atvr_em=None):
    """Apply ADTV + ATVR filter with optional Buffer-Rules.

    Entry-Schwellen (adtv_dm/em, atvr_dm/em) gelten für neue Kandidaten.
    Wenn incumbents_isin non-empty → Stocks mit ISIN in dieser Menge bekommen
    die weicheren Maintenance-Schwellen (m_adtv_dm/em, m_atvr_dm/em).
    Wenn m_* None, fallen Maintenance-Schwellen auf Entry zurück (kein Buffer-Effekt).
    """
    # Fallback: Maintenance = Entry wenn nicht explizit gesetzt
    if m_adtv_dm is None: m_adtv_dm = adtv_dm
    if m_adtv_em is None: m_adtv_em = adtv_em
    if m_atvr_dm is None: m_atvr_dm = atvr_dm
    if m_atvr_em is None: m_atvr_em = atvr_em

    # Pro-Stock Schwelle wählen: Incumbent → Maintenance, sonst → Entry
    if incumbents_isin is None:
        incumbents_isin = set()

    _isin = _norm_isin(df["ISIN"])
    _is_incumbent = _isin.isin(incumbents_isin)

    _adtv_dm_thr = np.where(_is_incumbent, m_adtv_dm, adtv_dm)
    _adtv_em_thr = np.where(_is_incumbent, m_adtv_em, adtv_em)
    _atvr_dm_thr = np.where(_is_incumbent, m_atvr_dm, atvr_dm)
    _atvr_em_thr = np.where(_is_incumbent, m_atvr_em, atvr_em)

    _cls = df["Classification"].fillna("")
    _a3m = df["3M ADTV Y2025"]
    _a6m = df["6M ADTV Y2025"]
    _atvr = df["ATVR"]

    mask_dm = (_cls=="DM") & (_a3m >= _adtv_dm_thr) & (_a6m >= _adtv_dm_thr) & (_atvr >= _atvr_dm_thr)
    mask_em = (_cls=="EM") & (_a3m >= _adtv_em_thr) & (_a6m >= _adtv_em_thr) & (_atvr >= _atvr_em_thr)

    return df[mask_dm | mask_em].copy()

def run_selection_pipeline(
    df_raw_in, country_cls, china_if, fol_year,
    # Universe & Exclusions
    thailand_mode, max_price, exclude_hk_cny, exclude_country_risk_na,
    exclude_naics_funds, exclude_euro_mtf, exclude_etf_sicav,
    # Size & Liquidity
    large_thr, mid_thr, small_thr, min_ff_pct, eumss_ff_ratio,
    adtv_dm, adtv_em, atvr_dm, atvr_em,
    # IF / FOL
    fol_matrix, fol_sector_fb, fol_enabled,
    if_cum_col, atvr_mcap_col,
    # Buffer
    incumbents_isin=None, apply_buffer=False,
    buffer_min_ff=None, buffer_coverage=90,
    buffer_adtv_dm=None, buffer_adtv_em=None,
    buffer_atvr_dm=None, buffer_atvr_em=None,
    # Size Buffer (segment hysteresis — Multi-Period only)
    apply_size_buffer=False, incumbent_segments=None, size_buffer_pp=5.0,
    # Universe
    excl_delisted=True,
    # Ineligible
    ineligible_df=None, apply_ineligible=False, selection_date=None,
    # Reihenfolge-Toggle: Labeling vor Liquidität (Markt-Coverage) statt danach
    label_before_liquidity=False,
    # Performance: vorgebautes Universe wiederverwenden (überspringt build_new_universe)
    prebuilt_universe=None,
):
    """Run the complete selection pipeline for one snapshot.

    label_before_liquidity: wenn True, läuft der Coverage-Waterfall (Large/Mid/Small
        Labeling) auf dem vollen post-EUMSS-Pool VOR der Liquidität (Markt-Coverage);
        die Liquidität wirkt danach nur noch als Mitgliedschafts-Gate (Label ∩ liquide).
        Default False = bisheriges Verhalten (Liquidität zuerst, Coverage auf gm_liq).
        Der EUMSS-Floor und alle anderen Parameter bleiben unverändert.

    prebuilt_universe: optionales, bereits gebautes Universe (build_new_universe-Output).
        Wenn gesetzt, wird der interne Universe-Build übersprungen (Performance). NUR
        übergeben, wenn es mit EXAKT denselben Universe-Parametern (Snapshot, Exclusions,
        FOL-Jahr/-Matrix, Klassifikation) gebaut wurde — sonst weicht das Ergebnis ab.

    Returns dict with:
        - 'gm_complete': final DataFrame with all segments and Index_Weight
        - 'gm_index_only': Standard Index (Large+Mid Cap only)
        - 'gm_universe':   Primary-only universe after FOL
        - 'eumss_full', 'eumss_ff': EUMSS thresholds
        - 'buffer_breakdown': dict with incumbent/newcomer counts (None if buffer inactive)
        - 'incumbents_isin_used': effective incumbents set used (for state propagation)
    """
    if incumbents_isin is None:
        incumbents_isin = set()

    # Buffer fallback: Maintenance = Entry if not set
    if buffer_min_ff is None:    buffer_min_ff = min_ff_pct
    if buffer_adtv_dm is None:   buffer_adtv_dm = adtv_dm
    if buffer_adtv_em is None:   buffer_adtv_em = adtv_em
    if buffer_atvr_dm is None:   buffer_atvr_dm = atvr_dm
    if buffer_atvr_em is None:   buffer_atvr_em = atvr_em

    # 1) Build universe (incl. FOL). Wenn der Aufrufer ein bereits gebautes Universe
    # mit IDENTISCHEN Parametern übergibt (z.B. GIMI-Tab reicht _gm_u_global durch),
    # den teuren Rebuild (~1s/Lauf) überspringen. Copy, weil die Pipeline gm_u als
    # eigenes Objekt behandelt (Subsets/Masken) — schützt den geteilten Original-Frame.
    if prebuilt_universe is not None:
        gm_u = prebuilt_universe.copy()
    else:
        gm_u = build_new_universe(
            df_raw_in, country_cls, thailand_mode, max_price,
            exclude_hk_cny, exclude_country_risk_na, exclude_naics_funds,
            exclude_euro_mtf, exclude_etf_sicav,
            china_if,
            atvr_mcap_col=atvr_mcap_col,
            excl_delisted=excl_delisted,
            fol_matrix=fol_matrix, fol_sector_fb=fol_sector_fb,
            fol_year=fol_year, fol_enabled=fol_enabled,
        )

    # 2) EUMSS calibration on DM **Primary-only** (top small_thr% coverage point).
    # Wichtig: Auf Primary-only kalibrieren, um Doppelzählung von Companies mit
    # mehreren Listings (z.B. Common + Pref) zu vermeiden. Die kalibrierten Schwellen
    # werden anschließend auf das volle Listing-Universe (inkl. Secondaries) angewendet.
    dm_only = gm_u[(gm_u["Classification"] == "DM") & (gm_u["Listing"] == "Primary")].copy()
    # Robustheit (#4): Wäre die "Listing"-Spalte abweichend geschrieben/leer, wäre
    # dm_only leer → eumss_full=0 → der EUMSS-Filter würde STILL nichts entfernen.
    # Statt dessen auf alle DM-Listings ausweichen (leichte Multi-Class-Doppelzählung,
    # aber echte Kalibrierung) und das Flag zurückgeben, damit die UI warnen kann.
    eumss_calib_fallback = False
    if len(dm_only) == 0 and bool((gm_u["Classification"] == "DM").any()):
        dm_only = gm_u[gm_u["Classification"] == "DM"].copy()
        eumss_calib_fallback = True
    # Sekundärer Sort-Key: bei gleichem Total MCap (Multi-Class derselben Company)
    # kommt das liquidere Listing (höheres Adj_FF_MCap) zuerst → deterministisches Ranking.
    dm_only = dm_only.sort_values(["Total MCap Y2025", "Adj_FF_MCap"], ascending=[False, False])
    dm_total_ff = dm_only["Free Float MCap Y2025"].sum()
    if dm_total_ff > 0:
        dm_only["_cum_ff_pct"] = dm_only["Free Float MCap Y2025"].cumsum() / dm_total_ff * 100
        eumss_pos = dm_only[dm_only["_cum_ff_pct"] >= small_thr].index
        eumss_full = float(dm_only.loc[eumss_pos[0], "Total MCap Y2025"]) if len(eumss_pos) > 0 else 0
    else:
        eumss_full = 0
    eumss_ff = eumss_full * eumss_ff_ratio

    # 3) EUMSS filter — buffer-aware Min FF%
    gm_isin = _norm_isin(gm_u["ISIN"])
    gm_is_inc = gm_isin.isin(incumbents_isin) if apply_buffer else pd.Series(False, index=gm_u.index)
    gm_min_ff_thr = np.where(gm_is_inc, buffer_min_ff, min_ff_pct)
    eumss_mask = ((gm_u["Total MCap Y2025"] >= eumss_full) &
                  (gm_u["Free Float MCap Y2025"] >= eumss_ff) &
                  (gm_u["Free Float Percent"] >= gm_min_ff_thr))
    gm_eumss = gm_u[eumss_mask].copy()

    # 4) Liquidity filter — buffer-aware
    gm_liq = apply_liquidity_new(
        gm_eumss, adtv_dm, adtv_em, atvr_dm, atvr_em,
        incumbents_isin=incumbents_isin if apply_buffer else None,
        m_adtv_dm=buffer_adtv_dm, m_adtv_em=buffer_adtv_em,
        m_atvr_dm=buffer_atvr_dm, m_atvr_em=buffer_atvr_em,
    )

    # 5) Coverage waterfall per country — buffer-aware
    # OPTION B: Large/Mid/Small auf POOL-Basis (Cum_Weight am gesamten Country-Pool).
    # Size Buffer (optional): Hysterese an den Grenzen large_thr (Large/Mid) und
    # mid_thr (Mid/Small) für Incumbents, abhängig vom Vorperioden-Segment. Wenn aus,
    # ist das Verhalten identisch zum bisherigen harten Cut.
    # #1: 0%-investierbare Titel (IF=0 → Adj_FF=0) bestehen EUMSS+Liquidität, sind aber
    # nicht investierbar (explizites Industrie-FOL=0, pre_investable, FF=0). MSCI schließt
    # FIF=0-Wertpapiere aus → eigenes Segment "Non-Investable": in KEINEM Index, aber im
    # Audit/Export sichtbar. Nur Adj_FF>0 läuft in den Coverage-Waterfall, damit kann das
    # tot==0-Skippen eines ganzen Landes (#2) nicht mehr auftreten.
    _adj_for_cov = pd.to_numeric(gm_liq["Adj_FF_MCap"], errors="coerce").fillna(0)
    gm_noninv = gm_liq[_adj_for_cov <= 0].copy()
    gm_noninv["Segment_New"] = "Non-Investable"
    # Reihenfolge-Toggle: Coverage-Pool = gm_liq (Liquidität zuerst, Default) ODER
    # gm_eumss (Labeling zuerst — Markt-Coverage auf vollem Float, illiquide Titel
    # zählen im Nenner mit und fallen erst per Mitgliedschafts-Gate unten raus).
    _seg_pool = gm_eumss if label_before_liquidity else gm_liq
    _adj_seg = pd.to_numeric(_seg_pool["Adj_FF_MCap"], errors="coerce").fillna(0)
    gm_liq_cov = _seg_pool[_adj_seg > 0].copy()

    use_size_buffer = bool(apply_size_buffer and incumbent_segments)
    gm_results = []
    for ctry, grp in gm_liq_cov.groupby("Mapping Country"):
        # Sekundärer Sort-Key: bei gleichem Total MCap (Multi-Class) liquideres Listing zuerst
        grp = grp.sort_values(["Total MCap Y2025", "Adj_FF_MCap"], ascending=[False, False]).copy()
        tot = grp[if_cum_col].sum()
        if tot == 0: continue
        grp["_c_before"] = grp[if_cum_col].cumsum().shift(1).fillna(0) / tot * 100

        if use_size_buffer:
            # Pro-Segment-Hysterese: Vorsegment je Titel → Übergangsfunktion (auf _c_before).
            _isin = _norm_isin(grp["ISIN"])
            grp["Segment_New"] = [
                _size_segment(incumbent_segments.get(_i), _cb, large_thr, mid_thr, size_buffer_pp)
                for _i, _cb in zip(_isin.values, grp["_c_before"].values)
            ]
        else:
            # Legacy: harter Standard-Cut (buffer_coverage für Incumbents), 70%-Split Large/Mid.
            # Straddle-Stock bleibt im höheren Bucket (konsistent mit 85%-Cut).
            if apply_buffer and len(incumbents_isin) > 0:
                _isin = _norm_isin(grp["ISIN"])
                grp_is_inc = _isin.isin(incumbents_isin)
                thr_per_stock = np.where(grp_is_inc, buffer_coverage, mid_thr)
            else:
                thr_per_stock = np.full(len(grp), mid_thr)
            in_cut = grp["_c_before"].values < thr_per_stock
            grp["Segment_New"] = np.where(
                in_cut,
                np.where(grp["_c_before"].values < large_thr, "Large Cap", "Mid Cap"),
                "Small Cap",
            )
        gm_results.append(grp)

    gm_all_cov = (pd.concat(gm_results, ignore_index=True) if gm_results
                  else pd.DataFrame(columns=gm_liq.columns.tolist() + ["Segment_New"]))

    # Labeling-zuerst: Mitgliedschaft = Label ∩ liquide. Auf dem vollen gm_eumss
    # gelabelte, aber illiquide Titel haben den Coverage-Nenner mitbestimmt, fallen
    # aber jetzt raus — alles Downstream (gm_std, gm_above85, gm_complete) wird so
    # automatisch liquiditäts-gefiltert.
    if label_before_liquidity and len(gm_all_cov) > 0:
        _liq_syms = set(gm_liq["Symbol"].dropna().unique())
        gm_all_cov = gm_all_cov[gm_all_cov["Symbol"].isin(_liq_syms)].copy()

    # Audit-Flag: Titel, deren Segment durch den Size Buffer abweichend vom reinen
    # Cut-off gehalten wurde (= Hysterese griff). Nur relevant bei aktivem Size Buffer.
    if use_size_buffer and len(gm_all_cov) > 0:
        _isin_all = _norm_isin(gm_all_cov["ISIN"])
        _prior_all = _isin_all.map(incumbent_segments)
        _cb_all = gm_all_cov["_c_before"].values
        _plain = np.where(_cb_all < large_thr, "Large Cap",
                          np.where(_cb_all < mid_thr, "Mid Cap", "Small Cap"))
        gm_all_cov["Size_Buffer_Held"] = [
            (isinstance(pr, str) and ac != pl and ac == pr)
            for pr, ac, pl in zip(_prior_all.values, gm_all_cov["Segment_New"].values, _plain)
        ]
    else:
        gm_all_cov["Size_Buffer_Held"] = False

    # Audit-Flag: Incumbents, die NUR dank des Coverage-Puffers (mid_thr + pp bzw.
    # buffer_coverage) im Standard-Index (Large/Mid) geblieben sind — der reine Cut-off
    # (_c_before ≥ mid_thr) hätte sie zu Small (= raus aus Standard) gemacht.
    # Einheitlich über beide Modi: wenn kein Puffer aktiv, ist ein Titel mit _c_before
    # ≥ mid_thr ohnehin nicht im Standard → Flag bleibt automatisch False.
    if len(gm_all_cov) > 0 and incumbents_isin:
        _isin_k = _norm_isin(gm_all_cov["ISIN"])
        gm_all_cov["Kept_In_Standard_By_Buffer"] = (
            _isin_k.isin(incumbents_isin)
            & (gm_all_cov["_c_before"] >= mid_thr)
            & gm_all_cov["Segment_New"].isin(["Large Cap", "Mid Cap"])
        )
    else:
        gm_all_cov["Kept_In_Standard_By_Buffer"] = False

    # Standard (Large+Mid) vs. coverage-basiertes Small (ersetzt das frühere gm_above85)
    gm_std     = gm_all_cov[gm_all_cov["Segment_New"].isin(["Large Cap", "Mid Cap"])].copy()
    gm_above85 = gm_all_cov[gm_all_cov["Segment_New"] == "Small Cap"].copy()

    # Variante A: Wer EUMSS besteht, aber die Liquidität reißt, erfüllt die
    # Investierbarkeits-Kriterien NICHT → komplett RAUS (nicht Small, nicht Micro,
    # nicht im IMI). Die Liquiditätshürde gilt damit für ALLE Tiers (Standard + Small).
    gm_liq_symbols   = set(gm_liq["Symbol"].dropna().unique())
    gm_eumss_symbols = set(gm_eumss["Symbol"].dropna().unique())
    gm_liq_excluded  = gm_eumss[~gm_eumss["Symbol"].isin(gm_liq_symbols)].copy()  # nur für Audit/Return
    # Micro = EUMSS gerissen (zu klein). Liquiditäts-Fails sind NICHT Micro.
    gm_micro = gm_u[~gm_u["Symbol"].isin(gm_eumss_symbols)].copy()
    gm_micro["Segment_New"] = "Micro Cap"

    # 6) Secondaries sind im Universe bereits enthalten und durchliefen alle Filter
    # (EUMSS, Liquidität, Coverage) konsistent mit Primaries — kein separater Re-Add nötig.
    gm_final = gm_std

    # gm_above85 = coverage-basiertes Small (hat Liquidität bestanden). gm_small entfällt (Variante A).
    # gm_noninv = EUMSS+Liquidität bestanden, aber IF=0 → "Non-Investable" (in keinem Index).
    gm_complete = pd.concat([gm_final, gm_above85, gm_micro, gm_noninv], ignore_index=True)
    gm_complete = gm_complete.drop_duplicates(subset=["Symbol"]).copy()
    # gm_micro trägt die Audit-Flags nicht → auf False auffüllen
    for _flag in ("Size_Buffer_Held", "Kept_In_Standard_By_Buffer"):
        if _flag in gm_complete.columns:
            gm_complete[_flag] = gm_complete[_flag].fillna(False).astype(bool)
        else:
            gm_complete[_flag] = False

    # 7) Ineligible filter
    gm_ie_removed = gm_complete.iloc[0:0].copy()
    if apply_ineligible and ineligible_df is not None and not ineligible_df.empty and selection_date is not None:
        gm_complete, gm_ie_removed, _ = apply_ineligible_filter(gm_complete, ineligible_df, selection_date)

    # 8) Index weights (Adj_FF_MCap basis) — use normalize_index_weight for exact 100.0 sum
    gm_complete = normalize_index_weight(gm_complete, adj_col="Adj_FF_MCap")

    # Standard Index = Large + Mid only. Re-normalise so this slice's weights sum to
    # 100% on their own (#3) — gm_complete's weights include Small/Micro/Non-Investable.
    gm_index_only = normalize_index_weight(
        gm_complete[gm_complete["Segment_New"].isin(["Large Cap", "Mid Cap"])].copy())

    # Buffer breakdown
    buffer_breakdown = None
    if apply_buffer and len(incumbents_isin) > 0 and len(gm_index_only) > 0:
        final_isin = _norm_isin(gm_index_only["ISIN"])
        final_isin_set = set(final_isin)
        kept = final_isin_set & incumbents_isin
        new_entries = final_isin_set - incumbents_isin
        lost = incumbents_isin - final_isin_set

        kept_df = gm_index_only[final_isin.isin(kept)].copy() if len(kept) > 0 else gm_index_only.iloc[:0].copy()
        if len(kept_df) > 0:
            ff_pct = pd.to_numeric(kept_df["Free Float Percent"], errors="coerce").fillna(0)
            adtv3 = pd.to_numeric(kept_df["3M ADTV Y2025"], errors="coerce").fillna(0)
            cls = kept_df["Classification"].fillna("")
            fail_ff = ff_pct < min_ff_pct
            fail_adtv = ((cls == "DM") & (adtv3 < adtv_dm)) | ((cls == "EM") & (adtv3 < adtv_em))
            saved = int((fail_ff | fail_adtv).sum())
        else:
            saved = 0

        buffer_breakdown = {
            "n_total_final":      len(gm_index_only),
            "n_incumbents_total": len(incumbents_isin),
            "n_kept_total":       len(kept),
            "n_kept_via_entry":   max(0, len(kept) - saved),
            "n_saved_by_buffer":  saved,
            "n_lost":             len(lost),
            "n_new_entries":      len(new_entries),
        }

    return {
        "gm_complete":      gm_complete,
        "gm_index_only":    gm_index_only,
        "gm_universe":      gm_u,
        "gm_eumss":         gm_eumss,
        "gm_liq":           gm_liq,
        "gm_liq_excluded":  gm_liq_excluded,
        "gm_std":           gm_std,
        "gm_final":         gm_final,
        "gm_noninv":        gm_noninv,
        "gm_ie_removed":    gm_ie_removed,
        "eumss_full":       eumss_full,
        "eumss_ff":         eumss_ff,
        "eumss_calib_fallback": eumss_calib_fallback,
        "buffer_breakdown": buffer_breakdown,
    }

__all__ = ['EUROPE_COUNTRIES', 'EXPORT_COL_RENAME', 'FOL_COUNTRY_CODE_MAP', 'INDEX_BY_CODE', 'INDEX_BY_NAME', 'INDEX_SERIES', 'MASTER_DYNAMIC_PREFIXES', 'MASTER_STATIC_REQUIRED', 'apply_fol_matrix', 'apply_ineligible_filter', 'apply_liquidity_new', 'build_index', 'build_new_universe', 'build_segment_matrix', 'build_snapshot_from_master', 'build_wide_matrix', 'clean_export_cols', 'with_fol_breakdown', 'format_bn', 'get_classification_dict', 'get_selection_date_for_snapshot', 'normalize_index_weight', 'run_selection_pipeline', 'to_excel_multi', 'validate_factset_data']
