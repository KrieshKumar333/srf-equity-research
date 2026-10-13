"""
dcf_model.py — 3-Scenario DCF with stage-dependent capex and sensitivity analysis.

Key design decisions:
  • Stage-dependent capex: high during SRF's investment phase (Yr1-2), tapering
    to normalised levels (Yr3-5) as new specialty chem plants ramp utilisation.
    This is the single most important modelling choice for SRF; a flat capex
    assumption dramatically underestimates FCF in the normalisation years.
  • EBITDA margin: gradually ramps from FY24 level to the scenario steady-state
    by Year 3, reflecting operational leverage on new capacity.
  • Floating-point safe: all comparisons use tolerance, not exact equality.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .config import (
    DA_PCT_REVENUE, NWC_DELTA_PCT, TAX_RATE, PROJECTION_YEARS,
    SENSITIVITY_WACC_RANGE, SENSITIVITY_TGROWTH_RANGE,
    RISK_FREE_RATE, EQUITY_RISK_PREMIUM, DEBT_COST_PRE_TAX, DEBT_TO_EV_RATIO,
    MOCK_DATA,
)
from . import config as _cfg   # dynamic lookup — always reads current SCENARIOS

logger = logging.getLogger(__name__)

_EPS = 1e-9   # tolerance for floating-point equality checks


# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class DCFOutput:
    scenario_name:     str
    projection_years:  List[int]
    revenue:           List[float]
    ebitda:            List[float]
    ebitda_margin_pct: List[float]
    da:                List[float]
    ebit:              List[float]
    nopat:             List[float]
    capex:             List[float]
    capex_pct:         List[float]    # capex as % of revenue each year
    delta_nwc:         List[float]
    fcf:               List[float]
    pv_fcf:            List[float]
    terminal_value:    float
    pv_terminal:       float
    enterprise_value:  float
    net_debt_cr:       float
    equity_value_cr:   float
    shares_cr:         float
    intrinsic_value:   float          # ₹ per share
    current_price:     float
    upside_pct:        float
    wacc:              float
    terminal_growth:   float
    ebitda_margin:     float
    capex_pct_yr1_2:   float
    capex_pct_yr3_5:   float
    tv_pct_of_ev:      float          # terminal value as % of EV (sanity check)


# ─────────────────────────────────────────────────────────────────────────────
class DCFModel:
    """
    Discounted Cash Flow model for SRF Limited.

    Features:
      - 5-year explicit FCFF projection
      - Stage-dependent capex (investment phase → normalised)
      - Graduated EBITDA margin ramp (from FY24 base → scenario steady-state)
      - Gordon Growth Model terminal value
      - 3 scenarios: Bull / Base / Bear
      - WACC × Terminal Growth sensitivity tables
      - Waterfall decomposition of enterprise value
    """

    def __init__(
        self,
        base_revenue_cr: float,
        net_debt_cr:     float,
        shares_cr:       float,
        current_price:   float,
        beta:            float = 1.1,
        base_ebitda_margin: float = 0.192,  # FY24 actual (~19.2%)
    ) -> None:
        self.base_revenue_cr    = base_revenue_cr
        self.net_debt_cr        = net_debt_cr
        self.shares_cr          = shares_cr
        self.current_price      = current_price
        self.beta               = beta
        self.base_ebitda_margin = base_ebitda_margin
        self._results: Dict[str, DCFOutput] = {}

    # ── WACC ──────────────────────────────────────────────────────────────────

    def implied_wacc(self) -> float:
        """CAPM-based WACC using India macro parameters."""
        ke = RISK_FREE_RATE + self.beta * EQUITY_RISK_PREMIUM
        kd = DEBT_COST_PRE_TAX * (1 - TAX_RATE)
        return (1 - DEBT_TO_EV_RATIO) * ke + DEBT_TO_EV_RATIO * kd

    # ── Single scenario ───────────────────────────────────────────────────────

    def run_scenario(self, scenario_name: str) -> DCFOutput:
        """Run one scenario; cache and return a DCFOutput."""
        if scenario_name in self._results:
            return self._results[scenario_name]

        sc = _cfg.SCENARIOS[scenario_name]
        years = list(range(1, PROJECTION_YEARS + 1))

        revenues, ebitdas, em_pcts, das, ebits = [], [], [], [], []
        nopats, capexes, capex_pcts, dnwcs, fcfs = [], [], [], [], []

        prev_rev = self.base_revenue_cr

        for yr in years:
            # ── Revenue ───────────────────────────────────────────────────────
            g   = sc.rev_growth_yr1_3 if yr <= 3 else sc.rev_growth_yr4_5
            rev = prev_rev * (1 + g)

            # ── EBITDA margin: ramp linearly from FY24 base → steady-state ───
            # Reaches full steady-state by Year 3; avoids step-change assumption.
            if yr <= 3:
                em = self.base_ebitda_margin + (sc.ebitda_margin - self.base_ebitda_margin) * (yr / 3)
            else:
                em = sc.ebitda_margin
            ebitda = rev * em

            # ── D&A, EBIT, NOPAT ──────────────────────────────────────────────
            da    = rev * DA_PCT_REVENUE
            ebit  = ebitda - da
            nopat = ebit * (1 - TAX_RATE)

            # ── Stage-dependent capex ─────────────────────────────────────────
            capex_pct = sc.capex_pct_yr1_2 if yr <= 2 else sc.capex_pct_yr3_5
            capex     = rev * capex_pct

            # ── Incremental NWC ───────────────────────────────────────────────
            delta_nwc = (rev - prev_rev) * NWC_DELTA_PCT

            # ── FCFF ──────────────────────────────────────────────────────────
            fcf = nopat + da - capex - delta_nwc

            revenues.append(round(rev,       1))
            ebitdas.append(round(ebitda,     1))
            em_pcts.append(round(em * 100,   2))
            das.append(round(da,             1))
            ebits.append(round(ebit,         1))
            nopats.append(round(nopat,       1))
            capexes.append(round(capex,      1))
            capex_pcts.append(round(capex_pct * 100, 1))
            dnwcs.append(round(delta_nwc,    1))
            fcfs.append(round(fcf,           1))

            prev_rev = rev

        # ── Discount FCFs ─────────────────────────────────────────────────────
        wacc = sc.wacc
        disc = [(1 / (1 + wacc) ** yr) for yr in years]
        pv_fcfs = [round(f * d, 2) for f, d in zip(fcfs, disc)]

        # ── Terminal value (Gordon Growth on Year-5 FCF) ──────────────────────
        if wacc <= sc.terminal_growth + _EPS:
            logger.error(f"[{scenario_name}] WACC ({wacc:.2%}) ≤ TG rate "
                         f"({sc.terminal_growth:.2%}). Terminal value infinite — "
                         f"increase WACC or decrease terminal growth.")
            tv, pv_tv = 0.0, 0.0
        else:
            tv   = fcfs[-1] * (1 + sc.terminal_growth) / (wacc - sc.terminal_growth)
            pv_tv = tv * disc[-1]

        # ── Bridge to equity value ────────────────────────────────────────────
        ev              = sum(pv_fcfs) + pv_tv
        equity_value_cr = ev - self.net_debt_cr
        intrinsic_value = (equity_value_cr / self.shares_cr) if self.shares_cr > 0 else np.nan
        upside_pct      = (intrinsic_value / self.current_price - 1) * 100 \
                          if (self.current_price > 0 and not np.isnan(intrinsic_value)) else np.nan
        tv_pct          = (pv_tv / ev * 100) if ev > _EPS else np.nan

        result = DCFOutput(
            scenario_name     = scenario_name,
            projection_years  = years,
            revenue           = revenues,
            ebitda            = ebitdas,
            ebitda_margin_pct = em_pcts,
            da                = das,
            ebit              = ebits,
            nopat             = nopats,
            capex             = capexes,
            capex_pct         = capex_pcts,
            delta_nwc         = dnwcs,
            fcf               = fcfs,
            pv_fcf            = pv_fcfs,
            terminal_value    = round(tv,    1),
            pv_terminal       = round(pv_tv, 1),
            enterprise_value  = round(ev,    1),
            net_debt_cr       = self.net_debt_cr,
            equity_value_cr   = round(equity_value_cr, 1),
            shares_cr         = self.shares_cr,
            intrinsic_value   = round(intrinsic_value, 1) if not np.isnan(intrinsic_value) else np.nan,
            current_price     = self.current_price,
            upside_pct        = round(upside_pct, 1) if not np.isnan(upside_pct) else np.nan,
            wacc              = wacc,
            terminal_growth   = sc.terminal_growth,
            ebitda_margin     = sc.ebitda_margin,
            capex_pct_yr1_2   = sc.capex_pct_yr1_2,
            capex_pct_yr3_5   = sc.capex_pct_yr3_5,
            tv_pct_of_ev      = round(tv_pct, 1) if not np.isnan(tv_pct) else np.nan,
        )

        self._results[scenario_name] = result
        logger.info(
            f"[{scenario_name}] IV: ₹{intrinsic_value:,.0f} | "
            f"Upside: {upside_pct:+.1f}% | EV: ₹{ev:,.0f} Cr | "
            f"TV%: {tv_pct:.0f}%"
        )
        return result

    # ── All scenarios ─────────────────────────────────────────────────────────

    def run_all_scenarios(self) -> Dict[str, DCFOutput]:
        for name in _cfg.SCENARIOS:
            self.run_scenario(name)
        return self._results

    def scenario_summary_table(self) -> pd.DataFrame:
        if not self._results:
            self.run_all_scenarios()
        rows = []
        for name, res in self._results.items():
            sc = _cfg.SCENARIOS[name]
            rows.append({
                "Scenario":               name,
                "Rev CAGR Yr1–3":         f"{sc.rev_growth_yr1_3:.0%}",
                "Rev CAGR Yr4–5":         f"{sc.rev_growth_yr4_5:.0%}",
                "EBITDA Margin (SS)":      f"{sc.ebitda_margin:.0%}",
                "Capex% Yr1-2 / Yr3-5":   f"{sc.capex_pct_yr1_2:.0%} / {sc.capex_pct_yr3_5:.0%}",
                "WACC":                    f"{res.wacc:.1%}",
                "Terminal Growth":         f"{res.terminal_growth:.1%}",
                "TV% of EV":               f"{res.tv_pct_of_ev:.0f}%",
                "EV (₹ Cr)":              f"{res.enterprise_value:,.0f}",
                "Intrinsic Value (₹/sh)":  f"{res.intrinsic_value:,.1f}",
                "Upside / (Downside)":     f"{res.upside_pct:+.1f}%",
            })
        return pd.DataFrame(rows).set_index("Scenario")

    def build_dcf_table(self, scenario_name: str) -> pd.DataFrame:
        res = self._results.get(scenario_name) or self.run_scenario(scenario_name)
        rows = []
        for i, yr in enumerate(res.projection_years):
            rows.append({
                "Year":                  f"FY+{yr}",
                "Revenue (₹ Cr)":        res.revenue[i],
                "EBITDA Margin (%)":     res.ebitda_margin_pct[i],
                "EBITDA (₹ Cr)":         res.ebitda[i],
                "D&A (₹ Cr)":            res.da[i],
                "EBIT (₹ Cr)":           res.ebit[i],
                "NOPAT (₹ Cr)":          res.nopat[i],
                "Capex% of Rev":         res.capex_pct[i],
                "(−) Capex (₹ Cr)":     -res.capex[i],
                "(−) ΔNWC (₹ Cr)":      -res.delta_nwc[i],
                "FCF (₹ Cr)":            res.fcf[i],
                "PV of FCF (₹ Cr)":      res.pv_fcf[i],
            })
        rows.append({
            "Year":                "Terminal Value",
            "Revenue (₹ Cr)":      None,
            "EBITDA Margin (%)":   None,
            "EBITDA (₹ Cr)":       None,
            "D&A (₹ Cr)":          None,
            "EBIT (₹ Cr)":         None,
            "NOPAT (₹ Cr)":        None,
            "Capex% of Rev":       None,
            "(−) Capex (₹ Cr)":   None,
            "(−) ΔNWC (₹ Cr)":    None,
            "FCF (₹ Cr)":          res.terminal_value,
            "PV of FCF (₹ Cr)":    res.pv_terminal,
        })
        return pd.DataFrame(rows).set_index("Year")

    # ── Sensitivity tables ────────────────────────────────────────────────────

    def sensitivity_table(
        self,
        scenario_name: str = "Base",
        metric: str = "intrinsic_value",
    ) -> pd.DataFrame:
        """WACC × Terminal Growth rate sensitivity heatmap."""
        res = self._results.get(scenario_name) or self.run_scenario(scenario_name)
        sc  = _cfg.SCENARIOS[scenario_name]
        base_wacc = res.wacc
        base_tg   = res.terminal_growth

        wacc_vals = [round(base_wacc + dw, 4) for dw in SENSITIVITY_WACC_RANGE]
        tg_vals   = [round(base_tg   + dt, 4) for dt in SENSITIVITY_TGROWTH_RANGE]

        grid: Dict[str, Dict] = {}
        for wv in wacc_vals:
            col: Dict = {}
            for tv in tg_vals:
                iv, up = self._quick_dcf(sc, wv, tv)
                col[f"TG {tv:.1%}"] = round(iv if metric == "intrinsic_value" else up, 1)
            grid[f"WACC {wv:.1%}"] = col
        return pd.DataFrame(grid).T

    def _quick_dcf(self, sc, wacc_v: float, tg_v: float):
        """Fast DCF pass for sensitivity grid; reuses scenario growth + margin + capex."""
        prev = self.base_revenue_cr
        pv_sum = 0.0
        last_fcf = 0.0
        for yr in range(1, PROJECTION_YEARS + 1):
            g   = sc.rev_growth_yr1_3 if yr <= 3 else sc.rev_growth_yr4_5
            rev = prev * (1 + g)
            em  = self.base_ebitda_margin + (sc.ebitda_margin - self.base_ebitda_margin) * (min(yr, 3) / 3)
            da  = rev * DA_PCT_REVENUE
            nopat = (rev * em - da) * (1 - TAX_RATE)
            cap_p = sc.capex_pct_yr1_2 if yr <= 2 else sc.capex_pct_yr3_5
            fcf   = nopat + da - rev * cap_p - (rev - prev) * NWC_DELTA_PCT
            pv_sum  += fcf / (1 + wacc_v) ** yr
            last_fcf = fcf
            prev = rev

        if wacc_v > tg_v + _EPS:
            tv   = last_fcf * (1 + tg_v) / (wacc_v - tg_v)
            pv_tv = tv / (1 + wacc_v) ** PROJECTION_YEARS
        else:
            pv_tv = 0.0

        ev = pv_sum + pv_tv
        eq = ev - self.net_debt_cr
        iv = (eq / self.shares_cr) if self.shares_cr > 0 else np.nan
        up = (iv / self.current_price - 1) * 100 if (self.current_price > 0 and not np.isnan(iv)) else np.nan
        return iv, up

    def waterfall_components(self, scenario_name: str = "Base") -> Dict:
        res = self._results.get(scenario_name) or self.run_scenario(scenario_name)
        return {
            "labels": [f"PV FCF Yr{yr}" for yr in res.projection_years] + ["PV Terminal", "Enterprise Value"],
            "values": res.pv_fcf + [res.pv_terminal, res.enterprise_value],
        }

    # ── Validation helper (float-safe) ────────────────────────────────────────

    def validate(self, scenario_name: str = "Base", tol: float = 1.0) -> bool:
        """Sanity-check EV bridge; tolerance in ₹ Crore."""
        res = self.run_scenario(scenario_name)
        ev_check = sum(res.pv_fcf) + res.pv_terminal
        eq_check = res.enterprise_value - res.net_debt_cr

        ok_ev = abs(res.enterprise_value - ev_check) < tol
        ok_eq = abs(res.equity_value_cr - eq_check)  < tol
        if not ok_ev:
            logger.warning(f"EV mismatch: stored={res.enterprise_value:.2f}, recomputed={ev_check:.2f}")
        if not ok_eq:
            logger.warning(f"Equity bridge mismatch: stored={res.equity_value_cr:.2f}, expected={eq_check:.2f}")
        return ok_ev and ok_eq
