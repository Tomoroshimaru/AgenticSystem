"""
Human Review Node
=================
Logs user selection (already processed by main.py).
"""

from typing import Dict, Any
from loguru import logger

from state import InvestmentState


def human_review_node(state: InvestmentState) -> Dict[str, Any]:
    """Log user's selection"""
    logger.info("=" * 50)
    logger.info("NODE 4: Human Review")
    logger.info("=" * 50)
    
    count = len(state.selected_deal_ids)
    logger.info(f"Processing {count} selected deal(s)")
    
    return {
        "current_step": "deals_selected",
        "messages": state.messages + [
            {"role": "assistant", "content": f"{count} deal(s) sélectionné(s)"}
        ]
    }
