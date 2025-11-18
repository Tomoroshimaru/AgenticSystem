"""
Query Generator Node
====================
Generates Notion API query from analyzed intent.
"""

import json
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from config import LLMConfig, APIConfig
from state import InvestmentState
from prompts import SQL_GENERATION_SYSTEM, SQL_GENERATION_PROMPT
from tools import NotionAPIClient


def extract_json(text: str) -> Dict[str, Any]:
    """
    Extraction ULTRA-robuste du JSON depuis la réponse LLM
    Gère TOUS les formats possibles, même les JSON incomplets
    """
    original_text = text
    logger.debug(f"Raw LLM response (first 500 chars):\n{text[:500]}")
    
    # Étape 1: Nettoyer le texte de base
    text = text.strip()
    
    # Étape 2: Supprimer les blocs markdown (```json ou ```)
    if "```" in text:
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1).strip()
            logger.debug(f"After markdown removal: {text[:200]}")
    
    # Étape 3: VÉRIFIER si le JSON commence bien par {
    # Si il commence par "filter" ou autre, c'est qu'il manque le {
    if not text.lstrip().startswith('{'):
        logger.warning(f"⚠️ JSON doesn't start with '{{', attempting to fix...")
        logger.warning(f"Problematic start: {repr(text[:50])}")
        
        # Chercher si on a "filter" ou d'autres clés directement
        if '"filter"' in text or "'filter'" in text:
            logger.warning("Found 'filter' key without opening brace, adding {")
            text = '{' + text
            # Vérifier si on a besoin d'ajouter } à la fin
            if not text.rstrip().endswith('}'):
                text = text + '}'
    
    # Étape 4: Trouver le JSON complet avec les accolades correspondantes
    brace_count = 0
    start_idx = -1
    end_idx = -1
    
    for i, char in enumerate(text):
        if char == '{':
            if start_idx == -1:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                end_idx = i + 1
                break
    
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx:end_idx]
        logger.debug(f"After brace extraction: {text[:200]}")
    else:
        logger.error("No valid JSON braces found!")
        logger.error(f"Text: {text[:500]}")
        raise ValueError(f"No valid JSON structure found in response")
    
    # Étape 5: Parser le JSON - Python's json.loads gère les espaces DANS le JSON
    try:
        parsed = json.loads(text)
        logger.info(f"✅ JSON parsed successfully: {len(str(parsed))} chars")
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse error: {e}")
        logger.error(f"Error at position {e.pos}")
        logger.error(f"Problematic text around error:\n{text[max(0, e.pos-50):min(len(text), e.pos+50)]}")
        logger.error(f"Full cleaned text:\n{text}")
        
        # Tentative ultime: utiliser ast.literal_eval
        try:
            import ast
            # Remplacer true/false/null par True/False/None
            fixed_text = text.replace('true', 'True').replace('false', 'False').replace('null', 'None')
            parsed = ast.literal_eval(fixed_text)
            logger.warning("⚠️ Used ast.literal_eval as fallback")
            # Reconvertir en dict compatible JSON
            return json.loads(json.dumps(parsed))
        except:
            pass
        
        raise ValueError(f"Invalid JSON format after cleaning: {str(e)}\nOriginal text:\n{original_text[:500]}")


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
        
        # Prepare messages avec instructions STRICTES pour le format JSON
        intent_json = analyzed_intent.model_dump_json(indent=2)
        
        # Prompt ULTRA-SIMPLIFIÉ pour forcer un JSON compact
        enhanced_prompt = f"""
Based on this analyzed intent:
{intent_json}

Generate a Notion API filter query.

MANDATORY FORMAT RULES:
1. Output ONLY valid JSON
2. NO markdown, NO backticks, NO explanations
3. Start with {{ and end with }}
4. Use compact format (minimize whitespace)

Example: {{"filter":{{"and":[{{"property":"Status","select":{{"equals":"Active"}}}}]}}}}

Your JSON query:"""
        
        messages = [
            SystemMessage(content=SQL_GENERATION_SYSTEM + "\n\nOUTPUT FORMAT: Return only pure JSON. No markdown. No text. Just JSON."),
            HumanMessage(content=enhanced_prompt)
        ]
        
        # Call LLM avec retry automatique
        max_parse_retries = 2
        query_dict = None
        
        for attempt in range(max_parse_retries + 1):
            try:
                logger.info(f"Calling LLM for query generation (attempt {attempt + 1}/{max_parse_retries + 1})...")
                response = llm.invoke(messages)
                response_text = response.content.strip()
                
                # LOGS MASSIFS pour débugger
                logger.info("="*60)
                logger.info(f"LLM RAW RESPONSE (attempt {attempt + 1}):")
                logger.info(f"Length: {len(response_text)} chars")
                logger.info(f"First 50 chars: {repr(response_text[:50])}")
                logger.info(f"Last 50 chars: {repr(response_text[-50:])}")
                logger.info(f"Full response:\n{response_text}")
                logger.info("="*60)
                
                # Extraction robuste du JSON
                query_dict = extract_json(response_text)
                logger.info("✅ JSON successfully parsed")
                logger.info(f"Parsed query keys: {query_dict.keys()}")
                break
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_parse_retries:
                    # Ajouter un message pour corriger le format
                    messages.append(HumanMessage(content=response_text))
                    messages.append(HumanMessage(content=f"""
The previous response had a JSON parsing error: {str(e)}

Please provide the EXACT SAME query but in PURE JSON format:
- Remove ALL markdown (```)
- Remove ALL explanatory text
- Start with {{ and end with }}
- Ensure valid JSON syntax

Output ONLY the corrected JSON:
"""))
                else:
                    logger.error(f"All parsing attempts failed")
                    return {
                        "current_step": "query_generation_failed",
                        "query_valid": False,
                        "query_errors": [f"Failed to parse JSON after {max_parse_retries + 1} attempts: {str(e)}"],
                        "retry_count": state.retry_count + 1
                    }
        
        # Valider la structure de la query
        notion_client = NotionAPIClient()
        is_valid, errors = notion_client.validate_query(query_dict)
        
        if is_valid:
            logger.info("✅ Query generated and validated successfully")
            return {
                "generated_query": json.dumps(query_dict, indent=2),
                "query_valid": True,
                "query_errors": [],
                "current_step": "query_generated",
                "retry_count": 0
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
        logger.error(f"❌ Query generation failed: {e}", exc_info=True)
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