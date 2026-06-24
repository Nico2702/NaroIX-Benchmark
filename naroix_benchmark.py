import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# ── Pipeline engine (extracted, Streamlit-free) ─────────────────────────────
from pipeline_core import *  # noqa: F401,F403  (public API via __all__)
from pipeline_core import _resolve_fol_row, _size_segment, _rank_band_select, _norm_isin  # internal helpers used by UI
from pipeline_core import derive_mapping_country  # zentrale Mapping-Country-Regel (File-Feld + Risk-First-Fallback)
from pipeline_core import apply_universe_exclusions, fif_inclusion_factor  # zentrale Exclusions + FIF-Formel
from pipeline_core import (
    load_master_excel as _c_load_master_excel,
    load_fol_matrix as _c_load_fol_matrix,
    load_ineligible_list as _c_load_ineligible_list,
    build_sector_fallback_table as _c_build_sector_fallback_table,
)

# Cache the file/data loaders at the UI layer (core stays cache-free).
@st.cache_data
def load_master_excel(file, valid_selection_dates_iso):
    return _c_load_master_excel(file, valid_selection_dates_iso)

@st.cache_data
def load_fol_matrix():
    return _c_load_fol_matrix()

@st.cache_data
def load_ineligible_list():
    return _c_load_ineligible_list()

@st.cache_data(show_spinner=False)
def build_sector_fallback_table(fol_matrix):
    return _c_build_sector_fallback_table(fol_matrix)

# ─── Helper functions ──────────────────────────────────────────────────────────

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NaroIX Benchmark Series",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0f1117; }
  [data-testid="stSidebar"] { background: #161b27; border-right: 1px solid #2a2f45; }
  h1, h2, h3, h4 { color: #e8eaf6; }
  .stTabs [data-baseweb="tab-list"] { gap: 8px; background: #161b27; padding: 4px 8px; border-radius: 10px; }
  .stTabs [data-baseweb="tab"] { background: #1e2536; border-radius: 8px; color: #8892b0; font-weight: 500; padding: 6px 20px; }
  .stTabs [aria-selected="true"] { background: #2979ff !important; color: #fff !important; }
  div[data-testid="metric-container"] {
    background: #161b27; border: 1px solid #2a2f45; border-radius: 12px;
    padding: 16px 20px;
  }
  .segment-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 600; margin: 2px;
  }
  .badge-large { background: #1a3a5c; color: #64b5f6; }
  .badge-mid   { background: #1a4a2a; color: #81c784; }
  .badge-small { background: #3a2a1a; color: #ffb74d; }
  .badge-em    { background: #3a1a3a; color: #ce93d8; }
  .info-box {
    background: #161b27; border-left: 4px solid #2979ff;
    padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;
    color: #aab4d0; font-size: 13px;
  }
  .warning-box {
    background: #2a1f00; border-left: 4px solid #ffc107;
    padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;
    color: #ffe082; font-size: 13px;
  }
  div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ─── Helper Functions ──────────────────────────────────────────────────────────



@st.cache_data(show_spinner=False)
def to_excel_one(df, sheet_name="Sheet1"):
    """Single-sheet Excel export, cached on df content — for the per-section
    download buttons in the Multi-Period tab (rebuilds only when the table changes)."""
    return to_excel_multi({sheet_name: df})

# clean_export_cols / EXPORT_COL_RENAME are imported from pipeline_core (single
# source of truth). to_excel_multi() applies clean_export_cols to every sheet, so
# Excel exports are handled centrally; the explicit calls below are only for the
# on-screen st.dataframe tables (which don't go through to_excel_multi).




# ── NaroIX Index Series — single source of truth ────────────────────────────
# Region: "DM", "EM", "GM" (= DM+EM; FM is always excluded). segments ⊆ Large/Mid/Small.
# Standard = Large+Mid, All Cap = Large+Mid+Small. The 6 aggregate products are just
# broader scopes of the 9 atomic region×size sleeves — one helper covers all 15.










SEGMENT_COLORS = {
    "Large Cap": "#2979ff",
    "Mid Cap":   "#00e676",
    "Small Cap": "#ff9100",
    "Micro / Excluded": "#37474f",
}


# ─── Europe Index Constituents (geographisch) ──────────────────────────────────
# Die DM/EM-Filterung pro Selection Date erfolgt dynamisch über Historical_Classification.xlsx.
# D.h. POLAND ist vor 2024-02-21 EM und landet nicht im (DM-basierten) Europe Index,
# GREECE/HUNGARY/CZECH REPUBLIC sind aktuell EM und werden analog ausgefiltert.


# ─── FOL Matrix Country Code Mapping ─────────────────────────────────────────
# FactSet "Exchange Country Name" (UPPERCASE) → ISO2 wie in der YAML.
# Nur Länder mit FOL-Einträgen in der Matrix. Nicht-gelistete Länder → IF=1.0.


@st.cache_data
def load_excel(file):
    """Load FactSet export, auto-detecting header row and year suffix.
    Returns (df, year_suffix) where columns are normalized to remove year suffix.
    """
    try:
        # Auto-detect header row (search first 10 rows for "Symbol" column)
        header_row = 0
        for i in range(10):
            _probe = pd.read_excel(file, header=i, nrows=1, dtype=str)
            if "Symbol" in _probe.columns:
                header_row = i
                break

        df = pd.read_excel(file, header=header_row, dtype=str)

        # Auto-detect year suffix from column names (e.g. "Total MCap Y2026" → "Y2026")
        import re as _re
        year_suffix = "Y2025"  # default fallback
        for col in df.columns:
            m = _re.search(r'(Y\d{4})$', col)
            if m:
                year_suffix = m.group(1)
                break

        # Normalize column names: remove year suffix so rest of code is year-agnostic
        rename_map = {
            f"Total MCap {year_suffix}":      "Total MCap Y2025",
            f"Share MCap {year_suffix}":      "Share MCap Y2025",   # informativ (Export), falls vorhanden
            f"Free Float MCap {year_suffix}": "Free Float MCap Y2025",
            f"Free Float Percent":            "Free Float Percent",
            f"1M ADTV {year_suffix}":         "1M ADTV Y2025",
            f"3M ADTV {year_suffix}":         "3M ADTV Y2025",
            f"6M ADTV {year_suffix}":         "6M ADTV Y2025",
            f"12M ADTV {year_suffix}":        "12M ADTV Y2025",
            # Column name differences between FactSet export versions
            "Country Name":                  "Exchange Country Name",
            "Float PCT":                     "Free Float Percent",
            "Sector":                        "FactSet Econ Sector",
            "Industry":                      "FactSet Industry",    # correct spelling in newer exports
            "Inudstry":                      "FactSet Industry",    # typo in older exports
        }
        df = df.rename(columns=rename_map)

        # If Exchange Country Name still missing, derive from Country of Incorp as fallback
        if "Exchange Country Name" not in df.columns:
            if "Country of Risk" in df.columns:
                df["Exchange Country Name"] = df["Country of Risk"].fillna("")
            else:
                df["Exchange Country Name"] = ""

        return df, year_suffix

    except Exception as e:
        st.error(f"Fehler beim Laden der Datei: {e}")
        return pd.DataFrame(), "Y2025"


# ═══════════════════════════════════════════════════════════════════════════
# Master-File Loader (Multi-Period)
# ═══════════════════════════════════════════════════════════════════════════

# Dynamische Feld-Prefixe (alle Felder mit YYYY-MM-DD Suffix im Master-File)
# Master-File-Format: "Float MCap" (getrennt). "FloatMCap" und "Free Float MCap"
# bleiben als Rückwärtskompatibilität für ältere Files.

# Pflicht-Statische Felder




def render_validation_warnings(df_raw, anomalies):
    """Render der Validierungs-Anomalien als Streamlit-UI."""
    if not anomalies:
        return  # Kein Issue — keine UI-Anzeige

    n_errors   = sum(1 for sev, _, _ in anomalies if sev == "error")
    n_warnings = sum(1 for sev, _, _ in anomalies if sev == "warning")
    n_total    = sum(int(mask.sum()) for _, _, mask in anomalies)

    summary = []
    if n_errors > 0:
        summary.append(f"{n_errors} Fehler")
    if n_warnings > 0:
        summary.append(f"{n_warnings} Warnung(en)")

    with st.expander(f"⚠️ Daten-Validierung: {' / '.join(summary)} ({n_total} betroffene Zeilen)", expanded=False):
        st.caption("Diese Anomalien sind nicht-blockierend; die Pipeline läuft trotzdem. "
                   "Bitte FactSet-Export prüfen.")
        for sev, label, mask in anomalies:
            n = int(mask.sum())
            icon = "🔴" if sev == "error" else "🟡"
            st.markdown(f"**{icon} {label} — {n} Treffer**")
            cols_show = [c for c in ["Exchange Ticker","Name","ISIN","Sec Type","Listing",
                                      "Free Float MCap Y2025","Free Float Percent",
                                      "Total MCap Y2025","Closing Price",
                                      "3M ADTV Y2025","6M ADTV Y2025"] if c in df_raw.columns]
            _sub = df_raw[mask][cols_show].copy()

            # Bei FF/Total-Anomalien: Ratio berechnen + nach Ratio absteigend sortieren
            if "FF MCap" in label and "Total MCap" in label:
                _tot = pd.to_numeric(_sub["Total MCap Y2025"], errors="coerce")
                _ff  = pd.to_numeric(_sub["Free Float MCap Y2025"], errors="coerce")
                _sub["FF/Total Ratio"] = (_ff / _tot.where(_tot > 0)).round(3)
                _sub = _sub.sort_values("FF/Total Ratio", ascending=False)

            st.dataframe(clean_export_cols(_sub).head(50), width='stretch', hide_index=True)
            if n > 50:
                st.caption(f"... {n-50} weitere ausgeblendet")






@st.cache_data
def load_historical_data():
    """Load Historical_Classification, Selection_Dates, and China_Inclusion_Factor.

    Akzeptiert Dateinamen sowohl mit Unterstrich als auch mit Leerzeichen.

    Returns:
        hc_df: DataFrame mit Country als Spalte + date-Objekten als Spaltenköpfen für Klassifikationen
        selection_dates: sortierte Liste aller Selection Dates (als date-Objekte)
        china_if_map: Dict {date: China Inclusion Factor (0.0-1.0)}
    """
    def _try_read(candidates, **kwargs):
        """Versuche Excel zu laden aus einer Liste von Kandidaten-Dateinamen."""
        _last_err = None
        for name in candidates:
            try:
                return pd.read_excel(name, **kwargs)
            except FileNotFoundError as e:
                _last_err = e
                continue
        raise FileNotFoundError(f"Keine der Varianten gefunden: {candidates}") from _last_err

    try:
        hc = _try_read(["Historical_Classification.xlsx", "Historical Classification.xlsx"])

        # Spalten-Header normalisieren (gemischt datetime/string → date)
        new_cols = ["Country"]
        for col in hc.columns[1:]:
            try:
                new_cols.append(pd.to_datetime(col).date())
            except Exception:
                new_cols.append(col)
        hc.columns = new_cols
        hc["Country"] = hc["Country"].astype(str).str.upper().str.strip()

        # Selection Dates
        sd = _try_read(["Selection_Dates.xlsx", "Selection Dates.xlsx"], usecols=[0])
        sd.columns = ["Selection Date"]
        sd["Selection Date"] = pd.to_datetime(sd["Selection Date"]).dt.date
        selection_dates = sorted(sd["Selection Date"].dropna().unique())

        # China Inclusion Factor
        ci = _try_read(["China_Inclusion_Factor.xlsx", "China Inclusion Factor.xlsx"])
        ci["Selection Date"] = pd.to_datetime(ci["Selection Date"]).dt.date
        china_if_map = dict(zip(ci["Selection Date"], ci["China Inclusion Factor"].astype(float)))

        return hc, selection_dates, china_if_map

    except Exception as e:
        st.error(f"Fehler beim Laden der Historical-Referenzfiles: {e}")
        return pd.DataFrame(), [], {}










# ═══════════════════════════════════════════════════════════════════════════
# FOL MATRIX (Foreign Ownership Limits per country/sector/industry/year)
# ═══════════════════════════════════════════════════════════════════════════













# ═══════════════════════════════════════════════════════════════════════════
# run_selection_pipeline: Komplette Pipeline gekapselt für Single + Multi-Period
# ═══════════════════════════════════════════════════════════════════════════



def render_new_tab(tab_name, df_included, large_pct, mid_pct,
                   china_if,
                   params_dict,
                   diag_rows=None, diag_caption=None,
                   adtv_dm=0, adtv_em=0, atvr_dm=0, atvr_em=0,
                   small_pct=99, min_ff=0.15, if_mode="Selektion",
                   df_universe=None, buffer_breakdown=None):
    """Render standard visuals for a new index tab.

    buffer_breakdown: optional dict with keys n_total_final, n_incumbents_total, n_kept_total,
                      n_kept_via_entry, n_saved_by_buffer, n_lost, n_new_entries.
                      Wenn gesetzt, wird ein Buffer-Audit-Block angezeigt.
    """

    df_dm = df_included[df_included["Classification"]=="DM"].copy()
    df_em = df_included[df_included["Classification"]=="EM"].copy()

    # Non-Investable (IF=0) wird mitgeführt, aber nur angezeigt wenn vorhanden —
    # sonst kein leerer Zusatz-Row im Normalfall (siehe seg_table unten).
    seg_order = ["Large Cap","Mid Cap","Small Cap","Micro Cap","Non-Investable"]

    # ── Top metrics (ACWI = Large+Mid only) ─────────────────────────────────
    _acwi_dm = df_dm[df_dm["Segment_New"].isin(["Large Cap","Mid Cap"])]
    _acwi_em = df_em[df_em["Segment_New"].isin(["Large Cap","Mid Cap"])]
    total_adj = df_included["Adj_FF_MCap"].sum()
    _acwi_adj = _acwi_dm["Adj_FF_MCap"].sum() + _acwi_em["Adj_FF_MCap"].sum()
    em_adj    = _acwi_em["Adj_FF_MCap"].sum()
    em_w      = em_adj / _acwi_adj * 100 if _acwi_adj > 0 else 0

    m1,m2,m3,m4,m5,m6,m7 = st.columns(7)
    m1.metric("Total ACWI",      f"{len(_acwi_dm)+len(_acwi_em):,}")
    m2.metric("DM Stocks",       f"{len(_acwi_dm):,}")
    m3.metric("EM Stocks",       f"{len(_acwi_em):,}")
    m4.metric("DM FF MCap",      format_bn(_acwi_dm["Free Float MCap Y2025"].sum()))
    m5.metric("EM FF MCap",      format_bn(_acwi_em["Free Float MCap Y2025"].sum()))
    m6.metric("EM Adj. FF MCap", format_bn(em_adj))
    m7.metric("EM Adj. Weight",  f"{em_w:.2f}%")

    # ── Selektionskriterien + Pipeline Diagnostik ────────────────────────────
    if diag_rows is not None:
        _eumss_line = ""
        if diag_caption and "EUMSS_FULL" in diag_caption:
            _parts = [p.strip() for p in diag_caption.split("|") if any(k in p for k in ["EUMSS_FULL","EUMSS_FF","FF Ratio"])]
            if _parts:
                _eumss_line = "<br>" + " &nbsp;|&nbsp; ".join(_parts)

        # Dynamische IF-Zusammenfassung aus dem DataFrame
        _if_parts = [f"China {china_if*100:.0f}%"]
        if "IF_Source" in df_included.columns:
            _non_cn = df_included[~df_included["Exchange Country Name"].fillna("").str.upper().eq("CHINA")]
            _fol_applied = _non_cn[_non_cn["IF_Source"].astype(str).isin(["Industry", "Sector (strengster)", "Country Default"])]
            if len(_fol_applied) > 0:
                _if_parts.append(f"FOL Matrix: {len(_fol_applied)} Stocks gemappt")
                _capped = _fol_applied[_fol_applied["IF"] < 1.0]
                if len(_capped) > 0:
                    _if_parts.append(f"davon gecappt (IF<1): {len(_capped)}")
            else:
                _if_parts.append("FOL Matrix: inaktiv")
        _if_line = " &nbsp;|&nbsp; ".join(_if_parts)

        st.markdown(f"""
<div class="info-box">
<b>Selektionskriterien</b><br>
Listing: {params_dict.get('Listing','—')} &nbsp;|&nbsp; Filter: {params_dict.get('Filter','—')} &nbsp;|&nbsp; IF: {if_mode}<br>
ADTV DM: {adtv_dm:,.0f} USD &nbsp;|&nbsp; ADTV EM: {adtv_em:,.0f} USD &nbsp;|&nbsp; ATVR DM: {atvr_dm*100:.0f}% &nbsp;|&nbsp; ATVR EM: {atvr_em*100:.0f}%<br>
Large: {large_pct}% &nbsp;|&nbsp; Mid: {mid_pct}% &nbsp;|&nbsp; Small: {small_pct}% &nbsp;|&nbsp; Min FF: {min_ff*100:.0f}%<br>
Inclusion Factor: {_if_line}{("<br><br>" + _eumss_line[4:]) if _eumss_line else ""}
</div>
""", unsafe_allow_html=True)
        with st.expander("🔍 Pipeline Diagnostik", expanded=False):
            st.dataframe(pd.DataFrame(diag_rows), width='stretch', hide_index=True)
            if diag_caption:
                st.caption(diag_caption)

    # ── Buffer Rules Audit ──────────────────────────────────────────────────
    if buffer_breakdown is not None:
        st.markdown("---")
        st.markdown("### 🛡️ Buffer Rules — Aufschlüsselung")
        bb = buffer_breakdown
        _ba, _bb, _bc = st.columns(3)
        with _ba:
            st.metric("Aktien insgesamt im Index", f"{bb['n_total_final']:,}")
        with _bb:
            st.metric("Davon waren bereits im Index", f"{bb['n_kept_total']:,}",
                      f"{bb['n_kept_total']/max(bb['n_incumbents_total'],1)*100:.1f}% der Incumbents")
        with _bc:
            st.metric("Neu im Index (durch Entry)", f"{bb['n_new_entries']:,}",
                      f"{bb['n_new_entries']/max(bb['n_total_final'],1)*100:.1f}% des Index")

        _bd, _be = st.columns(2)
        with _bd:
            st.metric("Incumbents — durch Buffer gerettet", f"{bb['n_saved_by_buffer']:,}",
                      help="Diese Aktien hätten die Entry-Schwellen NICHT geschafft, sind aber dank "
                           "weicherer Maintenance-Schwellen drin geblieben.")
        with _be:
            st.metric("Incumbents — aus Index gefallen", f"{bb['n_lost']:,}",
                      f"-{bb['n_lost']/max(bb['n_incumbents_total'],1)*100:.1f}% Drop-Out",
                      delta_color="inverse",
                      help="Diese Aktien waren in der vorherigen Periode im Index, haben aber selbst "
                           "die weicheren Maintenance-Schwellen nicht geschafft.")

        _df_bb = pd.DataFrame([
            {"Kategorie": "✅ Aktien insgesamt im Index", "Anzahl": bb["n_total_final"], "Anteil": "100.0%"},
            {"Kategorie": "  └─ davon Incumbents (waren letzte Periode drin)",
             "Anzahl": bb["n_kept_total"],
             "Anteil": f"{bb['n_kept_total']/max(bb['n_total_final'],1)*100:.1f}%"},
            {"Kategorie": "      ├─ via Entry-Regeln gehalten (auch ohne Buffer drin)",
             "Anzahl": bb["n_kept_via_entry"],
             "Anteil": f"{bb['n_kept_via_entry']/max(bb['n_total_final'],1)*100:.1f}%"},
            {"Kategorie": "      └─ via Buffer-Maintenance gerettet",
             "Anzahl": bb["n_saved_by_buffer"],
             "Anteil": f"{bb['n_saved_by_buffer']/max(bb['n_total_final'],1)*100:.1f}%"},
            {"Kategorie": "  └─ Neueinsteiger (Entry-Regeln neu erfüllt)",
             "Anzahl": bb["n_new_entries"],
             "Anteil": f"{bb['n_new_entries']/max(bb['n_total_final'],1)*100:.1f}%"},
            {"Kategorie": "❌ Aus Index gefallen (waren letzte Periode drin)",
             "Anzahl": bb["n_lost"],
             "Anteil": f"{bb['n_lost']/max(bb['n_incumbents_total'],1)*100:.1f}% der Incumbents"},
            {"Kategorie": "📊 Total Incumbents (Vorperiode)",
             "Anzahl": bb["n_incumbents_total"],
             "Anteil": "100.0%"},
        ])
        st.dataframe(_df_bb, width='stretch', hide_index=True)
        st.caption(
            f"Buffer-Saldo: **+{bb['n_new_entries']:,}** Neue, **-{bb['n_lost']:,}** Verlorene, "
            f"Netto-Veränderung Index-Größe: **{bb['n_total_final'] - bb['n_incumbents_total']:+,}** Stocks."
        )

    # ── 5 Index Products ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Index-Produkte — NaroIX Index Series**")
    st.caption(f"Alle {len(INDEX_SERIES)} Produkte für diesen Snapshot (Quelle: INDEX_SERIES). # Const = Konstituenten · "
               "DM/EM = Aufteilung (Global = DM+EM) · MCap = Summe über die Konstituenten. Frontier Markets (FM) ausgeschlossen.")
    _series_rows = []
    for _ix in INDEX_SERIES:
        _ci = build_index(df_included, _ix["region"], _ix["segments"],
                          industries=_ix.get("industries"), top_n=_ix.get("top_n"))
        _series_rows.append({
            "Code": _ix["code"],
            "Index": _ix["name"],
            "# Const": len(_ci),
            "DM": int((_ci["Classification"] == "DM").sum()),
            "EM": int((_ci["Classification"] == "EM").sum()),
            "FF MCap": format_bn(_ci["Free Float MCap Y2025"].sum()),
            "Adj. FF MCap": format_bn(_ci["Adj_FF_MCap"].sum()),
            "Coverage": _ix["coverage"],
            "Vergleichbar mit": _ix["vs"],
        })
    _series_df = pd.DataFrame(_series_rows)
    _flagship = {"NX-EU-LM", "NX-DM-LM", "NX-GM-LM"}   # Standard-Flaggschiffe (Large+Mid) hervorheben (EM bewusst nicht)
    def _style_series(df):
        def rs(row):
            return (["background-color:#1a3a5c;font-weight:700;"]*len(row)
                    if row["Code"] in _flagship else [""]*len(row))
        return df.style.apply(rs, axis=1)
    # Feste Höhe, damit alle Zeilen ohne inneren Scrollbalken sichtbar sind (~35px/Zeile + Header)
    st.dataframe(_style_series(_series_df), width='stretch', hide_index=True,
                 height=35 * (len(_series_df) + 1) + 3)

    st.markdown("""
<div class="info-box">
<b>Developed Markets (DM)</b> &nbsp;·&nbsp; <b>Emerging Markets (EM)</b> &nbsp;·&nbsp; <b>Global Markets (GM = DM+EM)</b><br>
Größenstufen (kumulative Adj-FF-Coverage pro Land): <b>Large</b> 0–70% · <b>Mid</b> 70–85% · <b>Small</b> 85–99%<br>
<b>Standard</b> = Large+Mid (Flaggschiff, hervorgehoben) &nbsp;·&nbsp; <b>All Cap</b> = Large+Mid+Small &nbsp;·&nbsp; Frontier Markets (FM) ausgeschlossen.<br>
<b>Thematisch / Fixed-Count</b>: US 500 (Top 500 US), US Tech 100 / US Tech (FactSet-Tech-Industrien), World 100 (Top 100 global) — Auswahl nach <b>Total MCap</b>, Gewichtung wie überall nach Adj-FF.
</div>
""", unsafe_allow_html=True)

    # ── Segment Tables ────────────────────────────────────────────────────────
    st.markdown("---")
    _sc1, _sc2 = st.columns(2)

    def seg_table(df_cls, label):
        rows = []
        std = df_cls[df_cls["Segment_New"].isin(["Large Cap","Mid Cap"])]
        std_adj = std["Adj_FF_MCap"].sum()
        for seg in seg_order:
            s = df_cls[df_cls["Segment_New"]==seg]
            if seg == "Non-Investable" and len(s) == 0:
                continue  # nur zeigen wenn es 0%-investierbare Titel gibt
            rows.append({
                "Segment": seg,
                "Stocks": len(s),
                "FF MCap": format_bn(s["Free Float MCap Y2025"].sum()) if len(s)>0 else "—",
                "Adj. FF MCap": format_bn(s["Adj_FF_MCap"].sum()) if len(s)>0 else "—",
                "Weight %": f"{s['Adj_FF_MCap'].sum()/std_adj*100:.2f}%" if std_adj>0 and len(s)>0 else "—",
            })
        # Standard Index subtotal
        rows.insert(2, {
            "Segment": f"── {label} Index (Large+Mid)",
            "Stocks": len(std),
            "FF MCap": format_bn(std["Free Float MCap Y2025"].sum()),
            "Adj. FF MCap": format_bn(std["Adj_FF_MCap"].sum()),
            "Weight %": "100.00%",
        })
        return pd.DataFrame(rows)

    with _sc1:
        st.markdown("**DM Segmente**")
        _dm_seg = seg_table(df_dm, "World")
        def _style_dm_seg(df):
            def rs(row):
                if "World Index" in row["Segment"]: return ["background-color:#1a3a5c;font-weight:700;"]*len(row)
                return [""]*len(row)
            return df.style.apply(rs, axis=1)
        st.dataframe(_style_dm_seg(_dm_seg), width='stretch', hide_index=True)

    with _sc2:
        st.markdown("**EM Segmente**")
        _em_seg = seg_table(df_em, "EM")
        def _style_em_seg(df):
            def rs(row):
                if "EM Index" in row["Segment"]: return ["background-color:#1a2a1a;font-weight:700;"]*len(row)
                return [""]*len(row)
            return df.style.apply(rs, axis=1)
        st.dataframe(_style_em_seg(_em_seg), width='stretch', hide_index=True)

    st.markdown("""
<div class="info-box">
<b>Weight %</b> — DM Segmente: Anteil am World Index (DM Large+Mid) &nbsp;|&nbsp; EM Segmente: Anteil am EM Index (EM Large+Mid)<br>
Small Cap und Micro Cap werden relativ zum jeweiligen Standard Index ausgewiesen.
</div>
""", unsafe_allow_html=True)

    # ── Country Breakdown ─────────────────────────────────────────────────────
    st.markdown("---")
    _cc1, _cc2 = st.columns(2)

    _acwi_dm_std = df_dm[df_dm["Segment_New"].isin(["Large Cap","Mid Cap"])]
    _acwi_em_std = df_em[df_em["Segment_New"].isin(["Large Cap","Mid Cap"])]
    _acwi_std_adj = _acwi_dm_std["Adj_FF_MCap"].sum() + _acwi_em_std["Adj_FF_MCap"].sum()

    def country_table(df_cls, cls_adj):
        ct = df_cls.groupby("Mapping Country").agg(
            Stocks=("Symbol","count"),
            FF_MCap=("Free Float MCap Y2025","sum"),
            Adj_MCap=("Adj_FF_MCap","sum"),
            Avg_MCap=("Adj_FF_MCap","mean"),
        ).reset_index().sort_values("Adj_MCap", ascending=False)
        ct["FF MCap"] = ct["FF_MCap"].apply(format_bn)
        ct["Avg Adj. MCap"] = ct["Avg_MCap"].apply(format_bn)
        ct["Weight %"] = (ct["Adj_MCap"] / cls_adj * 100).apply(lambda x: f"{x:.2f}%") if cls_adj > 0 else "—"
        return ct[["Mapping Country","Stocks","FF MCap","Avg Adj. MCap","Weight %"]].rename(columns={"Mapping Country":"Land"})

    with _cc1:
        st.markdown(f"**DM Country Breakdown ({len(_acwi_dm_std):,} Stocks — Large+Mid)**")
        st.dataframe(country_table(_acwi_dm_std, _acwi_dm_std["Adj_FF_MCap"].sum()),
                     width='stretch', hide_index=True)
    with _cc2:
        st.markdown(f"**EM Country Breakdown ({len(_acwi_em_std):,} Stocks — Large+Mid)**")
        st.dataframe(country_table(_acwi_em_std, _acwi_em_std["Adj_FF_MCap"].sum()),
                     width='stretch', hide_index=True)

    # ── Country Charts ────────────────────────────────────────────────────────
    st.markdown("---")
    _acwi_std = df_included[df_included["Segment_New"].isin(["Large Cap","Mid Cap"])].copy()
    _by_w = _acwi_std.groupby("Mapping Country").agg(
        Stocks=("Symbol","count"), Adj=("Adj_FF_MCap","sum")).reset_index()
    _by_w["Weight%"] = (_by_w["Adj"]/_acwi_std["Adj_FF_MCap"].sum()*100).round(2)
    _by_w = _by_w.sort_values("Adj", ascending=False)
    _top30 = _by_w.head(30)
    _rest  = _by_w.iloc[30:]
    if len(_rest):
        _top30 = pd.concat([pd.DataFrame([{"Mapping Country":f"Others ({len(_rest)})", "Stocks":_rest["Stocks"].sum(), "Adj":_rest["Adj"].sum(), "Weight%":_rest["Weight%"].sum()}]), _top30])
    _top30 = _top30.sort_values("Adj", ascending=True)

    _ch1, _ch2 = st.columns(2)
    with _ch1:
        st.markdown("**Nach Anzahl Stocks (%)**")
        _by_s2 = _acwi_std.groupby("Mapping Country").agg(Stocks=("Symbol","count")).reset_index()
        _by_s2["Pct"] = (_by_s2["Stocks"]/len(_acwi_std)*100).round(2)
        _by_s2 = _by_s2.sort_values("Stocks", ascending=False)
        _top30s = _by_s2.head(30)
        _rests  = _by_s2.iloc[30:]
        if len(_rests):
            _top30s = pd.concat([pd.DataFrame([{"Mapping Country":f"Others ({len(_rests)})", "Stocks":_rests["Stocks"].sum(), "Pct":_rests["Pct"].sum()}]), _top30s])
        _top30s = _top30s.sort_values("Stocks", ascending=True)
        fig_s = go.Figure(go.Bar(x=_top30s["Pct"], y=_top30s["Mapping Country"],
            orientation="h", marker_color="#2979ff",
            text=_top30s["Pct"].apply(lambda x: f"{x:.2f}%"), textposition="outside"))
        fig_s.update_layout(template="plotly_dark", paper_bgcolor="#0f1117", plot_bgcolor="#161b27",
            height=700, margin=dict(t=10,b=10,l=10,r=60), xaxis=dict(showgrid=False))
        st.plotly_chart(fig_s, width='stretch')

    with _ch2:
        st.markdown("**Nach Gewicht (Adj. FF MCap %)**")
        fig_w = go.Figure(go.Bar(x=_top30["Weight%"], y=_top30["Mapping Country"],
            orientation="h", marker_color="#ce93d8",
            text=_top30["Weight%"].apply(lambda x: f"{x:.2f}%"), textposition="outside"))
        fig_w.update_layout(template="plotly_dark", paper_bgcolor="#0f1117", plot_bgcolor="#161b27",
            height=700, margin=dict(t=10,b=10,l=10,r=60), xaxis=dict(showgrid=False))
        st.plotly_chart(fig_w, width='stretch')

    # ── Donut + IF Impact ────────────────────────────────────────────────────
    st.markdown("---")
    _d1, _d2 = st.columns([1,1])
    with _d1:
        st.markdown("**ACWI Composition (DM vs EM)**")
        _donut = pd.DataFrame([
            {"Label":"DM","FF MCap":df_dm[df_dm["Segment_New"].isin(["Large Cap","Mid Cap"])]["Adj_FF_MCap"].sum()},
            {"Label":"EM","FF MCap":df_em[df_em["Segment_New"].isin(["Large Cap","Mid Cap"])]["Adj_FF_MCap"].sum()},
        ])
        fig_d = px.pie(_donut, names="Label", values="FF MCap",
            color="Label", color_discrete_map={"DM":"#2979ff","EM":"#ce93d8"},
            template="plotly_dark", hole=0.45)
        fig_d.update_layout(paper_bgcolor="#0f1117", height=350, margin=dict(t=10,b=10))
        st.plotly_chart(fig_d, width='stretch')

    with _d2:
        st.markdown("**Inclusion Factor Impact**")
        _acwi_if = df_included[df_included["Segment_New"].isin(["Large Cap","Mid Cap"])].copy()
        _tot_ff  = _acwi_if["Free Float MCap Y2025"].sum()
        _tot_adj2 = _acwi_if["Adj_FF_MCap"].sum()

        # Pro Land aufschlüsseln (nur Länder mit echtem IF-Impact anzeigen)
        # Reihenfolge: China A/H zuerst, dann FOL-Länder, dann Thailand
        _if_rows = []

        _ecn = _acwi_if["Exchange Country Name"].fillna("").str.upper()
        _map_ctry = _acwi_if["Mapping Country"].fillna("").str.upper()
        _src = _acwi_if.get("IF_Source", pd.Series([""]*len(_acwi_if))).fillna("").astype(str)

        # China separat (A-Shares via Exchange=CHINA, H-Shares/Red Chips via Mapping=CHINA aber Exchange!=CHINA)
        _country_entries = [
            ("China A-Shares",              _ecn=="CHINA"),
            ("China H-Shares / Red Chips",  (_map_ctry=="CHINA") & (_ecn!="CHINA")),
            ("Indien (FOL)",                _ecn=="INDIA"),
            ("Saudi-Arabien (FOL)",         _ecn=="SAUDI ARABIA"),
            ("Qatar (FOL)",                 _ecn=="QATAR"),
            ("UAE (FOL)",                   _ecn=="UNITED ARAB EMIRATES"),
            ("Malaysia (FOL)",              _ecn=="MALAYSIA"),
            ("Kuwait (FOL)",                _ecn=="KUWAIT"),
            ("Indonesien (FOL)",            _ecn=="INDONESIA"),
            ("Süd-Korea (FOL)",             _ecn=="SOUTH KOREA"),
            ("Philippinen (FOL)",           _ecn=="PHILIPPINES"),
            ("Thailand (NVDR/SHARE)",       _ecn=="THAILAND"),
        ]

        for _nm, _msk in _country_entries:
            _sub = _acwi_if[_msk]
            if len(_sub) == 0:
                continue
            _ff  = _sub["Free Float MCap Y2025"].sum()
            _adj = _sub["Adj_FF_MCap"].sum()
            if _ff <= 0 and _adj <= 0:
                continue
            _capped = int((_sub["IF"] < 1.0).sum()) if "IF" in _sub.columns else 0
            _if_rows.append({
                "Land": _nm,
                "Stocks": len(_sub),
                "davon gecappt": _capped,
                "Weight (vor)":  round(_ff  / _tot_ff   * 100, 4) if _tot_ff   > 0 else 0,
                "Weight (nach)": round(_adj / _tot_adj2 * 100, 4) if _tot_adj2 > 0 else 0,
                "Δ":             round(_adj/_tot_adj2*100 - _ff/_tot_ff*100, 4) if _tot_ff>0 and _tot_adj2>0 else 0,
            })

        if _if_rows:
            _if_df = pd.DataFrame(_if_rows)
            _if_df = pd.concat([_if_df, pd.DataFrame([{
                "Land":"Total (IF-betroffen)",
                "Stocks": _if_df["Stocks"].sum(),
                "davon gecappt": _if_df["davon gecappt"].sum(),
                "Weight (vor)":  round(_if_df["Weight (vor)"].sum(),  4),
                "Weight (nach)": round(_if_df["Weight (nach)"].sum(), 4),
                "Δ":             round(_if_df["Δ"].sum(), 4)}])], ignore_index=True)
            def _sif(df):
                def rs(row):
                    if row["Land"]=="Total (IF-betroffen)": return ["background-color:#1a2a4a;font-weight:600;"]*len(row)
                    return [""]*len(row)
                return df.style.apply(rs, axis=1)
            st.dataframe(_sif(_if_df), width='stretch', hide_index=True)
        else:
            st.caption("Keine IF-betroffenen Länder im Index.")

    # ── Download ──────────────────────────────────────────────────────────────
    st.markdown("---")
    # IF + FOL_Value bleiben im Export (zeigen, wie Adj_FF_MCap zustande kommt;
    # to_excel_multi positioniert sie via with_fol_breakdown vor Adj_FF_MCap).
    _drop = ["_cum_pct","_c","_cp2","_cp2_before","ADTV_Best"]
    _drop_universe = _drop + ["Index_Weight"]

    def _prep(df, adj_col="Adj_FF_MCap"):
        cols = [c for c in df.columns if c not in _drop]
        return normalize_index_weight(df[cols].copy(), adj_col)

    # Universe sheet: use df_universe if provided (full primary+secondary after exclusions)
    # This matches the Universe Overview count in Tab 1
    _universe_dl = (df_universe if df_universe is not None else df_included).copy()
    _universe_dl = _universe_dl[[c for c in _universe_dl.columns if c not in _drop_universe]]

    _world_dm_dl  = df_included[(df_included["Classification"]=="DM") & df_included["Segment_New"].isin(["Large Cap","Mid Cap"])]
    _world_em_dl  = df_included[(df_included["Classification"]=="EM") & df_included["Segment_New"].isin(["Large Cap","Mid Cap"])]
    _acwi_dl      = df_included[df_included["Segment_New"].isin(["Large Cap","Mid Cap"])]
    _world_imi_dl = df_included[(df_included["Classification"]=="DM") & df_included["Segment_New"].isin(["Large Cap","Mid Cap","Small Cap"])]
    _acwi_imi_dl  = df_included[df_included["Segment_New"].isin(["Large Cap","Mid Cap","Small Cap"])]
    _europe_dl    = df_included[
        (df_included["Classification"]=="DM") &
        (df_included["Segment_New"].isin(["Large Cap","Mid Cap"])) &
        (df_included["Mapping Country"].isin(europe_countries))
    ] if europe_countries else pd.DataFrame()
    _params_dl    = pd.DataFrame([{"Parameter":k,"Wert":v} for k,v in params_dict.items()])

    _sheets = {
        "Universe":           _universe_dl,
        "World Index (DM)":   _prep(_world_dm_dl),
        "EM Index":           _prep(_world_em_dl),
        "ACWI Index":         _prep(_acwi_dl),
        "World IMI":          _prep(_world_imi_dl),
        "ACWI IMI":           _prep(_acwi_imi_dl),
    }
    if europe_countries and len(_europe_dl) > 0:
        _sheets["Europe Index"] = _prep(_europe_dl)
    _sheets["Parameter Settings"] = _params_dl

    st.download_button(
        f"⬇️ Download {tab_name} als Excel",
        data=to_excel_multi(_sheets),
        file_name=f"NaroIX_{tab_name.replace(' ','_')}_{_snapshot_label.replace('.','')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ─── Load Historical Reference Data (Classification, Selection Dates, China IF) ──
# Wird hier schon geladen, damit die Sidebar historische Defaults (z.B. China IF) anzeigen kann.
hc_df, selection_dates, china_if_map = load_historical_data()

if not selection_dates:
    st.error("❌ Historical_Classification.xlsx / Selection_Dates.xlsx / China_Inclusion_Factor.xlsx konnten nicht geladen werden. Bitte im Repo-Root ablegen.")
    st.stop()

# Ineligible List (optional — fehlt das File, wird der Filter automatisch deaktiviert)
ineligible_df = load_ineligible_list()

# FOL Matrix (PFLICHT — ohne YAML läuft der Index-Aufbau nicht)
fol_matrix, fol_version, _fol_debug = load_fol_matrix()
if not fol_matrix:
    st.error("❌ FOL Matrix konnte nicht geladen werden. Die Datei 'Historical FOL Register/NaroIX_FOL_Master_Aggregated.yaml' ist für den Index-Aufbau zwingend erforderlich.")
    with st.expander("🔍 Debug: welche Pfade wurden versucht?", expanded=True):
        st.code(
            f"CWD: {_fol_debug.get('cwd')}\n"
            f"Script-Dir: {_fol_debug.get('script_dir')}\n\n"
            f"Getestete Pfade:\n" +
            "\n".join(f"  - {p}" for p in _fol_debug.get('tried_paths', [])),
            language="text"
        )
    st.stop()
fol_sector_fb = build_sector_fallback_table(fol_matrix)


with st.sidebar:
    st.markdown("### 📁 Datenquelle")

    data_mode = st.radio(
        "Input-Modus:",
        ["Single Snapshot", "Master File (Multi-Period)"],
        index=0,
        key="data_mode",
        horizontal=False,
        help="Single Snapshot: Ein FactSet-Export pro Selection Date (bisheriger Modus).\n\n"
             "Master File: Ein File mit allen Perioden; dynamische Spalten haben YYYY-MM-DD-Suffix "
             "(z.B. 'Total MCap 2024-02-21'). Aktiviert Buffer-Rule-Verarbeitung über mehrere Perioden."
    )

    from datetime import date as _date

    # Für Master-Modus brauchen wir die ISO-Strings der Selection Dates zur Validierung
    _selection_dates_iso_set = {d.strftime("%Y-%m-%d") for d in selection_dates}

    master_data = None  # wird im Master-Modus befüllt
    uploaded = None

    if data_mode == "Single Snapshot":
        uploaded = st.file_uploader("FactSet Export (.xlsx)", type=["xlsx","xls"],
                                     key="uploaded_single")
        snapshot_date = st.date_input(
            "Snapshot Datum",
            value=_date.today(),  # dynamischer Default — picks the most recent selection date
            format="DD.MM.YYYY",
            key="snapshot_date",
            help="Datum des FactSet Exports — wird für Labels, Info-Boxen und Excel-Dateinamen verwendet."
        )
    else:
        # Master-File-Modus
        uploaded_master = st.file_uploader("Master File (.xlsx)", type=["xlsx","xls"],
                                            key="uploaded_master",
                                            help="Master-File mit allen Perioden. Spalten-Format: 'Feldname YYYY-MM-DD'.")
        if uploaded_master is not None:
            master_data = load_master_excel(uploaded_master, _selection_dates_iso_set)
            if master_data.get("error"):
                st.error(f"❌ {master_data['error']}")
                st.stop()

            # Warnings anzeigen
            for w in master_data.get("warnings", []):
                st.warning(f"⚠️ {w}")

            _detected = master_data["detected_dates"]
            st.success(f"✅ Master-File geladen: **{len(_detected)}** Selection Dates erkannt "
                       f"({_detected[0]} bis {_detected[-1]})")

            with st.expander("🔍 Details", expanded=False):
                st.write(f"**Detected Selection Dates ({len(_detected)}):**")
                st.code("\n".join(_detected), language="text")
                _extra = master_data.get("extra_static_cols", [])
                if _extra:
                    st.write(f"**Zusätzliche statische Spalten ({len(_extra)}):**")
                    st.code(", ".join(_extra), language="text")

            # Snapshot Date = default letztes Date aus dem Master
            _default_iso = _detected[-1]
            _default_date = _date.fromisoformat(_default_iso)
            snapshot_date = st.date_input(
                "Aktive Period (für Tab-Anzeige)",
                value=_default_date,
                format="DD.MM.YYYY",
                key="snapshot_date_master",
                help="Welches Selection Date aus dem Master-File soll in Tab 1/2/3 angezeigt werden? "
                     "(Multi-Period-Backtest-Lauf kommt in Phase 2c.)"
            )
        else:
            st.info("⬆️ Bitte Master-File hochladen.")
            st.stop()

    _snapshot_label = snapshot_date.strftime("%d.%m.%Y")

    # Aktives Selection Date ermitteln (letztes Selection Date ≤ snapshot_date)
    _active_selection_date = get_selection_date_for_snapshot(snapshot_date, selection_dates)
    if _active_selection_date is None:
        st.error(f"❌ Snapshot Datum liegt vor dem ersten Selection Date ({selection_dates[0]}).")
        st.stop()

    # Historischer China IF zu diesem Selection Date
    _china_if_historical = float(china_if_map.get(_active_selection_date, 0.20))

    st.caption(f"📅 Aktives Selection Date: **{_active_selection_date.strftime('%d.%m.%Y')}**  \n🇨🇳 Historischer China IF: **{_china_if_historical*100:.1f}%**")

    st.markdown("---")
    st.markdown("### 🌍 Universe & Exclusions")
    thailand_sec_type = st.radio(
        "Thailand Modus:",
        ["SHARE → NVDR", "SHARE only", "NVDR only"],
        index=0,
        key="thailand_sec_type",
        help="SHARE → NVDR: Qualifikation (FF MCap/FF%/EUMSS) auf SHARE, Liquiditätscheck + Index auf NVDR (empfohlen).\nSHARE only: Nur Primary SHAREs, kein NVDR-Switch.\nNVDR only: NVDRs als Secondary (nur wenn FF MCap im NVDR vorhanden)."
    )

    _cpa, _cpb = st.columns([3,4])
    with _cpa: use_max_price = st.checkbox("Max Price ≤", value=True, key="use_max_price")
    with _cpb: _max_price_raw = st.text_input("Max Price", value="20000", key="max_price_input",
        label_visibility="collapsed", disabled=not use_max_price)
    try:    max_closing_price = float(_max_price_raw.replace(",","")) if use_max_price else None
    except (ValueError, TypeError): max_closing_price = 20000.0

    with st.expander("Exclusions", expanded=False):
        exclude_hk_cny         = st.checkbox("HK (CNY)", value=True, key="excl_hk")
        exclude_country_risk_na = st.checkbox("Country of Risk = @NA", value=True, key="excl_cor")
        exclude_naics_funds     = st.checkbox("NAICS Investment Funds", value=True, key="excl_naics")
        exclude_euro_mtf        = st.checkbox("Exchange Euro MTF / @NA", value=True, key="excl_euro")
        exclude_etf_sicav       = st.checkbox("Name: ETF / SICAV / %", value=True, key="excl_etf")
        exclude_delisted        = st.checkbox("Listing Status = inaktiv (1)", value=True, key="excl_delisted",
            help="Deaktivieren für historische Snapshots — delisted Stocks waren zum Snapshot-Datum ggf. noch aktiv handelbar.")

    _ie_default = not ineligible_df.empty
    apply_ineligible = st.checkbox(
        "Ineligible-Filter anwenden",
        value=_ie_default,
        key="apply_ineligible",
        disabled=ineligible_df.empty,
        help=f"Wendet In-Eligible.xlsx zum Selection Date an — Stocks mit passender ISIN werden am Ende der Pipeline entfernt, Gewichte werden proportional umverteilt.\n\n{'Liste enthält '+str(len(ineligible_df))+' Regeln.' if not ineligible_df.empty else 'Kein In-Eligible.xlsx im Repo gefunden — Filter inaktiv.'}"
    )

    st.markdown("---")
    st.markdown("### 📊 Size Segmentation")
    _la, _lb = st.columns([3,4])
    with _la: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>Large Cap (%)</div>", unsafe_allow_html=True)
    with _lb: _large_raw = st.text_input("Large", value="70", key="large_thr_input", label_visibility="collapsed")
    _ma, _mb = st.columns([3,4])
    with _ma: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>Mid Cap (%)</div>", unsafe_allow_html=True)
    with _mb: _mid_raw = st.text_input("Mid", value="85", key="mid_thr_input", label_visibility="collapsed")
    _sa, _sb = st.columns([3,4])
    with _sa: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>Small Cap (%)</div>", unsafe_allow_html=True)
    with _sb: _small_raw = st.text_input("Small", value="99", key="small_thr_input", label_visibility="collapsed")
    _ffa, _ffb = st.columns([3,4])
    with _ffa: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>Min FF% (%)</div>", unsafe_allow_html=True)
    with _ffb: _ff_raw = st.text_input("Min FF", value="10", key="min_ff_input", label_visibility="collapsed")
    _eua, _eub = st.columns([3,4])
    with _eua: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>EUMSS FF Ratio (%)</div>", unsafe_allow_html=True)
    with _eub: _eumss_ff_raw = st.text_input("EUMSS FF Ratio", value="50", key="eumss_ff_ratio", label_visibility="collapsed")

    try:    large_thr  = int(_large_raw)
    except (ValueError, TypeError): large_thr  = 70
    try:    mid_thr    = int(_mid_raw)
    except (ValueError, TypeError): mid_thr    = 85
    try:    small_thr  = int(_small_raw)
    except (ValueError, TypeError): small_thr  = 99
    try:    min_ff_pct = float(_ff_raw) / 100
    except (ValueError, TypeError): min_ff_pct = 0.15
    try:    new_eumss_ff_ratio = float(_eumss_ff_raw) / 100
    except (ValueError, TypeError): new_eumss_ff_ratio = 0.50

    st.markdown("---")
    st.markdown("### 💧 Liquidität")
    st.caption("Entry-Schwellen | Rolle (Pre-/Post-Filter bzw. Mitgliedschafts-Gate) je nach Tab & Coverage-Reihenfolge-Toggle unten")
    _adtv_a, _adtv_b = st.columns([3,4])
    with _adtv_a: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>DM ADTV (USD)</div>", unsafe_allow_html=True)
    with _adtv_b: _adtv_dm_raw = st.text_input("DM ADTV", value="1000000", key="adtv_dm_new", label_visibility="collapsed")
    _adtv_c, _adtv_d = st.columns([3,4])
    with _adtv_c: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>EM ADTV (USD)</div>", unsafe_allow_html=True)
    with _adtv_d: _adtv_em_raw = st.text_input("EM ADTV", value="1000000", key="adtv_em_new", label_visibility="collapsed")
    _atvr_a, _atvr_b = st.columns([3,4])
    with _atvr_a: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>DM ATVR Min. (%)</div>", unsafe_allow_html=True)
    with _atvr_b: _atvr_dm_raw = st.text_input("DM ATVR", value="0", key="atvr_dm_new", label_visibility="collapsed")
    _atvr_c, _atvr_d = st.columns([3,4])
    with _atvr_c: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>EM ATVR Min. (%)</div>", unsafe_allow_html=True)
    with _atvr_d: _atvr_em_raw = st.text_input("EM ATVR", value="0", key="atvr_em_new", label_visibility="collapsed")

    try:    new_adtv_dm = float(_adtv_dm_raw.replace(",",""))
    except (ValueError, TypeError): new_adtv_dm = 1_000_000.0
    try:    new_adtv_em = float(_adtv_em_raw.replace(",",""))
    except (ValueError, TypeError): new_adtv_em = 1_000_000.0
    try:    new_atvr_dm = float(_atvr_dm_raw) / 100
    except (ValueError, TypeError): new_atvr_dm = 0.0
    try:    new_atvr_em = float(_atvr_em_raw) / 100
    except (ValueError, TypeError): new_atvr_em = 0.0

    st.caption("ATVR Nenner")
    atvr_denominator = st.radio(
        "ATVR Basis:",
        ["Free Float MCap", "Total MCap"],
        index=0,
        horizontal=True,
        key="atvr_denominator",
        help="Free Float MCap: MSCI-konform, höhere ATVR-Werte bei niedrigem FF.\nTotal MCap: konservativer, verhindert fälschliche Einstufung von Low-Float Stocks als liquide."
    )
    atvr_mcap_col = "Free Float MCap Y2025" if atvr_denominator == "Free Float MCap" else "Total MCap Y2025"

    st.caption("Coverage-Reihenfolge")
    label_before_liquidity = st.toggle(
        "Labeling vor Liquidität (Markt-Coverage)",
        value=False,
        key="label_before_liquidity",
        help="Aus (Default): Liquidität zuerst, Coverage auf dem liquiden Pool (bisheriges Verhalten).\n"
             "An: Large/Mid/Small-Labeling auf dem vollen post-EUMSS-Pool VOR der Liquidität — "
             "der Markt definiert die Größengrenzen, Liquidität wirkt nur noch als Mitgliedschafts-Gate. "
             "EUMSS-Floor und alle anderen Parameter (inkl. ATVR) bleiben aus der Sidebar unverändert."
    )

    st.markdown("---")
    st.markdown("### ⚖️ Inclusion Factors")

    # China IF: Auto (aus Historie) vs Manuell
    china_if_mode = st.radio(
        "China A-Shares IF:",
        ["Auto (historisch)", "Manuell"],
        index=0,
        horizontal=True,
        key="china_if_mode",
        help=f"Auto: übernimmt den historischen IF zum Selection Date ({_china_if_historical*100:.1f}% zum {_active_selection_date.strftime('%d.%m.%Y')}).\nManuell: eigener Wert für What-if Szenarien."
    )
    if china_if_mode == "Auto (historisch)":
        china_inclusion_factor = _china_if_historical
        use_china_factor = _china_if_historical > 0
        st.caption(f"→ aktiv: **{_china_if_historical*100:.1f}%**")
    else:
        _cna, _cnb = st.columns([4,2])
        with _cna: use_china_factor = st.checkbox("China A-Shares aktiv", value=True, key="use_china_factor")
        with _cnb: _china_raw = st.text_input("China", value=f"{_china_if_historical*100:.1f}", key="china_factor_input", label_visibility="collapsed", disabled=not use_china_factor)
        try:    china_inclusion_factor = float(_china_raw) / 100 if use_china_factor else 1.0
        except (ValueError, TypeError): china_inclusion_factor = _china_if_historical

    # FOL Matrix — YAML ist bereits beim Laden validiert
    _fol_iso_list = ", ".join(sorted(FOL_COUNTRY_CODE_MAP.values()))
    apply_fol = st.checkbox(
        "FOL Matrix anwenden",
        value=True,
        key="apply_fol",
        help=f"Wendet Foreign Ownership Limits aus 'Historical FOL Register/NaroIX_FOL_Master_Aggregated.yaml' an.\n\n"
             f"FIF-Formel: IF = min(1, FOL / Free Float %)\n"
             f"Fallback: Industry → Sector (strengster) → Country Default → 1.0\n\n"
             f"Betroffene Länder: {_fol_iso_list}\n"
             f"Thailand: FOL greift nur bei 'SHARE only', NVDR-Modi umgehen FOL.\n\n"
             f"YAML Version: {fol_version}"
    )
    if apply_fol:
        st.caption(f"→ aktiv: YAML {fol_version} | Snapshot-Jahr: **{_active_selection_date.year}**")
    else:
        st.caption("→ FOL Matrix deaktiviert: alle Nicht-China-Stocks bekommen IF=1.0 (nur für What-if)")

    st.markdown("**IF Anwendungsmodus**")
    if_selection_mode = st.radio(
        "IF greift bei:",
        ["Selektion", "Gewichtung"],
        index=0,
        horizontal=True,
        key="if_selection_mode",
        help="Selektion (MSCI-konform): Adj_FF_MCap bestimmt Segment-Zuteilung (Large/Mid/Small) und Coverage.\nGewichtung (nur für What-if): FF MCap bestimmt Selektion, IF wird nur für finale Indexgewichte angewendet. Nicht MSCI-konform."
    )
    if if_selection_mode == "Gewichtung":
        st.caption("⚠️ Research-Modus — nicht MSCI-konform")
    if_sort_col = "Adj_FF_MCap" if if_selection_mode == "Selektion" else "Free Float MCap Y2025"
    # Sort always on Total MCap (MSCI-konform), cumulative on if_sort_col
    if_cum_col = if_sort_col  # cumulative basis (Adj_FF_MCap or FF MCap)
    if_sort_col_size = "Total MCap Y2025"  # sort always on Total MCap

    st.markdown("---")
    st.markdown("### 🛡️ Buffer Rules")

    # Wenn sich der Modus seit letztem Run geändert hat, muss der Default neu greifen.
    # Streamlit ignoriert sonst den value=... Parameter zugunsten des gecachten Session-State.
    _buffer_default = (data_mode == "Master File (Multi-Period)")
    if st.session_state.get("_last_data_mode") != data_mode:
        st.session_state["apply_buffer"] = _buffer_default
        st.session_state["apply_size_buffer"] = _buffer_default
        st.session_state["_last_data_mode"] = data_mode

    apply_buffer = st.checkbox(
        "Buffer Rules aktivieren",
        value=True,
        key="apply_buffer",
        help="Bestehende Konstituenten (Incumbents) werden mit weicheren Maintenance-Schwellen geprüft.\n\n"
             "Neue Kandidaten müssen die strengeren Entry-Schwellen (oben konfiguriert) erfüllen.\n\n"
             "Im Single-Snapshot-Modus gibt es keine Incumbents — Buffer greift erst wenn man eine "
             "Incumbents-Liste bereitstellt. Im Master-Modus (Phase 2c) greift Buffer automatisch "
             "ab Period 2."
    )

    if apply_buffer:
        st.caption("Entry-Schwellen = oben konfigurierte Werte | Maintenance-Schwellen = weicher (unten)")

        # Min FF% Maintenance
        _bfa, _bfb = st.columns([3,4])
        with _bfa: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>Min FF% Maint. (%)</div>", unsafe_allow_html=True)
        with _bfb: _bf_ff_raw = st.text_input("Min FF Maint.", value="7.5", key="buffer_min_ff", label_visibility="collapsed")

        # Coverage Maintenance
        _bca, _bcb = st.columns([3,4])
        with _bca: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>Coverage Maint. (%)</div>", unsafe_allow_html=True)
        with _bcb: _bf_cov_raw = st.text_input("Coverage Maint.", value="90", key="buffer_coverage", label_visibility="collapsed")

        # ADTV Maintenance DM
        _bda, _bdb = st.columns([3,4])
        with _bda: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>ADTV DM Maint.</div>", unsafe_allow_html=True)
        with _bdb: _bf_adtv_dm_raw = st.text_input("ADTV DM Maint.", value="750000", key="buffer_adtv_dm", label_visibility="collapsed")

        # ADTV Maintenance EM
        _bea, _beb = st.columns([3,4])
        with _bea: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>ADTV EM Maint.</div>", unsafe_allow_html=True)
        with _beb: _bf_adtv_em_raw = st.text_input("ADTV EM Maint.", value="750000", key="buffer_adtv_em", label_visibility="collapsed")

        # ATVR Maintenance DM / EM — Default 0 (identisch mit Entry; bei 0 ist ATVR-Filter deaktiviert)
        _bta, _btb = st.columns([3,4])
        with _bta: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>ATVR DM Maint. (%)</div>", unsafe_allow_html=True)
        with _btb: _bf_atvr_dm_raw = st.text_input("ATVR DM Maint.", value="0", key="buffer_atvr_dm", label_visibility="collapsed")

        _bua, _bub = st.columns([3,4])
        with _bua: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>ATVR EM Maint. (%)</div>", unsafe_allow_html=True)
        with _bub: _bf_atvr_em_raw = st.text_input("ATVR EM Maint.", value="0", key="buffer_atvr_em", label_visibility="collapsed")

        # Parse
        try:    buffer_min_ff = float(_bf_ff_raw) / 100
        except (ValueError, TypeError): buffer_min_ff = 0.075
        try:    buffer_coverage = int(_bf_cov_raw)
        except (ValueError, TypeError): buffer_coverage = 90
        try:    buffer_adtv_dm = float(_bf_adtv_dm_raw)
        except (ValueError, TypeError): buffer_adtv_dm = 750_000
        try:    buffer_adtv_em = float(_bf_adtv_em_raw)
        except (ValueError, TypeError): buffer_adtv_em = 750_000
        try:    buffer_atvr_dm = float(_bf_atvr_dm_raw) / 100
        except (ValueError, TypeError): buffer_atvr_dm = 0.0
        try:    buffer_atvr_em = float(_bf_atvr_em_raw) / 100
        except (ValueError, TypeError): buffer_atvr_em = 0.0
    else:
        # Buffer inaktiv → Maintenance = Entry (keine Unterscheidung)
        buffer_min_ff = min_ff_pct
        buffer_coverage = 85  # will be overridden by mid_thr later where used
        buffer_adtv_dm = new_adtv_dm
        buffer_adtv_em = new_adtv_em
        buffer_atvr_dm = new_atvr_dm
        buffer_atvr_em = new_atvr_em
        st.caption("→ Buffer inaktiv — alle Stocks durchlaufen Entry-Schwellen.")

    # ── Size Buffer (Segment-Hysterese, nur Multi-Period) ──────────────────────
    st.markdown("---")
    apply_size_buffer = st.checkbox(
        "Size Buffer aktivieren",
        value=True,
        key="apply_size_buffer",
        help="Hysterese an den Segment-Grenzen Large↔Mid (70%) und Mid↔Small (85%): "
             "Bestandstitel wechseln das Size-Segment erst beim Durchschreiten der "
             "Pufferkante, statt bei jeder kleinen Coverage-Schwankung hin- und "
             "herzuspringen. Greift nur im Multi-Period-Lauf (braucht das Segment "
             "der Vorperiode) ab Periode 2. Untergrenze (Small↔Micro) bleibt über EUMSS."
    )
    if apply_size_buffer:
        _sba, _sbb = st.columns([3, 4])
        with _sba:
            st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>Buffer-Breite (pp)</div>", unsafe_allow_html=True)
        with _sbb:
            _sb_pp_raw = st.text_input("Size Buffer pp", value="5", key="size_buffer_pp_raw", label_visibility="collapsed")
        try:    size_buffer_pp = float(_sb_pp_raw)
        except (ValueError, TypeError): size_buffer_pp = 5.0
        st.caption(f"±{size_buffer_pp:g} pp um 70 % und 85 % · Large bleibt bis "
                   f"{70+size_buffer_pp:g} %, Mid zwischen {70-size_buffer_pp:g}–{85+size_buffer_pp:g} %.")
    else:
        size_buffer_pp = 5.0
        st.caption("→ Size Buffer inaktiv — Segmente werden bei jedem Rebalancing neu am Cut-off bestimmt.")

    # Incumbents-Upload (optional, für Single-Snapshot-Modus)
    incumbents_isin_set = set()
    if apply_buffer and data_mode == "Single Snapshot":
        with st.expander("📥 Incumbents-Liste (optional)", expanded=False):
            st.caption("Liste der ISINs die im vorigen Selection Date im Index waren. Wenn leer → alle als Entry-Kandidaten.")
            _incumb_file = st.file_uploader("Incumbents-Liste (.xlsx/.csv mit Spalte 'ISIN')",
                                            type=["xlsx","xls","csv"],
                                            key="incumbents_upload")
            if _incumb_file is not None:
                try:
                    if _incumb_file.name.lower().endswith(".csv"):
                        _incumb_df = pd.read_csv(_incumb_file)
                    else:
                        _incumb_df = pd.read_excel(_incumb_file)
                    if "ISIN" in _incumb_df.columns:
                        incumbents_isin_set = set(
                            _incumb_df["ISIN"].dropna().astype(str).str.strip().str.upper()
                        )
                        st.success(f"✅ {len(incumbents_isin_set)} Incumbent-ISINs geladen")
                    else:
                        st.error("Spalte 'ISIN' fehlt in der Datei")
                except Exception as e:
                    st.error(f"Fehler: {e}")

    st.markdown("---")
    st.markdown("<div style='color:#8892b0;font-size:11px;'>NaroIX Benchmark Series<br/>© 2026 NaroIX</div>", unsafe_allow_html=True)


# ─── Load Data ─────────────────────────────────────────────────────────────────

if data_mode == "Single Snapshot":
    if uploaded:
        df_raw, _year_suffix = load_excel(uploaded)
    else:
        st.info("👆 Bitte eine Excel-Datei hochladen um zu starten.")
        st.stop()
else:
    # Master-File-Modus: baue Snapshot für das aktive Selection Date
    _active_iso = _active_selection_date.strftime("%Y-%m-%d")
    if _active_iso not in master_data["periods"]:
        # Fallback: nimm das nächste verfügbare Date ≤ active
        _avail = [d for d in master_data["detected_dates"] if d <= _active_iso]
        if not _avail:
            st.error(f"❌ Keine Daten im Master-File für Selection Date ≤ {_active_iso} verfügbar.")
            st.stop()
        _active_iso = _avail[-1]
        st.warning(f"⚠️ Für {_active_selection_date.strftime('%d.%m.%Y')} keine Daten im Master-File. "
                   f"Nutze stattdessen **{_active_iso}**.")
    df_raw = build_snapshot_from_master(master_data, _active_iso)
    _year_suffix = "Y2025"  # Master-File normalisiert intern auf Y2025

# Daten-Konsistenz-Check (FactSet-Anomalien) — nicht-blockierend
_anomalies = validate_factset_data(df_raw)
render_validation_warnings(df_raw, _anomalies)

df_raw_original = df_raw.copy()

# Numeric conversion
for _col in ["Total MCap Y2025","Free Float MCap Y2025","Free Float Percent",
             "1M ADTV Y2025","3M ADTV Y2025","6M ADTV Y2025","12M ADTV Y2025","Closing Price"]:
    if _col in df_raw.columns:
        df_raw[_col] = pd.to_numeric(df_raw[_col], errors="coerce").fillna(0)
        df_raw_original[_col] = df_raw[_col]

# Classification-Lookup für aktives Selection Date (hc_df / selection_dates / china_if_map
# wurden bereits vor der Sidebar geladen; _active_selection_date wurde in der Sidebar berechnet)
country_cls = get_classification_dict(hc_df, _active_selection_date)
if not country_cls:
    st.error(f"❌ Keine Klassifikationen für Selection Date {_active_selection_date} gefunden.")
    st.stop()

# Europe Countries = hardcoded (geografisch). DM/EM-Filterung erfolgt dynamisch per Selection Date.
europe_countries = EUROPE_COUNTRIES

# Apply Mapping Country + Classification to BOTH df_raw and df_raw_original
# This must happen before any exclusions or filters so every stock — including
# secondaries that may later be excluded — carries its DM/EM classification.
for _df in [df_raw, df_raw_original]:
    _df["Mapping Country"] = derive_mapping_country(_df)
    _df["Classification"] = _df["Mapping Country"].map(country_cls)

# ── Tab 2 (ACWI) specific: build All universe (legacy) ───────────────────────
# Thailand filter for all-listings universe (Tab 2)
_th_mask = df_raw["Exchange Name"].fillna("").str.upper() == "THAILAND"
if thailand_sec_type == "SHARE only":
    df_raw_all = df_raw[~(_th_mask & (df_raw["Sec Type"].fillna("") == "NVDR"))].copy()
elif thailand_sec_type == "NVDR only":
    df_raw_all = df_raw[~(_th_mask & (df_raw["Sec Type"].fillna("") == "SHARE"))].copy()
else:  # SHARE → NVDR: keep SHAREs for all-listings, NVDRs handled in build_new_universe
    df_raw_all = df_raw[~(_th_mask & (df_raw["Sec Type"].fillna("") == "NVDR"))].copy()

# Exclusions on All universe — zentral via apply_universe_exclusions (gleiche Logik wie Engine).
# excl_delisted=False: df_raw_all ist die 'All-Listings'-Diagnosesicht und behaelt wie bisher
# auch delistete Titel (der echte Universe-Build entfernt sie via excl_delisted).
df_raw_all = apply_universe_exclusions(
    df_raw_all, max_price=max_closing_price, excl_hk_cny=exclude_hk_cny,
    excl_cor_na=exclude_country_risk_na, excl_naics=exclude_naics_funds,
    excl_euro=exclude_euro_mtf, excl_etf=exclude_etf_sicav, excl_delisted=False)
df_raw_all = df_raw_all[df_raw_all["Classification"].notna()].copy()

df_dm_full = df_raw_all[df_raw_all["Classification"] == "DM"].copy()
df_em_full = df_raw_all[df_raw_all["Classification"] == "EM"].copy()

# ─── Universe global vorberechnen ─────────────────────────────────────────────
# _gm_u (das Pipeline-Universe nach Exclusions + FOL) wird vor den Tabs
# einmalig berechnet, damit alle Tabs (insbesondere Helvetica) konsistenten
# Zugriff darauf haben, unabhängig davon welcher Tab zuerst angeklickt wird.
_gm_u_global = build_new_universe(
    df_raw_original, country_cls, thailand_sec_type, max_closing_price,
    exclude_hk_cny, exclude_country_risk_na, exclude_naics_funds, exclude_euro_mtf, exclude_etf_sicav,
    china_inclusion_factor,
    atvr_mcap_col=atvr_mcap_col, excl_delisted=exclude_delisted,
    fol_matrix=fol_matrix, fol_sector_fb=fol_sector_fb, fol_year=_active_selection_date.year,
    fol_enabled=apply_fol,
)


# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='text-align:center;padding:10px 0 5px'>
  <span style='font-size:28px;font-weight:700;color:#A0B4FF;letter-spacing:2px;'>NaroIX</span>
  <span style='font-size:18px;color:#8892b0;'> — Benchmark Series</span>
  <br><span style='font-size:12px;color:#8892b0;'>Snapshot: {_snapshot_label} &nbsp;|&nbsp; Datenjahr: {_year_suffix} &nbsp;|&nbsp; Selection Date: {_active_selection_date.strftime('%d.%m.%Y')} &nbsp;|&nbsp; China IF: {china_inclusion_factor*100:.1f}% &nbsp;|&nbsp; FOL: {'✅ aktiv' if apply_fol and fol_matrix else '❌ inaktiv'}</span>
</div>
""", unsafe_allow_html=True)

# ─── Tabs ───────────────────────────────────────────────────────────────────
tab_overview, tab_gimi, tab_europe, tab_germany, tab_switzerland, tab_helvetica, tab_helvetica_mp, tab_multi = st.tabs([
    "🌍 Universe Overview",
    "⚡ GIMI Method",
    "🇪🇺 Europe Index",
    "🇩🇪 Germany",
    "🇨🇭 Switzerland",
    "🏔️ Helvetica",
    "🏔️ Helvetica MP",
    "🔁 Multi-Period Run",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: Universe Overview
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.markdown("## 🌍 Universe Overview")
    st.caption("Rohdaten nach Exclusions und DM/EM Klassifikation — vor Liquiditäts- und Size-Filtern")

    # Use df_raw_all (All listings, after exclusions + classification)
    _ov_dm = df_dm_full.copy()
    _ov_em = df_em_full.copy()
    _ov_all = pd.concat([_ov_dm, _ov_em], ignore_index=True)

    # Top metrics
    _ov_c1,_ov_c2,_ov_c3,_ov_c4,_ov_c5 = st.columns(5)
    _ov_c1.metric("Total Stocks",  f"{len(_ov_all):,}")
    _ov_c2.metric("DM Stocks",     f"{len(_ov_dm):,}")
    _ov_c3.metric("EM Stocks",     f"{len(_ov_em):,}")
    _ov_c4.metric("DM FF MCap",    format_bn(_ov_dm["Free Float MCap Y2025"].sum()))
    _ov_c5.metric("EM FF MCap",    format_bn(_ov_em["Free Float MCap Y2025"].sum()))

    # Country breakdown
    _ov_col1, _ov_col2 = st.columns(2)
    with _ov_col1:
        _dm_ct_ov = _ov_dm.groupby("Mapping Country").agg(
            Stocks=("Symbol","count"), FF_MCap=("Free Float MCap Y2025","sum"),
            Avg_MCap=("Total MCap Y2025","mean")).reset_index().sort_values("FF_MCap",ascending=False)
        _dm_ct_ov["FF MCap (USD)"] = _dm_ct_ov["FF_MCap"].apply(format_bn)
        _dm_ct_ov["Avg MCap"]      = _dm_ct_ov["Avg_MCap"].apply(format_bn)
        _dm_ct_ov["Share (%)"]     = (_dm_ct_ov["FF_MCap"]/_dm_ct_ov["FF_MCap"].sum()*100).apply(lambda x: f"{x:.2f}%")
        st.markdown(f"**DM Universe — {len(_ov_dm):,} Stocks**")
        st.dataframe(_dm_ct_ov[["Mapping Country","Stocks","FF MCap (USD)","Avg MCap","Share (%)"]].rename(columns={"Mapping Country":"Land"}),
            width='stretch', height=400, hide_index=True)

    with _ov_col2:
        _em_ct_ov = _ov_em.groupby("Mapping Country").agg(
            Stocks=("Symbol","count"), FF_MCap=("Free Float MCap Y2025","sum"),
            Avg_MCap=("Total MCap Y2025","mean")).reset_index().sort_values("FF_MCap",ascending=False)
        _em_ct_ov["FF MCap (USD)"] = _em_ct_ov["FF_MCap"].apply(format_bn)
        _em_ct_ov["Avg MCap"]      = _em_ct_ov["Avg_MCap"].apply(format_bn)
        _em_ct_ov["Share (%)"]     = (_em_ct_ov["FF_MCap"]/_em_ct_ov["FF_MCap"].sum()*100).apply(lambda x: f"{x:.2f}%")
        st.markdown(f"**EM Universe — {len(_ov_em):,} Stocks**")
        st.dataframe(_em_ct_ov[["Mapping Country","Stocks","FF MCap (USD)","Avg MCap","Share (%)"]].rename(columns={"Mapping Country":"Land"}),
            width='stretch', height=400, hide_index=True)

    # Treemap
    st.markdown("---")
    st.markdown("**FF MCap Verteilung nach Land**")
    _ov_tree = _ov_all.groupby(["Classification","Mapping Country"]).agg(
        FF_MCap=("Free Float MCap Y2025","sum")).reset_index()
    _ov_fig = px.treemap(_ov_tree, path=["Classification","Mapping Country"],
        values="FF_MCap", color="Classification",
        color_discrete_map={"DM":"#2979ff","EM":"#ce93d8"}, template="plotly_dark")
    _ov_fig.update_layout(height=500, paper_bgcolor="#0f1117", margin=dict(t=10,b=10,l=10,r=10))
    st.plotly_chart(_ov_fig, width='stretch')

    # ── Exclusion Summary ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Exclusion Summary**")
    st.caption("Sequenziell — jeder Stock wird beim ersten zutreffenden Grund gezählt. Basis: df_raw_original (vor allen Filtern).")

    import re as _re_ov
    _exc_df = df_raw_original.copy()
    for _col in ["Total MCap Y2025","Free Float MCap Y2025","Free Float Percent",
                 "1M ADTV Y2025","3M ADTV Y2025","6M ADTV Y2025","12M ADTV Y2025","Closing Price"]:
        if _col in _exc_df.columns:
            _exc_df[_col] = pd.to_numeric(_exc_df[_col], errors="coerce").fillna(0)

    _total_raw = len(_exc_df)
    _exc_reason = pd.Series([""] * _total_raw, index=_exc_df.index)

    # 1. Thailand Modus
    _th_mask_ov = _exc_df["Exchange Name"].fillna("").str.upper() == "THAILAND"
    if thailand_sec_type == "SHARE only":
        _m = _th_mask_ov & (_exc_df["Sec Type"].fillna("") == "NVDR") & (_exc_reason == "")
        _exc_reason[_m] = "Thailand: NVDR excluded (SHARE only Modus)"
    elif thailand_sec_type == "NVDR only":
        _m = _th_mask_ov & (_exc_df["Sec Type"].fillna("") == "SHARE") & (_exc_reason == "")
        _exc_reason[_m] = "Thailand: SHARE excluded (NVDR only Modus)"
    else:  # SHARE → NVDR
        # SHAREs without a corresponding NVDR are excluded
        _th_nvdr_entities = set(_exc_df[_th_mask_ov & (_exc_df["Sec Type"].fillna("")=="NVDR")]["Entity ID"].dropna().unique())
        _m = (_th_mask_ov & (_exc_df["Sec Type"].fillna("")=="SHARE") &
              (~_exc_df["Entity ID"].isin(_th_nvdr_entities)) & (_exc_reason == ""))
        _exc_reason[_m] = "Thailand: SHARE ohne NVDR (SHARE→NVDR Modus)"
        # NVDRs without a corresponding qualified SHARE are excluded — handled by FF MCap = 0 check below

    # 2. FF MCap = 0 / negativ / fehlend
    _m = (_exc_df["Free Float MCap Y2025"] <= 0) & (_exc_reason == "")
    _exc_reason[_m] = "FF MCap = 0, negativ oder fehlend"

    # 3. Max Closing Price
    if max_closing_price:
        _m = (_exc_df["Closing Price"].fillna(0) >= max_closing_price) & (_exc_reason == "")
        _exc_reason[_m] = f"Closing Price ≥ {max_closing_price:,.0f} USD"

    # 4. HK CNY
    if exclude_hk_cny:
        _m = (_exc_df["Exchange Ticker"].str.contains("HKG", na=False) &
              (_exc_df["Trading Currency"] == "CNY")) & (_exc_reason == "")
        _exc_reason[_m] = "HK CNY (HKG + CNY)"

    # 5. Country of Risk = @NA
    if exclude_country_risk_na:
        _m = (_exc_df["Country of Risk"].fillna("") == "@NA") & (_exc_reason == "")
        _exc_reason[_m] = "Country of Risk = @NA"

    # 6. NAICS Investment Funds
    if exclude_naics_funds:
        _m = (_exc_df["NAICS"].fillna("").str.contains("Open-End Investment Fund", case=False, na=False)) & (_exc_reason == "")
        _exc_reason[_m] = "NAICS: Open-End Investment Fund"

    # 7. Euro MTF / @NA Exchange
    if exclude_euro_mtf:
        _m = (_exc_df["Exchange Name"].fillna("").isin(["Euro MTF", "@NA"])) & (_exc_reason == "")
        _exc_reason[_m] = "Exchange: Euro MTF / @NA"

    # 8. ETF / SICAV / %
    if exclude_etf_sicav:
        _m = (_exc_df["Name"].fillna("").str.contains(_re_ov.compile(r'\bETF\b|\bSICAV\b|%', _re_ov.IGNORECASE))) & (_exc_reason == "")
        _exc_reason[_m] = "Name: ETF / SICAV / %"

    # 9. Listing Status = 1 (Inactive / Delisted)
    if exclude_delisted and "Listing Status" in _exc_df.columns:
        _m = (_exc_df["Listing Status"].fillna("0").astype(str).str.strip() == "1") & (_exc_reason == "")
        _exc_reason[_m] = "Listing Status = 1 (Inactive / Delisted)"

    # 10. Kein Classification-Mapping
    _exc_df["_MappingCountry"] = derive_mapping_country(_exc_df)
    _exc_df["_Classification"] = _exc_df["_MappingCountry"].map(country_cls)
    _m = (_exc_df["_Classification"].isna()) & (_exc_reason == "")
    _exc_reason[_m] = "Kein DM/EM Mapping"

    _exc_df["_Reason"] = _exc_reason

    # Build summary table
    _excl_only = _exc_df[_exc_df["_Reason"] != ""]
    _incl_count = _total_raw - len(_excl_only)
    _exc_summary = _excl_only.groupby("_Reason").size().reset_index(name="# Stocks")
    _exc_summary = _exc_summary.sort_values("# Stocks", ascending=False).rename(columns={"_Reason":"Exclusion Grund"})
    _exc_summary["% Universe"] = (_exc_summary["# Stocks"] / _total_raw * 100).round(2)
    _total_row = pd.DataFrame([{"Exclusion Grund":"── Total Excluded","# Stocks":len(_excl_only),"% Universe":round(len(_excl_only)/_total_raw*100,2)}])
    _incl_row  = pd.DataFrame([{"Exclusion Grund":"✅ Verbleibend (inkl. Universe)","# Stocks":_incl_count,"% Universe":round(_incl_count/_total_raw*100,2)}])
    _exc_summary = pd.concat([_exc_summary, _total_row, _incl_row], ignore_index=True)

    st.dataframe(_exc_summary, width='stretch', hide_index=True)

    # ── Ungemappte Länder ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Länder ohne DM/EM Mapping**")
    st.caption("Stocks die alle Exclusions bestanden haben, aber kein Mapping in Historical_Classification.xlsx erhalten haben.")

    _unmapped = _exc_df[(_exc_df["_Reason"] == "Kein DM/EM Mapping")].copy()
    if len(_unmapped) > 0:
        _unmap_tbl = _unmapped.groupby("_MappingCountry").agg(
            Stocks=("Symbol","count"),
            FF_MCap=("Free Float MCap Y2025","sum"),
            Avg_MCap=("Total MCap Y2025","mean"),
        ).reset_index().sort_values("Stocks", ascending=False)
        _unmap_tbl["FF MCap (USD)"] = _unmap_tbl["FF_MCap"].apply(format_bn)
        _unmap_tbl["Avg MCap (USD)"] = _unmap_tbl["Avg_MCap"].apply(format_bn)
        st.dataframe(
            _unmap_tbl[["_MappingCountry","Stocks","FF MCap (USD)","Avg MCap (USD)"]].rename(
                columns={"_MappingCountry":"Mapping Country"}),
            width='stretch', hide_index=True)
    else:
        st.success("Alle Stocks haben ein DM/EM Mapping erhalten.")

    # ── Ineligible List (Audit-Trail zum aktiven Selection Date) ──────────────
    st.markdown("---")
    st.markdown("**Ineligible List — Ausschlüsse zum Selection Date**")
    st.caption(f"Basis: In-Eligible.xlsx | Selection Date: {_active_selection_date.strftime('%d.%m.%Y')} | Filter: {'aktiv' if apply_ineligible and not ineligible_df.empty else 'inaktiv'}")

    if ineligible_df.empty:
        st.info("ℹ️ Kein In-Eligible.xlsx im Repo gefunden — Filter inaktiv.")
    else:
        _sd_ts = pd.Timestamp(_active_selection_date)
        _active = ineligible_df[(ineligible_df["From"] <= _sd_ts) & (_sd_ts <= ineligible_df["To"])].copy()

        if _active.empty:
            st.success(f"Keine aktiven Ineligible-Regeln zum {_active_selection_date.strftime('%d.%m.%Y')}. Gesamt in Datei: {len(ineligible_df)} Regel(n).")
        else:
            # Show active rules with impact
            _active_display = _active.copy()
            _active_display["From"] = _active_display["From"].dt.strftime("%Y-%m-%d")
            _active_display["To"]   = _active_display["To"].apply(
                lambda x: "(noch aktiv)" if x >= pd.Timestamp("9999-12-31") else x.strftime("%Y-%m-%d"))

            # Match against universe to see which are in-scope
            _blocked_isins = set(_active["ISIN"].tolist())
            if "ISIN" in df_raw_all.columns:
                _in_universe = df_raw_all[df_raw_all["ISIN"].astype(str).str.strip().str.upper().isin(_blocked_isins)].copy()
                _isin_to_ffmcap = _in_universe.groupby(_in_universe["ISIN"].astype(str).str.strip().str.upper())["Free Float MCap Y2025"].sum().to_dict()
                _active_display["FF MCap (im Universe)"] = _active_display["ISIN"].map(_isin_to_ffmcap).fillna(0).apply(lambda x: format_bn(x) if x > 0 else "—")
            else:
                _active_display["FF MCap (im Universe)"] = "—"

            st.caption(f"**{len(_active)} aktive Regel(n)** zum Selection Date (von {len(ineligible_df)} gesamt):")
            st.dataframe(
                _active_display[["ISIN","Company Name","Country Mapping","From","To","Reason","FF MCap (im Universe)"]],
                width='stretch', hide_index=True)

            if not apply_ineligible:
                st.warning("⚠️ Filter ist deaktiviert — diese Stocks werden trotz Treffer im Index aufgenommen.")

    # ── FOL Matrix Coverage (Audit-Trail zum aktiven Snapshot-Jahr) ───────────
    st.markdown("---")
    st.markdown("**FOL Matrix Coverage — IF-Verteilung pro FOL-Land**")
    st.caption(f"Basis: Historical FOL Register/NaroIX_FOL_Master_Aggregated.yaml | Snapshot-Jahr: {_active_selection_date.year} | Matrix: {'aktiv' if apply_fol and fol_matrix else 'inaktiv'}")

    if not fol_matrix:
        st.info("ℹ️ Keine FOL-Matrix gefunden — alle Nicht-China-Stocks bekommen IF=1.0.")
    elif not apply_fol:
        st.warning("⚠️ FOL Matrix ist deaktiviert — Nicht-China-Stocks bekommen IF=1.0 (auch in FOL-Ländern).")
    else:
        # Aus dem Universe (nach Exclusions, vor EUMSS) alle FOL-Land-Stocks einsammeln
        # Wir verwenden df_raw_all (hat schon Classification + Adjusted MCap aus build_new_universe
        # beim GIMI-Durchlauf — aber Tab 1 läuft davor). Stattdessen ein eigener Mini-Resolver-Run
        # auf Universe-Level.
        _fol_year = _active_selection_date.year
        _fol_countries_upper = [c for c in FOL_COUNTRY_CODE_MAP.keys()]
        _fol_mask = df_raw_all["Exchange Country Name"].fillna("").str.upper().isin(_fol_countries_upper)
        _fol_stocks = df_raw_all[_fol_mask].copy()

        if _fol_stocks.empty:
            _fol_iso_msg = "/".join(sorted(FOL_COUNTRY_CODE_MAP.values()))
            st.info(f"Keine Stocks aus FOL-Ländern ({_fol_iso_msg}) im Universe.")
        else:
            # Resolve FOL pro Stock (ohne Thailand-/China-Override — reine YAML-Diagnostik)
            _audit_rows = []
            _thai_caveat = False
            for cc_upper, iso2 in FOL_COUNTRY_CODE_MAP.items():
                _c_stocks = _fol_stocks[_fol_stocks["Exchange Country Name"].fillna("").str.upper() == cc_upper].copy()
                if _c_stocks.empty:
                    continue

                _sources = []
                _ifs = []
                _fols = []
                for _, r in _c_stocks.iterrows():
                    sec = str(r.get("FactSet Econ Sector","") or "")
                    ind = str(r.get("FactSet Industry","") or "")
                    # Free Float Percent ist bereits als Dezimalwert 0.0–1.0 gespeichert (siehe Hinweis bei apply_fol_matrix)
                    ff_ratio = float(r.get("Free Float Percent", 0) or 0)

                    fol_v, src = _resolve_fol_row(cc_upper, sec, ind, _fol_year, fol_matrix, fol_sector_fb)

                    # Thailand override für die Audit-Anzeige
                    if cc_upper == "THAILAND" and thailand_sec_type in ["NVDR only", "SHARE → NVDR"]:
                        _if = 1.0
                        src = f"Thailand {thailand_sec_type} (NVDR)"
                        _thai_caveat = True
                    else:
                        _if = fif_inclusion_factor(fol_v, ff_ratio)
                        if src.startswith("pre_investable"):
                            _if = 0.0

                    _sources.append(src)
                    _ifs.append(_if)
                    _fols.append(fol_v)

                import collections as _coll
                _src_counter = _coll.Counter(_sources)
                _row = {
                    "Land": f"{iso2} ({fol_matrix[_fol_year][iso2]['country_name']})" if _fol_year in fol_matrix and iso2 in fol_matrix[_fol_year] else iso2,
                    "Stocks": len(_c_stocks),
                    "Industry-Match": _src_counter.get("Industry", 0),
                    "Sector-Fallback": _src_counter.get("Sector (strengster)", 0),
                    "Country-Default": _src_counter.get("Country Default", 0),
                    "Other/Override": sum(v for k,v in _src_counter.items() if k not in ["Industry","Sector (strengster)","Country Default"]),
                    "Median FOL": f"{float(np.median(_fols)):.2f}" if _fols else "—",
                    "Min IF": f"{float(np.min(_ifs)):.2f}" if _ifs else "—",
                    "Median IF": f"{float(np.median(_ifs)):.2f}" if _ifs else "—",
                }
                _audit_rows.append(_row)

            if _audit_rows:
                _audit_df = pd.DataFrame(_audit_rows)
                st.dataframe(_audit_df, width='stretch', hide_index=True)

                with st.expander("ℹ️ Spalten-Definitionen", expanded=False):
                    st.markdown("""
**Stocks** — Anzahl aller Aktien aus diesem Land im Universe (vor Segment-Filterung).

**Industry-Match** — Stocks deren `(FactSet Sector, FactSet Industry)`-Paar exakt in der YAML gefunden wurde. Präzisester Lookup.

**Sector-Fallback** — Stocks bei denen die exakte Industry nicht in der YAML steht, aber der Sector existiert. Fällt auf den **strengsten** `fol_automatic`-Wert im Sector zurück (konservativ).

**Country-Default** — Stocks bei denen weder Industry noch Sector gemappt werden konnten. Fällt auf `default_fol` des Landes zurück.

**Other/Override** — Spezialfälle außerhalb der YAML-Lookup-Kette: Thailand im NVDR-Modus (IF=1.0), Saudi pre_investable (IF=0), etc.

**Median FOL** — Median des `fol_automatic`-Werts aus der YAML für dieses Land. Zeigt was die YAML regulatorisch "sagt".

**Min IF** — Kleinster finaler Inclusion Factor nach FIF-Formel `min(1, FOL/FF%)`. Zeigt den stärksten Cap-Fall im Land. IF=1.0 bedeutet dass kein Stock gecappt wurde (FOL bindet nicht).

**Median IF** — Median finaler Inclusion Factor. IF=1.0 bedeutet für die typische Aktie bindet die FOL nicht (Free Float liegt ohnehin unter der FOL-Schwelle).
""")
                    if _thai_caveat:
                        st.info("Hinweis: Thailand-Werte in der Tabelle berücksichtigen den aktuellen Thailand-Modus ('NVDR only' oder 'SHARE → NVDR' → IF=1.0 per Override).")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: GIMI Method
# ══════════════════════════════════════════════════════════════════════════════
with tab_gimi:
    st.markdown("## ⚡ GIMI Method")
    _order_txt = ("EUMSS, Coverage (Markt), Liquidität (Gate)" if label_before_liquidity
                  else "EUMSS, Liquidität, Coverage")
    st.caption(f"Primary + Secondary konsistent durch {_order_txt} | EUMSS-Kalibrierung auf DM Primary-only | Coverage per Land auf Adj_FF_MCap")

    # Selektion über die zentrale Engine (identisch zum Multi-Period-Tab, keine Dublette).
    # GIMI = aktiver Einzel-Snapshot → kein Size Buffer (keine Vorperiode).
    _res = run_selection_pipeline(
        df_raw_original, country_cls, china_inclusion_factor, _active_selection_date.year,
        thailand_sec_type, max_closing_price,
        exclude_hk_cny, exclude_country_risk_na, exclude_naics_funds, exclude_euro_mtf, exclude_etf_sicav,
        large_thr, mid_thr, small_thr, min_ff_pct, new_eumss_ff_ratio,
        new_adtv_dm, new_adtv_em, new_atvr_dm, new_atvr_em,
        fol_matrix, fol_sector_fb, apply_fol,
        if_cum_col, atvr_mcap_col,
        incumbents_isin=incumbents_isin_set, apply_buffer=apply_buffer,
        buffer_min_ff=buffer_min_ff, buffer_coverage=buffer_coverage,
        buffer_adtv_dm=buffer_adtv_dm, buffer_adtv_em=buffer_adtv_em,
        buffer_atvr_dm=buffer_atvr_dm, buffer_atvr_em=buffer_atvr_em,
        apply_size_buffer=False,
        excl_delisted=exclude_delisted,
        ineligible_df=ineligible_df, apply_ineligible=apply_ineligible,
        selection_date=_active_selection_date,
        label_before_liquidity=label_before_liquidity,
        prebuilt_universe=_gm_u_global,  # identische Universe-Params → Rebuild sparen (~1s/Rerun)
    )
    if _res["eumss_full"] > 0 and len(_res["gm_complete"]) > 0:
        _gm_complete   = _res["gm_complete"]
        _gm_index_only = _res["gm_index_only"]
        _gm_u          = _res["gm_universe"]
        _gm_eumss      = _res["gm_eumss"]
        _gm_liq        = _res["gm_liq"]
        _gm_std        = _res["gm_std"]
        _gm_final      = _res["gm_final"]
        _gm_eumss_full = _res["eumss_full"]
        _gm_eumss_ff   = _res["eumss_ff"]
        _gm_ie_removed = _res["gm_ie_removed"]
        _buffer_breakdown = _res["buffer_breakdown"]
        if _res.get("eumss_calib_fallback"):
            st.warning("⚠️ EUMSS-Kalibrierung: keine DM-Primary-Listings gefunden — "
                       "Fallback auf alle DM-Listings (prüfe die 'Listing'-Spalte im Master-File).")
        _gm_all = df_raw_all[df_raw_all["Classification"].notna()]
        if apply_ineligible and not ineligible_df.empty:
            _, _, _gm_ie_active_rules = apply_ineligible_filter(_gm_complete, ineligible_df, _active_selection_date)
        else:
            _gm_ie_active_rules = ineligible_df.iloc[0:0].copy() if not ineligible_df.empty else pd.DataFrame()

        # Large/Mid Sub-Splits aus Schritt 4 — kein eigener Pipeline-Schritt, nur Aufschlüsselung
        _gm_large = _gm_std[_gm_std["Segment_New"]=="Large Cap"] if "Segment_New" in _gm_std.columns else _gm_std.iloc[0:0]
        _gm_mid   = _gm_std[_gm_std["Segment_New"]=="Mid Cap"]   if "Segment_New" in _gm_std.columns else _gm_std.iloc[0:0]

        _gm_diag = [
            {"Schritt":"0 — Raw (Primary + Secondary, klassifiziert)","DM":(_gm_all["Classification"]=="DM").sum(),"EM":(_gm_all["Classification"]=="EM").sum(),"Total":len(_gm_all),"Δ":"—"},
            {"Schritt":"1 — Universe (nach Exclusions + FOL)","DM":(_gm_u["Classification"]=="DM").sum(),"EM":(_gm_u["Classification"]=="EM").sum(),"Total":len(_gm_u),"Δ":f"-{len(_gm_all)-len(_gm_u):,}"},
            {"Schritt":f"2 — EUMSS Filter ({_gm_eumss_full/1e6:.0f}M)","DM":(_gm_eumss["Classification"]=="DM").sum(),"EM":(_gm_eumss["Classification"]=="EM").sum(),"Total":len(_gm_eumss),"Δ":f"-{len(_gm_u)-len(_gm_eumss):,}"},
            {"Schritt":"3 — Liquiditätsfilter" + (" (Mitgliedschafts-Gate)" if label_before_liquidity else ""),"DM":(_gm_liq["Classification"]=="DM").sum(),"EM":(_gm_liq["Classification"]=="EM").sum(),"Total":len(_gm_liq),"Δ":f"-{len(_gm_eumss)-len(_gm_liq):,}"},
            {"Schritt":f"4 — {mid_thr}% Coverage → Standard Index" + (" (Markt-Coverage auf vollem Pool vor Liquidität)" if label_before_liquidity else "") + (f" (+ Buffer {buffer_coverage}% für Incumbents)" if apply_buffer and len(incumbents_isin_set)>0 else ""),"DM":(_gm_std["Classification"]=="DM").sum(),"EM":(_gm_std["Classification"]=="EM").sum(),"Total":len(_gm_std),"Δ":f"-{len(_gm_liq)-len(_gm_std):,}"},
            {"Schritt":f"    ├─ Large Cap (_c_before < {large_thr}%)","DM":(_gm_large["Classification"]=="DM").sum() if len(_gm_large)>0 else 0,"EM":(_gm_large["Classification"]=="EM").sum() if len(_gm_large)>0 else 0,"Total":len(_gm_large),"Δ":"—"},
            {"Schritt":f"    └─ Mid Cap   (_c_before ≥ {large_thr}%)","DM":(_gm_mid["Classification"]=="DM").sum() if len(_gm_mid)>0 else 0,"EM":(_gm_mid["Classification"]=="EM").sum() if len(_gm_mid)>0 else 0,"Total":len(_gm_mid),"Δ":"—"},
            {"Schritt":f"5 — Ineligible-Filter ({'aktiv' if apply_ineligible and not ineligible_df.empty else 'inaktiv'})","DM":(_gm_complete["Classification"]=="DM").sum(),"EM":(_gm_complete["Classification"]=="EM").sum(),"Total":len(_gm_complete),"Δ":f"-{len(_gm_ie_removed):,}" if len(_gm_ie_removed)>0 else "—"},
        ]
        _gm_diag_caption = f"EUMSS_FULL: {format_bn(_gm_eumss_full)} | EUMSS_FF: {format_bn(_gm_eumss_ff)} | FF Ratio: {new_eumss_ff_ratio*100:.0f}% | Min FF%: {min_ff_pct*100:.0f}% | IF: {if_selection_mode} | FOL Matrix: {'✅ ' + str(fol_version) if apply_fol and fol_matrix else '❌ inaktiv'}"
        _gm_eumss_extra = f"EUMSS_FULL: {format_bn(_gm_eumss_full)} | EUMSS_FF: {format_bn(_gm_eumss_ff)} | FF Ratio: {new_eumss_ff_ratio*100:.0f}%"

        _gm_params = {"Methodik":"GIMI Method","Listing":"Primary + Secondary (konsistent durch Pipeline)",
            "Filter":"Pre (nach EUMSS)","EUMSS Kalibrierung (%)":f"{small_thr}%",
            "EUMSS_FULL (USD)":format_bn(_gm_eumss_full),"EUMSS FF Ratio (%)":f"{new_eumss_ff_ratio*100:.0f}%",
            "EUMSS_FF (USD)":format_bn(_gm_eumss_ff),"Min FF%":f"{min_ff_pct*100:.0f}%",
            "Coverage (%)":f"{mid_thr}%","Large Cap (%)":large_thr,
            "DM ADTV (USD)":f"{new_adtv_dm:,.0f}","EM ADTV (USD)":f"{new_adtv_em:,.0f}",
            "DM ATVR (%)":f"{new_atvr_dm*100:.0f}%","EM ATVR (%)":f"{new_atvr_em*100:.0f}%",
            "Max Price (USD)":f"{max_closing_price:,.0f}" if max_closing_price else "—",
            "China IF (Stock Connect)": f"{china_inclusion_factor*100:.1f}%",
            "FOL Matrix":"aktiv" if apply_fol and fol_matrix else "inaktiv",
            "FOL YAML Version": str(fol_version) if fol_version else "—",
            "FOL Snapshot-Jahr": _active_selection_date.year if apply_fol and fol_matrix else "—",
            "Ineligible-Filter":"aktiv" if apply_ineligible and not ineligible_df.empty else "inaktiv",
            "Ineligible — Regeln aktiv": len(_gm_ie_active_rules) if apply_ineligible and not ineligible_df.empty else 0,
            "Ineligible — Stocks entfernt": len(_gm_ie_removed)}

        # Full universe for download: _gm_u with segment labels + re-added secondaries
        _gm_seg_map = dict(zip(_gm_complete["Symbol"], _gm_complete["Segment_New"]))
        _gm_u_full = _gm_u.copy()
        _gm_u_full["Segment_New"] = _gm_u_full["Symbol"].map(_gm_seg_map).fillna("Excluded")

        # Add re-added secondaries (they are in _gm_final but not in _gm_u)
        _gm_secondaries = _gm_final[
            (_gm_final["Listing"].fillna("") == "Secondary") &
            (~_gm_final["Symbol"].isin(set(_gm_u_full["Symbol"])))
        ].copy()
        if len(_gm_secondaries) > 0:
            _gm_u_full = pd.concat([_gm_u_full, _gm_secondaries], ignore_index=True)

        render_new_tab("GIMI Method", _gm_complete, large_thr, mid_thr,
            china_inclusion_factor,
            _gm_params, diag_rows=_gm_diag,
            diag_caption=_gm_diag_caption,
            adtv_dm=new_adtv_dm, adtv_em=new_adtv_em, atvr_dm=new_atvr_dm, atvr_em=new_atvr_em,
            small_pct=small_thr, min_ff=min_ff_pct, if_mode=if_selection_mode,
            df_universe=df_raw_all, buffer_breakdown=_buffer_breakdown)
    else:
        st.error("Keine DM Stocks gefunden.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: Europe Index
# ══════════════════════════════════════════════════════════════════════════════
with tab_europe:
    st.markdown("## 🇪🇺 Europe Index")
    st.caption("Basis: GIMI Method — World Index (DM Large+Mid), gefiltert auf europäische Länder (hardcoded EUROPE_COUNTRIES-Liste + dynamische DM-Klassifikation pro Selection Date)")

    if not europe_countries:
        st.warning("⚠️ Keine europäischen Länder gefunden. Bitte prüfe die EUROPE_COUNTRIES-Konstante im Code.")
    else:
        st.markdown(f"""
<div class="info-box">
<b>Eligible European Countries ({len(europe_countries)}):</b><br>
{', '.join(sorted(europe_countries))}
</div>
""", unsafe_allow_html=True)

        # Europe Index = World Index (DM Large+Mid) filtered to European countries
        try:
            _eu_dm = _gm_complete[
                (_gm_complete["Classification"] == "DM") &
                (_gm_complete["Segment_New"].isin(["Large Cap", "Mid Cap"])) &
                (_gm_complete["Mapping Country"].isin(europe_countries))
            ].copy()

            # Renormalize weights
            _eu_tot = _eu_dm["Adj_FF_MCap"].sum()
            _eu_dm["Index_Weight"] = _eu_dm["Adj_FF_MCap"] / _eu_tot * 100 if _eu_tot > 0 else 0

            # Sort descending by weight
            _eu_dm = _eu_dm.sort_values("Index_Weight", ascending=False)

            # ── Metrics ──────────────────────────────────────────────────────
            _eu_large = _eu_dm[_eu_dm["Segment_New"] == "Large Cap"]
            _eu_mid   = _eu_dm[_eu_dm["Segment_New"] == "Mid Cap"]

            _mc1, _mc2, _mc3, _mc4, _mc5 = st.columns(5)
            _mc1.metric("Europe Stocks", f"{len(_eu_dm):,}")
            _mc2.metric("Large Cap", f"{len(_eu_large):,}")
            _mc3.metric("Mid Cap", f"{len(_eu_mid):,}")
            _mc4.metric("Länder", f"{_eu_dm['Mapping Country'].nunique():,}")
            _mc5.metric("Adj. FF MCap", f"${_eu_tot/1e9:.1f}B")

            # ── Country Breakdown ────────────────────────────────────────────
            st.markdown("---")
            _eu_col1, _eu_col2 = st.columns([2, 3])

            with _eu_col1:
                st.markdown("**Länder-Gewichtung**")
                _eu_ctry = _eu_dm.groupby("Mapping Country").agg(
                    Stocks=("Symbol", "count"),
                    Adj_FF_MCap=("Adj_FF_MCap", "sum")
                ).reset_index()
                _eu_ctry["Weight %"] = (_eu_ctry["Adj_FF_MCap"] / _eu_tot * 100).round(2)
                _eu_ctry = _eu_ctry.sort_values("Weight %", ascending=False)
                _eu_ctry["Weight %"] = _eu_ctry["Weight %"].map(lambda x: f"{x:.2f}%")
                _eu_ctry = _eu_ctry.drop(columns=["Adj_FF_MCap"])
                st.dataframe(_eu_ctry, width='stretch', hide_index=True)

            with _eu_col2:
                st.markdown("**Top 20 Stocks**")
                _top20_cols = ["Exchange Ticker", "Name", "Mapping Country", "Segment_New", "Index_Weight"]
                _top20 = _eu_dm[[c for c in _top20_cols if c in _eu_dm.columns]].head(20).copy()
                _top20["Index_Weight"] = _top20["Index_Weight"].map(lambda x: f"{x:.4f}%")
                st.dataframe(_top20, width='stretch', hide_index=True)

            # ── Download ─────────────────────────────────────────────────────
            st.markdown("---")
            # Internal working columns dropped from the export (Index_Weight is
            # recomputed by normalize_index_weight, so it can stay in the slice).
            # IF/FOL bleiben drin (with_fol_breakdown positioniert sie vor Adj_FF_MCap).
            _eu_cols = [c for c in _eu_dm.columns if c not in ["_cum_pct","_c","_cp2","_cp2_before","ADTV_Best"]]
            _eu_dl       = normalize_index_weight(_eu_dm[_eu_cols].copy())
            _eu_large_dl = normalize_index_weight(_eu_dm[_eu_dm["Segment_New"]=="Large Cap"][_eu_cols].copy())
            _eu_mid_dl   = normalize_index_weight(_eu_dm[_eu_dm["Segment_New"]=="Mid Cap"][_eu_cols].copy())

            _eu_params = {
                "Basis": "GIMI Method — World Index (DM Large+Mid)",
                "Snapshot Datum": _snapshot_label,
                "Europe Länder": ", ".join(sorted(europe_countries)),
                "ADTV DM": f"{new_adtv_dm:,.0f}",
                "ADTV EM": "n/a (nur DM)",
                "Min FF%": f"{min_ff_pct*100:.0f}%",
            }

            st.download_button(
                "⬇️ Download Europe Index als Excel",
                data=to_excel_multi({
                    "Europe Index":   _eu_dl,
                    "Europe Large":   _eu_large_dl,
                    "Europe Mid":     _eu_mid_dl,
                    "Parameter Settings": pd.DataFrame([{"Parameter": k, "Wert": v} for k, v in _eu_params.items()]),
                }),
                file_name=f"NaroIX_Europe_Index_{_snapshot_label.replace('.','')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        except NameError:
            st.warning("⚠️ Bitte zuerst Tab '⚡ GIMI Method' aufrufen damit der World Index berechnet wird.")


# ══════════════════════════════════════════════════════════════════════════════
# Helper: Single-Country Tab Renderer (für Germany, Switzerland, etc.)
# ══════════════════════════════════════════════════════════════════════════════
def render_single_country_tab(gm_complete_df, country_iso, country_display, flag_emoji=""):
    """
    Render Country-Tab mit 4 Sub-Sections (Standard, Large, Mid, Small) und
    Filter-Toggle für Mapping/Listing-Logik.

    Default: Mapping Country == X AND Exchange Country Name == X (MSCI-konform)
    """
    st.markdown(f"## {flag_emoji} {country_display}")
    st.caption(f"Country-Index für {country_display}. Filter: Mapping Country + Exchange Country Name (MSCI-konform).")

    # ── Filter-Modus auswählen ─────────────────────────────────────────────
    _filter_mode = st.radio(
        "Filter-Logik",
        options=[
            "Mapping + Listing (Default, MSCI-konform)",
            "Mapping Country only",
            "Exchange Country only",
        ],
        index=0,
        horizontal=True,
        key=f"filter_mode_{country_iso}",
        help=(
            "**Mapping + Listing:** Stocks die zum Land gehören (Country of Incorp/Risk) "
            "UND auch dort gelistet sind. Entspricht MSCI Country Index Logik.\n\n"
            "**Mapping only:** Stocks die zum Land gehören, unabhängig vom Listing-Ort "
            "(inkl. ADRs/Cross-Listings, z.B. BioNTech ADR für Deutschland).\n\n"
            "**Exchange only:** Stocks die im Land gelistet sind, unabhängig von der Mapping-Country-Logik."
        ),
    )

    # ── Filter anwenden ───────────────────────────────────────────────────
    if "Exchange Country Name" not in gm_complete_df.columns:
        st.error(f"❌ Spalte 'Exchange Country Name' fehlt im Pipeline-Output.")
        return

    _has_mapping = gm_complete_df["Mapping Country"] == country_iso
    _has_listing = gm_complete_df["Exchange Country Name"] == country_iso

    if _filter_mode.startswith("Mapping + Listing"):
        _country = gm_complete_df[_has_mapping & _has_listing].copy()
    elif _filter_mode.startswith("Mapping Country only"):
        _country = gm_complete_df[_has_mapping].copy()
    else:  # Exchange Country only
        _country = gm_complete_df[_has_listing].copy()

    if len(_country) == 0:
        st.warning(f"⚠️ Keine Stocks für {country_display} mit dem aktuellen Filter gefunden.")
        return

    # ── Differenz-Anzeige: was sind die Unterschiede zwischen den Modi? ─────
    _set_default  = set(gm_complete_df[_has_mapping & _has_listing]["Symbol"])
    _set_mapping  = set(gm_complete_df[_has_mapping]["Symbol"])
    _set_exchange = set(gm_complete_df[_has_listing]["Symbol"])

    _only_mapping  = _set_mapping  - _set_default   # in Mapping, nicht in Default → keine Listing
    _only_exchange = _set_exchange - _set_default   # in Exchange, nicht in Default → fremdes Mapping
    if len(_only_mapping) > 0 or len(_only_exchange) > 0:
        with st.expander(f"🔍 Filter-Differenzen: {len(_only_mapping)} ADRs/Cross-Listings + {len(_only_exchange)} Foreign-Mapping Stocks", expanded=False):
            if len(_only_mapping) > 0:
                st.markdown(f"**Stocks mit Mapping = {country_iso} aber Listing außerhalb** ({len(_only_mapping)}):")
                _diff1 = gm_complete_df[gm_complete_df["Symbol"].isin(_only_mapping)][
                    [c for c in ["Exchange Ticker","Name","Exchange Country Name","Listing","Sec Type","Segment_New"] if c in gm_complete_df.columns]
                ]
                st.dataframe(_diff1, width='stretch', hide_index=True)
            if len(_only_exchange) > 0:
                st.markdown(f"**Stocks mit Listing in {country_iso} aber Mapping woanders** ({len(_only_exchange)}):")
                _diff2 = gm_complete_df[gm_complete_df["Symbol"].isin(_only_exchange)][
                    [c for c in ["Exchange Ticker","Name","Mapping Country","Listing","Sec Type","Segment_New"] if c in gm_complete_df.columns]
                ]
                st.dataframe(_diff2, width='stretch', hide_index=True)

    # ── Header-Metrics ────────────────────────────────────────────────────
    _large_df = _country[_country["Segment_New"] == "Large Cap"].copy()
    _mid_df   = _country[_country["Segment_New"] == "Mid Cap"].copy()
    _small_df = _country[_country["Segment_New"] == "Small Cap"].copy()
    _std_df   = pd.concat([_large_df, _mid_df], ignore_index=True)  # Large + Mid

    _country_total_adj = _country[_country["Segment_New"].isin(["Large Cap","Mid Cap","Small Cap"])]["Adj_FF_MCap"].sum()

    st.markdown("---")
    _mc1, _mc2, _mc3, _mc4, _mc5 = st.columns(5)
    _mc1.metric(f"{country_display} Total", f"{len(_large_df)+len(_mid_df)+len(_small_df):,}")
    _mc2.metric("Large Cap", f"{len(_large_df):,}")
    _mc3.metric("Mid Cap", f"{len(_mid_df):,}")
    _mc4.metric("Small Cap", f"{len(_small_df):,}")
    _mc5.metric("Adj. FF MCap", f"${_country_total_adj/1e9:.1f}B")

    # ── 4 Sub-Sections: Standard, Large, Mid, Small ───────────────────────
    def _render_section(label, df, total_adj_ref, key_suffix, table_caption=""):
        """Render eine einzelne Section mit Header, Top-Tabelle und Download."""
        st.markdown("---")
        if len(df) == 0:
            st.markdown(f"### {label}")
            st.caption(f"Keine Stocks in dieser Section für {country_display}.")
            return
        # Re-normalize weights within section
        _df = df.copy()
        _sec_total = _df["Adj_FF_MCap"].sum()
        if _sec_total > 0:
            _df["Section_Weight"] = (_df["Adj_FF_MCap"] / _sec_total * 100).round(6)
        else:
            _df["Section_Weight"] = 0.0
        _df = _df.sort_values("Section_Weight", ascending=False)

        st.markdown(f"### {label}")
        if table_caption:
            st.caption(table_caption)
        _sc1, _sc2 = st.columns(2)
        _sc1.metric("Stocks", f"{len(_df):,}")
        _sc2.metric("Section Adj. FF MCap", f"${_sec_total/1e9:.2f}B")

        # Top Table
        _show_n = min(len(_df), 25)
        _top_cols = [c for c in ["Exchange Ticker", "Name", "Mapping Country",
                                  "Listing", "Sec Type", "Segment_New",
                                  "Adj_FF_MCap", "Section_Weight"] if c in _df.columns]
        _top = _df[_top_cols].head(_show_n).copy()
        if "Adj_FF_MCap" in _top.columns:
            _top["Adj_FF_MCap"] = _top["Adj_FF_MCap"].map(lambda x: f"${x/1e9:.2f}B" if x >= 1e9 else f"${x/1e6:.0f}M")
        if "Section_Weight" in _top.columns:
            _top["Section_Weight"] = _top["Section_Weight"].map(lambda x: f"{x:.4f}%")
        st.dataframe(_top, width='stretch', hide_index=True)
        if len(_df) > _show_n:
            st.caption(f"Anzeige: Top {_show_n} von {len(_df)} Stocks. Vollständige Liste im Excel-Download.")

        # Download
        _drop = ["_cum_pct","_c","_cp2","_cp2_before","ADTV_Best","Section_Weight"]  # IF/FOL bleiben für den Export
        _dl_df = _df[[c for c in _df.columns if c not in _drop]].copy()
        _dl_df = normalize_index_weight(_dl_df)
        _params = {
            "Country": country_display,
            "Section": label,
            "Filter-Modus": _filter_mode,
            "Snapshot Datum": _snapshot_label,
            "ADTV DM": f"{new_adtv_dm:,.0f}",
            "Min FF%": f"{min_ff_pct*100:.0f}%",
        }
        st.download_button(
            f"⬇️ Download {country_display} {label} als Excel",
            data=to_excel_multi({
                f"{country_display} {label}": _dl_df,
                "Parameter Settings": pd.DataFrame([{"Parameter": k, "Wert": v} for k, v in _params.items()]),
            }),
            file_name=f"NaroIX_{country_display.replace(' ','_')}_{label.replace(' ','_')}_{_snapshot_label.replace('.','')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_{country_iso}_{key_suffix}",
        )

    _render_section("Standard Index (Large + Mid)", _std_df, _country_total_adj, "std",
                    "Konstituenten des Standard Index für dieses Land (Large + Mid Cap zusammen).")
    _render_section("Large Cap", _large_df, _country_total_adj, "large")
    _render_section("Mid Cap", _mid_df, _country_total_adj, "mid")
    _render_section("Small Cap", _small_df, _country_total_adj, "small",
                    "Small Cap = Stocks die EUMSS und Liquidität bestehen, aber außerhalb des 85% Coverage-Cuts liegen.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: Germany
# ══════════════════════════════════════════════════════════════════════════════
with tab_germany:
    try:
        render_single_country_tab(_gm_complete, "GERMANY", "Germany", "🇩🇪")
    except NameError:
        st.warning("⚠️ Bitte zuerst Tab '⚡ GIMI Method' aufrufen damit die Pipeline berechnet wird.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: Switzerland
# ══════════════════════════════════════════════════════════════════════════════
with tab_switzerland:
    try:
        render_single_country_tab(_gm_complete, "SWITZERLAND", "Switzerland", "🇨🇭")
    except NameError:
        st.warning("⚠️ Bitte zuerst Tab '⚡ GIMI Method' aufrufen damit die Pipeline berechnet wird.")


# ══════════════════════════════════════════════════════════════════════════════
# Helper: Helvetica Pipeline (kundenspezifischer Schweizer Index)
# ══════════════════════════════════════════════════════════════════════════════
def build_helvetica_pipeline(gm_universe, use_buffer=False, adtv_thr=500_000, incumbents_isin=None,
                             prior_segments=None, label_before_liquidity=False):
    """Eigenständige Helvetica-Pipeline aus dem Universe (vor EUMSS).

    Schwellen — Entry (Neukandidaten) vs Maintenance (Bestandstitel/Inkumbenten):
                       Entry        Maintenance
      Min FF %         ≥ 10%        ≥ 7.5%
      Large Cap        _c_before <70%   <75%
      Standard         _c_before <85%   <90%
      Small Cap        _c_before <99%   <99.5%
    ADTV 3M: ein fester Wert ($0.5M / $0.25M via Toggle), kein Buffer.

    Buffer PRO TITEL: Maintenance-Schwellen gelten, wenn der Titel in `incumbents_isin`
    (Vorperioden-Konstituenten, Multi-Period) ist ODER `use_buffer=True` (globaler
    Vergleichsmodus im Single-Snapshot-Tab). Sonst Entry-Schwellen.

    `prior_segments` (Multi-Period): dict {Entity ID -> Segment_New der Vorperiode}. Aktiviert die
    firmen-interne ±5/±0,5-Coverage-Hysterese (Bestands-Firma bleibt in ihrem Segment, solange die
    Coverage im Band liegt) — so sind Helveticas Größenklassen deckungsgleich mit den Swiss-Size-
    Sub-Indizes. Ohne prior_segments: harter Cut.

    Variante B: Primary + Secondary laufen gemeinsam durch (beide bleiben drin, sofern sie
    die Filter individuell bestehen). Returns (helv [L/M/S], helv_full_pool [+Micro], params)."""
    ENTRY = {"min_ff": 0.10,  "large": 70.0, "std": 85.0, "small": 99.0}
    MAINT = {"min_ff": 0.075, "large": 75.0, "std": 90.0, "small": 99.5}
    _inc = set(incumbents_isin or [])

    def _maint(frame):
        _is = _norm_isin(frame["ISIN"]).isin(_inc)
        return (_is | bool(use_buffer)).to_numpy()

    # Step 1: Hard Filter — CH-gelistet, FF MCap > 0
    df = gm_universe[(gm_universe["Exchange Country Name"] == "SWITZERLAND") &
                     (gm_universe["Free Float MCap Y2025"] > 0)].copy()

    # Step 2: Min FF % — per-stock (Bestandstitel: 7.5%, sonst 10%)
    m = _maint(df)
    df = df[df["Free Float Percent"] >= np.where(m, MAINT["min_ff"], ENTRY["min_ff"])].copy()

    # Step 3: Liquidity — ein fester 3M-ADTV-Schwellenwert (kein Buffer).
    # Reihenfolge-Toggle: im Default VOR der Coverage; bei label_before_liquidity erst
    # NACH dem Labeling als Mitgliedschafts-Gate (Coverage läuft dann auf dem vollen
    # CH-Pool — illiquide Titel bestimmen die Größengrenzen mit, fallen aber unten raus).
    if not label_before_liquidity:
        df = df[df["3M ADTV Y2025"] >= adtv_thr].copy()

    # Step 3b: Company-level Dedup VOR dem Coverage-Cut — pro Firma nur die liquideste
    # Linie (höchstes 3M-ADTV). Verhindert Doppelzählung von Mehrfach-Listings (Variante B)
    # in der Coverage-Kumulation: jede Firma zählt genau einmal, mit derselben Linie, die
    # später im Sleeve landet. Für echte Paare (Roche/Swatch/Schindler) = die Primary-Linie;
    # hält aber z.B. Lindt korrekt über LISP, falls die Primary (LISN) preis-gefiltert wurde.
    df = _helv_dedup_most_liquid(df)

    _legacy = {"adtv_thr": adtv_thr, "use_buffer": use_buffer, "n_incumbents": len(_inc),
               "min_ff_pct": (MAINT if use_buffer else ENTRY)["min_ff"],
               "large_cut": (MAINT if use_buffer else ENTRY)["large"],
               "std_cut":   (MAINT if use_buffer else ENTRY)["std"],
               "small_cut": (MAINT if use_buffer else ENTRY)["small"]}
    if len(df) == 0:
        return df, df.copy(), _legacy

    # Step 4: Sort by Total MCap desc (Adj_FF tiebreaker), Straddle-Coverage auf Adj_FF
    df = df.sort_values(["Total MCap Y2025", "Adj_FF_MCap"], ascending=[False, False]).reset_index(drop=True)
    tot = df["Adj_FF_MCap"].sum()
    df["_c_before"] = (df["Adj_FF_MCap"].cumsum().shift(1).fillna(0) / tot * 100) if tot > 0 else 0.0

    # Step 5: Coverage-Cuts → Segment (firmen-intern, da der Cut über Total MCap läuft; Mehrfach-
    # Listings sind durch Step 3b ohnehin schon auf eine Linie reduziert).
    # ±5/±0,5-Maintenance-Hysterese: eine Bestands-Firma (war in der Vorperiode im jeweiligen
    # Segment laut `prior_segments`) bleibt in ihrem Segment, solange ihre Coverage im Band liegt
    # (Large < 75 %, Mid 65–90 %, Small 84,5–99,5 %). Neue Firmen: harter Cut. So sind Helveticas
    # Größenklassen deckungsgleich mit den Swiss-Size-Sub-Indizes (familien-konsistent). Die
    # ausgewählten 30 ändern sich dadurch praktisch nicht (Top-10 ist rang-basiert), nur die
    # Kern/Aufrücker-Labels. `use_buffer` (Single-Snapshot-Vergleich) verschiebt die harten Cuts
    # global; im Multi-Period ist use_buffer=False und die Hysterese übernimmt den Bestandsschutz.
    _cut = MAINT if use_buffer else ENTRY
    cb = df["_c_before"].to_numpy()
    _hard = np.where(cb < _cut["large"], "Large Cap",
              np.where(cb < _cut["std"], "Mid Cap",
                np.where(cb < _cut["small"], "Small Cap", "Micro Cap")))
    if prior_segments:
        _L, _M, _S = ENTRY["large"], ENTRY["std"], ENTRY["small"]  # 70 / 85 / 99
        _ent = df["Entity ID"].fillna("").astype(str).str.strip().to_numpy()
        _seg = []
        for _i in range(len(df)):
            _p = prior_segments.get(_ent[_i]); _c = cb[_i]; _s = _hard[_i]
            if   _p == "Large Cap" and _c < _L + 5.0:               _s = "Large Cap"
            elif _p == "Mid Cap"   and (_L - 5.0) <= _c < _M + 5.0: _s = "Mid Cap"
            elif _p == "Small Cap" and (_M - 0.5) <= _c < _S + 0.5: _s = "Small Cap"
            _seg.append(_s)
        df["Segment_New"] = _seg
    else:
        df["Segment_New"] = _hard

    # Reihenfolge-Toggle: Liquidität jetzt als Mitgliedschafts-Gate (nach dem Labeling).
    # Segment-Labels stammen aus der vollen Markt-Coverage; illiquide Titel fallen hier raus.
    if label_before_liquidity:
        df = df[df["3M ADTV Y2025"] >= adtv_thr].copy()

    helv = df[df["Segment_New"].isin(["Large Cap", "Mid Cap", "Small Cap"])].copy()  # Konstituenten i.e.S.
    helv_full_pool = df.copy()                                                       # inkl. Micro Cap
    return helv, helv_full_pool, _legacy


# ── Helvetica multi-asset allocation (target weights, % of the total index) ──────
# 45% static (cash + ETFs, not selected by the tool) + 55% tool-selected
# (Equity L/M/S = top-N each excl. Real Estate, equal-weighted; Real Estate = all
# qualifying incl. Micro, equal-weighted). Single source of truth — reused for Multi-Period.
HELVETICA_STATIC = [
    {"sleeve": "Cash",             "ticker": "CASH-CHF",     "name": "Cash (CHF)",                                      "weight": 5.0},
    {"sleeve": "Government Bonds", "ticker": "CSBGC7-SWX",   "name": "iShares Swiss Domestic Government Bond 3-7 ETF",  "weight": 5.0},
    {"sleeve": "Government Bonds", "ticker": "CSBGC0-SWX",   "name": "iShares Swiss Domestic Government Bond 7-15 ETF", "weight": 5.0},
    {"sleeve": "Corporate Bonds",  "ticker": "CHCORP-SWX",   "name": "iShares Core CHF Corporate Bond ETF",            "weight": 15.0},
    {"sleeve": "Gold",             "ticker": "PPFB-XEX",     "name": "iShares Physical Gold ETC",                      "weight": 7.5},
    {"sleeve": "Gold",             "ticker": "XAD5-XEX",     "name": "Xtrackers Physical Gold ETC",                    "weight": 7.5},
]  # = 45%
HELVETICA_EQUITY_SLEEVES = {"Large Cap": 10.0, "Mid Cap": 15.0, "Small Cap": 15.0}  # 40% Equity; top-10 each, equal-weighted (Large 1%/title, Mid & Small 1.5%/title)
HELVETICA_RE_WEIGHT = 15.0   # all qualifying Real Estate (incl. Micro), equal-weighted
HELVETICA_RE_INDUSTRIES = {"Real Estate Development", "Real Estate Investment Trusts"}  # FactSet RE-Klassen
HELVETICA_TOPN = 10          # top-N constituents per equity sleeve
HELVETICA_TARGET = {"Cash": 5.0, "Government Bonds": 10.0, "Corporate Bonds": 15.0,
                    "Large Cap": 10.0, "Mid Cap": 15.0, "Small Cap": 15.0, "Real Estate": 15.0, "Gold": 15.0}

HELVETICA_BUFFER_HARD = 8    # Equity-Top-10 Rang-Band: hart drin <= Rang 8
HELVETICA_BUFFER_EXIT = 13   # Inkumbent bleibt in den Top-10, solange Rang <= 13

def _helv_dedup_most_liquid(df, id_col="Entity ID", liq_col="3M ADTV Y2025"):
    """Pro Firma (Entity ID) nur die LIQUIDESTE Linie (höchstes 3M-ADTV) behalten —
    verhindert Doppelgewichte bei Mehrfach-Listings (Variante B, z.B. Roche ROP/RO,
    Swatch UHR/UHRN, Schindler SCHP/SCHN, Lindt LISN/LISP). Fehlt die Entity ID, wird
    auf die ISIN zurückgegriffen, sodass solche Zeilen NICHT fälschlich kollabieren."""
    if df is None or len(df) == 0:
        return df
    d = df.copy()
    eid = (d[id_col].astype(str).str.strip() if id_col in d.columns
           else pd.Series("", index=d.index))
    isin = _norm_isin(d["ISIN"])
    valid = eid.ne("") & eid.str.lower().ne("nan")
    key = eid.where(valid, "ISIN::" + isin)
    liq = pd.to_numeric(d[liq_col], errors="coerce").fillna(0.0) if liq_col in d.columns \
          else pd.Series(0.0, index=d.index)
    d = d.assign(_dedup_k=key.to_numpy(), _dedup_liq=liq.to_numpy())
    d = (d.sort_values("_dedup_liq", ascending=False)
           .drop_duplicates("_dedup_k", keep="first")
           .drop(columns=["_dedup_k", "_dedup_liq"]))
    return d


def build_helvetica_composite(helv, helv_full_pool, re_industries, incumbents_isin=None,
                              buffer_hard=HELVETICA_BUFFER_HARD, buffer_exit=HELVETICA_BUFFER_EXIT):
    """Compose the full Helvetica multi-asset index for one snapshot: 45% static sleeves
    (cash + ETFs, fixed weights) + 55% tool-selected, equal-weighted (Equity L/M/S = 10 each;
    Real Estate = all qualifying incl. Micro). Equal-weight fills the whole sleeve: each equity
    name = sleeve_weight / n (n<=10); each RE name = 15% / n_re.

    Equity = FIXED 10/10/10 as a SEQUENTIAL TOP-DOWN CASCADE (Large → Mid → Small). Each sleeve takes
    the top-10 of its OWN coverage segment, ranked by FREE-FLOAT MCap (Adj_FF_MCap, Total MCap as
    tiebreaker — the same key as the Swiss-size sub-indices; the size CLASS itself comes from Total MCap
    in the pipeline). Selected names are removed from the remaining pool before the next sleeve. If a
    segment has <10 own names, it pulls the BEST names (by Adj_FF_MCap) from the next-smaller segment
    (Large←Mid, Mid←Small, Small←Micro), marked "Aufrücker" (true size class preserved). Because those
    are removed, the next sleeve checks ">=10" on the REDUCED pool and the cascade propagates (a short
    Large can push Mid below 10 → Mid pulls from Small, etc.). LARGER segments are excluded as a source
    → NO overflow down: a segment keeping >10 names after deductions takes its top-10, the surplus is
    dropped. Each constituent carries True_Segment + Status (Kern/Aufrücker). The RANK-BAND buffer
    (_rank_band_select, hard/exit) runs over each sleeve's OWN segment, so the rank-10 cut is stabilised.
    Without `incumbents_isin` = plain top-10.

    Turnover control (Multi-Period): `incumbents_isin` (prior-period selected constituents) feeds the
    rank-band buffer per tranche. (The Real-Estate FF-incumbent buffer lives in build_helvetica_pipeline,
    since RE = all qualifying.) Returns (composition_df, sleeve_summary_df); Index_Weight in % of TOTAL."""
    is_re = lambda d: d["FactSet Industry"].isin(re_industries)
    # Company-level Dedup: pro Firma nur die liquideste Linie (höchstes 3M-ADTV) — so kann
    # keine Firma mit Mehrfach-Listing (Variante B) zwei Plätze belegen → nie Doppelgewichte.
    # Top-10-Auswahl je Sleeve: Rang nach FREE-FLOAT-MCAP (Adj_FF_MCap, Total MCap als Tiebreaker).
    # Damit zieht Helvetica genau die 10 größten Konstituenten des Float-MCap-gewichteten
    # Swiss-Size-Sub-Index (Segment-KLASSE bleibt firmen-intern über Total MCap, siehe Pipeline).
    helv_eq = (_helv_dedup_most_liquid(helv[~is_re(helv)])
               .sort_values(["Adj_FF_MCap", "Total MCap Y2025"], ascending=[False, False]).reset_index(drop=True))
    helv_eq = helv_eq.assign(_isin_k=_norm_isin(helv_eq["ISIN"]))

    rows = []
    _static_type = {"Cash": "Cash", "Government Bonds": "Bond - ETF",
                    "Corporate Bonds": "Bond - ETF", "Gold": "Gold - ETC"}
    for st_ in HELVETICA_STATIC:
        rows.append({"Sleeve": st_["sleeve"], "Type": _static_type.get(st_["sleeve"], "Static (ETF/Cash)"), "Exchange Ticker": st_["ticker"],
                     "Name": st_["name"], "ISIN": "", "Mapping Country": "", "FactSet Industry": "",
                     "Adj_FF_MCap": float("nan"), "Index_Weight": st_["weight"],
                     "True_Segment": "", "Status": ""})

    # Equity: feste 10/10/10-Sleeves als SEQUENZIELLE KASKADE (top-down: Large -> Mid -> Small). Jedes
    # Segment nimmt seine Top-10 aus dem RESTBESTAND (Rang nach Free-Float-MCap = Adj_FF_MCap, Total
    # MCap als Tiebreaker; Rang-Band-Buffer 8/13 NUR unter den eigenen Mitgliedern), und die gewählten
    # Titel werden danach aus dem Restbestand ENTFERNT. Hat ein Segment < 10 eigene Titel, zieht es die
    # BESTEN Titel des nächstkleineren Segments ab (Large<-Mid, Mid<-Small, Small<-Micro) — markiert als
    # "Aufrücker". Weil diese abgezogen sind, prüft das nächste Segment ">= 10" auf dem REDUZIERTEN
    # Bestand: drückt ein knappes Large das Mid unter 10, zieht Mid seinerseits aus Small nach usw.
    # (gewollte Kaskade). GRÖSSERE Segmente sind als Quelle ausgeschlossen (kein Übertrag nach unten);
    # der Überschuss eines Segments mit > 10 Titeln wird verworfen.
    _SEG_RANK = {"Large Cap": 0, "Mid Cap": 1, "Small Cap": 2, "Micro Cap": 3}
    _available = helv_eq
    for seg, sleeve_w in HELVETICA_EQUITY_SLEEVES.items():
        _sr = _SEG_RANK.get(seg, 9)
        _srank = _available["Segment_New"].map(lambda s: _SEG_RANK.get(s, 9))
        _own = _available[_srank == _sr].sort_values(["Adj_FF_MCap", "Total MCap Y2025"],
                                                     ascending=[False, False]).reset_index(drop=True)
        if incumbents_isin:
            seg_df = _rank_band_select(_own, HELVETICA_TOPN, incumbents_isin, buffer_hard, buffer_exit, id_col="_isin_k")
        else:
            seg_df = _own.head(HELVETICA_TOPN)
        if len(seg_df) < HELVETICA_TOPN:  # Kaskade: beste Titel aus kleineren Segmenten nachziehen (nach FF-MCap)
            _fb = _available[_srank > _sr].sort_values(["Adj_FF_MCap", "Total MCap Y2025"], ascending=[False, False])
            seg_df = pd.concat([seg_df, _fb.head(HELVETICA_TOPN - len(seg_df))], ignore_index=True)
        _available = _available[~_available["_isin_k"].isin(set(seg_df["_isin_k"]))]
        n = len(seg_df)
        w = sleeve_w / n if n else 0.0
        for _, r in seg_df.iterrows():
            _true = r.get("Segment_New")
            _tr = _SEG_RANK.get(_true, 9)
            _status = "Kern" if _tr == _sr else "Aufrücker"   # _tr >= _sr garantiert → nie Übertrag
            rows.append({"Sleeve": seg, "Type": "Equity", "Exchange Ticker": r.get("Exchange Ticker"),
                         "Name": r.get("Name"), "ISIN": r.get("ISIN"), "Mapping Country": r.get("Mapping Country"),
                         "FactSet Industry": r.get("FactSet Industry"), "Adj_FF_MCap": r.get("Adj_FF_MCap"),
                         "Index_Weight": w, "True_Segment": _true, "Status": _status})
    re_df = _helv_dedup_most_liquid(helv_full_pool[is_re(helv_full_pool)]) \
            .sort_values("Adj_FF_MCap", ascending=False)
    n_re = len(re_df)
    w_re = HELVETICA_RE_WEIGHT / n_re if n_re else 0.0
    for _, r in re_df.iterrows():
        rows.append({"Sleeve": "Real Estate", "Type": "Real Estate", "Exchange Ticker": r.get("Exchange Ticker"),
                     "Name": r.get("Name"), "ISIN": r.get("ISIN"), "Mapping Country": r.get("Mapping Country"),
                     "FactSet Industry": r.get("FactSet Industry"), "Adj_FF_MCap": r.get("Adj_FF_MCap"),
                     "Index_Weight": w_re, "True_Segment": "Real Estate", "Status": ""})
    comp = pd.DataFrame(rows)
    summ = comp.groupby("Sleeve", sort=False).agg(
        Positionen=("Name", "size"), **{"Ist-Gewicht %": ("Index_Weight", "sum")}).reset_index()
    summ["Ziel-Gewicht %"] = summ["Sleeve"].map(HELVETICA_TARGET)
    return comp, summ


def build_swiss_size_subindices(gm_universe, adtv_thr=1_000_000, prior_segments=None,
                                incumbents_isin=None, re_industries=None, use_buffer=False,
                                full=None, label_before_liquidity=False):
    """Drei eigenständige Swiss-Size-Sub-Indizes (Large / Mid / Small Cap), aus denen Helvetica
    die Top-10 zieht. Eigenschaften:
      - Universe: Exchange Country = CH, FF MCap > 0, FF % ≥ 10 % (Inkumbent/use_buffer ≥ 7,5 %), 3M-ADTV ≥ adtv_thr.
      - Variante B: ALLE Share Lines (kein Dedup) — Mehrfach-Listings dürfen vertreten sein.
      - Segment: firmen-interner Coverage-Cut (über build_helvetica_pipeline → eine Linie/Firma,
        inkl. ±5/±0,5-Hysterese via prior_segments). Jede Linie erbt das Segment IHRER Firma.
      - Gewichtung: Float-MCap (Adj_FF_MCap) cap-gewichtet, je Sub-Index auf 100 % normiert.
    `incumbents_isin` (Multi-Period): identische FF%-Maintenance (7,5 %) wie Helveticas Pipeline,
    damit Helveticas selektierte Titel stets eine Teilmenge des Sub-Index sind. `use_buffer` muss
    mit dem Helvetica-Composite übereinstimmen (Single-Tab-Vergleich), sonst weichen Segmentgrenzen
    und FF%-Schwelle ab. `full` = bereits berechneter helv_full_pool (mit Segment_New); wird er
    übergeben, entfällt der zweite, identische Pipeline-Lauf (Performance).
    Real Estate wird ausgeschlossen (eigenes Helvetica-Sleeve). Gibt dict {Segment: DataFrame}.
    """
    _re = re_industries or HELVETICA_RE_INDUSTRIES
    # 1) Firmen-Segmente (eine Linie je Firma) aus der Helvetica-Pipeline (firmen-interner Cut +
    #    Hysterese). `full` kann vom Aufrufer vorberechnet hereingereicht werden (identische Args)
    #    → spart den doppelten Pipeline-Lauf.
    if full is None:
        _, full, _ = build_helvetica_pipeline(gm_universe, use_buffer=use_buffer, adtv_thr=adtv_thr,
                                              incumbents_isin=incumbents_isin, prior_segments=prior_segments,
                                              label_before_liquidity=label_before_liquidity)
    if full is None or len(full) == 0:
        _empty = full.iloc[0:0].copy() if full is not None else pd.DataFrame()
        return {s: _empty.copy() for s in ["Large Cap", "Mid Cap", "Small Cap"]}
    _seg_by_ent = dict(zip(full["Entity ID"].fillna("").astype(str).str.strip(), full["Segment_New"]))
    # 2) Voller CH-Pool, ALLE Linien (gleiche Filter wie Helvetica, KEIN Dedup), ohne Real Estate.
    #    FF%-Maintenance (7,5 %) fuer Inkumbenten ODER use_buffer (identisch zur Pipeline) — sonst
    #    koennte ein Helvetica-Titel fehlen bzw. der Pool-Filter vom Composite abweichen.
    pool = gm_universe[(gm_universe["Exchange Country Name"] == "SWITZERLAND") &
                       (gm_universe["Free Float MCap Y2025"] > 0)].copy()
    _inc = set(incumbents_isin or [])
    _maint_pool = _norm_isin(pool["ISIN"]).isin(_inc) | bool(use_buffer)
    _ff_min = np.where(_maint_pool, 0.075, 0.10)
    pool = pool[(pool["Free Float Percent"] >= _ff_min) & (pool["3M ADTV Y2025"] >= adtv_thr)]
    pool = pool[~pool["FactSet Industry"].isin(_re)].copy()
    # 3) Jede Linie erbt das Segment ihrer Firma (firmen-interner Cut)
    pool["Segment_New"] = pool["Entity ID"].fillna("").astype(str).str.strip().map(_seg_by_ent)
    pool = pool[pool["Segment_New"].isin(["Large Cap", "Mid Cap", "Small Cap"])].copy()
    # 4) Float-MCap-Gewicht je Sub-Index (auf 100 % normiert)
    out = {}
    for seg in ["Large Cap", "Mid Cap", "Small Cap"]:
        s = pool[pool["Segment_New"] == seg].copy()
        _tot = s["Adj_FF_MCap"].sum()
        s["Index_Weight"] = (s["Adj_FF_MCap"] / _tot * 100.0) if _tot > 0 else 0.0
        out[seg] = s.sort_values("Adj_FF_MCap", ascending=False).reset_index(drop=True)
    return out


def render_helvetica_tab(gm_universe, label_before_liquidity=False):
    """Render Helvetica Tab — kundenspezifischer Schweizer Index."""
    st.markdown("## 🏔️ Helvetica")
    st.caption(
        "Kundenspezifischer Schweizer Multi-Asset-Index — 45 % statisch (Cash + Bond-/Gold-ETFs), "
        "55 % selektiert: Equity Large/Mid/Small (je Top 10, gleichgewichtet) + Real Estate "
        "(alle qualifizierten, gleichgewichtet). Eigenständige Schweiz-Pipeline (vor EUMSS)."
    )
    st.caption(f"📅 Snapshot: **{_snapshot_label}**")

    # ── Toggles ────────────────────────────────────────────────────────────
    _tg1, _tg2 = st.columns(2)
    with _tg1:
        _use_buffer = st.toggle(
            "Maintenance-Schwellen (Vergleich, alle Titel) — 75 / 90 / 99.5 % statt 70 / 85 / 99 %",
            value=False,
            key="helvetica_buffer_toggle",
            help=(
                "Reiner **Single-Snapshot-Vergleich** — NICHT der echte inkumbenten-basierte Buffer "
                "des Multi-Period-Tabs (dort: Rang-Band 8/13 + ±5/±0,5-Hysterese nur für Bestandstitel).\n\n"
                "**Aus (Default):** Entry-Schwellen — Coverage 70/85/99 %, FF % ≥ 10 %.\n\n"
                "**An:** Maintenance-Schwellen für **alle** Titel — Coverage 75/90/99.5 %, FF % ≥ 7.5 %. "
                "Zeigt, wie sich die gelockerten Schwellen auf das Universe auswirken; die Auswahl bleibt "
                "plain Top-10."
            ),
        )
    with _tg2:
        _adtv_lbl = st.radio(
            "3M-ADTV-Schwelle", ["$0.25M", "$0.5M", "$1.0M"], index=2, horizontal=True,
            key="helvetica_adtv_choice",
            help="3M ADTV ≥ gewählte Schwelle. $1.0M = Default (strenger; konzentrierterer "
                 "Real-Estate-Korb); $0.5M / $0.25M = inklusiver (mehr kleine Titel / Real Estate). "
                 "Unabhängig vom Buffer.",
        )

    _adtv_thr = {"$0.25M": 250_000, "$0.5M": 500_000, "$1.0M": 1_000_000}[_adtv_lbl]

    # ── Helvetica Pipeline laufen lassen ────────────────────────────────────
    helv, helv_full_pool, params = build_helvetica_pipeline(gm_universe, use_buffer=_use_buffer, adtv_thr=_adtv_thr,
                                                            label_before_liquidity=label_before_liquidity)

    if len(helv) == 0:
        st.warning("⚠️ Keine Stocks im Helvetica-Universe (Exchange Country = Switzerland, FF MCap > 0, Min FF%, ADTV-Schwellen).")
        return

    # ── Methodik-Box ───────────────────────────────────────────────────────
    _params_text = (
        f"**Aktive Schwellen** ({'Maintenance' if _use_buffer else 'Entry'}): "
        f"3M ADTV ≥ ${params['adtv_thr']/1e6:.1f}M (fest) | "
        f"FF % ≥ {params['min_ff_pct']*100:.1f}% | "
        f"Large Cap < {params['large_cut']:.1f}% | "
        f"Standard < {params['std_cut']:.1f}% | "
        f"Small Cap < {params['small_cut']:.1f}%"
    )
    st.info(_params_text)

    # ── Composite: 45% statische Sleeves (Cash/ETFs) + 55% selektiert (Equity/RE) ──
    RE_INDUSTRIES = HELVETICA_RE_INDUSTRIES
    comp, summ = build_helvetica_composite(helv, helv_full_pool, RE_INDUSTRIES)
    _total_w = comp["Index_Weight"].sum()

    st.markdown("---")
    st.markdown("### 🧱 Allokation — 45 % statisch + 55 % selektiert")
    _order = {sl: i for i, sl in enumerate(
        ["Cash", "Government Bonds", "Corporate Bonds", "Large Cap", "Mid Cap", "Small Cap", "Real Estate", "Gold"])}
    _summ = summ.assign(_o=summ["Sleeve"].map(_order)).sort_values("_o").drop(columns="_o")
    _summ_disp = _summ.copy()
    _summ_disp["Ziel-Gewicht %"] = _summ_disp["Ziel-Gewicht %"].map(lambda x: f"{x:.1f}%")
    _summ_disp["Ist-Gewicht %"] = _summ_disp["Ist-Gewicht %"].map(lambda x: f"{x:.2f}%")
    st.dataframe(_summ_disp[["Sleeve", "Ziel-Gewicht %", "Ist-Gewicht %", "Positionen"]],
                 width="stretch", hide_index=True)
    st.caption(
        f"Gesamtgewicht **{_total_w:.2f} %** (Soll 100 %). Statisch (45 %): Cash 5 · Govt Bonds 10 "
        f"(CSBGC7/CSBGC0) · Corp Bonds 15 (CHCORP) · Gold 15 (PPFB/XAD5). Selektiert (55 %): Equity 40 % "
        f"(Large 10 % = 1 %/Titel · Mid 15 % = 1,5 %/Titel · Small 15 % = 1,5 %/Titel, je Top-{HELVETICA_TOPN}), "
        f"Real Estate 15 % (alle qualifizierten gleichgewichtet)."
    )
    if abs(_total_w - 100.0) > 0.01:
        st.warning(
            f"⚠️ Gesamtgewicht {_total_w:.2f} % ≠ 100 % — ein Sleeve ist leer/unterbesetzt "
            f"(zu wenige Titel im Schweizer Universe). Bitte prüfen."
        )

    # ── Vollständige Index-Zusammensetzung ────────────────────────────────────
    st.markdown("### 📋 Index-Zusammensetzung")
    _disp = comp.copy()
    _disp["Gewicht %"] = _disp["Index_Weight"].map(lambda x: f"{x:.4f}%")
    _disp["Adj. FF MCap"] = _disp["Adj_FF_MCap"].map(
        lambda x: "" if pd.isna(x) else (f"${x/1e9:.2f}B" if x >= 1e9 else f"${x/1e6:.0f}M"))
    # Klassifikation: zeigt die "echte" Coverage-Klasse vs. den Sleeve. Kern = passt;
    # Aufrücker = via Kaskade aus kleinerer Klasse nachgezogen (Übertrag nach unten gibt es nicht).
    def _klass(row):
        if row.get("Type") != "Equity":
            return ""
        return "Kern" if row.get("Status") == "Kern" else f"{row.get('Status')} (echt: {row.get('True_Segment')})"
    _disp["Klassifikation"] = _disp.apply(_klass, axis=1)
    _cols = ["Sleeve", "Klassifikation", "Type", "Exchange Ticker", "Name", "Mapping Country",
             "FactSet Industry", "Adj. FF MCap", "Gewicht %"]
    st.dataframe(_disp[[c for c in _cols if c in _disp.columns]], width="stretch", hide_index=True,
                 height=min(35 * (len(_disp) + 1) + 3, 720))

    # ── Export ────────────────────────────────────────────────────────────────
    _meta = {
        "Index": "Helvetica (Multi-Asset)",
        "Modus": "Maintenance Buffer" if params["use_buffer"] else "Entry",
        "ADTV Schwelle": f"${params['adtv_thr']/1e6:.2f}M",
        "Min FF %": f"{params['min_ff_pct']*100:.1f}%",
        "Cuts L/Std/Small": f"{params['large_cut']:.1f}/{params['std_cut']:.1f}/{params['small_cut']:.1f}%",
        "Equity Top-N je Sleeve": HELVETICA_TOPN,
        "Snapshot Datum": _snapshot_label,
        "Gesamtgewicht %": f"{_total_w:.2f}",
    }
    st.download_button(
        "⬇️ Download Helvetica Index Composition (Excel)",
        data=to_excel_multi({
            "Helvetica Composition": comp,
            "Allocation Summary": _summ,
            "Parameter Settings": pd.DataFrame([{"Parameter": k, "Wert": v} for k, v in _meta.items()]),
        }),
        file_name=f"Helvetica_Composition_{_snapshot_label.replace('.','')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_helvetica_composition",
    )

    # ── Swiss Size Sub-Indizes & Helvetica-Selektion (Float-MCap-gewichtet, Variante B) ──
    # Konsolidiert: die frühere separate "Detail je Segment"-Ansicht ist hier aufgegangen. Die
    # Sub-Indizes zeigen je Größenklasse ALLE Share Lines (Float-MCap-Gewicht), markieren die von
    # Helvetica selektierten (✓) und deren Gewicht im Gesamtindex. Real Estate hat keinen Sub-Index
    # (eigenes Sleeve = alle qualifizierten) und steht als separater Block darunter.
    st.markdown("---")
    st.markdown("### 🇨🇭 Swiss Size Sub-Indizes & Helvetica-Selektion")
    st.caption(
        "Eigenständige Large/Mid/Small Cap Sub-Indizes (Exchange Country = CH, CH-interne Coverage, "
        "**alle** Share Lines, Float-MCap-gewichtet, je Sub-Index 100 %). Helvetica zieht je Sub-Index "
        "die Top-10 (liquideste Linie je Firma, gleichgewichtet). ✓ = von Helvetica selektiert · "
        "**Float-Gewicht** = Gewicht im Sub-Index · **Helvetica-Gewicht** = Gewicht im Gesamtindex "
        "(„–“ = nicht selektiert)."
    )
    _comp_w = comp.set_index("Exchange Ticker")["Index_Weight"].to_dict()
    _subs = build_swiss_size_subindices(gm_universe, adtv_thr=_adtv_thr,
                                        use_buffer=_use_buffer, full=helv_full_pool,
                                        label_before_liquidity=label_before_liquidity)
    _sub_export = {}
    for _seg in ["Large Cap", "Mid Cap", "Small Cap"]:
        _sdf = _subs.get(_seg)
        if _sdf is None or len(_sdf) == 0:
            st.markdown(f"**{_seg}** — keine Titel."); continue
        _d = _sdf.sort_values("Adj_FF_MCap", ascending=False).copy()
        _hw = _d["Exchange Ticker"].map(lambda t: _comp_w.get(t, 0.0))
        _d["In Helvetica"] = np.where(_hw > 0, "✓", "")
        _d["Float-Gewicht %"] = _d["Index_Weight"].map(lambda x: f"{x:.2f}%")
        _d["Helvetica-Gewicht %"] = [f"{w:.3f}%" if w > 0 else "—" for w in _hw]
        _d["Adj. FF MCap"] = _d["Adj_FF_MCap"].map(lambda x: f"${x/1e9:.2f}B" if x >= 1e9 else f"${x/1e6:.0f}M")
        st.markdown(f"**{_seg}** — {len(_d)} Linien / {_d['Entity ID'].nunique()} Firmen · "
                    f"{(_d['In Helvetica']=='✓').sum()} in Helvetica "
                    f"(Top-{min(HELVETICA_TOPN, _d['Entity ID'].nunique())})")
        _cols = ["In Helvetica", "Exchange Ticker", "Name", "Listing", "Adj. FF MCap",
                 "Float-Gewicht %", "Helvetica-Gewicht %"]
        st.dataframe(_d[[c for c in _cols if c in _d.columns]], width="stretch", hide_index=True,
                     height=min(35 * (len(_d) + 1) + 3, 430))
        _sub_export[f"Swiss {_seg}"] = _sdf

    # Real Estate: kein Sub-Index — eigenes Sleeve = alle qualifizierten (inkl. Micro), gleichgewichtet.
    _re_pool = helv_full_pool[helv_full_pool["FactSet Industry"].isin(RE_INDUSTRIES)]
    if len(_re_pool):
        _r = _re_pool.sort_values("Adj_FF_MCap", ascending=False).copy()
        _rw = _r["Exchange Ticker"].map(lambda t: _comp_w.get(t, 0.0))
        _r["In Helvetica"] = np.where(_rw > 0, "✓", "")
        _r["Helvetica-Gewicht %"] = [f"{w:.3f}%" if w > 0 else "—" for w in _rw]
        _r["Adj. FF MCap"] = _r["Adj_FF_MCap"].map(lambda x: f"${x/1e9:.2f}B" if x >= 1e9 else f"${x/1e6:.0f}M")
        st.markdown(f"**Real Estate** (kein Sub-Index — alle qualifizierten inkl. Micro, gleichgewichtet) · "
                    f"{len(_r)} Titel, {(_r['In Helvetica']=='✓').sum()} in Helvetica")
        _cols = ["In Helvetica", "Exchange Ticker", "Name", "Mapping Country", "FactSet Industry",
                 "Adj. FF MCap", "Helvetica-Gewicht %"]
        st.dataframe(_r[[c for c in _cols if c in _r.columns]], width="stretch", hide_index=True,
                     height=min(35 * (len(_r) + 1) + 3, 430))
        _sub_export["Real Estate"] = _re_pool

    if _sub_export:
        st.download_button(
            "⬇️ Swiss Size Sub-Indizes + Real Estate (Excel)",
            data=to_excel_multi(_sub_export),
            file_name=f"Swiss_Size_SubIndices_{_snapshot_label.replace('.','')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_swiss_subindices",
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: Helvetica
# ══════════════════════════════════════════════════════════════════════════════
with tab_helvetica:
    if _gm_u_global is None or len(_gm_u_global) == 0:
        st.warning("⚠️ Universe ist leer. Bitte Datei-Upload und Filter-Einstellungen prüfen.")
    else:
        render_helvetica_tab(_gm_u_global, label_before_liquidity)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6b: Helvetica Multi-Period
# ══════════════════════════════════════════════════════════════════════════════
with tab_helvetica_mp:
    st.markdown("## 🏔️ Helvetica Multi-Period")
    st.caption("Mehrperioden-Lauf des Helvetica-Multi-Asset-Index mit frei wählbaren "
               "Rebalancing-Terminen und echtem inkumbenten-basierten Maintenance-Buffer.")
    if data_mode != "Master File (Multi-Period)":
        st.info("Bitte im Sidebar **'Master File (Multi-Period)'** wählen und ein Master-File laden.")
    elif master_data is None or not master_data.get("detected_dates"):
        st.warning("⚠️ Kein Master-File geladen / keine Selection Dates erkannt.")
    else:
        _MON = {1: "Jan", 2: "Feb", 3: "Mär", 4: "Apr", 5: "Mai", 6: "Jun",
                7: "Jul", 8: "Aug", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Dez"}
        _dates_all = sorted(master_data["detected_dates"])
        _months_avail = sorted({int(d.split("-")[1]) for d in _dates_all})
        _years = sorted({int(d.split("-")[0]) for d in _dates_all})

        st.markdown("### 📅 Rebalancing-Termine")
        st.caption("Verfügbare Monate im Master: " + ", ".join(_MON[m] for m in _months_avail) + ".")
        _preset = st.radio("Frequenz", ["Quartalsweise (alle)", "Halbjährlich", "Jährlich", "Eigene Monate"],
                           index=0, horizontal=True, key="helv_mp_preset")
        if _preset == "Quartalsweise (alle)":
            _sel_months = list(_months_avail)
        elif _preset == "Halbjährlich":
            _sel_months = [m for m in (5, 11) if m in _months_avail] or list(_months_avail)  # Mai + Nov
        elif _preset == "Jährlich":
            _sel_months = [_months_avail[-1]]
        else:
            _sel_months = st.multiselect("Monate", _months_avail, default=_months_avail,
                                         format_func=lambda m: _MON[m], key="helv_mp_months")

        _c1, _c2, _c3, _c4 = st.columns(4)
        with _c1: _y0 = st.selectbox("Von Jahr", _years, index=0, key="helv_mp_y0")
        with _c2: _y1 = st.selectbox("Bis Jahr", _years, index=len(_years) - 1, key="helv_mp_y1")
        with _c3: _mp_buffer = st.toggle("Maintenance Buffer", value=True, key="helv_mp_buffer",
                      help="Inkumbenten-Bestandsschutz: Equity-Top-10 via Rang-Band (hart 8 / exit 13), "
                           "Real Estate via FF-Buffer (Bestands-RE bleibt bei FF ≥ 7.5%). Senkt den Turnover.")
        with _c4: _mp_adtv_lbl = st.selectbox("3M-ADTV", ["$0.25M", "$0.5M", "$1.0M"], index=2, key="helv_mp_adtv")
        _mp_adtv = {"$0.25M": 250_000, "$0.5M": 500_000, "$1.0M": 1_000_000}[_mp_adtv_lbl]

        _reb = [d for d in _dates_all
                if int(d.split("-")[1]) in set(_sel_months) and _y0 <= int(d.split("-")[0]) <= _y1]
        if not _reb:
            st.warning("Keine Rebalancing-Termine für die gewählten Monate/Jahre.")
        else:
            _mon_lbl = ", ".join(_MON[m] for m in _sel_months)
            _term_lbl = ", ".join(_reb) if len(_reb) <= 14 else f"{_reb[0]} … {_reb[-1]} ({len(_reb)})"
            st.caption(f"**{len(_reb)} Termine** ({_mon_lbl}): {_term_lbl}")
            # Konfig-Signatur des Laufs (Termine + Buffer + ADTV) — ändert sie sich nach einem Lauf,
            # werden die gespeicherten Ergebnisse ausgeblendet (sie passen dann nicht mehr zur Steuerung).
            _cfg = (tuple(_reb), bool(_mp_buffer), _mp_adtv)
            if st.button("▶️ Helvetica Multi-Period starten", type="primary", key="helv_mp_run"):
                _RE = HELVETICA_RE_INDUSTRIES
                _prev = set(); _prev_seg = {}; _comps = {}; _subs_by_date = {}; _rows = []
                _prog = st.progress(0, text="Starte…")
                for _i, _sd in enumerate(_reb):
                    _prog.progress(_i / len(_reb), text=f"{_sd} ({_i + 1}/{len(_reb)})")
                    _sdd = pd.Timestamp(_sd).date()
                    _cc = get_classification_dict(hc_df, _sdd)
                    _cif = float(china_if_map.get(_sdd, 0.20))
                    _snap = build_snapshot_from_master(master_data, _sd)
                    _gmu = build_new_universe(
                        _snap.copy(), _cc, thailand_sec_type, max_closing_price,
                        exclude_hk_cny, exclude_country_risk_na, exclude_naics_funds, exclude_euro_mtf, exclude_etf_sicav,
                        _cif, atvr_mcap_col=atvr_mcap_col, excl_delisted=exclude_delisted,
                        fol_matrix=fol_matrix, fol_sector_fb=fol_sector_fb, fol_year=_sdd.year, fol_enabled=apply_fol)
                    _seed = (len(_prev) == 0)
                    _inc = (_prev if (_mp_buffer and not _seed) else None)
                    _pseg = (_prev_seg if (_mp_buffer and not _seed) else None)
                    _helv, _full, _ = build_helvetica_pipeline(
                        _gmu, use_buffer=False, adtv_thr=_mp_adtv, incumbents_isin=_inc,
                        prior_segments=_pseg, label_before_liquidity=label_before_liquidity)
                    _comp, _ = build_helvetica_composite(_helv, _full, _RE, incumbents_isin=_inc)
                    _comps[_sd] = _comp
                    _subs_by_date[_sd] = build_swiss_size_subindices(
                        _gmu, adtv_thr=_mp_adtv, incumbents_isin=_inc, full=_full,
                        label_before_liquidity=label_before_liquidity)
                    _sel = _comp[_comp["Type"].isin(["Equity", "Real Estate"])]
                    _cur = set(_norm_isin(_sel["ISIN"])) - {""}
                    # Universe-Kennzahlen: komplettes (dedupliziertes) CH-Universe inkl. Micro vs. L+M+S
                    _seg_cnt = {sg: int((_helv["Segment_New"] == sg).sum())
                                for sg in ["Large Cap", "Mid Cap", "Small Cap"]}
                    _lms = sum(_seg_cnt.values())
                    _lms_str = f"{_seg_cnt['Large Cap']}/{_seg_cnt['Mid Cap']}/{_seg_cnt['Small Cap']}"
                    # Aufrücker je Segment (Equity-Kaskaden-Aufrücker aus kleinerer Klasse)
                    _eq = _comp[_comp["Type"] == "Equity"]
                    _auf = {sg: int(((_eq["Sleeve"] == sg) & (_eq.get("Status") == "Aufrücker")).sum())
                            for sg in ["Large Cap", "Mid Cap", "Small Cap"]}
                    _auf_str = (f"{_auf['Large Cap']}/{_auf['Mid Cap']}/{_auf['Small Cap']}"
                                if sum(_auf.values()) > 0 else "–")
                    _rows.append({
                        "Termin": _sd,
                        "Universe (CH)": len(_full),
                        "L+M+S": _lms,
                        "L/M/S": _lms_str,
                        "Selektiert": len(_sel),
                        "Equity": int((_comp["Type"] == "Equity").sum()),
                        "Real Estate": int((_comp["Type"] == "Real Estate").sum()),
                        "Aufrücker L/M/S": _auf_str,
                        "Gehalten": "Seed" if _seed else len(_cur & _prev),
                        "Neu": "Seed" if _seed else len(_cur - _prev),
                        "Raus": "Seed" if _seed else len(_prev - _cur),
                        "Gewicht %": round(_comp["Index_Weight"].sum(), 2),
                    })
                    _prev = _cur
                    # Vorperioden-Segmente (firmen-eben) für die ±5/±0,5-Hysterese der nächsten Periode
                    _prev_seg = dict(zip(_full["Entity ID"].fillna("").astype(str).str.strip(),
                                         _full["Segment_New"])) if len(_full) else {}
                _prog.progress(1.0, text="✅ Fertig")
                st.session_state["helv_mp_comps"] = _comps
                st.session_state["helv_mp_subs"] = _subs_by_date
                st.session_state["helv_mp_summary"] = pd.DataFrame(_rows)
                st.session_state["helv_mp_cfg"] = _cfg

            # Stale-Guard: weicht die aktuelle Steuerung von der des letzten Laufs ab, alte Ergebnisse
            # ausblenden (session_state leeren) und zum Neustart auffordern — sonst zeigt die Anzeige
            # unten einen Lauf, der nicht mehr zu Frequenz/Jahren/Buffer/ADTV oben passt.
            if st.session_state.get("helv_mp_comps") and st.session_state.get("helv_mp_cfg") != _cfg:
                for _k in ("helv_mp_comps", "helv_mp_subs", "helv_mp_summary", "helv_mp_cfg"):
                    st.session_state.pop(_k, None)
                st.info("ℹ️ Einstellungen geändert — bitte den Multi-Period-Lauf erneut starten.")

            if st.session_state.get("helv_mp_comps"):
                _comps = st.session_state["helv_mp_comps"]
                _keys = sorted(_comps.keys())
                st.markdown("---")
                st.markdown("### 📊 Summary je Rebalancing")
                st.caption("**Universe (CH)** = alle qualifizierten CH-Titel (dedupliziert, inkl. Micro) · "
                           "**L+M+S** = davon in den drei Größenklassen (gesamt) · "
                           "**L/M/S** = Aufteilung auf Large/Mid/Small (Coverage-Segmente) · "
                           "**Aufrücker L/M/S** = via Kaskade nachgezogene Equity-Titel je Segment (Large/Mid/Small; "
                           "„–\" = keine). Turnover (Gehalten/Neu/Raus) bezieht sich auf den selektierten "
                           "55%-Teil (Equity + Real Estate); die 45% statisch (Cash/ETFs) sind konstant.")
                st.dataframe(st.session_state["helv_mp_summary"], width="stretch", hide_index=True)

                st.markdown("### 🔍 Termin-Detail")
                _pk = st.selectbox("Termin", _keys, index=len(_keys) - 1, key="helv_mp_pick")
                _cd = _comps[_pk].copy()
                _cd["Gewicht %"] = _cd["Index_Weight"].map(lambda x: f"{x:.4f}%")
                st.caption(f"Helvetica am **{_pk}** — Gesamtgewicht {_comps[_pk]['Index_Weight'].sum():.2f}%")
                st.dataframe(
                    _cd[[c for c in ["Sleeve", "Type", "Exchange Ticker", "Name", "Mapping Country",
                                     "FactSet Industry", "Gewicht %"] if c in _cd.columns]],
                    width="stretch", hide_index=True, height=600)

                # Swiss Size Sub-Indizes für diesen Termin (cap-gewichtet, Variante B)
                _detail_export = {f"Helvetica {_pk}": _comps[_pk]}
                _subp = st.session_state.get("helv_mp_subs", {}).get(_pk, {})
                if _subp:
                    st.markdown(f"**🇨🇭 Swiss Size Sub-Indizes am {_pk}** "
                                "(Float-MCap-gewichtet, alle Share Lines; ✓ = von Helvetica selektiert):")
                    _hisin = set(_norm_isin(_comps[_pk][_comps[_pk]["Type"] == "Equity"]["ISIN"]))
                    _c3 = st.columns(3)
                    for _i, _seg in enumerate(["Large Cap", "Mid Cap", "Small Cap"]):
                        _sdf = _subp.get(_seg)
                        with _c3[_i]:
                            if _sdf is None or len(_sdf) == 0:
                                st.caption(f"{_seg}: –"); continue
                            st.caption(f"{_seg}: {len(_sdf)} Linien / {_sdf['Entity ID'].nunique()} Firmen")
                            _t = _sdf.copy()
                            _t["✓"] = np.where(_norm_isin(_t["ISIN"]).isin(_hisin), "✓", "")
                            _t["Gew %"] = _t["Index_Weight"].map(lambda x: f"{x:.2f}")
                            st.dataframe(_t[["✓", "Exchange Ticker", "Gew %"]], width="stretch",
                                         hide_index=True, height=260)
                        _detail_export[f"Swiss {_seg}"] = _sdf
                st.download_button(
                    f"⬇️ Termin-Detail {_pk} herunterladen (Excel)",
                    data=to_excel_multi(_detail_export),
                    file_name=f"Helvetica_Composition_{_pk.replace('-', '')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="helv_mp_dl_detail")

                _long = pd.concat(
                    [_comps[k][["Exchange Ticker", "Name", "Sleeve", "Type", "Index_Weight"]].assign(Termin=k)
                     for k in _keys], ignore_index=True)
                # Pro TITEL pivotieren (nicht nach Sleeve) — sonst wird ein Titel, der über die Zeit das
                # Segment wechselt, in mehrere Zeilen gesplittet und das Gewicht "fehlt" scheinbar.
                _wide = _long.pivot_table(index=["Exchange Ticker", "Name"], columns="Termin",
                                          values="Index_Weight", aggfunc="first").reset_index()
                # Sleeve-Info = Sleeve in der jüngsten Periode, in der der Titel vorkommt
                _last_sleeve = _long.sort_values("Termin").groupby("Exchange Ticker")["Sleeve"].last()
                _wide.insert(2, "Sleeve (zuletzt)", _wide["Exchange Ticker"].map(_last_sleeve))
                st.markdown("### 📐 Gewichtsmatrix (Titel × Termin, %)")
                st.caption("Eine Zeile je Titel über alle Termine. Wechselt ein Titel das Segment, zeigt "
                           "„Sleeve (zuletzt)\" das jüngste Segment; die Gewichte stehen lückenlos in der Zeile.")
                st.dataframe(_wide, width="stretch", hide_index=True)

                st.download_button(
                    "⬇️ Helvetica Multi-Period Export (Excel)",
                    data=to_excel_multi({"Summary": st.session_state["helv_mp_summary"],
                                         "Long": _long, "Weight Matrix": _wide}),
                    file_name=f"Helvetica_MultiPeriod_{_keys[0]}_to_{_keys[-1]}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="helv_mp_dl")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7: Multi-Period Run
# ══════════════════════════════════════════════════════════════════════════════
with tab_multi:
    st.markdown("## 🔁 Multi-Period Run")

    if data_mode != "Master File (Multi-Period)":
        st.info("ℹ️ Dieser Tab erfordert den **Master File (Multi-Period)** Modus. "
                "Bitte oben in der Sidebar umschalten und ein Master-File hochladen.")
    elif master_data is None:
        st.warning("⚠️ Bitte zuerst ein Master-File in der Sidebar hochladen.")
    else:
        _detected_dates = master_data["detected_dates"]
        st.caption(f"Master-File: **{len(_detected_dates)}** Selection Dates erkannt "
                   f"({_detected_dates[0]} bis {_detected_dates[-1]})")

        # Range-Picker
        _mr1, _mr2 = st.columns(2)
        with _mr1:
            start_iso = st.selectbox("Start-Periode (Seed)",
                                      options=_detected_dates,
                                      index=0,
                                      key="multi_start",
                                      help="Erste Periode des Multi-Period-Laufs. "
                                           "Hier gibt es noch keine Incumbents (Seed-Period) — "
                                           "alle Stocks durchlaufen Entry-Schwellen.")
        with _mr2:
            _end_default_idx = len(_detected_dates) - 1
            end_iso = st.selectbox("End-Periode",
                                    options=_detected_dates,
                                    index=_end_default_idx,
                                    key="multi_end",
                                    help="Letzte Periode des Multi-Period-Laufs.")

        # Validate range
        _periods_to_run = [d for d in _detected_dates if start_iso <= d <= end_iso]
        if not _periods_to_run:
            st.error("❌ Ungültiger Date-Range.")
        else:
            st.caption(f"📅 Geplante Periods im Lauf: **{len(_periods_to_run)}** "
                       f"({_periods_to_run[0]} → {_periods_to_run[-1]})")

            # Index-Selektion: welche Produkte der NaroIX Index Series berechnen?
            _code_options = [ix["code"] for ix in INDEX_SERIES]
            indices_to_run = st.multiselect(
                "Welche Indizes berechnen?",
                options=_code_options,
                default=["NX-GM-LM"],
                format_func=lambda c: f"{c} · {INDEX_BY_CODE[c]['name']}",
                key="multi_indices_codes",
                help="Option Y: pro Periode läuft die Pipeline EINMAL (globaler Buffer-State); "
                     "die gewählten Produkte sind konsistente Slices davon (build_index)."
            )

            run_btn = st.button("▶️ Multi-Period Run starten", type="primary", key="multi_run_btn",
                                 disabled=(len(indices_to_run) == 0))

            if run_btn:
                # Option Y: EIN globaler Pipeline-Lauf pro Periode; die gewählten Produkte
                # sind konsistente build_index-Slices davon. Buffer-Incumbents global
                # (= investierbares Universe L+M+S der Vorperiode) → ein Titel hat genau
                # EINE Size-Klasse über alle Produkte hinweg.
                results_per_index = {code: {} for code in indices_to_run}   # {code: {sd_iso: constituents}}
                prev_isin = set()                                   # globaler Membership-Incumbent-State
                prev_seg = {}                                       # globaler {ISIN: Segment} für Size Buffer
                prev_prod_isin = {code: set() for code in indices_to_run}   # je Produkt (Turnover-Stats)
                prev_prod_ckey = {code: set() for code in indices_to_run}   # je Produkt: Vorperioden-Company-Keys (Rang-Band-Buffer)
                _eumss_by_period = {}
                summary_rows = []

                progress = st.progress(0, text="Starte Multi-Period-Lauf...")
                _total = len(_periods_to_run)

                for _pi, sd_iso in enumerate(_periods_to_run):
                    progress.progress(_pi / max(_total, 1), text=f"Period {sd_iso} ({_pi+1}/{_total})")
                    sd_dt = pd.Timestamp(sd_iso).date()
                    _country_cls = get_classification_dict(hc_df, sd_dt)
                    _china_if_period = float(china_if_map.get(sd_dt, 0.20))
                    df_snapshot = build_snapshot_from_master(master_data, sd_iso)
                    is_seed = (len(prev_isin) == 0)

                    # EIN Pipeline-Lauf pro Periode mit globalem Incumbent-State
                    result = run_selection_pipeline(
                        df_snapshot.copy(), _country_cls, _china_if_period, sd_dt.year,
                        thailand_sec_type, max_closing_price,
                        exclude_hk_cny, exclude_country_risk_na,
                        exclude_naics_funds, exclude_euro_mtf, exclude_etf_sicav,
                        large_thr, mid_thr, small_thr, min_ff_pct, new_eumss_ff_ratio,
                        new_adtv_dm, new_adtv_em, new_atvr_dm, new_atvr_em,
                        fol_matrix, fol_sector_fb, apply_fol,
                        if_cum_col, atvr_mcap_col,
                        incumbents_isin=prev_isin,
                        apply_buffer=apply_buffer and not is_seed,
                        buffer_min_ff=buffer_min_ff, buffer_coverage=buffer_coverage,
                        buffer_adtv_dm=buffer_adtv_dm, buffer_adtv_em=buffer_adtv_em,
                        buffer_atvr_dm=buffer_atvr_dm, buffer_atvr_em=buffer_atvr_em,
                        apply_size_buffer=apply_size_buffer and not is_seed,
                        incumbent_segments=prev_seg, size_buffer_pp=size_buffer_pp,
                        ineligible_df=ineligible_df,
                        apply_ineligible=apply_ineligible,
                        selection_date=sd_dt,
                        label_before_liquidity=label_before_liquidity,
                    )
                    _gmc = result["gm_complete"]
                    _eumss_by_period[sd_iso] = (float(result.get("eumss_full") or 0.0),
                                                float(result.get("eumss_ff") or 0.0))

                    # Produkte = konsistente Slices desselben Laufs (build_index)
                    for code in indices_to_run:
                        _ix = INDEX_BY_CODE[code]
                        # Rang-Band-Buffer für Fixed-Count-Produkte: nur wenn Buffer aktiv,
                        # nicht in der Seed-Periode, und das Produkt buffer_hard definiert.
                        _use_rank_buf = bool(apply_buffer and not is_seed and _ix.get("buffer_hard"))
                        cons = build_index(_gmc, _ix["region"], _ix["segments"],
                                           industries=_ix.get("industries"), top_n=_ix.get("top_n"),
                                           incumbents_isin=(prev_prod_ckey[code] if _use_rank_buf else None),
                                           buffer_hard=_ix.get("buffer_hard"), buffer_exit=_ix.get("buffer_exit"))
                        results_per_index[code][sd_iso] = cons
                        # Company-Keys dieser Periode merken (für den Rang-Band-Buffer nächste Periode)
                        if _ix.get("buffer_hard"):
                            _ck = cons.get("Entity ID")
                            if _ck is not None:
                                _ck = _ck.fillna("").astype(str).str.strip()
                                _ck = _ck.where(_ck != "", _norm_isin(cons["ISIN"]))
                                prev_prod_ckey[code] = set(_ck) - {""}

                        cur = set(cons["ISIN"].dropna().astype(str).str.strip().str.upper())
                        prev = prev_prod_isin[code]
                        _held = (int(cons["Size_Buffer_Held"].fillna(False).sum())
                                 if "Size_Buffer_Held" in cons.columns else 0)
                        _kept_std = (int(cons["Kept_In_Standard_By_Buffer"].fillna(False).sum())
                                     if "Kept_In_Standard_By_Buffer" in cons.columns else 0)
                        summary_rows.append({
                            "Selection Date": sd_iso,
                            "Index": _ix["name"],
                            "Konstituenten": len(cons),
                            "Incumbents (Vorperiode)": len(prev),
                            "Davon gehalten": len(cur & prev),
                            "Davon aus Index gefallen": len(prev - cur),
                            "Neueinsteiger": len(cur - prev),
                            "Buffer-Saldo": (f"+{len(cur - prev)} / -{len(prev - cur)}") if not is_seed else "Seed",
                            "Index-Größe Δ": len(cur) - len(prev) if not is_seed else "—",
                            "Held by Size Buffer": _held if (apply_size_buffer and not is_seed) else ("Seed" if is_seed else 0),
                            "Kept in Standard (Buffer)": _kept_std if not is_seed else "Seed",
                        })
                        prev_prod_isin[code] = cur

                    # Globalen Incumbent-State weiterreichen: investierbares Universe (L+M+S)
                    _inv = _gmc[_gmc["Segment_New"].isin(["Large Cap", "Mid Cap", "Small Cap"])]
                    _inv_isin = _norm_isin(_inv["ISIN"])
                    prev_isin = set(_inv_isin)
                    prev_seg = {i: s for i, s in zip(_inv_isin.values, _inv["Segment_New"].values) if i}

                progress.progress(1.0, text=f"✅ Fertig: {_total} Perioden × {len(indices_to_run)} Produkte.")

                # Save to session state for export & display
                st.session_state["multi_results"] = results_per_index
                st.session_state["multi_eumss"] = _eumss_by_period
                _summary_df_run = pd.DataFrame(summary_rows)
                st.session_state["multi_summary"] = _summary_df_run
                # Detail-Ansicht nach jedem Lauf auf die letzte Periode defaulten
                # (Widget-Key persistiert sonst eine alte Auswahl und ignoriert index=).
                st.session_state["multi_detail_period"] = _periods_to_run[-1]

                # ── Schwere Export-Artefakte EINMALIG bauen (nicht bei jedem Rerun) ──
                # Long Format: EIN Sheet pro Produkt, alle Perioden gestapelt (Spalte
                # "Selection Date") statt 1 Sheet je Produkt×Periode → keine Sheet-Explosion.
                _sheets_long = {"Summary": _summary_df_run}
                _long_cols = ["Selection Date", "Exchange Ticker", "Name", "ISIN", "Entity ID",
                              "Classification", "Mapping Country", "Exchange Country Name",
                              "Segment_New", "Size_Buffer_Held", "Free Float Percent",
                              "Total MCap Y2025", "Share MCap Y2025", "Free Float MCap Y2025",
                              "FOL_Value", "IF", "Adj_FF_MCap", "IF_Source", "Index_Weight"]
                for _idx_name, _period_dict in results_per_index.items():
                    _parts = []
                    for _sd, _df in _period_dict.items():
                        _p = _df.copy()
                        _p.insert(0, "Selection Date", _sd)
                        _parts.append(_p)
                    if not _parts:
                        continue
                    _stacked = pd.concat(_parts, ignore_index=True)
                    _cols = [c for c in _long_cols if c in _stacked.columns]
                    _sheets_long[_idx_name[:31]] = _stacked[_cols].sort_values(
                        ["Selection Date", "Index_Weight"], ascending=[True, False]).reset_index(drop=True)

                # Wide Format (vektorisiert): Gewichtsmatrix pro Index
                _wide_by_idx = {}
                _sheets_wide = {"Summary": _summary_df_run}
                for _idx_name, _period_dict in results_per_index.items():
                    _wide, _pp = build_wide_matrix(_period_dict)
                    if _wide is None or _wide.empty:
                        continue
                    _wide_by_idx[_idx_name] = _wide
                    _sheets_wide[_idx_name[:31]] = _wide

                # Segment-Wanderung (vektorisiert): Segment×Periode-Matrix pro Index
                _segmat_by_idx = {}
                _sheets_seg = {"Summary": _summary_df_run}
                for _idx_name, _period_dict in results_per_index.items():
                    _seg, _spp = build_segment_matrix(_period_dict)
                    if _seg is None or _seg.empty:
                        continue
                    _segmat_by_idx[_idx_name] = _seg
                    _sheets_seg[_idx_name[:31]] = _seg

                st.session_state["multi_wide"] = _wide_by_idx
                st.session_state["multi_segmatrix"] = _segmat_by_idx
                st.session_state["multi_export_long_bytes"] = to_excel_multi(_sheets_long)
                st.session_state["multi_export_wide_bytes"] = to_excel_multi(_sheets_wide)
                st.session_state["multi_export_seg_bytes"] = to_excel_multi(_sheets_seg)

            # Display Results (if available)
            if "multi_results" in st.session_state:
                _summary_df = st.session_state["multi_summary"]
                _results = st.session_state["multi_results"]

                st.markdown("---")
                st.markdown("### 📊 Multi-Period Summary")
                st.dataframe(_summary_df, width='stretch', hide_index=True)

                # Detail-Picker pro Period+Index
                st.markdown("### 🔍 Detail-Ansicht")
                _di1, _di2 = st.columns(2)
                with _di1:
                    _sel_idx = st.selectbox("Index",
                                              options=list(_results.keys()),
                                              format_func=lambda c: INDEX_BY_CODE.get(c, {}).get("name", c),
                                              key="multi_detail_idx2")
                _sel_name = INDEX_BY_CODE.get(_sel_idx, {}).get("name", _sel_idx)
                with _di2:
                    _det_periods = sorted(_results[_sel_idx].keys())
                    # Default = letzte Periode; persistierten/ungültigen State auf letzte korrigieren
                    if st.session_state.get("multi_detail_period") not in _det_periods:
                        st.session_state["multi_detail_period"] = _det_periods[-1]
                    _sel_period = st.selectbox("Period",
                                                 options=_det_periods,
                                                 key="multi_detail_period")

                if _sel_idx and _sel_period:
                    _det = _results[_sel_idx][_sel_period]
                    st.caption(f"**{_sel_name}** am **{_sel_period}** — {len(_det)} Konstituenten, "
                               f"FF MCap total: {format_bn(_det['Free Float MCap Y2025'].sum())}, "
                               f"Adj. FF MCap: {format_bn(_det['Adj_FF_MCap'].sum())}")

                    _show_cols = [c for c in [
                        "Exchange Ticker", "Name", "ISIN", "Classification", "Mapping Country",
                        "Segment_New", "Free Float Percent", "Total MCap Y2025",
                        "Share MCap Y2025", "Free Float MCap Y2025", "FOL_Value", "IF", "Adj_FF_MCap", "Index_Weight"
                    ] if c in _det.columns]
                    _det_show = clean_export_cols(with_fol_breakdown(
                        _det[_show_cols].sort_values("Index_Weight", ascending=False).reset_index(drop=True)))
                    st.dataframe(_det_show.head(50), width='stretch', hide_index=True)
                    if len(_det) > 50:
                        st.caption(f"… {len(_det)-50} weitere — vollständig im Excel-Export verfügbar.")
                    st.download_button(
                        "📥 Detail-Ansicht herunterladen (alle Konstituenten)",
                        data=to_excel_one(_det_show, "Constituents"),
                        file_name=f"{_sel_idx}_{_sel_period}_constituents.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_detail",
                    )

                    # ── DM/EM Country Breakdown + Gewicht-Chart (GIMI-Stil) für die gewählte Periode ──
                    st.markdown("---")

                    def _country_table_mp(df_cls, cls_adj):
                        ct = df_cls.groupby(df_cls["Mapping Country"].fillna("—")).agg(
                            Stocks=("Symbol", "count"),
                            FF_MCap=("Free Float MCap Y2025", "sum"),
                            Adj_MCap=("Adj_FF_MCap", "sum"),
                            Avg_MCap=("Adj_FF_MCap", "mean"),
                        ).reset_index().sort_values("Adj_MCap", ascending=False)
                        ct["FF MCap"] = ct["FF_MCap"].apply(format_bn)
                        ct["Avg Adj. MCap"] = ct["Avg_MCap"].apply(format_bn)
                        ct["Weight %"] = ((ct["Adj_MCap"] / cls_adj * 100).apply(lambda x: f"{x:.2f}%")
                                          if cls_adj > 0 else "—")
                        return ct[["Mapping Country", "Stocks", "FF MCap", "Avg Adj. MCap", "Weight %"]].rename(
                            columns={"Mapping Country": "Land"})

                    _dm_sel = _det[_det["Classification"] == "DM"]
                    _em_sel = _det[_det["Classification"] == "EM"]
                    st.caption(f"**Country Breakdown — {_sel_name} am {_sel_period}** · "
                               f"{len(_dm_sel)} DM / {len(_em_sel)} EM · Weight % je relativ zur eigenen DM-/EM-Gruppe")
                    _ccp1, _ccp2 = st.columns(2)
                    with _ccp1:
                        st.markdown(f"**DM Country Breakdown ({len(_dm_sel):,} Stocks)**")
                        st.dataframe(_country_table_mp(_dm_sel, _dm_sel["Adj_FF_MCap"].sum()),
                                     width='stretch', hide_index=True)
                    with _ccp2:
                        st.markdown(f"**EM Country Breakdown ({len(_em_sel):,} Stocks)**")
                        st.dataframe(_country_table_mp(_em_sel, _em_sel["Adj_FF_MCap"].sum()),
                                     width='stretch', hide_index=True)

                    st.markdown("**Nach Gewicht (Adj. FF MCap %)** — Anteil am Index")
                    _tot_adj = _det["Adj_FF_MCap"].sum()
                    if _tot_adj > 0:
                        _gw1, _gw2 = st.columns(2)
                        with _gw1:
                            st.markdown("**Nach Land**")
                            _byw = _det.groupby("Mapping Country").agg(Adj=("Adj_FF_MCap", "sum")).reset_index()
                            _byw["Weight%"] = (_byw["Adj"] / _tot_adj * 100).round(2)
                            _byw = _byw.sort_values("Adj", ascending=False)
                            _top30 = _byw.head(30)
                            _rest = _byw.iloc[30:]
                            if len(_rest):
                                _top30 = pd.concat([pd.DataFrame([{"Mapping Country": f"Others ({len(_rest)})",
                                    "Adj": _rest["Adj"].sum(), "Weight%": _rest["Weight%"].sum()}]), _top30])
                            _top30 = _top30.sort_values("Adj", ascending=True)
                            _figw = go.Figure(go.Bar(x=_top30["Weight%"], y=_top30["Mapping Country"],
                                orientation="h", marker_color="#ce93d8",
                                text=_top30["Weight%"].apply(lambda x: f"{x:.2f}%"), textposition="outside"))
                            _figw.update_layout(template="plotly_dark", paper_bgcolor="#0f1117", plot_bgcolor="#161b27",
                                height=700, margin=dict(t=10, b=10, l=10, r=60), xaxis=dict(showgrid=False))
                            st.plotly_chart(_figw, width='stretch')
                        with _gw2:
                            st.markdown("**Nach Sektor (FactSet Economy)**")
                            _sec = _det.get("FactSet Economy")
                            if _sec is None:
                                _sec = pd.Series(["—"] * len(_det), index=_det.index)
                            _secvals = _sec.fillna("—").astype(str).str.strip().replace("", "—")
                            _bys = (_det.assign(_Sector=_secvals)
                                        .groupby("_Sector").agg(Adj=("Adj_FF_MCap", "sum")).reset_index())
                            _bys["Weight%"] = (_bys["Adj"] / _tot_adj * 100).round(2)
                            _bys = _bys.sort_values("Adj", ascending=True)
                            _figs = go.Figure(go.Bar(x=_bys["Weight%"], y=_bys["_Sector"],
                                orientation="h", marker_color="#2979ff",
                                text=_bys["Weight%"].apply(lambda x: f"{x:.2f}%"), textposition="outside"))
                            _figs.update_layout(template="plotly_dark", paper_bgcolor="#0f1117", plot_bgcolor="#161b27",
                                height=470, margin=dict(t=10, b=10, l=10, r=60), xaxis=dict(showgrid=False))
                            st.plotly_chart(_figs, width='stretch')

                            # Kleiner DM/EM-Gesamtanteil als flacher Balken — rechte Spalte
                            # (Sektor + DM/EM) ergibt zusammen ~ die Höhe des Länder-Graphen links.
                            st.markdown("**DM vs EM (Gesamtanteil)**")
                            _dm_adj = _det.loc[_det["Classification"] == "DM", "Adj_FF_MCap"].sum()
                            _em_adj = _det.loc[_det["Classification"] == "EM", "Adj_FF_MCap"].sum()
                            _tot2 = _dm_adj + _em_adj
                            if _tot2 > 0:
                                _dm_w = round(_dm_adj / _tot2 * 100, 2)
                                _em_w = round(_em_adj / _tot2 * 100, 2)
                                _figd = go.Figure(go.Bar(
                                    x=[_em_w, _dm_w], y=["EM", "DM"], orientation="h",
                                    marker_color=["#ce93d8", "#2979ff"],
                                    text=[f"{_em_w:.2f}%", f"{_dm_w:.2f}%"], textposition="outside"))
                                _figd.update_layout(template="plotly_dark", paper_bgcolor="#0f1117", plot_bgcolor="#161b27",
                                    height=180, margin=dict(t=10, b=10, l=10, r=60),
                                    xaxis=dict(showgrid=False, range=[0, 100]))
                                st.plotly_chart(_figd, width='stretch')
                            else:
                                st.caption("Keine DM/EM-Daten für diese Periode.")
                    else:
                        st.caption("Keine Adj. FF MCap-Daten für diese Periode.")

                # ── Index Characteristics pro Periode ───────────────────────────
                # Wie das MSCI-Factsheet: Anzahl Konstituenten + Mkt-Cap-Kennzahlen
                # (Index/Largest/Smallest/Avg/Median) je MCap-Basis, plus DM/EM-Gewicht.
                # Für den in der Detail-Ansicht gewählten Index (_sel_idx).
                st.markdown("---")
                st.markdown(f"### 📋 Index Characteristics — {_sel_name}")
                st.caption("Mkt Cap (**Total MCap**) in **USD Millions** · DM/EM-Gewicht nach Adj. FF MCap · "
                           "**EUMSS Full/FF** = auf DM-Primary kalibrierte Schwellen (Total- bzw. FF-MCap), global angewandt")

                _ic_bases = [("Total", "Total MCap Y2025")]
                _ic_rows = []
                for _sd in sorted(_results[_sel_idx].keys()):
                    _c = _results[_sel_idx][_sd]
                    _adj = pd.to_numeric(_c.get("Adj_FF_MCap"), errors="coerce") if "Adj_FF_MCap" in _c.columns else pd.Series(dtype=float)
                    _adj_tot = float(_adj.sum())
                    _cls = _c["Classification"] if "Classification" in _c.columns else pd.Series([""] * len(_c), index=_c.index)
                    _dm_w = (_adj[_cls == "DM"].sum() / _adj_tot * 100) if _adj_tot > 0 else 0.0
                    _em_w = (_adj[_cls == "EM"].sum() / _adj_tot * 100) if _adj_tot > 0 else 0.0
                    _row = {"Selection Date": _sd, "# Const": len(_c),
                            "DM W%": f"{_dm_w:.2f}%", "EM W%": f"{_em_w:.2f}%"}
                    _eu = st.session_state.get("multi_eumss", {}).get(_sd)
                    _row["EUMSS Full"] = f"{_eu[0]/1e6:,.2f}" if _eu else "—"
                    _row["EUMSS FF"]   = f"{_eu[1]/1e6:,.2f}" if _eu else "—"
                    for _lbl, _col in _ic_bases:
                        _v = (pd.to_numeric(_c.get(_col), errors="coerce").dropna() / 1e6
                              if _col in _c.columns else pd.Series(dtype=float))
                        if len(_v):
                            _row[f"Index ({_lbl})"]    = f"{_v.sum():,.2f}"
                            _row[f"Largest ({_lbl})"]  = f"{_v.max():,.2f}"
                            _row[f"Smallest ({_lbl})"] = f"{_v.min():,.2f}"
                            _row[f"Avg ({_lbl})"]      = f"{_v.mean():,.2f}"
                            _row[f"Median ({_lbl})"]   = f"{_v.median():,.2f}"
                        else:
                            for _m in ("Index", "Largest", "Smallest", "Avg", "Median"):
                                _row[f"{_m} ({_lbl})"] = "—"
                    _ic_rows.append(_row)
                st.dataframe(pd.DataFrame(_ic_rows), width='stretch', hide_index=True)

                # Excel-Export — Artefakte wurden EINMALIG nach dem Lauf gebaut
                # (s. run_btn-Block) und liegen im Session-State. Hier nur noch
                # ausliefern → kein Neuaufbau bei jedem Widget-Klick/Rerun.
                st.markdown("---")
                st.markdown("### 💾 Multi-Period Export")

                if "multi_export_long_bytes" in st.session_state:
                    st.download_button(
                        "📥 Konstituenten (Long Format — 1 Sheet/Produkt, alle Perioden)",
                        data=st.session_state["multi_export_long_bytes"],
                        file_name=f"NaroIX_MultiPeriod_Long_{_periods_to_run[0]}_to_{_periods_to_run[-1]}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                # ── Gewichtsmatrix (Wide Format) ──
                st.markdown("---")
                st.markdown("### 📐 Gewichtsmatrix — alle Konstituenten × alle Perioden")
                st.caption("Zeile = Aktie | Spalte = Selection Date | Wert = Indexgewicht (%) | Leer = nicht im Index "
                           "| **Segment = Stand der zuletzt vorhandenen Periode**")

                _wide_by_idx = st.session_state.get("multi_wide", {})
                # Datumsspalten robust per Muster (YYYY-MM-DD) erkennen — NICHT per
                # Ausschluss einer Statik-Liste (das bricht bei Spalten-Umbenennung
                # oder veraltetem session_state, siehe Symbol→Exchange-Ticker-Wechsel).
                _date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")

                if _wide_by_idx:
                    _first_idx = list(_wide_by_idx.keys())[0]
                    wide_df = _wide_by_idx[_first_idx]
                    date_cols = sorted(c for c in wide_df.columns
                                       if isinstance(c, str) and _date_re.match(c))

                    n_always   = int(wide_df[date_cols].notna().all(axis=1).sum())
                    _first_col = wide_df[date_cols].iloc[:, 0].notna()
                    _last_col  = wide_df[date_cols].iloc[:, -1].notna()
                    n_newcomer = int((_last_col & ~_first_col).sum())
                    n_dropout  = int((_first_col & ~_last_col).sum())
                    n_total    = len(wide_df)

                    st.markdown(f"**{_first_idx}** — {n_total} einzigartige Aktien über alle Perioden")
                    _m1, _m2, _m3, _m4, _m5 = st.columns(5)
                    _m1.metric("Immer im Index", n_always,
                               help="Stocks die in JEDER Period im Index waren.")
                    _m2.metric("Newcomer", n_newcomer,
                               help="Stocks die in der ersten Period nicht im Index waren, in der letzten aber schon.")
                    _m3.metric("Drop-Outs", n_dropout,
                               help="Stocks die in der ersten Period im Index waren, in der letzten aber nicht mehr.")
                    _m4.metric("Zeitweise dabei", n_total - n_always,
                               help="Stocks die mindestens eine Period im Index waren, aber nicht alle. "
                                    "Umfasst Newcomer, Drop-Outs und Stocks die zwischendurch rein/raus gingen.")
                    _m5.metric("Periods im Lauf", len(date_cols))

                    # Vorschau-Tabelle (Top 50 nach letztem Gewicht)
                    st.dataframe(
                        wide_df.head(50).style.format(
                            {sd: (lambda x: f"{x:.4f}%" if pd.notna(x) and x > 0 else ("" if pd.isna(x) else "0.0000%"))
                             for sd in date_cols},
                            na_rep=""
                        ),
                        width='stretch', hide_index=True
                    )
                    if n_total > 50:
                        st.caption(f"… {n_total-50} weitere Aktien im vollständigen Excel-Export.")

                if "multi_export_wide_bytes" in st.session_state:
                    st.download_button(
                        "📥 Gewichtsmatrix herunterladen (Wide Format)",
                        data=st.session_state["multi_export_wide_bytes"],
                        file_name=f"NaroIX_WeightMatrix_{_periods_to_run[0]}_to_{_periods_to_run[-1]}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                # ── Segment-Wanderung (Segment × Periode) ───────────────────────
                # Analog zur Gewichtsmatrix, aber die Zellen zeigen das Segment statt
                # des Gewichts → macht die Wanderung (Large↔Mid↔Small) über Zeit sichtbar.
                # Für den in der Detail-Ansicht gewählten Index (_sel_idx).
                st.markdown("---")
                st.markdown(f"### 🔀 Segment-Wanderung — {_sel_name}")
                st.caption("Zeile = Aktie | Spalte = Selection Date | Wert = Segment | Leer = nicht im Index "
                           "· Sortierung: meiste Segment-Wechsel zuerst")

                _seg_df = st.session_state.get("multi_segmatrix", {}).get(_sel_idx)
                if _seg_df is not None and not _seg_df.empty:
                    _seg_date_cols = sorted(c for c in _seg_df.columns
                                            if isinstance(c, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", c))
                    _seg_color = {"Large": "#2979ff", "Mid": "#00e676", "Small": "#ff9100", "Micro": "#37474f"}

                    def _style_segcell(v):
                        _c = _seg_color.get(v)
                        return f"background-color:{_c};color:#0b0b0b;font-weight:600" if _c else ""

                    st.dataframe(
                        _seg_df.head(50).style.map(_style_segcell, subset=_seg_date_cols).format(na_rep=""),
                        width='stretch', hide_index=True
                    )
                    if len(_seg_df) > 50:
                        st.caption(f"… {len(_seg_df)-50} weitere Aktien im vollständigen Excel-Export.")
                    if "multi_export_seg_bytes" in st.session_state:
                        st.download_button(
                            "📥 Segment-Wanderung herunterladen",
                            data=st.session_state["multi_export_seg_bytes"],
                            file_name=f"NaroIX_SegmentMatrix_{_periods_to_run[0]}_to_{_periods_to_run[-1]}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                else:
                    st.caption("Keine Segment-Daten für diesen Index verfügbar.")

                # ── Country-Gewichte über Zeit (Land × Periode) ─────────────────
                # Für den oben in der Detail-Ansicht gewählten Index (_sel_idx).
                # Ländergewicht = Summe Index_Weight (bereits in %, pro Index-Scope
                # auf 100 normiert). Zeigt die Entwicklung der Ländergewichte über alle Perioden.
                st.markdown("---")
                st.markdown(f"### 🌍 Country-Gewichte über Zeit — {_sel_name}")

                _cb_periods = sorted(_results[_sel_idx].keys())
                _cb_matrix = {}  # land -> {period_iso: weight%}
                for _sd in _cb_periods:
                    _dfp = _results[_sel_idx][_sd]
                    if "Mapping Country" not in _dfp.columns or "Index_Weight" not in _dfp.columns:
                        continue
                    _gp = _dfp.groupby(_dfp["Mapping Country"].fillna("—"))["Index_Weight"].sum()
                    for _land, _w in _gp.items():
                        _cb_matrix.setdefault(_land, {})[_sd] = round(float(_w), 4)

                if _cb_matrix:
                    _cb_rows = []
                    for _land, _wmap in _cb_matrix.items():
                        _row = {"Land": _land}
                        for _sd in _cb_periods:
                            _row[_sd] = _wmap.get(_sd)
                        _cb_rows.append(_row)
                    _cb_df = pd.DataFrame(_cb_rows).sort_values(
                        _cb_periods[-1], ascending=False, na_position="last"
                    ).reset_index(drop=True)

                    st.caption("Zeile = Land | Spalte = Selection Date | Wert = Ländergewicht in % | Leer = nicht im Index")
                    st.dataframe(
                        _cb_df.style.format(
                            {sd: (lambda x: f"{x:.2f}%" if pd.notna(x) else "") for sd in _cb_periods},
                            na_rep="",
                        ),
                        width='stretch', hide_index=True,
                    )
                    st.download_button(
                        "📥 Country-Gewichte herunterladen",
                        data=to_excel_one(_cb_df, "Country_x_Period"),
                        file_name=f"{_sel_idx}_country_weights_by_period.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_country",
                    )
                else:
                    st.caption("Keine Länder-Daten für diesen Index verfügbar.")

                # ── Sector-Gewichte über Zeit (Sektor × Periode) ────────────────
                # Analog zur Länder-Matrix, aber nach FactSet Economy → Sektor-Drift.
                st.markdown(f"### 🏭 Sector-Gewichte über Zeit — {_sel_name}")
                _sec_matrix = {}  # sektor -> {period_iso: weight%}
                for _sd in _cb_periods:
                    _dfp = _results[_sel_idx][_sd]
                    if "FactSet Economy" not in _dfp.columns or "Index_Weight" not in _dfp.columns:
                        continue
                    _secv = _dfp["FactSet Economy"].fillna("—").astype(str).str.strip().replace("", "—")
                    _gp = _dfp.assign(_S=_secv).groupby("_S")["Index_Weight"].sum()
                    for _s, _w in _gp.items():
                        _sec_matrix.setdefault(_s, {})[_sd] = round(float(_w), 4)

                if _sec_matrix:
                    _sec_rows = []
                    for _s, _wmap in _sec_matrix.items():
                        _row = {"Sektor": _s}
                        for _sd in _cb_periods:
                            _row[_sd] = _wmap.get(_sd)
                        _sec_rows.append(_row)
                    _sec_df = pd.DataFrame(_sec_rows).sort_values(
                        _cb_periods[-1], ascending=False, na_position="last").reset_index(drop=True)
                    st.caption("Zeile = Sektor (FactSet Economy) | Spalte = Selection Date | Wert = Sektorgewicht in %")
                    st.dataframe(
                        _sec_df.style.format(
                            {sd: (lambda x: f"{x:.2f}%" if pd.notna(x) else "") for sd in _cb_periods},
                            na_rep=""),
                        width='stretch', hide_index=True,
                        height=35 * (len(_sec_df) + 1) + 3)   # alle Sektoren ohne Scroll
                    st.download_button(
                        "📥 Sector-Gewichte herunterladen",
                        data=to_excel_one(_sec_df, "Sector_x_Period"),
                        file_name=f"{_sel_idx}_sector_weights_by_period.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_sector",
                    )
                else:
                    st.caption("Keine Sektor-Daten für diesen Index verfügbar.")

                # ── Tenure — längste Verweildauer im Index ──────────────────────
                st.markdown("---")
                st.markdown(f"### 🏅 Tenure — längste Verweildauer im Index ({_sel_name})")
                _wdf_t = st.session_state.get("multi_wide", {}).get(_sel_idx)
                if _wdf_t is not None and not _wdf_t.empty:
                    _tdate = sorted(c for c in _wdf_t.columns
                                    if isinstance(c, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", c))
                    _ntot = len(_tdate)

                    def _streak(vals):
                        best = cur = 0
                        for v in vals:
                            if pd.notna(v):
                                cur += 1; best = max(best, cur)
                            else:
                                cur = 0
                        return best

                    _present = _wdf_t[_tdate].notna().sum(axis=1)
                    _longest = _wdf_t[_tdate].apply(lambda r: _streak(r.values), axis=1)
                    _tcols = [c for c in ["Exchange Ticker", "Name", "ISIN", "Classification", "Mapping Country"]
                              if c in _wdf_t.columns]
                    _ten = _wdf_t[_tcols].copy()
                    _ten["Perioden im Index"] = _present.astype(int).astype(str) + f" / {_ntot}"
                    _ten["Längste Serie"] = _longest.astype(int)
                    _ten["Aktuell drin"] = _wdf_t[_tdate[-1]].notna().map({True: "✓", False: ""}) if _tdate else ""
                    _ten = (_ten.assign(_p=_present.values, _l=_longest.values)
                                .sort_values(["_p", "_l"], ascending=[False, False])
                                .drop(columns=["_p", "_l"]))
                    st.caption(f"Sortiert nach Perioden im Index (von {_ntot}), dann längster ununterbrochener Serie. Top 50.")
                    st.dataframe(_ten.head(50), width='stretch', hide_index=True)
                    if len(_ten) > 50:
                        st.caption(f"… {len(_ten)-50} weitere — alle im Excel-Export.")
                    st.download_button(
                        "📥 Tenure herunterladen (alle Titel)",
                        data=to_excel_one(_ten.reset_index(drop=True), "Tenure"),
                        file_name=f"{_sel_idx}_tenure.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_tenure",
                    )
                else:
                    st.caption("Keine Matrix-Daten für diesen Index verfügbar.")
