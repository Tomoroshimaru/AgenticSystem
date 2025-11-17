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
    
    This node interrupts the workflow and waits for user input.
    The user must select which deals to enrich.
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates
    """
    logger.info("=" * 50)
    logger.info("NODE 4: Human Review (HITL)")
    logger.info("=" * 50)
    
    try:
        notion_results = state.notion_results
        
        if not notion_results:
            logger.warning("No deals to review")
            return {
                "current_step": "no_deals_to_review",
                "selected_deal_ids": []
            }
        
        logger.info(f"Presenting {len(notion_results)} deals for review")
        
        # Format deals for presentation
        deals_presentation = []
        for i, deal in enumerate(notion_results, 1):
            deal_info = (
                f"[{i}] {deal.company}\n"
                f"    Sector: {deal.sector or 'N/A'} | "
                f"Round: {deal.round or 'N/A'} | "
                f"Amount: {deal.amount_raised or 'N/A'} | "
                f"Country: {deal.country or 'N/A'}"
            )
            deals_presentation.append(deal_info)
        
        presentation_text = "\n\n".join(deals_presentation)
        
        logger.info("Deals for review:")
        logger.info(f"\n{presentation_text}")
        
        # Prepare instruction message
        instruction = (
            f"📊 J'ai trouvé {len(notion_results)} levée(s) de fonds :\n\n"
            f"{presentation_text}\n\n"
            "Veuillez sélectionner les deals à enrichir en fournissant leurs numéros "
            "(ex: 1,3,5 ou all pour tous).\n"
            "Vous pouvez aussi ajouter des commentaires optionnels."
        )
        
        # Interrupt and wait for user input
        # The user will need to resume with Command(resume={...})
        user_input = interrupt(instruction)
        
        # When resumed, parse the user input
        logger.info(f"User input received: {user_input}")
        
        # Parse selection
        selected_ids = []
        user_feedback = None
        
        if isinstance(user_input, dict):
            selection = user_input.get("selection", "")
            user_feedback = user_input.get("feedback", None)
        elif isinstance(user_input, str):
            selection = user_input
        else:
            logger.error(f"Unexpected user input type: {type(user_input)}")
            selection = ""
        
        # Parse selection string
        if selection.lower().strip() == "all":
            selected_ids = [deal.id for deal in notion_results]
            logger.info("User selected ALL deals")
        else:
            # Parse comma-separated numbers
            try:
                indices = [int(x.strip()) for x in selection.split(",") if x.strip()]
                selected_ids = [
                    notion_results[i - 1].id
                    for i in indices
                    if 1 <= i <= len(notion_results)
                ]
                logger.info(f"User selected {len(selected_ids)} deal(s): indices {indices}")
            except (ValueError, IndexError) as e:
                logger.error(f"Failed to parse selection: {e}")
                selected_ids = []
        
        if not selected_ids:
            logger.warning("No valid deals selected")
            message = "Aucun deal sélectionné. Workflow terminé."
        else:
            message = f"Parfait ! J'ai sélectionné {len(selected_ids)} deal(s) pour enrichissement."
        
        return {
            "selected_deal_ids": selected_ids,
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