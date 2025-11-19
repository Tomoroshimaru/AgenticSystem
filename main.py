"""
Investment Agent - Main Orchestration
======================================
LangGraph workflow for investment deal analysis and enrichment.
DuckDB-powered CSV data source.
"""

import sys
from typing import Literal
from loguru import logger
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from state import InvestmentState
from config import WorkflowConfig, LogConfig, validate_config
from nodes import (
    intent_analyzer_node,
    sql_query_generator_node,
    duckdb_fetcher_node,
    human_review_node,
    web_enrichment_node,
    pdf_generator_node,
    drive_uploader_node
)


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configure loguru logging"""
    logger.remove()
    logger.add(
        sys.stdout,
        format=LogConfig.LOG_FORMAT,
        level=LogConfig.LOG_LEVEL,
        colorize=True
    )
    logger.add(
        "logs/investment_agent.log",
        format=LogConfig.LOG_FORMAT,
        level="DEBUG",
        rotation="10 MB",
        retention="7 days"
    )


# ============================================================================
# ROUTING LOGIC
# ============================================================================

def route_after_sql_generation(state: InvestmentState) -> Literal["duckdb_fetcher", "intent_analyzer", "__end__"]:
    if state.query_valid:
        logger.info("✓ SQL valid → fetch data")
        return "duckdb_fetcher"
    
    if state.retry_count >= WorkflowConfig.MAX_RETRY_ATTEMPTS:
        logger.error(f"✗ Max retries exceeded")
        return END
    
    logger.warning(f"✗ SQL invalid (retry {state.retry_count})")
    return "intent_analyzer"


def route_after_fetch(state: InvestmentState) -> Literal["human_review", "__end__"]:
    if state.results_count > 0:
        logger.info(f"✓ Found {state.results_count} deals → review")
        return "human_review"
    
    logger.warning("✗ No results")
    return END


def route_after_review(state: InvestmentState) -> Literal["web_enrichment", "__end__"]:
    if state.selected_deal_ids:
        logger.info(f"✓ {len(state.selected_deal_ids)} selected → enrich")
        return "web_enrichment"
    
    logger.warning("✗ No deals selected")
    return END


def route_after_enrichment(state: InvestmentState) -> Literal["pdf_generator", "__end__"]:
    if state.enriched_deals and state.total_similar_companies > 0:
        logger.info(f"✓ {state.total_similar_companies} companies → PDF")
        return "pdf_generator"
    
    logger.warning("✗ No enrichment")
    return END


def route_after_pdf(state: InvestmentState) -> Literal["drive_uploader", "__end__"]:
    if state.pdf_generated and state.pdf_local_path:
        logger.info("✓ PDF ready → upload")
        return "drive_uploader"
    
    logger.error("✗ PDF failed")
    return END


# ============================================================================
# GRAPH BUILDER
# ============================================================================

def build_workflow() -> StateGraph:
    logger.info("Building workflow...")
    
    builder = StateGraph(InvestmentState)
    
    builder.add_node("intent_analyzer", intent_analyzer_node)
    builder.add_node("sql_generator", sql_query_generator_node)
    builder.add_node("data_fetcher", duckdb_fetcher_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("enrichment", web_enrichment_node)
    builder.add_node("pdf_generator", pdf_generator_node)
    builder.add_node("drive_uploader", drive_uploader_node)
    
    builder.add_edge(START, "intent_analyzer")
    builder.add_edge("intent_analyzer", "sql_generator")
    
    builder.add_conditional_edges(
        "sql_generator",
        route_after_sql_generation,
        {"duckdb_fetcher": "data_fetcher", "intent_analyzer": "intent_analyzer", END: END}
    )
    
    builder.add_conditional_edges(
        "data_fetcher",
        route_after_fetch,
        {"human_review": "human_review", END: END}
    )
    
    builder.add_conditional_edges(
        "human_review",
        route_after_review,
        {"web_enrichment": "enrichment", END: END}
    )
    
    builder.add_conditional_edges(
        "enrichment",
        route_after_enrichment,
        {"pdf_generator": "pdf_generator", END: END}
    )
    
    builder.add_conditional_edges(
        "pdf_generator",
        route_after_pdf,
        {"drive_uploader": "drive_uploader", END: END}
    )
    
    builder.add_edge("drive_uploader", END)
    
    checkpointer = MemorySaver()
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"]
    )
    
    logger.info("✓ Workflow built")
    return graph


# ============================================================================
# EXECUTION
# ============================================================================

def run_workflow(user_query: str, thread_id: str = "default"):
    logger.info(f"Starting workflow: {user_query}")
    
    graph = build_workflow()
    
    initial_state = InvestmentState(
        user_query=user_query,
        messages=[{"role": "user", "content": user_query}]
    )
    
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # Run until interrupt
        result = graph.invoke(initial_state.model_dump(), config)
        
        snapshot = graph.get_state(config)
        
        if snapshot.next:  # Interrupted
            logger.info("⏸️  Awaiting user input")
            
            deals = snapshot.values.get("deals", [])
            
            if deals:
                print("\n" + "=" * 70)
                print("📊 DEALS FOUND")
                print("=" * 70)
                
                for i, deal in enumerate(deals, 1):
                    print(f"\n[{i}] {deal['company']}")
                    print(f"    {deal.get('sector', 'N/A')} | "
                          f"{deal.get('round', 'N/A')} | "
                          f"{deal.get('amount_raised', 'N/A')}")
                
                print("\n" + "=" * 70)
                
                selection = input("\nSelect deals (1,3,5 or 'all'): ").strip()
                feedback = input("Feedback (optional): ").strip()
                
                # Parse selection immediately
                selected_indices = []
                if selection.lower() == "all":
                    selected_indices = list(range(len(deals)))
                else:
                    try:
                        nums = [int(x.strip()) for x in selection.split(",") if x.strip()]
                        selected_indices = [i - 1 for i in nums if 1 <= i <= len(deals)]
                    except:
                        pass
                
                # Update state with parsed selection
                graph.update_state(config, {
                    "selected_deal_ids": selected_indices,
                    "user_feedback": feedback or None
                })
                
                # Continue
                result = graph.invoke(None, config)
                
                logger.info("Workflow completed")
        
        print("\n✅ WORKFLOW COMPLETED")
        
        if result.get("workflow_complete"):
            print(f"\n📊 Summary:")
            print(f"   - Deals: {len(result.get('selected_deal_ids', []))}")
            print(f"   - Similar: {result.get('total_similar_companies', 0)}")
            
            if result.get("drive_file_url"):
                print(f"\n📄 {result['drive_file_url']}")
            elif result.get("pdf_local_path"):
                print(f"\n📄 {result['pdf_local_path']}")
        
        if result.get("errors"):
            print("\n⚠️  Errors:")
            for err in result["errors"]:
                print(f"   - {err['message']}")
        
        return result
        
    except KeyboardInterrupt:
        logger.warning("Interrupted")
        print("\n⚠️  Interrupted")
        return None
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        print(f"\n❌ {e}")
        raise


def interactive_mode():
    print("🤖 INVESTMENT AGENT")
    print("\nFind deals from CSV. Type 'quit' to exit.\n")
    
    thread_id = "interactive_session"
    
    while True:
        try:
            query = input("\n💬 Query: ").strip()
            
            if query.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break
            
            if not query:
                continue
            
            run_workflow(query, thread_id)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\n❌ {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    setup_logging()
    logger.info("Starting...")
    
    try:
        validate_config()
    except Exception as e:
        logger.error(f"Config error: {e}")
        print(f"\n❌ {e}")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_workflow(query)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
