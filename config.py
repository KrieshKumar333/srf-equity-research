"""
config.py — Central configuration for SRF Limited Equity Research Platform
All assumptions, tickers, and model parameters are defined here.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
#  TARGET COMPANY
# ─────────────────────────────────────────────────────────────────────────────
TARGET_TICKER: str = "SRF.NS"
TARGET_NAME: str = "SRF Limited"
SECTOR: str = "Specialty Chemicals"
EXCHANGE: str = "NSE"
CURRENCY_SYMBOL: str = "₹"
FISCAL_YEAR_END: str = "March"
REPORT_DATE: str = "October 2026"
ANALYST_NAME: str = "Krrish Kumar"
INSTITUTION: str = "Independent Research"

# ─────────────────────────────────────────────────────────────────────────────
#  PEER UNIVERSE
# ─────────────────────────────────────────────────────────────────────────────
PEERS: List[Tuple[str, str]] = [
    ("Aarti Industries",        "AARTIIND.NS"),
    ("Navin Fluorine Intl.",    "NAVINFLUOR.NS"),
    ("Gujarat Fluorochem.",     "GUJFLUORO.NS"),
    ("Deepak Nitrite",          "DEEPAKNTR.NS"),
    ("Vinati Organics",         "VINATIORGA.NS"),
    ("Fine Organics",           "FINEORG.NS"),
    ("Sudarshan Chemical",      "SUDARSCHEM.NS"),
    ("Balaji Amines",           "BALAMINES.NS"),
]

# ─────────────────────────────────────────────────────────────────────────────
#  MOCK / FALLBACK DATA  (FY20–FY24 approximate from public disclosures)
#  Values in ₹ Crore unless stated
# ─────────────────────────────────────────────────────────────────────────────
MOCK_DATA: Dict = {
    "fiscal_years": ["FY20", "FY21", "FY22", "FY23", "FY24"],
    "revenue_cr":   [8_700,  10_200, 13_400, 15_800, 14_600],
    "ebitda_cr":    [1_700,   2_300,  3_100,  3_200,  2_800],
    "ebit_cr":      [1_200,   1_700,  2_300,  2_100,  1_600],
    "pat_cr":       [  700,   1_400,  2_000,  1_800,    850],
    "capex_cr":     [1_200,   1_600,  2_200,  3_500,  2_900],
    "da_cr":        [  500,     600,    800,  1_100,  1_200],
    "net_debt_cr":  5_500,
    "cash_cr":      1_200,
    "total_assets_cr": 22_000,
    "equity_cr":    12_500,
    "shares_cr":    28.6,            # crore shares outstanding
    "current_price": 2_250.0,        # ₹ per share (approximate)
    "52w_high":     2_750.0,
    "52w_low":      1_800.0,
    "beta":         1.10,
    "eps":  [24.5, 49.0, 69.9, 63.0, 29.7],
    "bvps": [282,  326,  388,  436,  448],
}

# ─────────────────────────────────────────────────────────────────────────────
#  DCF SCENARIO DATACLASS
#  capex_pct_yr1_2  — capex/revenue during the high-investment phase (Yr1–2)
#  capex_pct_yr3_5  — capex/revenue after the cycle normalises  (Yr3–5)
#
#  WHY STAGE-DEPENDENT CAPEX?
#  SRF's FY23-24 capex was ~22% of revenue as it built out specialty chem
#  capacity. The FCF inflection thesis (a key re-rating catalyst) relies on
#  capex falling to ~8-9% by FY27 as the new plants ramp to full utilisation.
#  A single flat capex rate would misrepresent the FCF profile entirely.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Scenario:
    rev_growth_yr1_3:  float   # Annual revenue growth, Years 1–3
    rev_growth_yr4_5:  float   # Annual revenue growth, Years 4–5
    ebitda_margin:     float   # Steady-state EBITDA margin (reached by Yr3)
    wacc:              float   # Weighted average cost of capital
    terminal_growth:   float   # Perpetuity growth rate
    capex_pct_yr1_2:   float = 0.16   # High-capex investment phase
    capex_pct_yr3_5:   float = 0.09   # Normalised maintenance + growth capex


SCENARIOS: Dict[str, Scenario] = {
    # ─── Bull: strong China+1 ramp, capex normalises quickly, low WACC ────────
    "Bull": Scenario(
        rev_growth_yr1_3  = 0.22,
        rev_growth_yr4_5  = 0.15,
        ebitda_margin     = 0.26,
        wacc              = 0.110,
        terminal_growth   = 0.060,
        capex_pct_yr1_2   = 0.14,
        capex_pct_yr3_5   = 0.07,
    ),
    # ─── Base: consensus recovery, moderate capex taper ─────────────────────
    "Base": Scenario(
        rev_growth_yr1_3  = 0.14,
        rev_growth_yr4_5  = 0.10,
        ebitda_margin     = 0.23,
        wacc              = 0.130,
        terminal_growth   = 0.055,
        capex_pct_yr1_2   = 0.16,
        capex_pct_yr3_5   = 0.09,
    ),
    # ─── Bear: prolonged destocking, margin compression, high capex drag ─────
    "Bear": Scenario(
        rev_growth_yr1_3  = 0.05,
        rev_growth_yr4_5  = 0.03,
        ebitda_margin     = 0.19,
        wacc              = 0.150,
        terminal_growth   = 0.040,
        capex_pct_yr1_2   = 0.18,
        capex_pct_yr3_5   = 0.12,
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
#  FIXED DCF PARAMETERS  (common across scenarios)
# ─────────────────────────────────────────────────────────────────────────────
DA_PCT_REVENUE:    float = 0.072   # D&A as % of revenue (SRF 5-yr avg)
CAPEX_PCT_REVENUE: float = 0.095   # Default (used only in excel/report summary)
NWC_DELTA_PCT:     float = 0.020   # Incremental NWC as % of Δrevenue
TAX_RATE:          float = 0.250   # India corporate tax (Section 115BAA)
PROJECTION_YEARS:  int   = 5

# ─────────────────────────────────────────────────────────────────────────────
#  INDIA MACRO  (WACC build-up components)
# ─────────────────────────────────────────────────────────────────────────────
RISK_FREE_RATE:       float = 0.071   # India 10Y G-Sec yield
EQUITY_RISK_PREMIUM:  float = 0.065   # Damodaran India ERP
DEBT_COST_PRE_TAX:    float = 0.090   # Typical BBB-rated Indian co.
DEBT_TO_EV_RATIO:     float = 0.15    # SRF target capital structure

# ─────────────────────────────────────────────────────────────────────────────
#  SENSITIVITY RANGES
# ─────────────────────────────────────────────────────────────────────────────
SENSITIVITY_WACC_RANGE:    List[float] = [-0.020, -0.010, 0.0, +0.010, +0.020]
SENSITIVITY_TGROWTH_RANGE: List[float] = [-0.010, -0.005, 0.0, +0.005, +0.010]

# ─────────────────────────────────────────────────────────────────────────────
#  OUTPUT PATHS
# ─────────────────────────────────────────────────────────────────────────────
EXCEL_OUTPUT:  str = "outputs/SRF_Equity_Research.xlsx"
PDF_OUTPUT:    str = "outputs/SRF_Research_Note.pdf"
