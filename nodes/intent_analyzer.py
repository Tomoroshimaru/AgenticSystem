"""
Intent Analyzer Node
====================
Analyzes user query and extracts structured search criteria.
"""

import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from config import LLMConfig, APIConfig
from state import InvestmentState, AnalyzedIntent, add_error
from prompts import INTENT_ANALYSIS_SYSTEM, INTENT_ANALYSIS_PROMPT


def intent_analyzer_node(state: InvestmentState) -> Dict[str, Any]:
    """
    Node 1: Analyze user intent and extract search criteria
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates
    """
    logger.info("=" * 50)
    logger.info("NODE 1: Intent Analyzer")
    logger.info("=" * 50)
    try:
        user_query = state.user_query
        
        if not user_query:
            logger.error("No user query provided")
            return {
                "current_step": "error",
                "errors": state.errors + [
                    {
                        "node": "intent_analyzer",
                        "error_type": "ValidationError",
                        "message": "User query is empty",
                        "retry_possible": False
                    }
                ]
            }
        
        logger.info(f"Analyzing query: {user_query}")
        
        # Initialize LLM
        llm = ChatOpenAI(
            model=LLMConfig.MODEL_NAME,
            temperature=LLMConfig.TEMPERATURE_INTENT,
            max_tokens=LLMConfig.MAX_TOKENS_INTENT,
            api_key=APIConfig.OPENAI_API_KEY
        )
        
        # Prepare messages
        messages = [
            SystemMessage(content=INTENT_ANALYSIS_SYSTEM),
            HumanMessage(content=INTENT_ANALYSIS_PROMPT.format(user_query=user_query))
        ]
        
        # Call LLM
        logger.info("Calling LLM for intent analysis...")
        response = llm.invoke(messages)
        
        # Parse response
        response_text = response.content.strip()
        logger.info(f"LLM Response:\n{response_text}")
        
        # Clean response (remove markdown code blocks if present)
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            intent_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {response_text}")
            
            return {
                "current_step": "intent_analysis_failed",
                "errors": state.errors + [
                    {
                        "node": "intent_analyzer",
                        "error_type": "JSONDecodeError",
                        "message": f"Failed to parse LLM response as JSON: {str(e)}",
                        "retry_possible": False
                    }
                ]
            }
        
        # Validate and create AnalyzedIntent
        analyzed_intent = AnalyzedIntent(**intent_data)
        
        logger.info(f"✅ Intent analyzed successfully:")
        logger.info(f"   Query type: {analyzed_intent.query_type}")
        logger.info(f"   Criteria: {analyzed_intent.criteria}")
        logger.info(f"   Max results: {analyzed_intent.max_results}")
        
        # Update state
        return {
            "analyzed_intent": analyzed_intent,
            "current_step": "intent_analyzed",
            "messages": state.messages + [
                {"role": "assistant", "content": f"J'ai analysé votre requête. Je recherche des levées avec les critères suivants : {json.dumps(analyzed_intent.criteria, ensure_ascii=False)}"}
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Intent analysis failed: {e}")
        
        return {
            "current_step": "intent_analysis_failed",
            "errors": state.errors + [
                {
                    "node": "intent_analyzer",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "retry_possible": True
                }
            ]
        }