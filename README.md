SRF Limited - Equity Research Platform

What This Project Does

A complete, professional equity research model for SRF Limited (NSE: SRF.NS) - India's leading
specialty chemicals conglomerate. Replicates the exact workflow of a GIR sell-side research analyst:
fetch data → analyse financials → build DCF → compare peers → generate research note.

Outputs Generated
File	Description
`outputs/SRF_Equity_Research.xlsx`	4-sheet Excel: Cover KPIs, Historical Financials, 3-Scenario DCF, Peer Comps
`outputs/SRF_Research_Note.pdf`	Professional 6-page initiating coverage research note
`dashboard.py`	Interactive Streamlit app with live DCF sliders + all charts
---

Why SRF Limited?
Chemical Engineering domain expertise → genuine insight into fluorination chemistry, HF handling,
specialty chemical value chains - the core of SRF's moat

---
Key Modelling Choices
1. Stage-Dependent Capex (Most Important)
SRF's capex/revenue was ~22% in FY23–24 during peak capacity investment. Assuming a flat capex
rate massively underestimates FCF as the cycle normalises. This model uses:
Years 1–2 (investment phase): scenario-specific high capex (14–18% of revenue)
Years 3–5 (normalisation): tapered capex (7–12% of revenue)
This is the FCF inflection thesis - the primary bull case catalyst.
2. EBITDA Margin Ramp
Margin is graduated from FY24 actuals (~19%) to steady-state by Year 3. Avoids the
unrealistic step-change assumption common in junior models.
3. 3-Scenario DCF + Sensitivity
Bull / Base / Bear with WACC × Terminal Growth sensitivity heatmap. Base Case shows
the market pricing in near-Bull-Case assumptions — an analytically honest finding.
---
Setup & Run
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run full pipeline (live data from Yahoo Finance)
python run.py

# 3. Run with offline mock data (for testing without internet)
python run.py --mock

# 4. Launch interactive dashboard
streamlit run dashboard.py

# In dashboard: toggle "Use offline demo data" in sidebar if no internet
```
---
Project Structure
```
project1_equity_research/
├── src/
│   ├── config.py             # All assumptions, tickers, scenarios
│   ├── data_fetcher.py       # yfinance + mock data fallback
│   ├── financial_analysis.py # Ratio calculations, growth metrics
│   ├── dcf_model.py          # 3-scenario DCF, sensitivity analysis
│   ├── excel_export.py       # Excel workbook (4 sheets, formatted)
│   └── report_generator.py   # PDF research note (reportlab)
├── dashboard.py              # Streamlit interactive dashboard
├── run.py                    # Batch runner (Excel + PDF)
├── requirements.txt
└── outputs/                  # Generated files land here
```
---
 
> *Built equity research platform for Indian specialty chemicals sector;
> constructed 3-scenario stage-dependent DCF (Bull/Base/Bear) and 8-peer EV/EBITDA comparable analysis for SRF Ltd
  (NSE)
> base case IV ₹662 vs CMP ₹2,250 - market pricing near-Bull assumptions;
> authored 6-page initiating coverage PDF research note;
> deployed Streamlit dashboard with live WACC/growth sliders and sensitivity heatmaps*
Key metrics to update: replace with actual yfinance numbers once run live.
