"""
Query Generator Node
====================
Generates Notion API query from analyzed intent.
"""

import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from config import LLMConfig, APIConfig
from state import InvestmentState
from prompts import SQL_GENERATION_SYSTEM, SQL_GENERATION_PROMPT
from tools import NotionAPIClient

def extract_json(text: str) -> str:
    """Extrait le JSON d'une réponse LLM"""
    text = text.strip()
    
    # Supprimer les backticks markdown
    if text.startswith("```"):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text
        text = text.replace("```json", "").replace("```", "").strip()
    
    # Trouver le JSON
    start = text.find("{")
    end = text.rfind("}") + 1
    
    if start == -1 or end == 0:
        raise ValueError(f"Pas de JSON: {text[:200]}")
    
    return text[start:end]

def query_generator_node(state: InvestmentState) -> Dict[str, Any]:
    """
    Node 2: Generate Notion API query from analyzed intent
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates
    """
    logger.info("=" * 50)
    logger.info("NODE 2: Query Generator")
    logger.info("=" * 50)
    
    try:
        analyzed_intent = state.analyzed_intent
        
        if not analyzed_intent:
            logger.error("No analyzed intent available")
            return {
                "current_step": "error",
                "query_valid": False,
                "query_errors": ["No analyzed intent available"]
            }
        
        logger.info(f"Generating Notion query for criteria: {analyzed_intent.criteria}")
        
        # Initialize LLM
        llm = ChatOpenAI(
            model=LLMConfig.MODEL_NAME,
            temperature=LLMConfig.TEMPERATURE_SQL,
            max_tokens=LLMConfig.MAX_TOKENS_SQL,
            api_key=APIConfig.OPENAI_API_KEY
        )
        
        # Prepare messages
        intent_json = analyzed_intent.model_dump_json(indent=2)
        
        messages = [
            SystemMessage(content=SQL_GENERATION_SYSTEM),
            HumanMessage(content=SQL_GENERATION_PROMPT.format(analyzed_intent=intent_json))
        ]
        
        # Call LLM
        logger.info("Calling LLM for query generation...")
        response = llm.invoke(messages)
        
        # Parse response
        response_text = response.content.strip()
        logger.info(f"LLM Response:\n{response_text}")
        
        # Clean response
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            clean_text = extract_json(response_text)
            query_dict = json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON query: {e}")
            
            return {
                "current_step": "query_generation_failed",
                "query_valid": False,
                "query_errors": [f"Failed to parse query JSON: {str(e)}"],
                "retry_count": state.retry_count + 1
            }
        
        # Validate query structure
        notion_client = NotionAPIClient()
        is_valid, errors = notion_client.validate_query(query_dict)
        
        if is_valid:
            logger.info("✅ Query generated and validated successfully")
            
            return {
                "generated_query": json.dumps(query_dict, indent=2),
                "query_valid": True,
                "query_errors": [],
                "current_step": "query_generated",
                "retry_count": 0  # Reset retry count on success
            }
        else:
            logger.warning(f"⚠️ Query validation failed: {errors}")
            
            return {
                "generated_query": json.dumps(query_dict, indent=2),
                "query_valid": False,
                "query_errors": errors,
                "current_step": "query_validation_failed",
                "retry_count": state.retry_count + 1
            }
        
    except Exception as e:
        logger.error(f"❌ Query generation failed: {e}")
        
        return {
            "current_step": "query_generation_failed",
            "query_valid": False,
            "query_errors": [str(e)],
            "retry_count": state.retry_count + 1,
            "errors": state.errors + [
                {
                    "node": "query_generator",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "retry_possible": True
                }
            ]
        }