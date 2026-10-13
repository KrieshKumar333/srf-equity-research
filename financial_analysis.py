"""
financial_analysis.py — Computes all financial ratios, growth metrics,
and capital structure indicators for the equity research model.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
def _safe_div(numerator: float, denominator: float) -> float:
    """Division guard: returns NaN when denominator is 0 or either is NaN."""
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return np.nan
    return numerator / denominator


def _cagr(start: float, end: float, years: int) -> float:
    """Compound Annual Growth Rate."""
    if pd.isna(start) or pd.isna(end) or start <= 0 or years <= 0:
        return np.nan
    return (end / start) ** (1 / years) - 1


# ─────────────────────────────────────────────────────────────────────────────
class FinancialAnalyzer:
    """
    Computes all profitability, efficiency, leverage, and valuation ratios.
    Input: validated company data dictionary from DataFetcher.get_company_data().
    """

    def __init__(self, data: Dict) -> None:
        self.d = data
        self._ratios: Optional[pd.DataFrame] = None
        self._summary: Optional[Dict] = None

    # ── Core timeseries metrics ───────────────────────────────────────────────

    @property
    def years(self) -> List[str]:
        return self.d.get("fiscal_years", [])

    @property
    def revenue(self) -> np.ndarray:
        return np.array(self.d.get("revenue_cr", []), dtype=float)

    @property
    def ebitda(self) -> np.ndarray:
        return np.array(self.d.get("ebitda_cr", []), dtype=float)

    @property
    def pat(self) -> np.ndarray:
        return np.array(self.d.get("pat_cr", []), dtype=float)

    @property
    def da(self) -> np.ndarray:
        return np.array(self.d.get("da_cr", []), dtype=float)

    # ── Ratio computation ─────────────────────────────────────────────────────

    def compute_ratios(self) -> pd.DataFrame:
        """
        Returns a DataFrame (index = fiscal years) with all key ratios.
        Never raises: any missing input results in NaN for that ratio.
        """
        if self._ratios is not None:
            return self._ratios

        n = len(self.years)
        if n == 0:
            logger.error("No financial data available for ratio computation.")
            return pd.DataFrame()

        rev  = self.revenue
        ebit = self.ebitda
        net  = self.pat
        da_  = self.da

        # ── Profitability ratios ──────────────────────────────────────────────
        ebitda_margin = np.array([_safe_div(e, r) * 100 for e, r in zip(ebit, rev)])
        pat_margin    = np.array([_safe_div(p, r) * 100 for p, r in zip(net, rev)])
        ebit_         = ebit - da_  # EBIT = EBITDA - D&A
        ebit_margin   = np.array([_safe_div(e, r) * 100 for e, r in zip(ebit_, rev)])

        # ── Growth metrics ────────────────────────────────────────────────────
        rev_growth = np.concatenate([[np.nan],
            [_safe_div(rev[i] - rev[i-1], rev[i-1]) * 100 for i in range(1, n)]])
        ebitda_growth = np.concatenate([[np.nan],
            [_safe_div(ebit[i] - ebit[i-1], ebit[i-1]) * 100 for i in range(1, n)]])
        pat_growth = np.concatenate([[np.nan],
            [_safe_div(net[i] - net[i-1], net[i-1]) * 100 for i in range(1, n)]])

        # ── Capital efficiency ────────────────────────────────────────────────
        total_assets = self.d.get("total_assets_cr", np.nan)
        equity_cr    = self.d.get("equity_cr", np.nan)
        net_debt     = self.d.get("net_debt_cr", np.nan)
        capital_employed = (float(total_assets) - float(equity_cr) + float(net_debt)) if not any(
            pd.isna(x) for x in [total_assets, equity_cr, net_debt]) else np.nan

        # ROCE and ROE (point-in-time with latest balance sheet)
        latest_ebit = float(ebit_[-1]) - float(da_[-1]) if n > 0 else np.nan
        roce_arr = np.full(n, np.nan)
        if not pd.isna(capital_employed) and capital_employed != 0:
            roce_arr[-1] = _safe_div(latest_ebit, capital_employed) * 100

        roe_arr = np.full(n, np.nan)
        if not pd.isna(equity_cr) and float(equity_cr) != 0:
            roe_arr[-1] = _safe_div(float(net[-1]), float(equity_cr)) * 100

        # ── Leverage ──────────────────────────────────────────────────────────
        de_ratio = np.full(n, np.nan)
        nd_ebitda = np.full(n, np.nan)
        if not pd.isna(net_debt) and not pd.isna(equity_cr):
            de_ratio[-1]  = _safe_div(float(net_debt), float(equity_cr))
        if not pd.isna(net_debt):
            nd_ebitda[-1] = _safe_div(float(net_debt), float(ebit[-1]))

        # ── Per-share metrics (if available) ─────────────────────────────────
        eps_arr  = np.array(self.d.get("eps",  [np.nan] * n), dtype=float)
        bvps_arr = np.array(self.d.get("bvps", [np.nan] * n), dtype=float)

        df = pd.DataFrame({
            "Fiscal Year":       self.years,
            "Revenue (₹ Cr)":   np.round(rev, 0),
            "EBITDA (₹ Cr)":    np.round(ebit, 0),
            "PAT (₹ Cr)":       np.round(net, 0),
            "EBITDA Margin (%)": np.round(ebitda_margin, 1),
            "PAT Margin (%)":    np.round(pat_margin, 1),
            "EBIT Margin (%)":   np.round(ebit_margin, 1),
            "Rev. Growth (%)":   np.round(rev_growth, 1),
            "EBITDA Growth (%)": np.round(ebitda_growth, 1),
            "PAT Growth (%)":    np.round(pat_growth, 1),
            "ROCE (%)":          np.round(roce_arr, 1),
            "ROE (%)":           np.round(roe_arr, 1),
            "D/E Ratio (x)":     np.round(de_ratio, 2),
            "ND / EBITDA (x)":   np.round(nd_ebitda, 2),
            "EPS (₹)":           np.round(eps_arr, 1),
            "BVPS (₹)":          np.round(bvps_arr, 1),
        }).set_index("Fiscal Year")

        self._ratios = df
        logger.info(f"Financial ratios computed for {n} fiscal years.")
        return df

    def compute_summary_stats(self) -> Dict:
        """
        Returns key single-value statistics used in the research note header
        and dashboard KPI cards.
        """
        if self._summary is not None:
            return self._summary

        df = self.compute_ratios()
        rev  = self.revenue
        ebit = self.ebitda
        n    = len(rev)

        summary = {
            # Growth CAGRs
            "rev_cagr_3y":    _cagr(rev[-4],  rev[-1],  3) * 100 if n >= 4 else np.nan,
            "rev_cagr_5y":    _cagr(rev[0],   rev[-1],  n-1) * 100 if n >= 2 else np.nan,
            "ebitda_cagr_5y": _cagr(ebit[0],  ebit[-1], n-1) * 100 if n >= 2 else np.nan,
            # Margins (latest year)
            "ebitda_margin_latest": float(df["EBITDA Margin (%)"].iloc[-1])  if not df.empty else np.nan,
            "pat_margin_latest":    float(df["PAT Margin (%)"].iloc[-1])     if not df.empty else np.nan,
            # Latest abs values
            "latest_revenue_cr": float(rev[-1])  if n > 0 else np.nan,
            "latest_ebitda_cr":  float(ebit[-1]) if n > 0 else np.nan,
            "latest_pat_cr":     float(self.pat[-1]) if n > 0 else np.nan,
            # Balance sheet
            "net_debt_cr":    float(self.d.get("net_debt_cr", np.nan)),
            "equity_cr":      float(self.d.get("equity_cr", np.nan)),
            "total_assets_cr":float(self.d.get("total_assets_cr", np.nan)),
            # Market
            "current_price": float(self.d.get("current_price", np.nan)),
            "market_cap_cr": float(self.d.get("market_cap_cr", np.nan)),
            "shares_cr":     float(self.d.get("shares_cr", np.nan)),
            "52w_high":      float(self.d.get("52w_high", np.nan)),
            "52w_low":       float(self.d.get("52w_low", np.nan)),
            "beta":          float(self.d.get("beta", 1.0)),
        }

        # Enterprise value
        mktcap_cr = summary["market_cap_cr"]
        nd_cr     = summary["net_debt_cr"]
        if not any(pd.isna(x) for x in [mktcap_cr, nd_cr]):
            summary["ev_cr"] = mktcap_cr + nd_cr
        else:
            summary["ev_cr"] = np.nan

        # EV/EBITDA and P/E
        summary["ev_ebitda"] = _safe_div(summary["ev_cr"], summary["latest_ebitda_cr"])
        eps = self.d.get("eps", [np.nan])
        summary["pe_ratio"]  = _safe_div(summary["current_price"], float(eps[-1])) if eps else np.nan

        # Revenue decline flag
        summary["rev_declined_latest"] = bool(rev[-1] < rev[-2]) if n >= 2 else False

        self._summary = summary
        return summary
