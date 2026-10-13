"""
report_generator.py — Generates a professional PDF research note using ReportLab.
Layout mirrors the structure of a real sell-side equity research note.
"""

from __future__ import annotations

import io
import logging
from datetime import date
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, Image, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

from .config import (
    TARGET_NAME, SECTOR, EXCHANGE, ANALYST_NAME, INSTITUTION, REPORT_DATE, PDF_OUTPUT
)

logger = logging.getLogger(__name__)

# ── Color palette (ReportLab HexColor) ───────────────────────────────────────
NAVY    = colors.HexColor("#0D2B59")
LIGHT_B = colors.HexColor("#E8EEF8")
GRAY    = colors.HexColor("#F5F5F5")
DKGRAY  = colors.HexColor("#444444")
GREEN   = colors.HexColor("#1A6B3A")
RED_C   = colors.HexColor("#9B2020")
GOLD    = colors.HexColor("#C8A000")
WHITE   = colors.white
BLACK   = colors.black


# ─────────────────────────────────────────────────────────────────────────────
class ResearchNoteGenerator:
    """
    Produces a 6–8 page PDF research note with:
      • Cover / header
      • Executive Summary + Recommendation
      • Business Description
      • Financial Analysis (charts + tables)
      • DCF Valuation Summary
      • Peer Comparables
      • Investment Thesis & Key Risks
    """

    def __init__(
        self,
        summary: Dict,
        ratios_df: pd.DataFrame,
        dcf_results: Dict,
        peer_df: pd.DataFrame,
        output_path: str = PDF_OUTPUT,
    ) -> None:
        self.summary    = summary
        self.ratios     = ratios_df
        self.dcf        = dcf_results
        self.peers      = peer_df
        self.output_path = output_path
        self._styles    = self._build_styles()

    # ── Style registry ────────────────────────────────────────────────────────

    def _build_styles(self) -> Dict:
        base = getSampleStyleSheet()
        styles = {
            "title": ParagraphStyle("Title", parent=base["Normal"],
                fontSize=18, textColor=NAVY, fontName="Helvetica-Bold",
                spaceAfter=6, alignment=TA_LEFT),
            "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"],
                fontSize=10, textColor=DKGRAY, fontName="Helvetica",
                spaceAfter=4),
            "h2": ParagraphStyle("H2", parent=base["Normal"],
                fontSize=12, textColor=WHITE, fontName="Helvetica-Bold",
                backColor=NAVY, borderPad=4, spaceAfter=4, leading=18),
            "h3": ParagraphStyle("H3", parent=base["Normal"],
                fontSize=10, textColor=NAVY, fontName="Helvetica-Bold",
                spaceAfter=3),
            "body": ParagraphStyle("Body", parent=base["Normal"],
                fontSize=9, fontName="Helvetica", leading=14,
                textColor=BLACK, spaceAfter=6, alignment=TA_JUSTIFY),
            "bullet": ParagraphStyle("Bullet", parent=base["Normal"],
                fontSize=9, fontName="Helvetica", leading=13,
                leftIndent=12, bulletIndent=4, spaceAfter=3),
            "kpi_label": ParagraphStyle("KpiLabel", parent=base["Normal"],
                fontSize=8, textColor=DKGRAY, fontName="Helvetica"),
            "kpi_value": ParagraphStyle("KpiValue", parent=base["Normal"],
                fontSize=13, textColor=NAVY, fontName="Helvetica-Bold"),
            "footer": ParagraphStyle("Footer", parent=base["Normal"],
                fontSize=7, textColor=DKGRAY, fontName="Helvetica",
                alignment=TA_CENTER),
            "disclaimer": ParagraphStyle("Disclaimer", parent=base["Normal"],
                fontSize=7, textColor=DKGRAY, fontName="Helvetica-Oblique",
                leading=9, alignment=TA_LEFT),
        }
        return styles

    # ── Public: generate PDF ──────────────────────────────────────────────────

    def generate(self) -> str:
        """Build and save the PDF research note. Returns output path."""
        doc = BaseDocTemplate(
            self.output_path,
            pagesize=A4,
            leftMargin=1.8 * cm, rightMargin=1.8 * cm,
            topMargin=2.2 * cm, bottomMargin=2.2 * cm,
        )
        main_frame = Frame(doc.leftMargin, doc.bottomMargin,
                           doc.width, doc.height, id="main")
        doc.addPageTemplates([PageTemplate(id="main", frames=[main_frame],
                                           onPage=self._draw_header_footer)])

        story: List = []
        story += self._cover_section()
        story += self._executive_summary()
        story += self._business_description()
        story += self._financial_analysis()
        story += self._valuation_section()
        story += self._peer_comparables()
        story += self._investment_thesis_risks()
        story += self._disclaimer_section()

        doc.build(story)
        logger.info(f"PDF research note saved → {self.output_path}")
        return self.output_path

    # ── Page header / footer callback ─────────────────────────────────────────

    def _draw_header_footer(self, canvas, doc):
        canvas.saveState()
        # Top bar
        canvas.setFillColor(NAVY)
        canvas.rect(doc.leftMargin - 1 * cm, A4[1] - 1.5 * cm, A4[0] - 2 * cm, 0.5 * cm, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(doc.leftMargin, A4[1] - 1.25 * cm,
                          f"{TARGET_NAME} ({EXCHANGE}) — Independent Equity Research")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(A4[0] - doc.rightMargin, A4[1] - 1.25 * cm, REPORT_DATE)
        # Bottom bar
        canvas.setFillColor(NAVY)
        canvas.rect(doc.leftMargin - 1 * cm, doc.bottomMargin - 0.8 * cm, A4[0] - 2 * cm, 0.25 * cm, fill=1, stroke=0)
        canvas.setFillColor(DKGRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(doc.leftMargin, doc.bottomMargin - 0.6 * cm,
                          f"Page {canvas.getPageNumber()} | {ANALYST_NAME} | {INSTITUTION}")
        canvas.drawRightString(A4[0] - doc.rightMargin, doc.bottomMargin - 0.6 * cm,
                               "FOR INFORMATIONAL PURPOSES ONLY — NOT INVESTMENT ADVICE")
        canvas.restoreState()

    # ── Section builders ──────────────────────────────────────────────────────

    def _cover_section(self) -> List:
        s = self.summary
        base = self.dcf.get("Base")
        rating = "BUY" if (base and base.upside_pct > 15) else \
                 ("SELL" if (base and base.upside_pct < -10) else "HOLD")
        rating_color = GREEN if rating == "BUY" else (RED_C if rating == "SELL" else GOLD)

        elements = [Spacer(1, 0.3 * cm)]
        elements.append(Paragraph(TARGET_NAME, self._styles["title"]))
        elements.append(Paragraph(
            f"{SECTOR} | {EXCHANGE} | CMP: ₹{s.get('current_price', 'N/A'):.0f} | "
            f"Market Cap: ₹{s.get('market_cap_cr', 0):,.0f} Cr",
            self._styles["subtitle"]))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=NAVY))
        elements.append(Spacer(1, 0.3 * cm))

        # KPI table
        kpi_data = [
            ["CMP (₹)", "52W High", "52W Low", "Market Cap (₹ Cr)", "EV (₹ Cr)", "Beta"],
            [
                f"₹{s.get('current_price', 0):.0f}",
                f"₹{s.get('52w_high', 0):.0f}",
                f"₹{s.get('52w_low', 0):.0f}",
                f"₹{s.get('market_cap_cr', 0):,.0f}",
                f"₹{s.get('ev_cr', 0):,.0f}",
                f"{s.get('beta', 1.0):.2f}",
            ],
        ]
        kpi_table = Table(kpi_data, colWidths=[2.8 * cm] * 6)
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 8),
            ("BACKGROUND",  (0, 1), (-1, 1), LIGHT_B),
            ("FONTNAME",    (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 1), (-1, 1), 10),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, 1), [LIGHT_B]),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 0.4 * cm))

        # Rating / target price box
        rating_data = [
            ["RECOMMENDATION", "TARGET PRICE (Base)", "UPSIDE / (DOWNSIDE)", "ANALYST"],
            [rating,
             f"₹{base.intrinsic_value:,.0f}" if base else "N/A",
             f"{base.upside_pct:+.1f}%" if base else "N/A",
             ANALYST_NAME],
        ]
        rt = Table(rating_data, colWidths=[4.2 * cm] * 4)
        rt.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 8),
            ("FONTNAME",    (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 1), (0, 1), 16),
            ("FONTSIZE",    (1, 1), (-1, 1), 12),
            ("TEXTCOLOR",   (0, 1), (0, 1), rating_color),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("GRID",        (0, 0), (-1, -1), 0.5, NAVY),
            ("ROWHEIGHT",   (0, 1), (0, 1), 30),
        ]))
        elements.append(rt)
        elements.append(Spacer(1, 0.5 * cm))
        return elements

    def _executive_summary(self) -> List:
        s = self.summary
        base = self.dcf.get("Base")
        bull = self.dcf.get("Bull")
        bear = self.dcf.get("Bear")

        elements = [Paragraph("EXECUTIVE SUMMARY", self._styles["h2"]), Spacer(1, 0.2 * cm)]
        thesis = (
            f"We initiate coverage on <b>SRF Limited</b> with a <b>{'BUY' if (base and base.upside_pct > 15) else 'HOLD'}</b> "
            f"recommendation and a 12-month Base Case target price of <b>₹{base.intrinsic_value:,.0f}</b> "
            f"({''+str(round(base.upside_pct,1)) if base and base.upside_pct >= 0 else str(round(base.upside_pct,1))}% "
            f"{'upside' if base and base.upside_pct >= 0 else 'downside'} to CMP of ₹{s.get('current_price', 0):.0f}). "
            f"SRF is India's leading specialty chemicals conglomerate with dominant positions in fluorochemicals, "
            f"specialty chemicals, packaging films, and technical textiles. Our conviction stems from three pillars: "
            f"(1) large-scale fluorination capacity investments creating a defensible moat, "
            f"(2) structural tailwinds from China+1 sourcing strategy of global agrochemical and pharma companies, and "
            f"(3) improving FCF generation as the capex cycle moderates from FY26E onwards."
        )
        elements.append(Paragraph(thesis, self._styles["body"]))
        elements.append(Spacer(1, 0.3 * cm))

        # Scenario table
        sc_data = [
            ["Scenario", "Revenue CAGR\n(FY24–FY29E)", "EBITDA Margin", "WACC", "Intrinsic Value (₹/sh)", "Upside"],
        ]
        for sc_name, res in [("Bear", bear), ("Base", base), ("Bull", bull)]:
            from .config import SCENARIOS
            sc = SCENARIOS[sc_name]
            sc_data.append([
                sc_name,
                f"{((sc.rev_growth_yr1_3 * 3 + sc.rev_growth_yr4_5 * 2) / 5):.0%}",
                f"{sc.ebitda_margin:.0%}",
                f"{res.wacc:.1%}" if res else "N/A",
                f"₹{res.intrinsic_value:,.0f}" if res else "N/A",
                f"{res.upside_pct:+.1f}%" if res else "N/A",
            ])
        t = Table(sc_data, colWidths=[2.2 * cm, 3.2 * cm, 2.6 * cm, 2 * cm, 3.4 * cm, 2.4 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 8),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("GRID",        (0, 0), (-1, -1), 0.5, NAVY),
            ("ROWBACKGROUNDS", (1, 1), (-1, -1), [GRAY, LIGHT_B]),
            ("FONTNAME",    (0, 2), (-1, 2), "Helvetica-Bold"),  # Base row bold
        ]))
        elements.append(t)
        return elements

    def _business_description(self) -> List:
        elements = [Spacer(1, 0.5 * cm), Paragraph("BUSINESS DESCRIPTION", self._styles["h2"]), Spacer(1, 0.2 * cm)]
        desc = (
            "SRF Limited, incorporated in 1970 and headquartered in New Delhi, operates across four business segments: "
            "<b>Chemicals</b> (comprising fluorochemicals and specialty chemicals), <b>Packaging Films</b>, "
            "<b>Technical Textiles</b>, and <b>Others</b>. The Chemicals segment—contributing ~50% of revenues—is the "
            "primary value driver and benefits from SRF's proprietary fluorination technology developed over three decades. "
            "The company's fluorination capability positions it as a critical supplier to global agrochemical and pharmaceutical "
            "MNCs seeking China-independent supply chains. <br/><br/>"
            "Key competitive advantages from a chemical engineering perspective: "
        )
        elements.append(Paragraph(desc, self._styles["body"]))
        bullets = [
            "Fluorination chemistry — high technical barriers; complex handling of HF (hydrofluoric acid) limits new entrants",
            "Multipurpose plant (MPP) architecture — rapid product switching between agrochemical and pharmaceutical intermediates",
            "Captive HF production — backward integration into hydrofluoric acid provides cost and supply security",
            "R&D pipeline — 30+ molecules in development for innovator pharma companies (CRAMS model)",
        ]
        for b in bullets:
            elements.append(Paragraph(f"• {b}", self._styles["bullet"]))
        return elements

    def _financial_analysis(self) -> List:
        elements = [Spacer(1, 0.5 * cm), Paragraph("FINANCIAL ANALYSIS", self._styles["h2"]), Spacer(1, 0.2 * cm)]
        elements.append(Paragraph(
            "Historical financials reflect SRF's capital-intensive growth phase. Revenue declined ~7.6% in FY24 vs FY23, "
            "primarily due to a destocking cycle in global agrochemicals and compression in refrigerant gas realisations. "
            "However, structural capacity investments (₹10,000+ Cr capex over FY22–FY25) position SRF for volume-led "
            "recovery as the chemical cycle turns. EBITDA margins have compressed from the peak of ~20% (FY22) to ~19% (FY24) "
            "due to operating deleverage, but are expected to recover toward 22–25% by FY26E–FY27E as new specialty "
            "chemicals capacity ramps up on long-term supply agreements.", self._styles["body"]))

        # Embed revenue + margin chart
        chart_img = self._revenue_ebitda_chart()
        if chart_img:
            elements.append(chart_img)
            elements.append(Spacer(1, 0.3 * cm))

        # Key ratios table
        elements.append(Paragraph("Key Financial Metrics", self._styles["h3"]))
        df = self.ratios
        show_cols = ["Revenue (₹ Cr)", "EBITDA (₹ Cr)", "PAT (₹ Cr)",
                     "EBITDA Margin (%)", "Rev. Growth (%)", "ROCE (%)"]
        avail_cols = [c for c in show_cols if c in df.columns]
        tbl_data = [[""] + list(df.index)]
        for col in avail_cols:
            row = [col]
            for yr in df.index:
                val = df.loc[yr, col]
                row.append("N/A" if pd.isna(val) else f"{val:.1f}")
            tbl_data.append(row)

        col_w = [5.0 * cm] + [2.4 * cm] * len(df.index)
        t = Table(tbl_data, colWidths=col_w)
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
            ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 0), (-1, -1), 8),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME",    (0, 1), (0, -1), "Helvetica-Bold"),
            ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY]),
        ]))
        elements.append(t)
        return elements

    def _valuation_section(self) -> List:
        elements = [Spacer(1, 0.5 * cm), Paragraph("VALUATION", self._styles["h2"]), Spacer(1, 0.2 * cm)]
        base = self.dcf.get("Base")
        elements.append(Paragraph(
            f"Our 5-year DCF model discounts Free Cash Flows to Firm (FCFF) using a Base Case WACC of "
            f"{base.wacc:.1%}. Terminal value is computed using the Gordon Growth Model at a perpetuity growth "
            f"rate of {base.terminal_growth:.1%}, reflecting India's long-term nominal GDP trajectory. "
            f"The terminal value represents {base.pv_terminal / base.enterprise_value:.0%} of Enterprise Value "
            f"in the Base Case — within the acceptable range for a growth chemical company. "
            f"Net debt of ₹{base.net_debt_cr:,.0f} Cr is deducted to derive Equity Value.", self._styles["body"]))

        # Sensitivity note
        elements.append(Paragraph(
            f"Sensitivity analysis (Base Scenario): intrinsic value ranges from "
            f"₹{min(self.dcf.get('Bear', base).intrinsic_value, base.intrinsic_value) * 0.85:.0f} to "
            f"₹{max(self.dcf.get('Bull', base).intrinsic_value, base.intrinsic_value) * 1.05:.0f} per share "
            f"across reasonable WACC (±200bps) and terminal growth (±100bps) assumptions.",
            self._styles["body"]))
        return elements

    def _peer_comparables(self) -> List:
        elements = [Spacer(1, 0.5 * cm), Paragraph("PEER COMPARABLE ANALYSIS", self._styles["h2"]), Spacer(1, 0.2 * cm)]
        df = self.peers
        show_cols = ["Company", "EV/EBITDA (x)", "P/E (x)", "P/B (x)", "Revenue (₹ Cr)", "Rev. Growth YoY (%)"]
        avail_cols = [c for c in show_cols if c in df.columns]
        tbl_data = [avail_cols]
        for _, row_d in df.iterrows():
            row = [str(row_d[c]) if c == "Company" else ("N/A" if pd.isna(row_d[c]) else f"{row_d[c]:.1f}") for c in avail_cols]
            tbl_data.append(row)

        col_w = [4.5 * cm] + [2.4 * cm] * (len(avail_cols) - 1)
        t = Table(tbl_data, colWidths=col_w)
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 8),
            ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
            ("FONTNAME",    (0, 1), (0, 1), "Helvetica-Bold"),  # SRF row
            ("BACKGROUND",  (0, 1), (-1, 1), LIGHT_B),          # SRF row highlight
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 2), (-1, -1), [WHITE, GRAY]),
        ]))
        elements.append(t)
        elements.append(Paragraph(
            "SRF trades at a premium to peers on EV/EBITDA given its best-in-class fluorine chemistry moat and "
            "the optionality in its specialty chemicals pipeline. The premium is partially justified but warrants "
            "monitoring as earnings recovery timelines are uncertain.", self._styles["body"]))
        return elements

    def _investment_thesis_risks(self) -> List:
        elements = [Spacer(1, 0.5 * cm), Paragraph("INVESTMENT THESIS & KEY RISKS", self._styles["h2"]),
                    Spacer(1, 0.2 * cm)]

        elements.append(Paragraph("Investment Thesis", self._styles["h3"]))
        thesis_points = [
            "<b>China+1 tailwind:</b> Global agrochemical and pharma MNCs are diversifying supply chains away from China. "
            "SRF's fluorine chemistry capabilities make it a preferred partner for these transitions, with a robust "
            "multi-year revenue backlog from long-term supply agreements.",
            "<b>Capex cycle peaking:</b> SRF has invested ₹10,000+ Cr over FY22–FY25, building out specialty chemicals "
            "capacity. As capex moderates from FY26, FCF inflection is expected to be significant — a key re-rating catalyst.",
            "<b>Technical moat:</b> Fluorination chemistry (HF handling, cryogenic processes) has a steep learning curve. "
            "Limited Indian or global competitors with comparable technical depth protect SRF's long-term margins.",
        ]
        for pt in thesis_points:
            elements.append(Paragraph(f"• {pt}", self._styles["bullet"]))

        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph("Key Risks", self._styles["h3"]))
        risk_points = [
            "<b>Agrochemical destocking:</b> Global inventory overhang could persist longer than expected, delaying "
            "revenue recovery in the specialty chemicals segment.",
            "<b>Feedstock cost volatility:</b> Crude-linked inputs (HF, chloromethanes) and energy costs are significant. "
            "Inability to pass through cost increases compresses margins.",
            "<b>Capex execution risk:</b> Delays in new capacity commissioning or cost overruns could stretch the "
            "balance sheet; net debt has risen meaningfully.",
            "<b>Regulatory risk:</b> Any adverse change in HFC refrigerant regulations (Kigali Amendment phase-down "
            "schedules) could impact the fluorochemicals revenue stream.",
        ]
        for pt in risk_points:
            elements.append(Paragraph(f"• {pt}", self._styles["bullet"]))
        return elements

    def _disclaimer_section(self) -> List:
        elements = [Spacer(1, 1.0 * cm), HRFlowable(width="100%", thickness=0.5, color=DKGRAY)]
        text = (
            "DISCLAIMER: This research note has been prepared by an independent analyst and is intended solely for "
            "educational and informational purposes. It does not constitute investment advice, a solicitation, or an "
            "offer to buy or sell any securities. The analysis is based on publicly available information and reasonable "
            "assumptions. Actual results may differ materially. The analyst does not hold a position in SRF Limited at "
            "the time of writing. Past performance is not indicative of future results. All financial data sourced from "
            "public filings and market data providers. Not SEBI registered research."
        )
        elements.append(Paragraph(text, self._styles["disclaimer"]))
        return elements

    # ── Embedded chart ────────────────────────────────────────────────────────

    def _revenue_ebitda_chart(self) -> Optional[Image]:
        """Generate an embedded Revenue & EBITDA margin bar + line chart."""
        try:
            years  = list(self.ratios.index)
            rev    = list(self.ratios["Revenue (₹ Cr)"].fillna(0))
            ebitda = list(self.ratios["EBITDA Margin (%)"].fillna(0))

            fig, ax1 = plt.subplots(figsize=(8, 3))
            x = np.arange(len(years))
            bars = ax1.bar(x, rev, color="#0D2B59", alpha=0.85, width=0.55, label="Revenue (₹ Cr)")
            ax1.set_ylabel("Revenue (₹ Cr)", fontsize=8, color="#0D2B59")
            ax1.tick_params(axis="y", labelcolor="#0D2B59", labelsize=8)
            ax1.set_xticks(x)
            ax1.set_xticklabels(years, fontsize=8)
            ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"₹{v:,.0f}"))

            ax2 = ax1.twinx()
            ax2.plot(x, ebitda, color="#C8A000", marker="o", linewidth=2,
                     markersize=5, label="EBITDA Margin (%)")
            ax2.set_ylabel("EBITDA Margin (%)", fontsize=8, color="#C8A000")
            ax2.tick_params(axis="y", labelcolor="#C8A000", labelsize=8)
            ax2.set_ylim(0, max(ebitda) * 1.5 if ebitda else 40)

            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=7)
            ax1.set_title("Revenue and EBITDA Margin — Historical", fontsize=9, pad=8, color="#0D2B59")
            fig.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return Image(buf, width=16 * cm, height=5.5 * cm)
        except Exception as e:
            logger.warning(f"Chart generation failed: {e}")
            return None
