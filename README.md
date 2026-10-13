# SRF Limited - Equity Research Model

I built this project to teach myself how sell-side equity research actually works -
not from a textbook but by doing it for a real company I have genuine interest in.

SRF Limited caught my attention because of my Chemical Engineering background.
Everyone covers SRF from the financial statements. But the real moat is the
fluorination chemistry - handling hydrofluoric acid at commercial scale requires
specialised metallurgy, safety infrastructure, and decades of institutional knowledge.
That is not something you can read off a balance sheet, and it is not something
a competitor can replicate quickly. That angle is what I wanted to model properly.

## What I Built

A complete end-to-end equity research workflow in Python:

- **3-Scenario DCF Model** (Bull / Base / Bear) with stage-dependent capex
  - Key insight: SRF's capex was ~20% of revenue at peak investment phase,
    normalising to 7-9% from FY27 as new specialty chemicals plants ramp
  - This FCF inflection is the entire bull thesis - flat capex models get this completely wrong
- **8-Peer EV/EBITDA Comparable Analysis** - Navin Fluorine, Gujarat Fluorochem,
  Aarti Industries, Deepak Nitrite, Vinati Organics, Fine Organics, Sudarshan Chemical, Balaji Amines
- **WACC built from first principles** - CAPM with India 10Y G-Sec, Damodaran ERP, market beta
- **Sensitivity heatmap** - WACC x Terminal Growth Rate (5x5 grid)
- **6-page PDF research note** - formatted like a real initiating coverage note
- **4-sheet Excel workbook** - Cover KPIs, Financials, DCF Model, Peer Comps
- **Streamlit dashboard** - live DCF with adjustable assumptions, peer charts, research note tab

## Key Finding

**Base Case Intrinsic Value: Rs. 662/share vs CMP ~Rs. 2,250**

The market is pricing near-Bull Case assumptions (22% revenue CAGR, 26% EBITDA margins).
Rating: **HOLD** - the thesis is real, but the valuation leaves zero margin of safety.

The Bull Case (Rs. 2,320) requires the FCF inflection to materialise on schedule.
That is credible - but you are paying full price for it today.

## Why Chemical Engineering Matters Here

SRF's fluorination chemistry involves handling HF (hydrofluoric acid) - requiring
specialised reactor metallurgy (Hastelloy), PTFE-lined equipment, and trained operators.
The learning curve is 10+ years. SRF has 30 years of experience, captive HF production,
and multipurpose plants that switch between agrochemical and pharmaceutical intermediates.
Only ~5 companies globally have full fluorination chain capability at commercial scale.
SRF is the only Indian one. That is the moat - and it is wider than the financials suggest.

## Tech Stack

`Python` `pandas` `NumPy` `yfinance` `reportlab` `xlsxwriter` `Streamlit` `Plotly`

## Setup

```bash
pip install -r requirements.txt

# Run with live data (Yahoo Finance)
python run.py

# Run offline (no internet needed)
python run.py --mock

# Launch interactive dashboard
python -m streamlit run dashboard.py
```

## Project Structure

```
SRF-Equity-Research/
|-- src/
|   |-- __init__.py
|   |-- config.py              # All assumptions, tickers, DCF scenarios
|   |-- data_fetcher.py        # Yahoo Finance + fallback mock data
|   |-- financial_analysis.py  # Ratio calculations, growth metrics
|   |-- dcf_model.py           # 3-scenario DCF with stage-dependent capex
|   |-- excel_export.py        # 4-sheet formatted Excel workbook
|   `-- report_generator.py    # 6-page PDF research note
|-- outputs/
|   |-- SRF_Equity_Research_FINAL.xlsx
|   `-- SRF_Research_Note_FINAL.pdf
|-- .gitignore
|-- dashboard.py               # Streamlit interactive dashboard
|-- README.md
|-- requirements.txt
`-- run.py                     # CLI runner (data -> analysis -> Excel + PDF)
```

## What I Learned

The biggest lesson: a DCF is only as honest as its assumptions.
Using flat historical capex for a company in an active investment cycle
produces a fundamentally misleading model. Stage-dependent capex - the single
most important choice in this model - changes the entire FCF profile.

Also: a HOLD recommendation requires more intellectual courage than a BUY.
It means you think the thesis is valid but the market has already priced it in.

## Disclaimer

Independent research for learning purposes only.
Not SEBI-registered investment advice. Not for distribution.
