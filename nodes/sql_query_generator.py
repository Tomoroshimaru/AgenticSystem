"""
SQL Query Generator Node
=========================
Generates SQL query from analyzed intent for DuckDB execution.
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from config import LLMConfig, APIConfig
from state import InvestmentState
from prompts import SQL_GENERATION_SYSTEM, SQL_GENERATION_PROMPT
from tools.duckdb_api import DuckDBClient


def sql_query_generator_node(state: InvestmentState) -> Dict[str, Any]:
    """
    Node 2: Generate SQL query from analyzed intent
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates
    """
    logger.info("=" * 50)
    logger.info("NODE 2: SQL Query Generator")
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
        
        logger.info(f"Generating SQL query for criteria: {analyzed_intent.criteria}")
        logger.info(f"Max results: {analyzed_intent.max_results if analyzed_intent.max_results else 'UNLIMITED'}")
        
        # Initialize LLM
        llm = ChatOpenAI(
            model=LLMConfig.MODEL_NAME,
            temperature=LLMConfig.TEMPERATURE_SQL,
            max_tokens=LLMConfig.MAX_TOKENS_SQL,
            api_key=APIConfig.OPENAI_API_KEY
        )
        
        # Get database schema
        duckdb_client = DuckDBClient(APIConfig.DUCKDB_CSV_PATH)
        schema = duckdb_client.get_schema()
        
        # Format schema for prompt
        schema_str = "\n".join([f"  - {col}: {dtype}" for col, dtype in schema.items()])
        
        # Prepare prompt
        intent_json = analyzed_intent.model_dump_json(indent=2)
        
        enhanced_prompt = f"""
Based on this analyzed intent:
{intent_json}

Generate a SQL query for DuckDB that selects fundraising deals from the 'deals' table.

DATABASE SCHEMA:
{schema_str}

IMPORTANT RULES:
1. Table name is 'deals'
2. Use exact column names from schema (case-sensitive)
3. Return ALL columns (SELECT *)
4. Handle NULL values appropriately
5. Use LIKE for partial text matching (case-insensitive: ILIKE)
6. Combine multiple conditions with AND/OR
7. CRITICAL: Only add LIMIT clause if max_results is specified and not null
   - If max_results is null or not present: NO LIMIT clause (return all matching results)
   - If max_results has a value: add LIMIT clause with that value

FIELD MAPPING:
- Sector filter: WHERE "Sector 1" = 'Fintech' OR "Sector 2" = 'Fintech'
- Round filter: WHERE "Round" ILIKE '%Series A%'
- Country filter: WHERE "Country" = 'United States'
- Amount filter: WHERE CAST(REPLACE("Amount_Raised", ' M$', '') AS FLOAT) > 10.0
- Investors filter: WHERE "Investors" ILIKE '%Sequoia%'
- Spotted Date After: WHERE "Spotted_Date" >= '2025-01-01'
- Spotted Date Before: WHERE "Spotted_Date" <= '2025-12-31'
- Founding Year: WHERE "Founding_Year" = '2020'
- Founding Year Min: WHERE CAST("Founding_Year" AS INTEGER) >= 2020
- Founding Year Max: WHERE CAST("Founding_Year" AS INTEGER) <= 2022

EXAMPLES:

Example 1 (NO LIMIT - return all results):
Intent: {{"criteria": {{"sector": "AI"}}, "max_results": null}}
SQL: SELECT * FROM deals WHERE "Sector 1" ILIKE '%AI%'

Example 2 (WITH LIMIT):
Intent: {{"criteria": {{"sector": "Fintech"}}, "max_results": 10}}
SQL: SELECT * FROM deals WHERE "Sector 1" ILIKE '%Fintech%' LIMIT 10

Example 3 (Date + Investor filters, NO LIMIT):
Intent: {{"criteria": {{"investors": "Sequoia", "spotted_date_after": "2025-01-01"}}, "max_results": null}}
SQL: SELECT * FROM deals WHERE "Investors" ILIKE '%Sequoia%' AND "Spotted_Date" >= '2025-01-01'

Example 4 (Founding year filter, NO LIMIT):
Intent: {{"criteria": {{"founding_year_min": "2020", "tags": ["AI"]}}, "max_results": null}}
SQL: SELECT * FROM deals WHERE CAST("Founding_Year" AS INTEGER) >= 2020 AND ("Tag 1" ILIKE '%AI%' OR "Tag 2" ILIKE '%AI%' OR "Tag 3" ILIKE '%AI%')

Your SQL query (output ONLY the SQL, no explanations):
"""
        
        messages = [
            SystemMessage(content=SQL_GENERATION_SYSTEM),
            HumanMessage(content=enhanced_prompt)
        ]
        
        # Call LLM with retries
        max_retries = 2
        sql_query = None
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Calling LLM for SQL generation (attempt {attempt + 1}/{max_retries + 1})...")
                response = llm.invoke(messages)
                sql_query = response.content.strip()
                
                # Clean SQL (remove markdown if present)
                if "```sql" in sql_query or "```" in sql_query:
                    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
                
                logger.info(f"Generated SQL:\n{sql_query}")
                
                # Validate SQL
                is_valid, error_msg = duckdb_client.validate_query(sql_query)
                
                if is_valid:
                    logger.info("✅ SQL query validated successfully")
                    
                    # Check if LIMIT is appropriate
                    has_limit = "LIMIT" in sql_query.upper()
                    should_have_limit = analyzed_intent.max_results is not None
                    
                    if has_limit and not should_have_limit:
                        logger.warning("⚠️ Query has LIMIT but max_results is None - removing LIMIT")
                        sql_query = sql_query.split("LIMIT")[0].strip()
                    elif not has_limit and should_have_limit:
                        logger.info(f"✅ Adding LIMIT {analyzed_intent.max_results}")
                        sql_query = f"{sql_query} LIMIT {analyzed_intent.max_results}"
                    
                    return {
                        "generated_query": sql_query,
                        "query_valid": True,
                        "query_errors": [],
                        "current_step": "query_generated",
                        "retry_count": 0
                    }
                else:
                    logger.warning(f"⚠️ SQL validation failed: {error_msg}")
                    
                    if attempt < max_retries:
                        # Ask LLM to fix the query
                        messages.append(HumanMessage(content=sql_query))
                        messages.append(HumanMessage(content=f"""
The SQL query has an error: {error_msg}

Please fix the query and output ONLY the corrected SQL:
"""))
                    else:
                        return {
                            "generated_query": sql_query,
                            "query_valid": False,
                            "query_errors": [error_msg],
                            "current_step": "query_validation_failed",
                            "retry_count": state.retry_count + 1
                        }
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt >= max_retries:
                    return {
                        "current_step": "query_generation_failed",
                        "query_valid": False,
                        "query_errors": [str(e)],
                        "retry_count": state.retry_count + 1
                    }
        
    except Exception as e:
        logger.error(f"❌ SQL generation failed: {e}", exc_info=True)
        return {
            "current_step": "query_generation_failed",
            "query_valid": False,
            "query_errors": [str(e)],
            "retry_count": state.retry_count + 1,
            "errors": state.errors + [
                {
                    "node": "sql_query_generator",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "retry_possible": True
                }
            ]
        }
