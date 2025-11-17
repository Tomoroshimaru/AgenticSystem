"""
Drive Uploader Node
===================
Uploads PDF report to Google Drive.
"""

from typing import Dict, Any
from loguru import logger

from state import InvestmentState
from tools import GoogleDriveClient


def drive_uploader_node(state: InvestmentState) -> Dict[str, Any]:
    """
    Node 7: Upload PDF to Google Drive
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates
    """
    logger.info("=" * 50)
    logger.info("NODE 7: Drive Uploader")
    logger.info("=" * 50)
    
    try:
        pdf_path = state.pdf_local_path
        
        if not pdf_path or not state.pdf_generated:
            logger.error("No PDF to upload")
            return {
                "current_step": "no_pdf_to_upload",
                "drive_upload_success": False,
                "drive_file_url": None
            }
        
        logger.info(f"Uploading PDF to Google Drive: {pdf_path}")
        
        # Initialize Drive client
        drive_client = GoogleDriveClient()
        
        # Upload file
        file_id, file_url = drive_client.upload_file(
            file_path=pdf_path,
            mime_type='application/pdf'
        )
        
        logger.info(f"✅ PDF uploaded to Drive: {file_url}")
        
        # Success message
        summary_message = (
            f"✅ Rapport généré avec succès !\n\n"
            f"📊 Résumé :\n"
            f"- {len(state.selected_deal_ids)} deal(s) enrichi(s)\n"
            f"- {state.total_similar_companies} cibles similaires identifiées\n\n"
            f"📄 Rapport disponible ici :\n{file_url}"
        )
        
        return {
            "drive_upload_success": True,
            "drive_file_url": file_url,
            "drive_file_id": file_id,
            "current_step": "completed",
            "workflow_complete": True,
            "messages": state.messages + [
                {"role": "assistant", "content": summary_message}
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Drive upload failed: {e}")
        
        return {
            "current_step": "drive_upload_failed",
            "drive_upload_success": False,
            "drive_file_url": None,
            "errors": state.errors + [
                {
                    "node": "drive_uploader",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "retry_possible": True
                }
            ]
        }
