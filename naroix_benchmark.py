import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from auth import require_login

# ─── Helper functions ──────────────────────────────────────────────────────────
def format_bn(val):
    if val >= 1e12: return f"{val/1e12:.2f}T"
    if val >= 1e9:  return f"{val/1e9:.2f}B"
    if val >= 1e6:  return f"{val/1e6:.2f}M"
    return f"{val:.0f}"

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NaroIX Benchmark Series",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Auth ──────────────────────────────────────────────────────────────────────
_github_user = require_login()

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

def to_excel_download(df, sheet_name="Index"):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buf.getvalue()


def to_excel_multi(sheets: dict):
    """Export multiple DataFrames as sheets. sheets = {sheet_name: df}"""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return buf.getvalue()


def normalize_index_weight(df, adj_col="Adj_FF_MCap"):
    """Recalculate Index_Weight based on the sheet's own Adj_FF_MCap total, sorted descending."""
    df = df.copy()
    tot = df[adj_col].sum() if adj_col in df.columns else 0
    if tot > 0:
        df["Index_Weight"] = df[adj_col] / tot * 100
    else:
        df["Index_Weight"] = 0.0
    return df.sort_values("Index_Weight", ascending=False)


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


# ─── FOL Matrix Country Code Mapping ─────────────────────────────────────────
# FactSet "Exchange Country Name" (UPPERCASE) → ISO2 wie in der YAML.
# Nur Länder mit FOL-Einträgen in der Matrix. Nicht-gelistete Länder → IF=1.0.
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
}



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


@st.cache_data
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


# ═══════════════════════════════════════════════════════════════════════════
# FOL MATRIX (Foreign Ownership Limits per country/sector/industry/year)
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data
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

    candidates_rel = [
        "Historical FOL Register/NaroIX_FOL_Master_Aggregated.yaml",
        "Historical_FOL_Register/NaroIX_FOL_Master_Aggregated.yaml",
        "NaroIX_FOL_Master_Aggregated.yaml",
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
            fol_matrix[yr_int][cc] = {
                "default_fol": float(cd.get("default_fol", 1.0)),
                "investability_status": cd.get("investability_status", "investable"),
                "country_name": cd.get("country_name", cc),
                "industries": industries_lookup,
            }

    return fol_matrix, version, debug_info


@st.cache_data
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


def _resolve_fol_row(ecn_upper, sector, industry, year, fol_matrix, sector_fallback):
    """Returns (fol_value, source_label) for a single stock.

    Fallback-Kette:
      1. Industry-Match → "Industry"
      2. Sector-Fallback (strengster Industry-Wert im Sector) → "Sector (strengster)"
      3. default_fol des Landes → "Country Default"
      4. 1.0 → "Kein FOL-Mapping"
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

    # Industry-Match
    ind_match = cdata["industries"].get((sector, industry))
    if ind_match is not None:
        return ind_match["fol_automatic"], "Industry"

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

    fol_values = []
    sources = []
    for i in range(len(df)):
        fol_v, src = _resolve_fol_row(ecn.iloc[i], sectors.iloc[i], industries.iloc[i],
                                       year, fol_matrix, sector_fallback)
        fol_values.append(fol_v)
        sources.append(src)

    df["FOL_Value"] = fol_values
    df["IF_Source"] = sources

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
    """Build clean Primary-only universe with Thailand mode handling."""
    import re as _re
    df = df_raw_orig.copy()
    for col in ["Total MCap Y2025","Free Float MCap Y2025","Free Float Percent",
                "1M ADTV Y2025","3M ADTV Y2025","6M ADTV Y2025","12M ADTV Y2025","Closing Price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

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

    # Step 2: Primary only (NVDRs in SHARE→NVDR mode are already Secondary but included)
    _th_remaining = df["Exchange Name"].fillna("").str.upper() == "THAILAND"
    df = df[(df["Listing"].fillna("") == "Primary") | _th_remaining].copy()

    # Step 3: Exclusions
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
        df = df[df["Listing Status"].fillna("0").astype(str).str.strip() != "1"].copy()

    # Step 4: Classification
    df["Mapping Country"] = df.apply(
        lambda r: r["Country of Incorp"] if r.get("Exchange Country Name","") == r.get("Country of Incorp","")
                  else r.get("Country of Risk",""), axis=1)
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


def apply_liquidity_new(df, adtv_dm, adtv_em, atvr_dm, atvr_em):
    """Apply ADTV + ATVR filter."""
    mask = ((df["Classification"]=="DM") &
            (df["3M ADTV Y2025"]>=adtv_dm) &
            (df["6M ADTV Y2025"]>=adtv_dm) &
            (df["ATVR"]>=atvr_dm)) | \
           ((df["Classification"]=="EM") &
            (df["3M ADTV Y2025"]>=adtv_em) &
            (df["6M ADTV Y2025"]>=adtv_em) &
            (df["ATVR"]>=atvr_em))
    return df[mask].copy()


def assign_segments_new(df, large_pct, mid_pct, small_pct, group_col="Mapping Country",
                        sort_col="Total MCap Y2025", cum_col="Adj_FF_MCap"):
    """Assign Large/Mid/Small/Micro Cap segments per group.
    Sort on sort_col (Total MCap), cumulative on cum_col (Adj_FF_MCap) — MSCI-konform.
    """
    results = []
    for grp_val, grp in df.groupby(group_col):
        grp = grp.sort_values(sort_col, ascending=False).copy()
        total = grp[cum_col].sum()
        if total == 0:
            grp["Segment_New"] = "Micro Cap"
            results.append(grp)
            continue
        grp["_cum_pct"] = grp[cum_col].cumsum() / total * 100
        grp["Segment_New"] = np.where(grp["_cum_pct"] <= large_pct, "Large Cap",
                             np.where(grp["_cum_pct"] <= mid_pct,   "Mid Cap",
                             np.where(grp["_cum_pct"] <= small_pct, "Small Cap", "Micro Cap")))
        results.append(grp)
    return pd.concat(results, ignore_index=True)


def add_secondary_listings(df_selected, df_raw_orig, adtv_dm, adtv_em, atvr_dm, atvr_em,
                             max_price, thailand_mode, china_if,
                             min_ff_pct=0.15, atvr_mcap_col="Free Float MCap Y2025",
                             excl_hk_cny=True,
                             fol_matrix=None, fol_sector_fb=None, fol_year=None, fol_enabled=True):
    """Add secondary share classes for selected entities.
    Secondaries must pass the same liquidity, FF% and price checks as primaries.
    """
    selected_entities = set(df_selected["Entity ID"].dropna().unique())
    df_sec = df_raw_orig[
        (df_raw_orig["Listing"].fillna("") == "Secondary") &
        (df_raw_orig["Entity ID"].isin(selected_entities))
    ].copy()

    # Thailand handling in secondary listings
    _th = df_sec["Exchange Name"].fillna("").str.upper() == "THAILAND"
    if thailand_mode == "NVDR only":
        # Exclude Thai SHAREs from secondaries
        df_sec = df_sec[~(_th & (df_sec["Sec Type"].fillna("") == "SHARE"))].copy()
    elif thailand_mode == "SHARE only":
        # Exclude Thai NVDRs from secondaries
        df_sec = df_sec[~(_th & (df_sec["Sec Type"].fillna("") == "NVDR"))].copy()
    elif thailand_mode == "SHARE → NVDR":
        # NVDRs are already in the main universe — exclude all Thai stocks from secondaries
        df_sec = df_sec[~_th].copy()

    # HK CNY exclusion — same as primary pipeline
    if excl_hk_cny:
        df_sec = df_sec[~(df_sec["Exchange Ticker"].str.contains("HKG", na=False) & (df_sec["Trading Currency"] == "CNY"))].copy()

    if len(df_sec) == 0:
        return df_selected

    for col in ["Total MCap Y2025","Free Float MCap Y2025","Free Float Percent",
                "1M ADTV Y2025","3M ADTV Y2025","6M ADTV Y2025","12M ADTV Y2025","Closing Price"]:
        df_sec[col] = pd.to_numeric(df_sec[col], errors="coerce").fillna(0)

    # ── Same checks as primary pipeline ──────────────────────────────────────
    # FF MCap > 0
    df_sec = df_sec[df_sec["Free Float MCap Y2025"] > 0].copy()

    # Free Float %
    df_sec = df_sec[df_sec["Free Float Percent"] >= min_ff_pct].copy()

    # Max Price
    if max_price:
        df_sec = df_sec[df_sec["Closing Price"].fillna(0) < max_price].copy()

    if len(df_sec) == 0:
        return df_selected

    # Inclusion Factors + Adj_FF_MCap — via FOL Matrix (oder Legacy Fallback)
    # Inclusion Factors + Adj_FF_MCap via FOL Matrix (Pflicht)
    df_sec = apply_fol_matrix(df_sec, fol_matrix, fol_sector_fb, fol_year, thailand_mode,
                               fol_enabled=fol_enabled, china_if=china_if)

    # ADTV_Best + ATVR
    df_sec["ADTV_Best"] = df_sec["12M ADTV Y2025"].where(df_sec["12M ADTV Y2025"]>0,
                          df_sec["6M ADTV Y2025"].where(df_sec["6M ADTV Y2025"]>0,
                          df_sec["3M ADTV Y2025"].where(df_sec["3M ADTV Y2025"]>0,
                          df_sec["1M ADTV Y2025"])))
    df_sec["ATVR"] = np.where(df_sec[atvr_mcap_col]>0,
                              df_sec["ADTV_Best"]*252/df_sec[atvr_mcap_col], 0)

    # Classification — already set on df_raw_original at load time
    # Just filter out stocks with no mapping
    if "Classification" not in df_sec.columns or df_sec["Classification"].isna().all():
        cls_map = df_selected[["Entity ID","Classification"]].drop_duplicates(subset=["Entity ID"])\
                    .set_index("Entity ID")["Classification"].to_dict()
        df_sec["Classification"] = df_sec["Entity ID"].map(cls_map)
    df_sec = df_sec[df_sec["Classification"].notna()].copy()

    # Liquidity filter: 3M ADTV + 6M ADTV + ATVR
    liq_mask = (
        ((df_sec["Classification"]=="DM") &
         (df_sec["3M ADTV Y2025"] >= adtv_dm) &
         (df_sec["6M ADTV Y2025"] >= adtv_dm) &
         (df_sec["ATVR"] >= atvr_dm)) |
        ((df_sec["Classification"]=="EM") &
         (df_sec["3M ADTV Y2025"] >= adtv_em) &
         (df_sec["6M ADTV Y2025"] >= adtv_em) &
         (df_sec["ATVR"] >= atvr_em))
    )
    df_sec = df_sec[liq_mask].copy()

    # Remove already included symbols
    existing_symbols = set(df_selected["Symbol"].unique())
    df_sec = df_sec[~df_sec["Symbol"].isin(existing_symbols)].copy()

    if len(df_sec) == 0:
        return df_selected

    # Inherit Segment_New from primary via Entity ID
    if "Segment_New" in df_selected.columns:
        seg_map = df_selected[["Entity ID","Segment_New"]].drop_duplicates(subset=["Entity ID"])\
                    .set_index("Entity ID")["Segment_New"].to_dict()
        df_sec["Segment_New"] = df_sec["Entity ID"].map(seg_map)

    return pd.concat([df_selected, df_sec], ignore_index=True)


def render_new_tab(tab_name, df_included, large_pct, mid_pct,
                   china_if,
                   params_dict,
                   diag_rows=None, diag_caption=None,
                   adtv_dm=0, adtv_em=0, atvr_dm=0, atvr_em=0,
                   small_pct=99, min_ff=0.15, if_mode="Selektion",
                   df_universe=None):
    """Render standard visuals for a new index tab."""

    df_dm = df_included[df_included["Classification"]=="DM"].copy()
    df_em = df_included[df_included["Classification"]=="EM"].copy()

    seg_order = ["Large Cap","Mid Cap","Small Cap","Micro Cap"]

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
            st.dataframe(pd.DataFrame(diag_rows), use_container_width=True, hide_index=True)
            if diag_caption:
                st.caption(diag_caption)

    # ── 5 Index Products ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Index-Produkte**")
    _world_dm  = df_dm[df_dm["Segment_New"].isin(["Large Cap","Mid Cap"])]
    _world_em  = df_em[df_em["Segment_New"].isin(["Large Cap","Mid Cap"])]
    _imi_dm_s  = df_dm[df_dm["Segment_New"]=="Small Cap"]
    _imi_em_s  = df_em[df_em["Segment_New"]=="Small Cap"]

    _idx_rows = [
        {"Index": "🌍 World Index",  "DM": len(_world_dm), "EM": "—", "Total": len(_world_dm),
         "DM FF MCap": format_bn(_world_dm["Free Float MCap Y2025"].sum()),
         "EM FF MCap": "—", "EM Adj. FF MCap": "—",
         "Total FF MCap": format_bn(_world_dm["Free Float MCap Y2025"].sum()),
         "Adj. Weight DM": f"{_world_dm['Adj_FF_MCap'].sum()/total_adj*100:.2f}%" if total_adj>0 else "—"},
        {"Index": "🌏 EM Index",     "DM": "—", "EM": len(_world_em), "Total": len(_world_em),
         "DM FF MCap": "—",
         "EM FF MCap": format_bn(_world_em["Free Float MCap Y2025"].sum()),
         "EM Adj. FF MCap": format_bn(_world_em["Adj_FF_MCap"].sum()),
         "Total FF MCap": format_bn(_world_em["Adj_FF_MCap"].sum()),
         "Adj. Weight DM": f"{_world_em['Adj_FF_MCap'].sum()/total_adj*100:.2f}%" if total_adj>0 else "—"},
        {"Index": "🌐 ACWI Index",   "DM": len(_world_dm), "EM": len(_world_em), "Total": len(_world_dm)+len(_world_em),
         "DM FF MCap": format_bn(_world_dm["Free Float MCap Y2025"].sum()),
         "EM FF MCap": format_bn(_world_em["Free Float MCap Y2025"].sum()),
         "EM Adj. FF MCap": format_bn(_world_em["Adj_FF_MCap"].sum()),
         "Total FF MCap": format_bn(_world_dm["Free Float MCap Y2025"].sum()+_world_em["Adj_FF_MCap"].sum()),
         "Adj. Weight DM": "100.00%"},
        {"Index": "🌍+ World IMI",   "DM": len(_world_dm)+len(_imi_dm_s), "EM": "—", "Total": len(_world_dm)+len(_imi_dm_s),
         "DM FF MCap": format_bn(_world_dm["Free Float MCap Y2025"].sum()+_imi_dm_s["Free Float MCap Y2025"].sum()),
         "EM FF MCap": "—", "EM Adj. FF MCap": "—",
         "Total FF MCap": format_bn(_world_dm["Free Float MCap Y2025"].sum()+_imi_dm_s["Free Float MCap Y2025"].sum()),
         "Adj. Weight DM": "—"},
        {"Index": "🌐+ ACWI IMI",    "DM": len(_world_dm)+len(_imi_dm_s), "EM": len(_world_em)+len(_imi_em_s),
         "Total": len(_world_dm)+len(_imi_dm_s)+len(_world_em)+len(_imi_em_s),
         "DM FF MCap": format_bn(_world_dm["Free Float MCap Y2025"].sum()+_imi_dm_s["Free Float MCap Y2025"].sum()),
         "EM FF MCap": format_bn(_world_em["Free Float MCap Y2025"].sum()+_imi_em_s["Free Float MCap Y2025"].sum()),
         "EM Adj. FF MCap": format_bn(_world_em["Adj_FF_MCap"].sum()+_imi_em_s["Adj_FF_MCap"].sum()),
         "Total FF MCap": format_bn((_world_dm["Free Float MCap Y2025"].sum()+_imi_dm_s["Free Float MCap Y2025"].sum())+(_world_em["Adj_FF_MCap"].sum()+_imi_em_s["Adj_FF_MCap"].sum())),
         "Adj. Weight DM": "—"},
    ]
    _idx_df = pd.DataFrame(_idx_rows)
    def _style_idx(df):
        def rs(row):
            if "ACWI Index" in str(row["Index"]): return ["background-color:#1a3a5c;font-weight:700;"]*len(row)
            return [""]*len(row)
        return df.style.apply(rs, axis=1)
    st.dataframe(_style_idx(_idx_df), use_container_width=True, hide_index=True)

    st.markdown("""
<div class="info-box">
🌍 <b>World Index</b> — DM Large Cap + Mid Cap &nbsp;|&nbsp;
🌏 <b>EM Index</b> — EM Large Cap + Mid Cap &nbsp;|&nbsp;
🌐 <b>ACWI Index</b> — World Index + EM Index<br>
🌍+ <b>World IMI</b> — World Index + DM Small Cap &nbsp;|&nbsp;
🌐+ <b>ACWI IMI</b> — ACWI Index + DM Small Cap + EM Small Cap
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
        st.dataframe(_style_dm_seg(_dm_seg), use_container_width=True, hide_index=True)

    with _sc2:
        st.markdown("**EM Segmente**")
        _em_seg = seg_table(df_em, "EM")
        def _style_em_seg(df):
            def rs(row):
                if "EM Index" in row["Segment"]: return ["background-color:#1a2a1a;font-weight:700;"]*len(row)
                return [""]*len(row)
            return df.style.apply(rs, axis=1)
        st.dataframe(_style_em_seg(_em_seg), use_container_width=True, hide_index=True)

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
                     use_container_width=True, hide_index=True)
    with _cc2:
        st.markdown(f"**EM Country Breakdown ({len(_acwi_em_std):,} Stocks — Large+Mid)**")
        st.dataframe(country_table(_acwi_em_std, _acwi_em_std["Adj_FF_MCap"].sum()),
                     use_container_width=True, hide_index=True)

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
        st.plotly_chart(fig_s, use_container_width=True)

    with _ch2:
        st.markdown("**Nach Gewicht (Adj. FF MCap %)**")
        fig_w = go.Figure(go.Bar(x=_top30["Weight%"], y=_top30["Mapping Country"],
            orientation="h", marker_color="#ce93d8",
            text=_top30["Weight%"].apply(lambda x: f"{x:.2f}%"), textposition="outside"))
        fig_w.update_layout(template="plotly_dark", paper_bgcolor="#0f1117", plot_bgcolor="#161b27",
            height=700, margin=dict(t=10,b=10,l=10,r=60), xaxis=dict(showgrid=False))
        st.plotly_chart(fig_w, use_container_width=True)

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
        st.plotly_chart(fig_d, use_container_width=True)

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
            st.dataframe(_sif(_if_df), use_container_width=True, hide_index=True)
        else:
            st.caption("Keine IF-betroffenen Länder im Index.")

    # ── Download ──────────────────────────────────────────────────────────────
    st.markdown("---")
    _drop = ["_cum_pct","_c","_cp2","ADTV_Best","IF"]
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
    uploaded = st.file_uploader("FactSet Export (.xlsx)", type=["xlsx","xls"])

    from datetime import date as _date
    snapshot_date = st.date_input(
        "Snapshot Datum",
        value=_date(2025, 12, 31),
        format="DD.MM.YYYY",
        key="snapshot_date",
        help="Datum des FactSet Exports — wird für Labels, Info-Boxen und Excel-Dateinamen verwendet."
    )
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
    except: max_closing_price = 20000.0

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
    except: large_thr  = 70
    try:    mid_thr    = int(_mid_raw)
    except: mid_thr    = 85
    try:    small_thr  = int(_small_raw)
    except: small_thr  = 99
    try:    min_ff_pct = float(_ff_raw) / 100
    except: min_ff_pct = 0.15
    try:    new_eumss_ff_ratio = float(_eumss_ff_raw) / 100
    except: new_eumss_ff_ratio = 0.50

    st.markdown("---")
    st.markdown("### 💧 Liquidität")
    st.caption("Post-Filter für Tabs 2–4 | Pre-Filter für Tab 5 (GIMI)")
    _adtv_a, _adtv_b = st.columns([3,4])
    with _adtv_a: st.markdown("<div style='padding-top:8px;font-size:13px;color:#e8eaf6;'>DM ADTV (USD)</div>", unsafe_allow_html=True)
    with _adtv_b: _adtv_dm_raw = st.text_input("DM ADTV", value="2000000", key="adtv_dm_new", label_visibility="collapsed")
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
    except: new_adtv_dm = 1_500_000.0
    try:    new_adtv_em = float(_adtv_em_raw.replace(",",""))
    except: new_adtv_em = 750_000.0
    try:    new_atvr_dm = float(_atvr_dm_raw) / 100
    except: new_atvr_dm = 0.0
    try:    new_atvr_em = float(_atvr_em_raw) / 100
    except: new_atvr_em = 0.0

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
        except: china_inclusion_factor = _china_if_historical

    # FOL Matrix (IN, VN, SA, QA, AE, MY, KW, ID, KR, PH, TH) — YAML ist bereits beim Laden validiert
    apply_fol = st.checkbox(
        "FOL Matrix anwenden",
        value=True,
        key="apply_fol",
        help=f"Wendet Foreign Ownership Limits aus 'Historical FOL Register/NaroIX_FOL_Master_Aggregated.yaml' an.\n\n"
             f"FIF-Formel: IF = min(1, FOL / Free Float %)\n"
             f"Fallback: Industry → Sector (strengster) → Country Default → 1.0\n\n"
             f"Betroffene Länder: IN, VN, SA, QA, AE, MY, KW, ID, KR, PH, TH\n"
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
    st.markdown("<div style='color:#8892b0;font-size:11px;'>NaroIX Benchmark Series<br/>© 2026 NaroIX</div>", unsafe_allow_html=True)


# ─── Load Data ─────────────────────────────────────────────────────────────────

if uploaded:
    df_raw, _year_suffix = load_excel(uploaded)
else:
    st.info("👆 Bitte eine Excel-Datei hochladen um zu starten.")
    st.stop()

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
    _df["Mapping Country"] = _df.apply(
        lambda r: r["Country of Incorp"] if r.get("Exchange Country Name","") == r.get("Country of Incorp","")
                  else r.get("Country of Risk",""), axis=1)
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

# Exclusions on All universe
df_raw_all = df_raw_all[df_raw_all["Free Float MCap Y2025"] > 0].copy()
if max_closing_price:
    df_raw_all = df_raw_all[df_raw_all["Closing Price"].fillna(0) < max_closing_price].copy()
if exclude_hk_cny:
    df_raw_all = df_raw_all[~(df_raw_all["Exchange Ticker"].str.contains("HKG", na=False) & (df_raw_all["Trading Currency"] == "CNY"))].copy()
if exclude_country_risk_na:
    df_raw_all = df_raw_all[df_raw_all["Country of Risk"].fillna("") != "@NA"].copy()
if exclude_naics_funds:
    df_raw_all = df_raw_all[~df_raw_all["NAICS"].fillna("").str.contains("Open-End Investment Fund", case=False, na=False)].copy()
if exclude_euro_mtf:
    df_raw_all = df_raw_all[~df_raw_all["Exchange Name"].fillna("").isin(["Euro MTF","@NA"])].copy()
if exclude_etf_sicav:
    import re as _re_etf
    df_raw_all = df_raw_all[~df_raw_all["Name"].fillna("").str.contains(_re_etf.compile(r'\bETF\b|\bSICAV\b|%', _re_etf.IGNORECASE))].copy()
df_raw_all = df_raw_all[df_raw_all["Classification"].notna()].copy()

df_dm_full = df_raw_all[df_raw_all["Classification"] == "DM"].copy()
df_em_full = df_raw_all[df_raw_all["Classification"] == "EM"].copy()

# Apply post-filter (for Tab 2)
def apply_post_filter(df):
    mask = ((df["Classification"]=="DM") &
            (df["3M ADTV Y2025"] >= new_adtv_dm) & (df["6M ADTV Y2025"] >= new_adtv_dm)) | \
           ((df["Classification"]=="EM") &
            (df["3M ADTV Y2025"] >= new_adtv_em) & (df["6M ADTV Y2025"] >= new_adtv_em))


# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='text-align:center;padding:10px 0 5px'>
  <span style='font-size:28px;font-weight:700;color:#A0B4FF;letter-spacing:2px;'>NaroIX</span>
  <span style='font-size:18px;color:#8892b0;'> — Benchmark Series</span>
  <br><span style='font-size:12px;color:#8892b0;'>Snapshot: {_snapshot_label} &nbsp;|&nbsp; Datenjahr: {_year_suffix} &nbsp;|&nbsp; Selection Date: {_active_selection_date.strftime('%d.%m.%Y')} &nbsp;|&nbsp; China IF: {china_inclusion_factor*100:.1f}% &nbsp;|&nbsp; FOL: {'✅ aktiv' if apply_fol and fol_matrix else '❌ inaktiv'}</span>
</div>
""", unsafe_allow_html=True)

# ─── Tabs ───────────────────────────────────────────────────────────────────
tab_overview, tab_gimi, tab_europe = st.tabs([
    "🌍 Universe Overview",
    "⚡ GIMI Method",
    "🇪🇺 Europe Index",
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
            use_container_width=True, height=400, hide_index=True)

    with _ov_col2:
        _em_ct_ov = _ov_em.groupby("Mapping Country").agg(
            Stocks=("Symbol","count"), FF_MCap=("Free Float MCap Y2025","sum"),
            Avg_MCap=("Total MCap Y2025","mean")).reset_index().sort_values("FF_MCap",ascending=False)
        _em_ct_ov["FF MCap (USD)"] = _em_ct_ov["FF_MCap"].apply(format_bn)
        _em_ct_ov["Avg MCap"]      = _em_ct_ov["Avg_MCap"].apply(format_bn)
        _em_ct_ov["Share (%)"]     = (_em_ct_ov["FF_MCap"]/_em_ct_ov["FF_MCap"].sum()*100).apply(lambda x: f"{x:.2f}%")
        st.markdown(f"**EM Universe — {len(_ov_em):,} Stocks**")
        st.dataframe(_em_ct_ov[["Mapping Country","Stocks","FF MCap (USD)","Avg MCap","Share (%)"]].rename(columns={"Mapping Country":"Land"}),
            use_container_width=True, height=400, hide_index=True)

    # Treemap
    st.markdown("---")
    st.markdown("**FF MCap Verteilung nach Land**")
    _ov_tree = _ov_all.groupby(["Classification","Mapping Country"]).agg(
        FF_MCap=("Free Float MCap Y2025","sum")).reset_index()
    _ov_fig = px.treemap(_ov_tree, path=["Classification","Mapping Country"],
        values="FF_MCap", color="Classification",
        color_discrete_map={"DM":"#2979ff","EM":"#ce93d8"}, template="plotly_dark")
    _ov_fig.update_layout(height=500, paper_bgcolor="#0f1117", margin=dict(t=10,b=10,l=10,r=10))
    st.plotly_chart(_ov_fig, use_container_width=True)

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
    _exc_df["_MappingCountry"] = _exc_df.apply(
        lambda r: r["Country of Incorp"] if r.get("Exchange Country Name","") == r.get("Country of Incorp","")
                  else r.get("Country of Risk",""), axis=1)
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

    st.dataframe(_exc_summary, use_container_width=True, hide_index=True)

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
            use_container_width=True, hide_index=True)
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
                use_container_width=True, hide_index=True)

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
            st.info("Keine Stocks aus FOL-Ländern (IN/VN/SA/QA/AE/MY/KW/ID/KR/PH/TH) im Universe.")
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
                        _if = min(1.0, fol_v / ff_ratio) if ff_ratio > 0 else 1.0
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
                st.dataframe(_audit_df, use_container_width=True, hide_index=True)

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
    st.caption("Primary only + Secondary Listings (re-added) | EUMSS Pre-Filter | Liquidität Pre-Filter | Coverage per Land auf Adj_FF_MCap")

    _gm_u = build_new_universe(df_raw_original, country_cls, thailand_sec_type, max_closing_price,
        exclude_hk_cny, exclude_country_risk_na, exclude_naics_funds, exclude_euro_mtf, exclude_etf_sicav,
        china_inclusion_factor,
        atvr_mcap_col=atvr_mcap_col, excl_delisted=exclude_delisted,
        fol_matrix=fol_matrix, fol_sector_fb=fol_sector_fb, fol_year=_active_selection_date.year,
        fol_enabled=apply_fol)

    # EUMSS calibration on DM (using small_thr = 99%)
    _gm_dm_all = _gm_u[_gm_u["Classification"]=="DM"].sort_values("Total MCap Y2025", ascending=False).copy()
    _gm_ff_tot = _gm_dm_all["Free Float MCap Y2025"].sum()
    if _gm_ff_tot > 0:
        _gm_dm_all["_cp"] = _gm_dm_all["Free Float MCap Y2025"].cumsum() / _gm_ff_tot * 100
        _gm_eumss_rows = _gm_dm_all[_gm_dm_all["_cp"] >= small_thr]
        if len(_gm_eumss_rows) == 0:
            st.error("EUMSS konnte nicht kalibriert werden.")
            st.stop()
        _gm_eumss_full = _gm_eumss_rows.iloc[0]["Total MCap Y2025"]
        _gm_eumss_ff   = _gm_eumss_full * new_eumss_ff_ratio

        # EUMSS filter
        _gm_mask_eumss = ((_gm_u["Total MCap Y2025"] >= _gm_eumss_full) &
                          (_gm_u["Free Float MCap Y2025"] >= _gm_eumss_ff) &
                          (_gm_u["Free Float Percent"] >= min_ff_pct))
        _gm_eumss = _gm_u[_gm_mask_eumss].copy()

        # Pre-liquidity filter
        _gm_liq = apply_liquidity_new(_gm_eumss, new_adtv_dm, new_adtv_em, new_atvr_dm, new_atvr_em)

        # Coverage per country → Standard Index
        # Sort: Total MCap (MSCI-konform), Cumulative: if_cum_col (Adj_FF_MCap or FF MCap)
        _gm_results = []
        for _ctry, _grp in _gm_liq.groupby("Mapping Country"):
            _grp = _grp.sort_values("Total MCap Y2025", ascending=False).copy()
            _tot = _grp[if_cum_col].sum()
            if _tot == 0: continue
            _grp["_c"] = _grp[if_cum_col].cumsum() / _tot * 100
            _cut = _grp[_grp["_c"] >= mid_thr].index
            _inc = _grp.loc[:_cut[0]] if len(_cut)>0 else _grp
            _tot_inc = _inc[if_cum_col].sum()
            _inc = _inc.copy()
            _inc["_cp2"] = _inc[if_cum_col].cumsum() / _tot_inc * 100 if _tot_inc>0 else 0
            _inc["Segment_New"] = np.where(_inc["_cp2"] <= large_thr, "Large Cap", "Mid Cap")
            _gm_results.append(_inc)

        _gm_std = pd.concat(_gm_results, ignore_index=True) if _gm_results else pd.DataFrame(columns=_gm_liq.columns.tolist()+["Segment_New"])

        # Small Cap = passed EUMSS but not in liquidity filter
        _gm_std_symbols   = set(_gm_std["Symbol"].dropna().unique())
        _gm_liq_symbols   = set(_gm_liq["Symbol"].dropna().unique())
        _gm_eumss_symbols = set(_gm_eumss["Symbol"].dropna().unique())
        _gm_u_symbols     = set(_gm_u["Symbol"].dropna().unique())

        _gm_small = _gm_eumss[~_gm_eumss["Symbol"].isin(_gm_liq_symbols)].copy()
        _gm_small["Segment_New"] = "Small Cap"
        # Also add stocks in liquidity but above 85% cutoff
        _gm_above85 = _gm_liq[~_gm_liq["Symbol"].isin(_gm_std_symbols)].copy()
        _gm_above85["Segment_New"] = "Small Cap"

        # Micro Cap = below EUMSS
        _gm_micro = _gm_u[~_gm_u["Symbol"].isin(_gm_eumss_symbols)].copy()
        _gm_micro["Segment_New"] = "Micro Cap"

        # Add secondary listings for standard index only
        _gm_final = add_secondary_listings(_gm_std, df_raw_original, new_adtv_dm, new_adtv_em,
            new_atvr_dm, new_atvr_em, max_closing_price, thailand_sec_type,
            china_inclusion_factor,
            min_ff_pct=min_ff_pct, atvr_mcap_col=atvr_mcap_col, excl_hk_cny=exclude_hk_cny,
            fol_matrix=fol_matrix, fol_sector_fb=fol_sector_fb, fol_year=_active_selection_date.year,
            fol_enabled=apply_fol)

        _gm_complete = pd.concat([_gm_final, _gm_small, _gm_above85, _gm_micro], ignore_index=True)
        _gm_complete = _gm_complete.drop_duplicates(subset=["Symbol"]).copy()

        # ── Ineligible-Filter (final step): ISINs auf Sperrliste entfernen ──────
        _gm_count_before_ie = len(_gm_complete)
        if apply_ineligible and not ineligible_df.empty:
            _gm_complete, _gm_ie_removed, _gm_ie_active_rules = apply_ineligible_filter(
                _gm_complete, ineligible_df, _active_selection_date)
        else:
            _gm_ie_removed = _gm_complete.iloc[0:0].copy()
            _gm_ie_active_rules = ineligible_df.iloc[0:0].copy() if not ineligible_df.empty else pd.DataFrame()

        _gm_tot_adj = _gm_complete["Adj_FF_MCap"].sum()
        _gm_complete["Index_Weight"] = _gm_complete["Adj_FF_MCap"]/_gm_tot_adj*100 if _gm_tot_adj>0 else 0

        _gm_all = df_raw_all[df_raw_all["Classification"].notna()]
        _gm_diag = [
            {"Schritt":"0 — Universe (Primary + Secondary)","DM":(_gm_all["Classification"]=="DM").sum(),"EM":(_gm_all["Classification"]=="EM").sum(),"Total":len(_gm_all),"Δ":"—"},
            {"Schritt":"1 — Universe (Primary only)","DM":(_gm_u["Classification"]=="DM").sum(),"EM":(_gm_u["Classification"]=="EM").sum(),"Total":len(_gm_u),"Δ":f"-{len(_gm_all)-len(_gm_u):,}"},
            {"Schritt":f"2 — EUMSS Filter ({_gm_eumss_full/1e6:.0f}M)","DM":(_gm_eumss["Classification"]=="DM").sum(),"EM":(_gm_eumss["Classification"]=="EM").sum(),"Total":len(_gm_eumss),"Δ":f"-{len(_gm_u)-len(_gm_eumss):,}"},
            {"Schritt":"3 — Liquiditätsfilter (Pre)","DM":(_gm_liq["Classification"]=="DM").sum(),"EM":(_gm_liq["Classification"]=="EM").sum(),"Total":len(_gm_liq),"Δ":f"-{len(_gm_eumss)-len(_gm_liq):,}"},
            {"Schritt":f"4 — {mid_thr}% Coverage","DM":(_gm_std["Classification"]=="DM").sum(),"EM":(_gm_std["Classification"]=="EM").sum(),"Total":len(_gm_std),"Δ":f"-{len(_gm_liq)-len(_gm_std):,}"},
            {"Schritt":"5 — Secondary Listings re-added (+)","DM":(_gm_final["Classification"]=="DM").sum(),"EM":(_gm_final["Classification"]=="EM").sum(),"Total":len(_gm_final),"Δ":f"+{len(_gm_final)-len(_gm_std):,}"},
            {"Schritt":f"6 — Ineligible-Filter ({'aktiv' if apply_ineligible and not ineligible_df.empty else 'inaktiv'})","DM":(_gm_complete["Classification"]=="DM").sum(),"EM":(_gm_complete["Classification"]=="EM").sum(),"Total":len(_gm_complete),"Δ":f"-{len(_gm_ie_removed):,}" if len(_gm_ie_removed)>0 else "—"},
        ]
        _gm_diag_caption = f"EUMSS_FULL: {format_bn(_gm_eumss_full)} | EUMSS_FF: {format_bn(_gm_eumss_ff)} | FF Ratio: {new_eumss_ff_ratio*100:.0f}% | Min FF%: {min_ff_pct*100:.0f}% | IF: {if_selection_mode} | FOL Matrix: {'✅ ' + str(fol_version) if apply_fol and fol_matrix else '❌ inaktiv'}"
        _gm_eumss_extra = f"EUMSS_FULL: {format_bn(_gm_eumss_full)} | EUMSS_FF: {format_bn(_gm_eumss_ff)} | FF Ratio: {new_eumss_ff_ratio*100:.0f}%"

        _gm_params = {"Methodik":"GIMI Method","Listing":"Primary only + Secondary Listings (re-added)",
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
            df_universe=df_raw_all)
    else:
        st.error("Keine DM Stocks gefunden.")



# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: Europe Index
# ══════════════════════════════════════════════════════════════════════════════
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
                st.dataframe(_eu_ctry, use_container_width=True, hide_index=True)

            with _eu_col2:
                st.markdown("**Top 20 Stocks**")
                _top20_cols = ["Symbol", "Name", "Mapping Country", "Segment_New", "Index_Weight"]
                _top20 = _eu_dm[[c for c in _top20_cols if c in _eu_dm.columns]].head(20).copy()
                _top20["Index_Weight"] = _top20["Index_Weight"].map(lambda x: f"{x:.4f}%")
                st.dataframe(_top20, use_container_width=True, hide_index=True)

            # ── Download ─────────────────────────────────────────────────────
            st.markdown("---")
            _drop_eu = ["_cum_pct","_c","_cp2","ADTV_Best","IF","Index_Weight"]
            _eu_dl = normalize_index_weight(_eu_dm[[c for c in _eu_dm.columns if c not in ["_cum_pct","_c","_cp2","ADTV_Best","IF"]].copy()])
            _eu_large_dl = normalize_index_weight(_eu_dm[_eu_dm["Segment_New"]=="Large Cap"][[c for c in _eu_dm.columns if c not in ["_cum_pct","_c","_cp2","ADTV_Best","IF"]].copy()])
            _eu_mid_dl   = normalize_index_weight(_eu_dm[_eu_dm["Segment_New"]=="Mid Cap"][[c for c in _eu_dm.columns if c not in ["_cum_pct","_c","_cp2","ADTV_Best","IF"]].copy()])

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
