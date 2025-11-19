"""
Web Enrichment Node
===================
Searches the web for similar companies and calculates similarity scores.
"""

import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from config import LLMConfig, APIConfig, WorkflowConfig, SimilarityWeights
from state import InvestmentState, EnrichedDeal, SimilarCompany, Deal
from tools import SerperSearchClient
from prompts import ENRICHMENT_SYSTEM, ENRICHMENT_PROMPT, SEARCH_QUERY_TEMPLATE


def web_enrichment_node(state: InvestmentState) -> Dict[str, Any]:
    """Node 5: Enrich selected deals with similar companies"""
    logger.info("=" * 50)
    logger.info("NODE 5: Web Enrichment")
    logger.info("=" * 50)
    
    try:
        selected_deal_ids = state.selected_deal_ids
        deals = state.deals
        
        if not selected_deal_ids:
            logger.warning("No deals selected")
            return {
                "current_step": "no_deals_selected",
                "enriched_deals": [],
                "total_similar_companies": 0
            }
        
        # Get selected deals
        selected_deals = [
            deals[i]
            for i in selected_deal_ids
            if i < len(deals)
        ]
        
        logger.info(f"Enriching {len(selected_deals)} deal(s)")
        
        # Initialize clients
        search_client = SerperSearchClient()
        llm = ChatOpenAI(
            model=LLMConfig.MODEL_NAME,
            temperature=LLMConfig.TEMPERATURE_ENRICHMENT,
            max_tokens=LLMConfig.MAX_TOKENS_ENRICHMENT,
            api_key=APIConfig.OPENAI_API_KEY
        )
        
        enriched_deals = []
        
        for i, deal in enumerate(selected_deals, 1):
            logger.info(f"Processing {i}/{len(selected_deals)}: {deal.company}")
            
            try:
                enriched_deal = _enrich_single_deal(deal, search_client, llm, state)
                enriched_deals.append(enriched_deal)
                logger.info(f"✅ Found {len(enriched_deal.similar_companies)} similar")
            except Exception as e:
                logger.error(f"Failed to enrich {deal.company}: {e}")
                enriched_deals.append(EnrichedDeal(
                    original_deal=deal,
                    similar_companies=[],
                    enrichment_success=False
                ))
        
        total_similar = sum(len(ed.similar_companies) for ed in enriched_deals)
        
        logger.info(f"✅ Total: {total_similar} similar companies")
        
        return {
            "enriched_deals": enriched_deals,
            "total_similar_companies": total_similar,
            "current_step": "enrichment_complete",
            "messages": state.messages + [
                {"role": "assistant", "content": f"{total_similar} entreprises similaires trouvées."}
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Enrichment failed: {e}")
        
        return {
            "current_step": "enrichment_failed",
            "enriched_deals": [],
            "total_similar_companies": 0,
            "errors": state.errors + [{
                "node": "web_enrichment",
                "error_type": type(e).__name__,
                "message": str(e),
                "retry_possible": True
            }]
        }


def _enrich_single_deal(
    deal: Deal,
    search_client: SerperSearchClient,
    llm: ChatOpenAI,
    state: InvestmentState
) -> EnrichedDeal:
    """Enrich a single deal"""
    tags = " ".join([t for t in deal.tags if t])
    
    search_query = SEARCH_QUERY_TEMPLATE.format(
        sector=deal.sector or "",
        round=deal.round or "",
        company_name=deal.company,
        tags=tags
    )
    
    logger.info(f"Search: {search_query}")
    
    search_results = search_client.search(search_query, num_results=10)
    
    if not search_results:
        return EnrichedDeal(
            original_deal=deal,
            similar_companies=[],
            enrichment_success=False
        )
    
    search_results_text = "\n\n".join([
        f"[{i+1}] {r['title']}\nURL: {r['link']}\n{r['snippet']}"
        for i, r in enumerate(search_results)
    ])
    
    messages = [
        SystemMessage(content=ENRICHMENT_SYSTEM),
        HumanMessage(content=ENRICHMENT_PROMPT.format(
            company_name=deal.company,
            sector=deal.sector or "N/A",
            round=deal.round or "N/A",
            tags=tags or "N/A",
            pitch=deal.pitch or "N/A",
            search_results=search_results_text
        ))
    ]
    
    response = llm.invoke(messages)
    response_text = response.content.strip()
    
    # Clean JSON
    if response_text.startswith("```json"):
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif response_text.startswith("```"):
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    try:
        result_data = json.loads(response_text)
        similar_companies_data = result_data.get("similar_companies", [])
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        similar_companies_data = []
    
    similar_companies = []
    
    for comp_data in similar_companies_data[:state.enrichment_criteria["max_similar_per_deal"]]:
        try:
            if comp_data.get("similarity_score", 0) >= state.enrichment_criteria["min_similarity"]:
                similar_companies.append(SimilarCompany(**comp_data))
        except Exception as e:
            logger.warning(f"Failed to create SimilarCompany: {e}")
    
    return EnrichedDeal(
        original_deal=deal,
        similar_companies=similar_companies,
        enrichment_success=True
    )
