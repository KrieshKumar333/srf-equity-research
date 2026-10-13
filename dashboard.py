"""
dashboard.py — SRF Limited Equity Research Dashboard
Run: python -m streamlit run dashboard.py
"""
from __future__ import annotations
import sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
logging.basicConfig(level=logging.WARNING)

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from src.config import TARGET_NAME, SECTOR, EXCHANGE, SCENARIOS
from src.data_fetcher import DataFetcher
from src.financial_analysis import FinancialAnalyzer
from src.dcf_model import DCFModel

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SRF Ltd — Equity Research",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 SRF Limited")
    st.caption(f"{EXCHANGE} · {SECTOR}")
    st.divider()

    use_mock = st.toggle("Use offline demo data", value=False)
    st.divider()

    st.subheader("🟢 Bull Case")
    bull_g1 = st.number_input("Rev Growth Yr1-3 %", 5, 35, 20, 1, key="bg1") / 100
    bull_g2 = st.number_input("Rev Growth Yr4-5 %", 5, 25, 15, 1, key="bg2") / 100
    bull_em = st.number_input("EBITDA Margin %",    10, 35, 25, 1, key="bem") / 100
    bull_wc = st.number_input("WACC %",           8.0,20.0,12.0,0.5,key="bwc") / 100
    bull_tg = st.number_input("Terminal Growth %", 2.0, 8.0, 6.0,0.5,key="btg") / 100

    st.divider()
    st.subheader("🔵 Base Case")
    base_g1 = st.number_input("Rev Growth Yr1-3 %", 5, 35, 12, 1, key="bg1b") / 100
    base_g2 = st.number_input("Rev Growth Yr4-5 %", 5, 25,  8, 1, key="bg2b") / 100
    base_em = st.number_input("EBITDA Margin %",    10, 35, 22, 1, key="bemb") / 100
    base_wc = st.number_input("WACC %",           8.0,20.0,13.5,0.5,key="bwcb") / 100
    base_tg = st.number_input("Terminal Growth %", 2.0, 8.0, 5.0,0.5,key="btgb") / 100

    st.divider()
    st.subheader("🔴 Bear Case")
    bear_g1 = st.number_input("Rev Growth Yr1-3 %", 1, 20,  4, 1, key="bg1r") / 100
    bear_g2 = st.number_input("Rev Growth Yr4-5 %", 1, 15,  3, 1, key="bg2r") / 100
    bear_em = st.number_input("EBITDA Margin %",    10, 30, 18, 1, key="bemr") / 100
    bear_wc = st.number_input("WACC %",          10.0,22.0,15.5,0.5,key="bwcr") / 100
    bear_tg = st.number_input("Terminal Growth %", 1.0, 6.0, 3.5,0.5,key="btgr") / 100

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Fetching SRF data from Yahoo Finance…")
def load_data(mock: bool):
    f  = DataFetcher(use_mock=mock)
    cd = f.get_company_data()
    ph = f.get_price_history()
    pd_= f.get_peer_data()
    return cd, ph, pd_

try:
    company_data, price_hist, peer_df = load_data(use_mock)
except Exception as e:
    st.error(f"Data error: {e}. Enable 'offline demo data' in sidebar.")
    st.stop()

analyzer  = FinancialAnalyzer(company_data)
ratios_df = analyzer.compute_ratios()
summary   = analyzer.compute_summary_stats()

# ── Run DCF with user inputs ───────────────────────────────────────────────────
def run_dcf(cd, bull_g1, bull_g2, bull_em, bull_wc, bull_tg,
                base_g1, base_g2, base_em, base_wc, base_tg,
                bear_g1, bear_g2, bear_em, bear_wc, bear_tg):
    import src.config as cfg
    from src.config import Scenario
    # Write directly into cfg module so dcf_model._cfg.SCENARIOS sees the update
    cfg.SCENARIOS = {
        "Bull": Scenario(bull_g1, bull_g2, bull_em, bull_wc, bull_tg, 0.14, 0.07),
        "Base": Scenario(base_g1, base_g2, base_em, base_wc, base_tg, 0.16, 0.09),
        "Bear": Scenario(bear_g1, bear_g2, bear_em, bear_wc, bear_tg, 0.18, 0.12),
    }
    mdl = DCFModel(
        base_revenue_cr   = cd["latest_revenue_cr"],
        net_debt_cr       = cd.get("net_debt_cr", 5500),
        shares_cr         = cd.get("shares_cr", 28.6),
        current_price     = cd.get("current_price", 2250),
        beta              = cd.get("beta", 1.1),
        base_ebitda_margin= cd["ebitda_cr"][-1] / cd["revenue_cr"][-1],
    )
    res = mdl.run_all_scenarios()
    return mdl, res

dcf_model, dcf_results = run_dcf(
    company_data,
    bull_g1, bull_g2, bull_em, bull_wc, bull_tg,
    base_g1, base_g2, base_em, base_wc, base_tg,
    bear_g1, bear_g2, bear_em, bear_wc, bear_tg,
)

base = dcf_results.get("Base")
bull = dcf_results.get("Bull")
bear = dcf_results.get("Bear")
price = company_data.get("current_price", 2250) or 2250
rating = "BUY" if base and base.upside_pct > 15 else ("SELL" if base and base.upside_pct < -10 else "HOLD")
rating_color = {"BUY": "green", "HOLD": "orange", "SELL": "red"}[rating]

# ── Page header ────────────────────────────────────────────────────────────────
col_h, col_r = st.columns([5, 1])
with col_h:
    st.title("SRF Limited — Equity Research")
    src_label = "Mock Data" if use_mock else "Live Data · Yahoo Finance"
    st.caption(f"Independent Research | {SECTOR} | {EXCHANGE} | {src_label}")
with col_r:
    st.markdown(f"### :{rating_color}[{rating}]")
    if base:
        st.caption(f"Target ₹{base.intrinsic_value:,.0f}")

st.divider()

# ── KPI strip ──────────────────────────────────────────────────────────────────
k1,k2,k3,k4,k5,k6 = st.columns(6)
k1.metric("CMP (₹)",        f"₹{price:,.0f}")
k2.metric("Market Cap",     f"₹{summary.get('market_cap_cr',0):,.0f} Cr")
k3.metric("EV/EBITDA",      f"{summary.get('ev_ebitda',0):.1f}x")
k4.metric("EBITDA Margin",  f"{summary.get('ebitda_margin_latest',0):.1f}%")
k5.metric("Base IV (₹)",    f"₹{base.intrinsic_value:,.0f}" if base else "N/A",
          f"{base.upside_pct:+.1f}%" if base else "")
k6.metric("Beta",           f"{summary.get('beta',1.0):.2f}")

st.divider()

# ── Tabs ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Price & Overview",
    "💰 Financials",
    "🧮 DCF Valuation",
    "🔍 Peer Comparables",
    "📑 Research Note",
])

# ══ TAB 1: Price & Overview ═══════════════════════════════════════════════════
with tab1:
    col_chart, col_snap = st.columns([3, 1])

    with col_chart:
        if not price_hist.empty:
            fig = go.Figure()
            fig.add_scatter(
                x=price_hist.index, y=price_hist["Close"],
                line=dict(color="#1f77b4", width=2),
                fill="tozeroy", fillcolor="rgba(31,119,180,0.08)",
                name="Close Price",
            )
            fig.update_layout(
                title="5-Year Price History — SRF Ltd (NSE)",
                yaxis_title="Price (₹)",
                template="plotly_white",
                height=380, hovermode="x unified",
                margin=dict(l=0,r=0,t=40,b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Price history unavailable.")

    with col_snap:
        st.subheader("Company Snapshot")
        snap = {
            "52W High":    f"₹{summary.get('52w_high',0):,.0f}",
            "52W Low":     f"₹{summary.get('52w_low',0):,.0f}",
            "Shares (Cr)": f"{summary.get('shares_cr',0):.1f}",
            "Revenue FY24":f"₹{summary.get('latest_revenue_cr',0):,.0f} Cr",
            "EBITDA FY24": f"₹{summary.get('latest_ebitda_cr',0):,.0f} Cr",
            "Net Debt":    f"₹{summary.get('net_debt_cr',0):,.0f} Cr",
            "Beta":        f"{summary.get('beta',1.0):.2f}",
        }
        for k, v in snap.items():
            st.markdown(f"**{k}** — {v}")

    st.subheader("DCF Scenario Bridge")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.error(f"**Bear Case**\n\n### ₹{bear.intrinsic_value:,.0f}\n{bear.upside_pct:+.1f}% vs CMP")
    with sc2:
        st.info(f"**Base Case**\n\n### ₹{base.intrinsic_value:,.0f}\n{base.upside_pct:+.1f}% vs CMP")
    with sc3:
        st.success(f"**Bull Case**\n\n### ₹{bull.intrinsic_value:,.0f}\n{bull.upside_pct:+.1f}% vs CMP")

# ══ TAB 2: Financials ═════════════════════════════════════════════════════════
with tab2:
    if ratios_df.empty:
        st.warning("No financial data loaded.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            rev = ratios_df["Revenue (₹ Cr)"].fillna(0)
            fig_rev = go.Figure()
            fig_rev.add_bar(x=list(ratios_df.index), y=list(rev),
                            marker_color="#1f77b4", name="Revenue",
                            text=[f"₹{v:,.0f}" for v in rev],
                            textposition="outside")
            fig_rev.update_layout(title="Revenue (₹ Crore)",
                                  template="plotly_white", height=300,
                                  showlegend=False, margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_rev, use_container_width=True)

        with c2:
            em = ratios_df["EBITDA Margin (%)"].fillna(np.nan)
            pm = ratios_df["PAT Margin (%)"].fillna(np.nan)
            fig_mg = go.Figure()
            fig_mg.add_scatter(x=list(ratios_df.index), y=list(em),
                               mode="lines+markers+text", name="EBITDA Margin",
                               line=dict(color="#ff7f0e", width=2),
                               text=[f"{v:.1f}%" for v in em.fillna(0)],
                               textposition="top center")
            fig_mg.add_scatter(x=list(ratios_df.index), y=list(pm),
                               mode="lines+markers", name="PAT Margin",
                               line=dict(color="#2ca02c", width=2, dash="dot"))
            fig_mg.update_layout(title="Margin Trends (%)",
                                 template="plotly_white", height=300,
                                 margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_mg, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            gr = ratios_df["Rev. Growth (%)"].fillna(0)
            colors = ["#2ca02c" if v >= 0 else "#d62728" for v in gr]
            fig_gr = go.Figure()
            fig_gr.add_bar(x=list(ratios_df.index), y=list(gr),
                           marker_color=colors)
            fig_gr.add_hline(y=0, line_dash="dash", line_color="grey")
            fig_gr.update_layout(title="Revenue Growth YoY (%)",
                                 template="plotly_white", height=280,
                                 showlegend=False, margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_gr, use_container_width=True)

        with c4:
            pat = ratios_df["PAT (₹ Cr)"].fillna(0)
            fig_pat = go.Figure()
            fig_pat.add_bar(x=list(ratios_df.index), y=list(pat),
                            marker_color="#9467bd")
            fig_pat.update_layout(title="Profit After Tax (₹ Crore)",
                                  template="plotly_white", height=280,
                                  showlegend=False, margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_pat, use_container_width=True)

        st.subheader("Historical Ratios Table")
        st.dataframe(ratios_df.T.style.format("{:.1f}", na_rep="N/A"),
                     use_container_width=True, height=380)

# ══ TAB 3: DCF Valuation ═════════════════════════════════════════════════════
with tab3:
    st.info("Adjust assumptions using the **number inputs in the sidebar** — charts update instantly.")

    sc_tab1, sc_tab2, sc_tab3 = st.tabs(["Scenario Comparison", "Base Case Detail", "Sensitivity"])

    with sc_tab1:
        fig_iv = go.Figure()
        fig_iv.add_bar(
            x=["Bear", "Base", "Bull"],
            y=[bear.intrinsic_value, base.intrinsic_value, bull.intrinsic_value],
            marker_color=["#d62728", "#1f77b4", "#2ca02c"],
            text=[f"₹{v:,.0f}" for v in [bear.intrinsic_value, base.intrinsic_value, bull.intrinsic_value]],
            textposition="outside",
        )
        fig_iv.add_hline(y=price, line_dash="dash", line_color="orange", line_width=2,
                         annotation_text=f"CMP ₹{price:,.0f}")
        fig_iv.update_layout(title="Intrinsic Value vs CMP — All Scenarios",
                             yaxis_title="₹ per share",
                             template="plotly_white", height=400,
                             showlegend=False, margin=dict(l=0,r=0,t=50,b=0))
        st.plotly_chart(fig_iv, use_container_width=True)

        st.subheader("Scenario Summary")
        try:
            st.dataframe(dcf_model.scenario_summary_table(), use_container_width=True)
        except Exception:
            st.dataframe(dcf_model.scenario_summary_table().astype(str), use_container_width=True)

    with sc_tab2:
        st.subheader("Year-by-Year FCF Projection — Base Case")
        try:
            st.dataframe(dcf_model.build_dcf_table("Base").style.format("{:,.1f}", na_rep="—"),
                         use_container_width=True)
        except Exception:
            st.dataframe(dcf_model.build_dcf_table("Base").astype(str), use_container_width=True)

        if base:
            fig_fcf = go.Figure()
            fig_fcf.add_bar(
                x=[f"FY+{yr}" for yr in base.projection_years], y=base.fcf,
                marker_color="#1f77b4",
                text=[f"₹{v:,.0f}" for v in base.fcf], textposition="outside",
            )
            fig_fcf.update_layout(title="Projected Free Cash Flow — Base Case (₹ Cr)",
                                  template="plotly_white", height=300,
                                  showlegend=False, margin=dict(l=0,r=0,t=50,b=0))
            st.plotly_chart(fig_fcf, use_container_width=True)

    with sc_tab3:
        st.subheader("Sensitivity: Intrinsic Value (₹/sh) — WACC × Terminal Growth")
        try:
            sens = dcf_model.sensitivity_table("Base", "intrinsic_value")
            fig_s = go.Figure(data=go.Heatmap(
                z=sens.values.tolist(),
                x=list(sens.columns), y=list(sens.index),
                colorscale=[[0,"#d62728"],[0.5,"#f5f5f5"],[1,"#2ca02c"]],
                text=[[f"₹{v:,.0f}" for v in row] for row in sens.values],
                texttemplate="%{text}", textfont=dict(size=11),
            ))
            fig_s.update_layout(title="Intrinsic Value Sensitivity",
                                xaxis_title="Terminal Growth Rate",
                                yaxis_title="WACC",
                                template="plotly_white", height=360,
                                margin=dict(l=0,r=60,t=50,b=0))
            st.plotly_chart(fig_s, use_container_width=True)
        except Exception as e:
            st.warning(f"Sensitivity chart error: {e}")

# ══ TAB 4: Peer Comparables ═══════════════════════════════════════════════════
with tab4:
    if peer_df.empty:
        st.warning("Peer data unavailable.")
    else:
        display_cols = [c for c in peer_df.columns if c != "Ticker"]
        show_df = peer_df[display_cols].copy()

        c1, c2 = st.columns(2)
        with c1:
            ev_col = "EV/EBITDA (x)"
            if ev_col in show_df.columns:
                fig_ev = px.bar(show_df, x="Company", y=ev_col,
                                title="EV/EBITDA (x) Comparison",
                                color="Company", text=ev_col)
                fig_ev.update_traces(texttemplate="%{text:.1f}x", textposition="outside",
                                     showlegend=False)
                fig_ev.update_layout(template="plotly_white", height=360,
                                     xaxis_tickangle=-30,
                                     margin=dict(l=0,r=0,t=50,b=80))
                st.plotly_chart(fig_ev, use_container_width=True)

        with c2:
            pe_col = "P/E (x)"
            if pe_col in show_df.columns:
                fig_pe = px.bar(show_df, x="Company", y=pe_col,
                                title="P/E (x) Comparison",
                                text=pe_col)
                fig_pe.update_traces(texttemplate="%{text:.1f}x", textposition="outside",
                                     marker_color="#1f77b4")
                fig_pe.update_layout(template="plotly_white", height=360,
                                     xaxis_tickangle=-30,
                                     margin=dict(l=0,r=0,t=50,b=80))
                st.plotly_chart(fig_pe, use_container_width=True)

        st.subheader("Peer Comparable Table")
        num_cols = show_df.select_dtypes(include="number").columns
        st.dataframe(
            show_df.style.format(
                {c: "{:.1f}" for c in num_cols}, na_rep="N/A"
            ),
            use_container_width=True, height=380,
        )

# ══ TAB 5: Research Note ═════════════════════════════════════════════════════
with tab5:
    st.header("SRF Limited — Research Note Summary")
    st.caption("Independent Research | October 2026 | Krrish Kumar")

    col_l, col_r = st.columns([3, 1])
    with col_l:
        up_dn = "upside" if base and base.upside_pct >= 0 else "downside"
        st.markdown(f"""
**Recommendation: {rating} | Target Price (Base): ₹{base.intrinsic_value:,.0f} | {abs(base.upside_pct):.1f}% {up_dn}**

---

#### Investment Thesis

**1. Fluorochemicals Moat — Durable Competitive Advantage**
SRF's three-decade expertise in fluorine chemistry (HF handling, catalysis, cryogenic processing)
constitutes a high-barrier technical moat. Only ~5 companies globally can handle the full
fluorination value chain at commercial scale, and SRF is the only Indian company among them
with backward integration into captive HF production.

**2. China+1 — Structural Multi-Year Demand Tailwind**
Global agrochemical and pharmaceutical MNCs are diversifying supply chains away from China.
SRF has secured long-term supply agreements (3–5 years) for specialty chemical intermediates,
providing strong revenue visibility into FY27E+.

**3. FCF Inflection — Capex Cycle Peaking in FY25**
SRF invested ₹10,000+ Cr over FY22–FY25 building specialty chemicals capacity.
As capex moderates from FY26, FCF generation is expected to inflect sharply — the primary
re-rating catalyst not fully priced by the market.

---

#### Valuation Summary

| Scenario | Intrinsic Value (₹/sh) | vs CMP | WACC | TG Rate |
|----------|----------------------|--------|------|---------|
| Bull | ₹{bull.intrinsic_value:,.0f} | {bull.upside_pct:+.1f}% | {bull.wacc:.1%} | {bull.terminal_growth:.1%} |
| **Base** | **₹{base.intrinsic_value:,.0f}** | **{base.upside_pct:+.1f}%** | **{base.wacc:.1%}** | **{base.terminal_growth:.1%}** |
| Bear | ₹{bear.intrinsic_value:,.0f} | {bear.upside_pct:+.1f}% | {bear.wacc:.1%} | {bear.terminal_growth:.1%} |

---

#### Key Risks
- Agrochemical destocking cycle persisting into FY26
- Feedstock cost (HF, chloromethanes) volatility
- Capex execution delays on new specialty chemicals plants
- Kigali Amendment HFC phase-down pressure on refrigerant revenues

---
*Independent research for informational purposes only. Not SEBI-registered investment advice.*
""")

    with col_r:
        st.subheader("Export")
        if st.button("📥 Generate Excel", use_container_width=True):
            try:
                import tempfile, os
                from src.excel_export import ExcelExporter
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                    ExcelExporter(ratios_df, summary, dcf_model,
                                  peer_df, dcf_results, tmp.name).export()
                    with open(tmp.name, "rb") as f:
                        st.download_button("⬇ Download Excel", f.read(),
                                           "SRF_Equity_Research.xlsx",
                                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    os.unlink(tmp.name)
            except Exception as e:
                st.error(f"Excel error: {e}")

        if st.button("📄 Generate PDF", use_container_width=True):
            try:
                import tempfile, os
                from src.report_generator import ResearchNoteGenerator
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    ResearchNoteGenerator(summary, ratios_df,
                                          dcf_results, peer_df, tmp.name).generate()
                    with open(tmp.name, "rb") as f:
                        st.download_button("⬇ Download PDF", f.read(),
                                           "SRF_Research_Note.pdf", "application/pdf")
                    os.unlink(tmp.name)
            except Exception as e:
                st.error(f"PDF error: {e}")
