"""
run.py — Batch runner: fetches data, runs all models, exports Excel + PDF.
Usage: python run.py [--mock]
  --mock   Use fallback mock data (no internet required for testing)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make src importable
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run")


def main(use_mock: bool = False) -> None:
    from src.config import EXCEL_OUTPUT, PDF_OUTPUT
    from src.data_fetcher import DataFetcher
    from src.financial_analysis import FinancialAnalyzer
    from src.dcf_model import DCFModel
    from src.excel_export import ExcelExporter
    from src.report_generator import ResearchNoteGenerator

    # ── 1. Fetch data ─────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("SRF Limited — Equity Research Model")
    logger.info("=" * 60)
    fetcher = DataFetcher(use_mock=use_mock)
    company_data = fetcher.get_company_data()
    price_history = fetcher.get_price_history()
    peer_df = fetcher.get_peer_data()
    logger.info(f"Data source: {company_data['data_source']}")
    logger.info(f"Current price: ₹{company_data.get('current_price', 'N/A')}")

    # ── 2. Financial analysis ─────────────────────────────────────────────────
    analyzer = FinancialAnalyzer(company_data)
    ratios_df = analyzer.compute_ratios()
    summary = analyzer.compute_summary_stats()
    logger.info(f"5Y Revenue CAGR: {summary.get('rev_cagr_5y', 0):.1f}%")
    logger.info(f"Latest EBITDA margin: {summary.get('ebitda_margin_latest', 0):.1f}%")

    # ── 3. DCF model ──────────────────────────────────────────────────────────
    dcf = DCFModel(
        base_revenue_cr=company_data["latest_revenue_cr"],
        net_debt_cr=company_data.get("net_debt_cr", 0),
        shares_cr=company_data.get("shares_cr", 28.6),
        current_price=company_data.get("current_price", 2250),
        beta=company_data.get("beta", 1.1),
    )
    dcf_results = dcf.run_all_scenarios()
    summary_tbl = dcf.scenario_summary_table()
    print("\n" + "─" * 60)
    print(summary_tbl.to_string())
    print("─" * 60 + "\n")

    # ── 4. Export Excel ────────────────────────────────────────────────────────
    logger.info("Exporting Excel workbook...")
    exporter = ExcelExporter(
        ratios_df=ratios_df,
        summary=summary,
        dcf_model=dcf,
        peer_df=peer_df,
        dcf_results=dcf_results,
        output_path=EXCEL_OUTPUT,
    )
    excel_path = exporter.export()
    logger.info(f"✓ Excel → {excel_path}")

    # ── 5. Generate PDF research note ─────────────────────────────────────────
    logger.info("Generating PDF research note...")
    reporter = ResearchNoteGenerator(
        summary=summary,
        ratios_df=ratios_df,
        dcf_results=dcf_results,
        peer_df=peer_df,
        output_path=PDF_OUTPUT,
    )
    pdf_path = reporter.generate()
    logger.info(f"✓ PDF  → {pdf_path}")

    logger.info("=" * 60)
    logger.info("All outputs generated successfully.")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SRF Equity Research Runner")
    parser.add_argument("--mock", action="store_true",
                        help="Use mock data (no internet required)")
    args = parser.parse_args()
    main(use_mock=args.mock)
