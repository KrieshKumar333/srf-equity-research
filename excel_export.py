"""
excel_export.py — Exports the full equity research model to a formatted Excel workbook.
Uses xlsxwriter for rich formatting (bold headers, conditional formatting, number formats).
"""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np
import pandas as pd
import xlsxwriter

from .config import EXCEL_OUTPUT, TARGET_NAME, REPORT_DATE

logger = logging.getLogger(__name__)

# ─────────── Color palette ────────────────────────────────────────────────────
NAVY   = "#0D2B59"
GOLD   = "#D4A017"
LIGHT  = "#E8EEF8"
WHITE  = "#FFFFFF"
GREEN  = "#1A6B3A"
RED    = "#9B2020"
LGRAY  = "#F5F5F5"


class ExcelExporter:
    """
    Writes four worksheets:
      1. Cover          – summary card
      2. Financials     – historical P&L + ratios
      3. DCF Model      – 3-scenario DCF projection
      4. Peer Comps     – peer comparable table
    """

    def __init__(
        self,
        ratios_df: pd.DataFrame,
        summary: Dict,
        dcf_model,
        peer_df: pd.DataFrame,
        dcf_results: Dict,
        output_path: str = EXCEL_OUTPUT,
    ) -> None:
        self.ratios_df  = ratios_df
        self.summary    = summary
        self.dcf_model  = dcf_model
        self.peer_df    = peer_df
        self.dcf_results = dcf_results
        self.output_path = output_path

    def export(self) -> str:
        """Write the workbook and return the output path."""
        wb = xlsxwriter.Workbook(self.output_path, {"strings_to_numbers": True})
        self._define_formats(wb)
        self._write_cover(wb)
        self._write_financials(wb)
        self._write_dcf(wb)
        self._write_peers(wb)
        wb.close()
        logger.info(f"Excel workbook saved → {self.output_path}")
        return self.output_path

    # ── Format registry ────────────────────────────────────────────────────────

    def _define_formats(self, wb: xlsxwriter.Workbook) -> None:
        """Pre-define all cell formats."""
        self.fmt = {
            "title":  wb.add_format({"bold": True, "font_size": 18, "font_color": NAVY, "align": "center", "valign": "vcenter"}),
            "hdr":    wb.add_format({"bold": True, "font_color": WHITE, "bg_color": NAVY, "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True}),
            "subhdr": wb.add_format({"bold": True, "font_color": NAVY, "bg_color": LIGHT, "border": 1}),
            "num":    wb.add_format({"num_format": "#,##0.0", "border": 1, "align": "right"}),
            "num0":   wb.add_format({"num_format": "#,##0", "border": 1, "align": "right"}),
            "pct":    wb.add_format({"num_format": "0.0%", "border": 1, "align": "right"}),
            "pct1":   wb.add_format({"num_format": "0.0\"%\"", "border": 1, "align": "right"}),
            "label":  wb.add_format({"border": 1, "bold": True}),
            "plain":  wb.add_format({"border": 1}),
            "green":  wb.add_format({"num_format": "0.0\"%\"", "font_color": GREEN, "border": 1, "align": "right"}),
            "red_f":  wb.add_format({"num_format": "0.0\"%\"", "font_color": RED,   "border": 1, "align": "right"}),
            "kpi_lbl":wb.add_format({"bold": True, "font_color": NAVY, "bg_color": LGRAY, "border": 1}),
            "kpi_val":wb.add_format({"bold": True, "font_size": 13, "num_format": "#,##0.0", "border": 1, "align": "center"}),
            "section":wb.add_format({"bold": True, "font_color": WHITE, "bg_color": NAVY, "font_size": 11}),
        }

    # ── Cover sheet ────────────────────────────────────────────────────────────

    def _write_cover(self, wb: xlsxwriter.Workbook) -> None:
        ws = wb.add_worksheet("Cover")
        ws.set_column("A:A", 28)
        ws.set_column("B:B", 22)
        ws.set_column("C:C", 22)
        ws.set_row(0, 50)

        ws.merge_range("A1:C1", f"{TARGET_NAME} — Equity Research", self.fmt["title"])
        ws.merge_range("A2:C2", f"Independent Research | {REPORT_DATE}", wb.add_format({"align": "center", "font_color": "#555555", "italic": True}))

        # KPI cards
        s = self.summary
        base = self.dcf_results.get("Base")
        kpis = [
            ("Current Price (₹)",         s.get("current_price", "N/A")),
            ("52W High / Low (₹)",         f"{s.get('52w_high', 'N/A'):.0f} / {s.get('52w_low', 'N/A'):.0f}"),
            ("Market Cap (₹ Cr)",          s.get("market_cap_cr", "N/A")),
            ("Enterprise Value (₹ Cr)",    s.get("ev_cr", "N/A")),
            ("EV / EBITDA (x)",            s.get("ev_ebitda", "N/A")),
            ("Revenue FY24 (₹ Cr)",        s.get("latest_revenue_cr", "N/A")),
            ("EBITDA FY24 (₹ Cr)",         s.get("latest_ebitda_cr", "N/A")),
            ("EBITDA Margin FY24 (%)",      f"{s.get('ebitda_margin_latest', 0):.1f}%"),
            ("Base Intrinsic Value (₹/sh)", f"₹{base.intrinsic_value:,.0f}" if base else "N/A"),
            ("Upside / (Downside)",         f"{base.upside_pct:+.1f}%" if base else "N/A"),
        ]

        for idx, (label, value) in enumerate(kpis):
            row = idx + 4
            ws.write(row, 0, label, self.fmt["kpi_lbl"])
            ws.write(row, 1, str(value), wb.add_format({"border": 1, "bold": True, "align": "center"}))

        # Rating box
        ws.merge_range("A16:B16", "⭐ RECOMMENDATION", wb.add_format({"bold": True, "bg_color": NAVY, "font_color": WHITE, "align": "center"}))
        rating_val = "BUY" if (base and base.upside_pct > 15) else ("SELL" if (base and base.upside_pct < -10) else "HOLD")
        ws.merge_range("A17:B17", rating_val, wb.add_format({"bold": True, "font_size": 16, "font_color": GREEN if rating_val == "BUY" else RED, "align": "center", "border": 1}))

    # ── Financials sheet ───────────────────────────────────────────────────────

    def _write_financials(self, wb: xlsxwriter.Workbook) -> None:
        ws = wb.add_worksheet("Financials")
        ws.set_column("A:A", 28)
        for col in range(1, len(self.ratios_df) + 1):
            ws.set_column(col, col, 14)

        years = list(self.ratios_df.index)
        ws.merge_range(0, 0, 0, len(years), "Historical Financial Summary — SRF Limited", self.fmt["title"])

        # Headers
        ws.write(1, 0, "Metric", self.fmt["hdr"])
        for i, yr in enumerate(years):
            ws.write(1, i + 1, yr, self.fmt["hdr"])

        # Write rows
        row = 2
        sections = {
            "P&L SUMMARY (₹ Crore)": ["Revenue (₹ Cr)", "EBITDA (₹ Cr)", "PAT (₹ Cr)"],
            "MARGINS": ["EBITDA Margin (%)", "PAT Margin (%)", "EBIT Margin (%)"],
            "GROWTH": ["Rev. Growth (%)", "EBITDA Growth (%)", "PAT Growth (%)"],
            "RETURNS & LEVERAGE": ["ROCE (%)", "ROE (%)", "D/E Ratio (x)", "ND / EBITDA (x)"],
            "PER-SHARE DATA": ["EPS (₹)", "BVPS (₹)"],
        }
        for section_title, cols in sections.items():
            ws.merge_range(row, 0, row, len(years), section_title, self.fmt["section"])
            row += 1
            for metric in cols:
                if metric not in self.ratios_df.columns:
                    continue
                ws.write(row, 0, metric, self.fmt["label"])
                for i, yr in enumerate(years):
                    val = self.ratios_df.loc[yr, metric]
                    if pd.isna(val):
                        ws.write(row, i + 1, "N/A", self.fmt["plain"])
                    else:
                        ws.write(row, i + 1, float(val), self.fmt["num"])
                row += 1

    # ── DCF sheet ──────────────────────────────────────────────────────────────

    def _write_dcf(self, wb: xlsxwriter.Workbook) -> None:
        ws = wb.add_worksheet("DCF Model")
        ws.set_column("A:A", 28)
        for col in range(1, 9):
            ws.set_column(col, col, 14)

        ws.merge_range(0, 0, 0, 8, "DCF Valuation Model — 3-Scenario Analysis", self.fmt["title"])

        # Scenario summary
        ws.write(2, 0, "SCENARIO SUMMARY", self.fmt["section"])
        summary_df = self.dcf_model.scenario_summary_table()
        ws.write(3, 0, "Scenario", self.fmt["hdr"])
        for i, col_name in enumerate(summary_df.columns):
            ws.write(3, i + 1, col_name, self.fmt["hdr"])
        for r_idx, (sc_name, row_data) in enumerate(summary_df.iterrows()):
            ws.write(4 + r_idx, 0, sc_name, self.fmt["label"])
            for c_idx, val in enumerate(row_data):
                ws.write(4 + r_idx, c_idx + 1, str(val), self.fmt["plain"])

        start_row = 10
        for sc_name, res in self.dcf_results.items():
            ws.merge_range(start_row, 0, start_row, 8, f"Scenario: {sc_name}  |  Intrinsic Value: ₹{res.intrinsic_value:,.0f}  |  Upside: {res.upside_pct:+.1f}%", self.fmt["section"])
            dcf_table = self.dcf_model.build_dcf_table(sc_name)
            ws.write(start_row + 1, 0, "Line Item", self.fmt["hdr"])
            for i, col_name in enumerate(dcf_table.columns):
                ws.write(start_row + 1, i + 1, col_name, self.fmt["hdr"])
            for r_idx, (yr_label, row_data) in enumerate(dcf_table.iterrows()):
                ws.write(start_row + 2 + r_idx, 0, yr_label, self.fmt["label"])
                for c_idx, val in enumerate(row_data):
                    if val is None or (isinstance(val, float) and np.isnan(val)):
                        ws.write(start_row + 2 + r_idx, c_idx + 1, "—", self.fmt["plain"])
                    else:
                        ws.write(start_row + 2 + r_idx, c_idx + 1, float(val), self.fmt["num"])
            start_row += len(dcf_table) + 6

        # Sensitivity table
        ws.merge_range(start_row, 0, start_row, 6, "Sensitivity: Intrinsic Value (₹) — Base Scenario  |  WACC vs. Terminal Growth Rate", self.fmt["section"])
        sens = self.dcf_model.sensitivity_table("Base", "intrinsic_value")
        ws.write(start_row + 1, 0, "WACC \\ TG Rate", self.fmt["hdr"])
        for i, col_name in enumerate(sens.columns):
            ws.write(start_row + 1, i + 1, col_name, self.fmt["hdr"])
        for r_idx, (wacc_label, row_data) in enumerate(sens.iterrows()):
            ws.write(start_row + 2 + r_idx, 0, wacc_label, self.fmt["label"])
            for c_idx, val in enumerate(row_data):
                ws.write(start_row + 2 + r_idx, c_idx + 1, float(val), self.fmt["num0"])

    # ── Peers sheet ────────────────────────────────────────────────────────────

    def _write_peers(self, wb: xlsxwriter.Workbook) -> None:
        ws = wb.add_worksheet("Peer Comparables")

        # Exclude the raw Ticker column from display — not useful in Excel
        display_cols = [c for c in self.peer_df.columns if c != "Ticker"]
        num_cols = len(display_cols)

        ws.set_column("A:A", 26)
        for col in range(1, num_cols):
            ws.set_column(col, col, 16)

        ws.merge_range(0, 0, 0, num_cols - 1,
                       "Peer Comparable Analysis — Indian Specialty Chemicals",
                       self.fmt["title"])
        for i, col_name in enumerate(display_cols):
            ws.write(2, i, col_name, self.fmt["hdr"])

        for r_idx, row_data in self.peer_df.iterrows():
            is_srf = "SRF" in str(row_data["Company"])
            row_fmt = wb.add_format({
                "border": 1,
                "bold": is_srf,
                "bg_color": LIGHT if is_srf else WHITE,
            })
            for c_idx, col_name in enumerate(display_cols):
                val = row_data[col_name]
                # Write strings as strings, numbers as numbers, NaN as N/A
                if isinstance(val, str):
                    ws.write(3 + r_idx, c_idx, val, row_fmt)
                elif pd.isna(val):
                    ws.write(3 + r_idx, c_idx, "N/A", self.fmt["plain"])
                else:
                    try:
                        ws.write(3 + r_idx, c_idx, float(val), self.fmt["num"])
                    except (TypeError, ValueError):
                        ws.write(3 + r_idx, c_idx, str(val), self.fmt["plain"])

        # Peer median row (skip Company column, only average numeric columns)
        med_row = len(self.peer_df) + 4
        ws.write(med_row, 0, "Peer Median (ex-SRF)", self.fmt["subhdr"])
        peers_only = self.peer_df[~self.peer_df["Company"].str.contains("SRF", na=False)]
        for c_idx, col_name in enumerate(display_cols[1:], start=1):
            try:
                numeric_col = pd.to_numeric(peers_only[col_name], errors="coerce")
                med = numeric_col.median()
                ws.write(med_row, c_idx,
                         round(float(med), 1) if not pd.isna(med) else "N/A",
                         self.fmt["num"])
            except Exception:
                ws.write(med_row, c_idx, "N/A", self.fmt["plain"])
