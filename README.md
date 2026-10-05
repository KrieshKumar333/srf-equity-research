# 📊 SRF Limited (NSE: SRF.NS) — Automated Equity Research & Valuation Platform

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B.svg)](https://streamlit.io/)
[![Financial Data](https://img.shields.io/badge/Data-yfinance-green.svg)](https://pypi.org/project/yfinance/)
[![PDF Generation](https://img.shields.io/badge/ReportLab-PDF-red.svg)](https://pypi.org/project/reportlab/)

**Goldman Sachs Global Investment Research (GIR) Summer Analyst Application (2026)**[cite: 3]

An end-to-end, automated equity research platform analyzing **SRF Limited**, India's leading specialty chemicals conglomerate. This project replicates the comprehensive workflow of a sell-side GIR analyst: fetching live market data, computing historical financials, building a multi-scenario DCF model, benchmarking peers, and automatically generating professional research deliverables[cite: 3].

---

## 💡 The Investment Thesis & Differentiator

As a researcher bridging **Chemical Engineering** (BIT Mesra) and **Data Science** (IIT Madras), this project applies domain-specific technical expertise to financial modeling. 

Understanding fluorination chemistry, HF handling, and the specialty chemical value chain is critical to evaluating SRF's economic moat[cite: 3]. The valuation thesis specifically models a **Free Cash Flow (FCF) inflection**[cite: 3]. Rather than applying a flat capital expenditure rate, the DCF model applies stage-dependent capex assumptions[cite: 3] to capture the normalization of cash flows following SRF’s ₹10,000+ Cr investment phase.

---

## ✨ Key Features

1. **Live Data Pipeline:** Automatically fetches real-time pricing, historical financials, and peer data via `yfinance`[cite: 3, 4], with a seamless fallback to offline mock data for robust testing.
2. **Advanced DCF Valuation:** A dynamic 3-scenario Discounted Cash Flow model (Bull, Base, Bear)[cite: 2, 3] incorporating:
   - Graduated EBITDA margin ramps[cite: 3].
   - Stage-dependent capex forecasting (14-18% dropping to 7-12%)[cite: 3].
   - WACC vs. Terminal Growth sensitivity heatmaps[cite: 2, 3].
3. **Peer Comparables:** Automated tracking of EV/EBITDA and P/E ratios across 8 regional and global peers[cite: 2, 3].
4. **Interactive Streamlit Dashboard:** A web-based UI (`dashboard.py`) featuring live scenario toggles, interactive Plotly charts, and instant valuation bridges[cite: 2, 3, 4].
5. **Automated Deliverables:** One-click generation of:
   - A fully formatted, 4-sheet Excel workbook (`openpyxl`, `xlsxwriter`)[cite: 3, 4].
   - A professional 6-page Initiating Coverage PDF research note (`reportlab`)[cite: 3, 4].

---

## 🚀 Installation & Usage

### 1. Local Setup
Clone the repository and install the required dependencies:

```bash
git clone [https://github.com/your-username/srf-equity-research.git](https://github.com/your-username/srf-equity-research.git)
cd srf-equity-research
pip install -r requirements.txt
