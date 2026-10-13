"""
data_fetcher.py — Fetches financial data from Yahoo Finance.
Falls back gracefully to config mock data if network/data is unavailable.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

from .config import (
    MOCK_DATA, PEERS, TARGET_NAME, TARGET_TICKER,
)

logger = logging.getLogger(__name__)

# Conversion: yfinance returns raw currency units; SRF reports in ₹
_CRORE = 1e7          # 1 Crore = 10 million


def _to_cr(value: float) -> float:
    """Convert raw currency value → ₹ Crore, handling NaN safely."""
    if pd.isna(value):
        return np.nan
    return value / _CRORE


def _safe_get(df: pd.DataFrame, row: str, col: object) -> float:
    """Retrieve df.loc[row, col] safely; return NaN on any failure."""
    try:
        val = df.loc[row, col]
        return float(val) if not pd.isna(val) else np.nan
    except Exception:
        return np.nan


# ─────────────────────────────────────────────────────────────────────────────
class DataFetcher:
    """
    Retrieves and validates all financial data for the target company and peers.
    Priority: yfinance live data → fallback to MOCK_DATA constants.
    """

    def __init__(self, ticker: str = TARGET_TICKER, use_mock: bool = False) -> None:
        self.ticker = ticker
        self._use_mock = use_mock
        self._yf: Optional[yf.Ticker] = None
        self._cache: Dict = {}

    @property
    def yf_ticker(self) -> yf.Ticker:
        if self._yf is None:
            self._yf = yf.Ticker(self.ticker)
        return self._yf

    # ── Public interface ──────────────────────────────────────────────────────

    def get_company_data(self) -> Dict:
        """Return complete, validated financial dataset for the target company."""
        if "company" in self._cache:
            return self._cache["company"]

        if self._use_mock:
            data = self._build_from_mock()
        else:
            data = self._fetch_live()
            if data is None:
                logger.warning("Live data fetch failed. Switching to fallback data.")
                data = self._build_from_mock()

        self._cache["company"] = data
        return data

    def get_price_history(self, period: str = "5y") -> pd.DataFrame:
        """Return daily OHLCV price history."""
        if self._use_mock:
            return self._mock_price_history()
        try:
            df = self.yf_ticker.history(period=period)
            if df.empty:
                raise ValueError("Empty price response")
            logger.info(f"Price data: {len(df)} trading days loaded.")
            return df
        except Exception as e:
            logger.warning(f"Price fetch failed ({e}). Using mock prices.")
            return self._mock_price_history()

    def get_peer_data(self) -> pd.DataFrame:
        """Return a DataFrame of key valuation metrics for the peer universe."""
        if self._use_mock:
            return self._mock_peer_data()
        rows = []
        for name, tkr in PEERS:
            rows.append(self._fetch_single_peer(name, tkr))
        df = pd.DataFrame(rows)
        # Add target company row at top
        cd = self.get_company_data()
        target_row = self._build_target_peer_row(cd)
        df = pd.concat([pd.DataFrame([target_row]), df], ignore_index=True)
        return df

    # ── Live data fetch ────────────────────────────────────────────────────────

    def _fetch_live(self) -> Optional[Dict]:
        """Attempt to fetch all live data; return None on critical failure."""
        try:
            info = self.yf_ticker.info
            if not info or "currentPrice" not in info:
                raise ValueError("Company info not available")

            income, balance, cashflow = self._fetch_statements()

            data: Dict = {
                "ticker":        self.ticker,
                "company_name":  TARGET_NAME,
                "data_source":   "yfinance",
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice", np.nan),
                "market_cap_cr": _to_cr(info.get("marketCap", np.nan)),
                "shares_cr":     _to_cr(info.get("sharesOutstanding", np.nan)),
                "52w_high":      info.get("fiftyTwoWeekHigh", np.nan),
                "52w_low":       info.get("fiftyTwoWeekLow", np.nan),
                "beta":          info.get("beta", 1.0) or 1.0,
            }

            # ── Timeseries financials ─────────────────────────────────────────
            if not income.empty:
                data.update(self._parse_income(income))
            else:
                data.update(self._mock_timeseries())

            # ── Balance sheet ─────────────────────────────────────────────────
            if not balance.empty:
                latest = balance.columns[0]
                total_debt = _safe_get(balance, "Total Debt", latest)
                cash       = _safe_get(balance, "Cash And Cash Equivalents", latest)
                data["net_debt_cr"]    = _to_cr(total_debt - cash)
                data["total_assets_cr"]= _to_cr(_safe_get(balance, "Total Assets", latest))
                data["equity_cr"]      = _to_cr(_safe_get(balance, "Stockholders Equity", latest))
            else:
                data["net_debt_cr"]     = MOCK_DATA["net_debt_cr"]
                data["total_assets_cr"] = MOCK_DATA["total_assets_cr"]
                data["equity_cr"]       = MOCK_DATA["equity_cr"]

            # ── Shares fallback ────────────────────────────────────────────────
            if pd.isna(data.get("shares_cr", np.nan)):
                data["shares_cr"] = MOCK_DATA["shares_cr"]

            # ── Latest revenue for DCF base ────────────────────────────────────
            data["latest_revenue_cr"] = data["revenue_cr"][-1]
            logger.info(f"Live data loaded. Source: yfinance | Price: ₹{data['current_price']:.0f}")
            return data

        except Exception as e:
            logger.error(f"Live data error: {e}")
            return None

    def _fetch_statements(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Fetch annual income, balance sheet, cashflow from yfinance."""
        try:
            income   = self.yf_ticker.financials      # annual
            balance  = self.yf_ticker.balance_sheet
            cashflow = self.yf_ticker.cashflow
            return (
                income   if income   is not None else pd.DataFrame(),
                balance  if balance  is not None else pd.DataFrame(),
                cashflow if cashflow is not None else pd.DataFrame(),
            )
        except Exception as e:
            logger.error(f"Statement fetch error: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def _parse_income(self, income: pd.DataFrame) -> Dict:
        """Extract revenue, EBITDA, PAT timeseries from income statement."""
        revenues, ebitdas, pats, da_vals, fiscal_years = [], [], [], [], []
        for col in reversed(income.columns):   # chronological order
            rev  = _safe_get(income, "Total Revenue", col)
            ebit = _safe_get(income, "EBIT", col)
            da   = _safe_get(income, "Reconciled Depreciation", col)
            pat  = _safe_get(income, "Net Income", col)
            revenues.append(_to_cr(rev))
            da_val = da if not pd.isna(da) else 0.0
            ebitdas.append(_to_cr(ebit + da_val) if not pd.isna(ebit) else np.nan)
            da_vals.append(_to_cr(da_val))
            pats.append(_to_cr(pat))
            fiscal_years.append(str(col.year) if hasattr(col, "year") else str(col))

        return {
            "fiscal_years": fiscal_years,
            "revenue_cr":   revenues,
            "ebitda_cr":    ebitdas,
            "da_cr":        da_vals,
            "pat_cr":       pats,
        }

    # ── Peer fetch ─────────────────────────────────────────────────────────────

    def _fetch_single_peer(self, name: str, tkr: str) -> Dict:
        """Fetch one peer company's valuation metrics."""
        row: Dict = {"Company": name, "Ticker": tkr}
        try:
            info = yf.Ticker(tkr).info or {}
            mktcap = info.get("marketCap", np.nan)
            ev     = info.get("enterpriseValue", np.nan)
            ebitda = info.get("ebitda", np.nan)
            pe     = info.get("trailingPE", np.nan)
            pb     = info.get("priceToBook", np.nan)
            revgr  = info.get("revenueGrowth", np.nan)
            rev    = info.get("totalRevenue", np.nan)

            row.update({
                "Market Cap (₹ Cr)":  round(_to_cr(mktcap), 0)  if not pd.isna(mktcap) else np.nan,
                "EV (₹ Cr)":          round(_to_cr(ev),     0)  if not pd.isna(ev)     else np.nan,
                "Revenue (₹ Cr)":     round(_to_cr(rev),    0)  if not pd.isna(rev)    else np.nan,
                "EV/EBITDA (x)":      round(ev / ebitda, 1)     if not (pd.isna(ev) or pd.isna(ebitda) or ebitda == 0) else np.nan,
                "P/E (x)":            round(pe, 1)              if not pd.isna(pe)     else np.nan,
                "P/B (x)":            round(pb, 1)              if not pd.isna(pb)     else np.nan,
                "Rev. Growth YoY (%)": round(revgr * 100, 1)   if not pd.isna(revgr)  else np.nan,
            })
        except Exception as e:
            logger.warning(f"Peer fetch failed for {name}: {e}")
            row.update({k: np.nan for k in [
                "Market Cap (₹ Cr)", "EV (₹ Cr)", "Revenue (₹ Cr)",
                "EV/EBITDA (x)", "P/E (x)", "P/B (x)", "Rev. Growth YoY (%)"
            ]})
        return row

    def _build_target_peer_row(self, cd: Dict) -> Dict:
        """Build peer row entry for the target company itself."""
        price    = cd.get("current_price", np.nan)
        shares   = cd.get("shares_cr", np.nan)
        mktcap   = price * shares * _CRORE if not (pd.isna(price) or pd.isna(shares)) else np.nan
        net_debt = cd.get("net_debt_cr", 0) * _CRORE
        ev       = mktcap + net_debt if not pd.isna(mktcap) else np.nan
        rev      = cd.get("latest_revenue_cr", np.nan)
        ebitda   = cd.get("ebitda_cr", [np.nan])[-1]
        return {
            "Company": f"SRF Limited ⭐",
            "Ticker":  TARGET_TICKER,
            "Market Cap (₹ Cr)":   round(mktcap  / _CRORE, 0) if not pd.isna(mktcap)   else np.nan,
            "EV (₹ Cr)":           round(ev / _CRORE, 0)       if not pd.isna(ev)        else np.nan,
            "Revenue (₹ Cr)":      round(rev, 0)               if not pd.isna(rev)       else np.nan,
            "EV/EBITDA (x)":       round(ev / (ebitda * _CRORE), 1) if not (pd.isna(ev) or pd.isna(ebitda) or ebitda == 0) else np.nan,
            "P/E (x)":             np.nan,
            "P/B (x)":             np.nan,
            "Rev. Growth YoY (%)": np.nan,
        }

    # ── Mock / fallback helpers ───────────────────────────────────────────────

    def _build_from_mock(self) -> Dict:
        """Build complete data dictionary from MOCK_DATA constants."""
        md = MOCK_DATA
        data = {
            "ticker":           self.ticker,
            "company_name":     TARGET_NAME,
            "data_source":      "mock_data",
            "fiscal_years":     md["fiscal_years"],
            "revenue_cr":       md["revenue_cr"],
            "ebitda_cr":        md["ebitda_cr"],
            "ebit_cr":          md["ebit_cr"],
            "pat_cr":           md["pat_cr"],
            "da_cr":            md["da_cr"],
            "capex_cr":         md["capex_cr"],
            "net_debt_cr":      md["net_debt_cr"],
            "cash_cr":          md["cash_cr"],
            "total_assets_cr":  md["total_assets_cr"],
            "equity_cr":        md["equity_cr"],
            "shares_cr":        md["shares_cr"],
            "current_price":    md["current_price"],
            "market_cap_cr":    md["current_price"] * md["shares_cr"],  # price × shares(cr) → Cr
            "52w_high":         md["52w_high"],
            "52w_low":          md["52w_low"],
            "beta":             md["beta"],
            "eps":              md["eps"],
            "bvps":             md["bvps"],
            "latest_revenue_cr":md["revenue_cr"][-1],
        }
        logger.info("Using mock financial data (yfinance unavailable).")
        return data

    def _mock_timeseries(self) -> Dict:
        """Return timeseries financial fields from mock data."""
        md = MOCK_DATA
        return {
            "fiscal_years": md["fiscal_years"],
            "revenue_cr":   md["revenue_cr"],
            "ebitda_cr":    md["ebitda_cr"],
            "pat_cr":       md["pat_cr"],
            "da_cr":        md["da_cr"],
        }

    def _mock_price_history(self) -> pd.DataFrame:
        """Generate synthetic 5-year price history around mock current price."""
        import datetime
        base_price = MOCK_DATA["current_price"]
        dates = pd.date_range(end=datetime.date.today(), periods=1260, freq="B")
        np.random.seed(42)
        log_returns = np.random.normal(0.0005, 0.018, len(dates))
        prices = base_price * np.exp(np.cumsum(log_returns) - np.cumsum(log_returns)[-1])
        return pd.DataFrame({
            "Open":   prices * 0.998,
            "High":   prices * 1.012,
            "Low":    prices * 0.988,
            "Close":  prices,
            "Volume": np.random.randint(200_000, 2_000_000, len(dates)),
        }, index=dates)

    def _mock_peer_data(self) -> pd.DataFrame:
        """Return mock peer comparables table."""
        rows = [
            {"Company": "SRF Limited ⭐",         "Ticker": "SRF.NS",          "Market Cap (₹ Cr)": 64_000, "EV (₹ Cr)": 69_500, "Revenue (₹ Cr)": 14_600, "EV/EBITDA (x)": 24.8, "P/E (x)": 75.3, "P/B (x)": 5.1, "Rev. Growth YoY (%)": -7.6},
            {"Company": "Aarti Industries",        "Ticker": "AARTIIND.NS",     "Market Cap (₹ Cr)": 15_200, "EV (₹ Cr)": 18_800, "Revenue (₹ Cr)":  7_100, "EV/EBITDA (x)": 19.2, "P/E (x)": 42.1, "P/B (x)": 3.8, "Rev. Growth YoY (%)":  4.2},
            {"Company": "Navin Fluorine Intl.",    "Ticker": "NAVINFLUOR.NS",   "Market Cap (₹ Cr)": 16_800, "EV (₹ Cr)": 16_400, "Revenue (₹ Cr)":  2_400, "EV/EBITDA (x)": 31.5, "P/E (x)": 65.0, "P/B (x)": 8.2, "Rev. Growth YoY (%)": -8.1},
            {"Company": "Gujarat Fluorochem.",     "Ticker": "GUJFLUORO.NS",    "Market Cap (₹ Cr)": 22_100, "EV (₹ Cr)": 22_800, "Revenue (₹ Cr)":  4_900, "EV/EBITDA (x)": 28.4, "P/E (x)": 58.2, "P/B (x)": 7.1, "Rev. Growth YoY (%)": -12.4},
            {"Company": "Deepak Nitrite",          "Ticker": "DEEPAKNTR.NS",    "Market Cap (₹ Cr)": 21_400, "EV (₹ Cr)": 20_900, "Revenue (₹ Cr)":  7_300, "EV/EBITDA (x)": 17.8, "P/E (x)": 34.5, "P/B (x)": 4.2, "Rev. Growth YoY (%)":  6.8},
            {"Company": "Vinati Organics",         "Ticker": "VINATIORGA.NS",   "Market Cap (₹ Cr)": 17_900, "EV (₹ Cr)": 17_200, "Revenue (₹ Cr)":  2_100, "EV/EBITDA (x)": 32.1, "P/E (x)": 52.8, "P/B (x)": 9.6, "Rev. Growth YoY (%)":  3.2},
            {"Company": "Fine Organics",           "Ticker": "FINEORG.NS",      "Market Cap (₹ Cr)":  8_200, "EV (₹ Cr)":  7_800, "Revenue (₹ Cr)":  2_400, "EV/EBITDA (x)": 18.9, "P/E (x)": 38.4, "P/B (x)": 7.8, "Rev. Growth YoY (%)": -2.1},
            {"Company": "Sudarshan Chemical",      "Ticker": "SUDARSCHEM.NS",   "Market Cap (₹ Cr)":  4_100, "EV (₹ Cr)":  4_600, "Revenue (₹ Cr)":  2_800, "EV/EBITDA (x)": 14.2, "P/E (x)": 31.2, "P/B (x)": 3.1, "Rev. Growth YoY (%)":  5.5},
            {"Company": "Balaji Amines",           "Ticker": "BALAMINES.NS",    "Market Cap (₹ Cr)":  3_800, "EV (₹ Cr)":  3_900, "Revenue (₹ Cr)":  2_200, "EV/EBITDA (x)": 13.6, "P/E (x)": 27.4, "P/B (x)": 4.4, "Rev. Growth YoY (%)":  1.8},
        ]
        return pd.DataFrame(rows)
