"""
PDF Generator Node
==================
Generates PDF report from enriched deals.
"""

from typing import Dict, Any
from loguru import logger

from state import InvestmentState
from tools import PDFReportBuilder


def pdf_generator_node(state: InvestmentState) -> Dict[str, Any]:
    """
    Node 6: Generate PDF report from enriched deals
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates
    """
    logger.info("=" * 50)
    logger.info("NODE 6: PDF Generator")
    logger.info("=" * 50)
    
    try:
        enriched_deals = state.enriched_deals
        
        if not enriched_deals:
            logger.warning("No enriched deals to generate PDF")
            return {
                "current_step": "no_deals_to_pdf",
                "pdf_generated": False,
                "pdf_local_path": None
            }
        
        logger.info(f"Generating PDF for {len(enriched_deals)} enriched deal(s)")
        
        # Initialize PDF builder
        pdf_builder = PDFReportBuilder()
        
        # Generate report
        pdf_path = pdf_builder.generate_report(
            enriched_deals=enriched_deals,
            user_query=state.user_query
        )
        
        logger.info(f"✅ PDF generated: {pdf_path}")
        
        return {
            "pdf_generated": True,
            "pdf_local_path": pdf_path,
            "current_step": "pdf_generated",
            "messages": state.messages + [
                {"role": "assistant", "content": f"Rapport PDF généré avec succès : {pdf_path}"}
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ PDF generation failed: {e}")
        
        return {
            "current_step": "pdf_generation_failed",
            "pdf_generated": False,
            "pdf_local_path": None,
            "errors": state.errors + [
                {
                    "node": "pdf_generator",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "retry_possible": True
                }
            ]
        }