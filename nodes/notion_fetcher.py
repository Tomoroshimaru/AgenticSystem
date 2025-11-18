"""
Notion Fetcher Node
===================
Executes Notion query and retrieves fundraising deals.
"""

import json
from typing import Dict, Any
from loguru import logger

from config import WorkflowConfig
from state import InvestmentState
from tools import NotionAPIClient


def notion_fetcher_node(state: InvestmentState) -> Dict[str, Any]:
    """
    Node 3: Fetch deals from Notion database
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates
    """
    logger.info("=" * 50)
    logger.info("NODE 3: Notion Fetcher")
    logger.info("=" * 50)
    
    try:
        generated_query = state.generated_query
        
        if not generated_query or not state.query_valid:
            logger.error("No valid query available")
            return {
                "current_step": "error",
                "results_count": 0,
                "notion_results": []
            }
        
        logger.info("Executing Notion query...")
        
        # Parse query
        query_dict = json.loads(generated_query)
        
        # Initialize Notion client
        notion_client = NotionAPIClient()
        
        # Execute query
        deals = notion_client.query_database(
            filter_query=query_dict,
            max_results=WorkflowConfig.MAX_NOTION_RESULTS
        )
        
        results_count = len(deals)
        
        logger.info(f"✅ Found {results_count} deals in Notion")
        
        # Log deal details
        if results_count > 0:
            logger.info("Deal details:")
            for i, deal in enumerate(deals, 1):
                logger.info(f"  {i}. {deal.company} - {deal.sector} - {deal.round} - {deal.amount_raised}")
        
        # Prepare message for user
        if results_count > 0:
            message = f"J'ai trouvé {results_count} levée(s) de fonds correspondant à vos critères."
        else:
            message = "Aucune levée de fonds trouvée pour ces critères."
        
        return {
            "notion_results": deals,
            "results_count": results_count,
            "current_step": "notion_fetched",
            "messages": state.messages + [
                {"role": "assistant", "content": message}
            ]
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse query JSON: {e}")
        
        return {
            "current_step": "notion_fetch_failed",
            "results_count": 0,
            "notion_results": [],
            "errors": state.errors + [
                {
                    "node": "notion_fetcher",
                    "error_type": "JSONDecodeError",
                    "message": str(e),
                    "retry_possible": False
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Notion fetch failed: {e}")
        
        return {
            "current_step": "notion_fetch_failed",
            "results_count": 0,
            "notion_results": [],
            "errors": state.errors + [
                {
                    "node": "notion_fetcher",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "retry_possible": True
                }
            ]
        }