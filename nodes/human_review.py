"""
Human Review Node
=================
Human-in-the-loop node for selecting deals to enrich.
"""

from typing import Dict, Any
from langgraph.types import interrupt
from loguru import logger

from state import InvestmentState


def human_review_node(state: InvestmentState) -> Dict[str, Any]:
    """
    Node 4: Human-in-the-loop for deal selection
    """
    logger.info("=" * 50)
    logger.info("NODE 4: Human Review (HITL)")
    logger.info("=" * 50)
    
    try:
        deals = state.deals
        
        if not deals:
            logger.warning("No deals to review")
            return {
                "current_step": "no_deals_to_review",
                "selected_deal_ids": []
            }
        
        logger.info(f"Presenting {len(deals)} deals for review")
        
        # Format presentation
        deals_presentation = []
        for i, deal in enumerate(deals, 1):
            deal_info = (
                f"[{i}] {deal.company}\n"
                f"    Sector: {deal.sector or 'N/A'} | "
                f"Round: {deal.round or 'N/A'} | "
                f"Amount: {deal.amount_raised or 'N/A'} | "
                f"Country: {deal.country or 'N/A'}"
            )
            deals_presentation.append(deal_info)
        
        presentation_text = "\n\n".join(deals_presentation)
        
        instruction = (
            f"📊 J'ai trouvé {len(deals)} levée(s) de fonds :\n\n"
            f"{presentation_text}\n\n"
            "Veuillez sélectionner les deals à enrichir (ex: 1,3,5 ou 'all')."
        )
        
        # Interrupt for user input
        user_input = interrupt(instruction)
        
        logger.info(f"User input received: {user_input}")
        
        # Parse selection
        selected_indices = []
        user_feedback = None
        
        if isinstance(user_input, dict):
            selection = user_input.get("selection", "")
            user_feedback = user_input.get("feedback", None)
        elif isinstance(user_input, str):
            selection = user_input
        else:
            logger.error(f"Unexpected input type: {type(user_input)}")
            selection = ""
        
        # Parse selection
        if selection.lower().strip() == "all":
            selected_indices = list(range(len(deals)))
            logger.info("User selected ALL deals")
        else:
            try:
                user_nums = [int(x.strip()) for x in selection.split(",") if x.strip()]
                selected_indices = [
                    i - 1
                    for i in user_nums
                    if 1 <= i <= len(deals)
                ]
                logger.info(f"User selected {len(selected_indices)} deal(s)")
            except (ValueError, IndexError) as e:
                logger.error(f"Failed to parse selection: {e}")
                selected_indices = []
        
        if not selected_indices:
            message = "Aucun deal sélectionné. Workflow terminé."
        else:
            message = f"Parfait ! {len(selected_indices)} deal(s) sélectionné(s)."
        
        return {
            "selected_deal_ids": selected_indices,
            "user_feedback": user_feedback,
            "current_step": "deals_selected",
            "messages": state.messages + [
                {"role": "user", "content": selection},
                {"role": "assistant", "content": message}
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Human review failed: {e}")
        
        return {
            "current_step": "human_review_failed",
            "selected_deal_ids": [],
            "errors": state.errors + [
                {
                    "node": "human_review",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "retry_possible": False
                }
            ]
        }
