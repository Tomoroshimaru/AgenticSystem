"""
Web Enrichment Node
===================
Searches the web for similar companies and calculates similarity scores.
"""

import json
from typing import Dict, Any, List, Set
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from config import LLMConfig, APIConfig, WorkflowConfig, SimilarityWeights
from state import InvestmentState, EnrichedDeal, SimilarCompany, NotionDeal
from tools import SerperSearchClient
from prompts import ENRICHMENT_SYSTEM, ENRICHMENT_PROMPT, SEARCH_QUERY_TEMPLATE


def web_enrichment_node(state: InvestmentState) -> Dict[str, Any]:
    """
    Node 5: Enrich selected deals with similar companies from web search
    
    Args:
        state: Current workflow state
        
    Returns:
        State updates
    """
    logger.info("=" * 50)
    logger.info("NODE 5: Web Enrichment")
    logger.info("=" * 50)
    
    try:
        selected_deal_ids = state.selected_deal_ids
        notion_results = state.notion_results
        
        if not selected_deal_ids:
            logger.warning("No deals selected for enrichment")
            return {
                "current_step": "no_deals_selected",
                "enriched_deals": [],
                "total_similar_companies": 0
            }
        
        # Get selected deals
        selected_deals = [
            deal for deal in notion_results
            if deal.id in selected_deal_ids
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
            logger.info(f"Processing deal {i}/{len(selected_deals)}: {deal.company}")
            
            try:
                # Enrich single deal
                enriched_deal = _enrich_single_deal(
                    deal=deal,
                    search_client=search_client,
                    llm=llm,
                    state=state
                )
                
                enriched_deals.append(enriched_deal)
                
                logger.info(f"✅ Found {len(enriched_deal.similar_companies)} similar companies for {deal.company}")
                
            except Exception as e:
                logger.error(f"Failed to enrich deal {deal.company}: {e}")
                
                # Add empty enrichment on failure
                enriched_deals.append(EnrichedDeal(
                    original_deal=deal,
                    similar_companies=[],
                    enrichment_success=False
                ))
        
        total_similar = sum(len(ed.similar_companies) for ed in enriched_deals)
        
        logger.info(f"✅ Enrichment complete: {total_similar} similar companies found across {len(enriched_deals)} deals")
        
        return {
            "enriched_deals": enriched_deals,
            "total_similar_companies": total_similar,
            "current_step": "enrichment_complete",
            "messages": state.messages + [
                {"role": "assistant", "content": f"Enrichissement terminé ! J'ai trouvé {total_similar} entreprises similaires au total."}
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Web enrichment failed: {e}")
        
        return {
            "current_step": "enrichment_failed",
            "enriched_deals": [],
            "total_similar_companies": 0,
            "errors": state.errors + [
                {
                    "node": "web_enrichment",
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "retry_possible": True
                }
            ]
        }


def _enrich_single_deal(
    deal: NotionDeal,
    search_client: SerperSearchClient,
    llm: ChatOpenAI,
    state: InvestmentState
) -> EnrichedDeal:
    """
    Enrich a single deal with similar companies
    
    Args:
        deal: Deal to enrich
        search_client: Serper search client
        llm: OpenAI LLM
        state: Current state
        
    Returns:
        EnrichedDeal with similar companies
    """
    # Build search query
    tags = " ".join(filter(None, [deal.tag_1, deal.tag_2, deal.tag_3]))
    
    search_query = SEARCH_QUERY_TEMPLATE.format(
        sector=deal.sector or "",
        round=deal.round or "",
        company_name=deal.company,
        tags=tags
    )
    
    logger.info(f"Search query: {search_query}")
    
    # Perform web search
    search_results = search_client.search(search_query, num_results=10)
    
    if not search_results:
        logger.warning(f"No search results for {deal.company}")
        return EnrichedDeal(
            original_deal=deal,
            similar_companies=[],
            enrichment_success=False
        )
    
    # Format search results for LLM
    search_results_text = "\n\n".join([
        f"[{i+1}] {r['title']}\nURL: {r['link']}\n{r['snippet']}"
        for i, r in enumerate(search_results)
    ])
    
    # Call LLM to extract similar companies
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
    
    logger.info("Calling LLM to analyze search results...")
    response = llm.invoke(messages)
    
    # Parse response
    response_text = response.content.strip()
    
    # Clean response
    if response_text.startswith("```json"):
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif response_text.startswith("```"):
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    # Parse JSON
    try:
        result_data = json.loads(response_text)
        similar_companies_data = result_data.get("similar_companies", [])
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        similar_companies_data = []
    
    # Create SimilarCompany objects
    similar_companies = []
    
    for comp_data in similar_companies_data[:state.enrichment_criteria["max_similar_per_deal"]]:
        try:
            # Filter by similarity threshold
            if comp_data.get("similarity_score", 0) >= state.enrichment_criteria["min_similarity"]:
                similar_comp = SimilarCompany(**comp_data)
                similar_companies.append(similar_comp)
        except Exception as e:
            logger.warning(f"Failed to create SimilarCompany: {e}")
            continue
    
    return EnrichedDeal(
        original_deal=deal,
        similar_companies=similar_companies,
        enrichment_success=True
    )


def calculate_similarity_score(
    deal: NotionDeal,
    candidate: Dict[str, Any]
) -> float:
    """
    Calculate similarity score between a deal and a candidate company
    
    Args:
        deal: Original deal from Notion
        candidate: Candidate company data
        
    Returns:
        Similarity score (0-1)
    """
    score = 0.0
    
    # Sector match (30%)
    if candidate.get("sector", "").lower() == (deal.sector or "").lower():
        score += SimilarityWeights.SECTOR_WEIGHT
    
    # Round match (25%)
    if candidate.get("round", "").lower() == (deal.round or "").lower():
        score += SimilarityWeights.ROUND_WEIGHT
    
    # Tags match (25%)
    deal_tags = {deal.tag_1, deal.tag_2, deal.tag_3} - {None, ""}
    candidate_tags = set(candidate.get("tags", []))
    
    if deal_tags and candidate_tags:
        tag_overlap = len(deal_tags & candidate_tags)
        score += (tag_overlap / max(len(deal_tags), 1)) * SimilarityWeights.TAGS_WEIGHT
    
    # Pitch similarity (20%) - simple keyword matching
    if deal.pitch and candidate.get("description"):
        deal_keywords = set(deal.pitch.lower().split())
        candidate_keywords = set(candidate.get("description", "").lower().split())
        
        if deal_keywords and candidate_keywords:
            keyword_overlap = len(deal_keywords & candidate_keywords)
            keyword_score = min(keyword_overlap / 10, 1.0)  # Normalize
            score += keyword_score * SimilarityWeights.PITCH_WEIGHT
    
    return round(score, 2)