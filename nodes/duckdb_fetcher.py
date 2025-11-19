"""
DuckDB Fetcher Node
===================
Executes SQL query on CSV data and retrieves fundraising deals.
"""

from typing import Dict, Any
from loguru import logger

from config import WorkflowConfig, APIConfig
from state import InvestmentState
from tools.duckdb_api import DuckDBClient, format_deal_for_display


def duckdb_fetcher_node(state: InvestmentState) -> Dict[str, Any]:
    """
    Node 3: Fetch deals from CSV using DuckDB SQL
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates
    """
    logger.info("=" * 50)
    logger.info("NODE 3: DuckDB Fetcher")
    logger.info("=" * 50)
    
    try:
        sql_query = state.generated_query
        
        if not sql_query or not state.query_valid:
            logger.error("No valid SQL query available")
            return {
                "current_step": "error",
                "results_count": 0,
                "deals": []
            }
        
        logger.info("Executing SQL query...")
        logger.info(f"Query: {sql_query[:200]}...")
        
        # Initialize DuckDB client
        duckdb_client = DuckDBClient(APIConfig.DUCKDB_CSV_PATH)
        
        # Execute query
        raw_results = duckdb_client.execute_query(sql_query)
        
        # Format results
        formatted_deals = [
            format_deal_for_display(deal)
            for deal in raw_results
        ]
        
        results_count = len(formatted_deals)
        
        logger.info(f"✅ Found {results_count} deals")
        
        # Log deal details
        if results_count > 0:
            logger.info("Deal details:")
            for i, deal in enumerate(formatted_deals[:5], 1):
                logger.info(
                    f"  {i}. {deal['company']} - {deal['sector']} - "
                    f"{deal['round']} - {deal['amount_raised']}"
                )
            
            if results_count > 5:
                logger.info(f"  ... and {results_count - 5} more")
        
        # Prepare message
        if results_count > 0:
            message = f"J'ai trouvé {results_count} levée(s) de fonds correspondant à vos critères."
        else:
            message = "Aucune levée de fonds trouvée pour ces critères."
        
        return {
            "deals": formatted_deals,
            "results_count": results_count,
            "current_step": "deals_fetched",
            "messages": state.messages + [
                {"role": "assistant", "content": message}
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ DuckDB fetch failed: {e}")
        
        return {
            "current_step": "fetch_failed",
            "results_count": 0,
            "deals": [],
            "errors": state.errors + [
                {
                    "node": "duckdb_fetcher",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "retry_possible": True
                }
            ]
        }
