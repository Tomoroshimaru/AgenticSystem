"""
Prompts package
===============
Centralized prompt templates for all nodes.
"""

from .intent_analysis import INTENT_ANALYSIS_PROMPT, INTENT_ANALYSIS_SYSTEM
from .sql_generation import SQL_GENERATION_PROMPT, SQL_GENERATION_SYSTEM
from .enrichment import ENRICHMENT_PROMPT, ENRICHMENT_SYSTEM, SEARCH_QUERY_TEMPLATE

__all__ = [
    "INTENT_ANALYSIS_PROMPT",
    "INTENT_ANALYSIS_SYSTEM",
    "SQL_GENERATION_PROMPT",
    "SQL_GENERATION_SYSTEM",
    "ENRICHMENT_PROMPT",
    "ENRICHMENT_SYSTEM",
    "SEARCH_QUERY_TEMPLATE", 
]