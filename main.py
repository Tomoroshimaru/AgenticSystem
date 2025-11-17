"""
Investment Agent - Main Orchestration
======================================
LangGraph workflow for investment deal analysis and enrichment.
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
    query_generator_node,
    notion_fetcher_node,
    human_review_node,
    web_enrichment_node,
    pdf_generator_node,
    drive_uploader_node
)


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure loguru logging"""
    logger.remove()  # Remove default handler
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
# CONDITIONAL ROUTING FUNCTIONS
# ============================================================================

def route_after_query_generation(state: InvestmentState) -> Literal["notion_fetcher", "intent_analyzer"]:
    """
    Route after query generation based on validation
    
    Args:
        state: Current state
        
    Returns:
        Next node name
    """
    if state.query_valid:
        logger.info("✓ Query valid → routing to notion_fetcher")
        return "notion_fetcher"
    else:
        # Check retry limit
        if state.retry_count >= WorkflowConfig.MAX_RETRY_ATTEMPTS:
            logger.error(f"✗ Max retries ({WorkflowConfig.MAX_RETRY_ATTEMPTS}) exceeded")
            return END
        
        logger.warning(f"✗ Query invalid (retry {state.retry_count}/{WorkflowConfig.MAX_RETRY_ATTEMPTS}) → routing back to intent_analyzer")
        return "intent_analyzer"


def route_after_notion_fetch(state: InvestmentState) -> Literal["human_review", "__end__"]:
    """
    Route after Notion fetch based on results
    
    Args:
        state: Current state
        
    Returns:
        Next node name
    """
    if state.results_count > 0:
        logger.info(f"✓ Found {state.results_count} results → routing to human_review")
        return "human_review"
    else:
        logger.warning("✗ No results found → ending workflow")
        return END


def route_after_human_review(state: InvestmentState) -> Literal["web_enrichment", "__end__"]:
    """
    Route after human review based on selection
    
    Args:
        state: Current state
        
    Returns:
        Next node name
    """
    if len(state.selected_deal_ids) > 0:
        logger.info(f"✓ {len(state.selected_deal_ids)} deal(s) selected → routing to web_enrichment")
        return "web_enrichment"
    else:
        logger.warning("✗ No deals selected → ending workflow")
        return END


def route_after_enrichment(state: InvestmentState) -> Literal["pdf_generator", "__end__"]:
    """
    Route after enrichment based on results
    
    Args:
        state: Current state
        
    Returns:
        Next node name
    """
    if state.enriched_deals and state.total_similar_companies > 0:
        logger.info(f"✓ {state.total_similar_companies} similar companies found → routing to pdf_generator")
        return "pdf_generator"
    else:
        logger.warning("✗ No enrichment data → ending workflow")
        return END


def route_after_pdf(state: InvestmentState) -> Literal["drive_uploader", "__end__"]:
    """
    Route after PDF generation
    
    Args:
        state: Current state
        
    Returns:
        Next node name
    """
    if state.pdf_generated and state.pdf_local_path:
        logger.info("✓ PDF generated → routing to drive_uploader")
        return "drive_uploader"
    else:
        logger.error("✗ PDF generation failed → ending workflow")
        return END


# ============================================================================
# GRAPH BUILDER
# ============================================================================

def build_graph() -> StateGraph:
    """
    Build the LangGraph workflow
    
    Returns:
        Compiled StateGraph
    """
    logger.info("Building LangGraph workflow...")
    
    # Create graph builder
    builder = StateGraph(InvestmentState)
    
    # Add nodes
    logger.info("Adding nodes...")
    builder.add_node("intent_analyzer", intent_analyzer_node)
    builder.add_node("query_generator", query_generator_node)
    builder.add_node("notion_fetcher", notion_fetcher_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("web_enrichment", web_enrichment_node)
    builder.add_node("pdf_generator", pdf_generator_node)
    builder.add_node("drive_uploader", drive_uploader_node)
    
    # Define edges
    logger.info("Defining edges...")
    
    # Entry point
    builder.add_edge(START, "intent_analyzer")
    
    # Intent Analyzer → Query Generator (always)
    builder.add_edge("intent_analyzer", "query_generator")
    
    # Query Generator → Notion Fetcher OR back to Intent (conditional)
    builder.add_conditional_edges(
        "query_generator",
        route_after_query_generation,
        {
            "notion_fetcher": "notion_fetcher",
            "intent_analyzer": "intent_analyzer",
            END: END
        }
    )
    
    # Notion Fetcher → Human Review OR End (conditional)
    builder.add_conditional_edges(
        "notion_fetcher",
        route_after_notion_fetch,
        {
            "human_review": "human_review",
            END: END
        }
    )
    
    # Human Review → Web Enrichment OR End (conditional)
    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "web_enrichment": "web_enrichment",
            END: END
        }
    )
    
    # Web Enrichment → PDF Generator OR End (conditional)
    builder.add_conditional_edges(
        "web_enrichment",
        route_after_enrichment,
        {
            "pdf_generator": "pdf_generator",
            END: END
        }
    )
    
    # PDF Generator → Drive Uploader OR End (conditional)
    builder.add_conditional_edges(
        "pdf_generator",
        route_after_pdf,
        {
            "drive_uploader": "drive_uploader",
            END: END
        }
    )
    
    # Drive Uploader → End (always)
    builder.add_edge("drive_uploader", END)
    
    logger.info("✓ Graph structure defined")
    
    return builder


def compile_graph(builder: StateGraph) -> StateGraph:
    """
    Compile the graph with checkpointing
    
    Args:
        builder: Graph builder
        
    Returns:
        Compiled graph
    """
    logger.info("Compiling graph with checkpointing...")
    
    # Use MemorySaver for checkpointing (in-memory for simplicity)
    # For production, use SqliteSaver or PostgresSaver
    checkpointer = MemorySaver()
    
    graph = builder.compile(checkpointer=checkpointer)
    
    logger.info("✓ Graph compiled successfully")
    
    return graph


# ============================================================================
# MAIN EXECUTION FUNCTIONS
# ============================================================================

def run_workflow(user_query: str, thread_id: str = "default"):
    """
    Run the complete workflow for a user query
    
    Args:
        user_query: User's search query
        thread_id: Thread ID for conversation tracking
    """
    logger.info("=" * 70)
    logger.info("STARTING INVESTMENT AGENT WORKFLOW")
    logger.info("=" * 70)
    logger.info(f"User Query: {user_query}")
    logger.info(f"Thread ID: {thread_id}")
    logger.info("=" * 70)
    
    # Build and compile graph
    builder = build_graph()
    graph = compile_graph(builder)
    
    # Initialize state
    initial_state = InvestmentState(
        user_query=user_query,
        messages=[{"role": "user", "content": user_query}]
    )
    
    # Configuration for execution
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    try:
        # Execute graph
        logger.info("Starting graph execution...")
        
        result = None
        for event in graph.stream(initial_state.model_dump(), config, stream_mode="values"):
            result = event
            
            # Log current step
            current_step = result.get("current_step", "unknown")
            logger.info(f"Current step: {current_step}")
            
            # Check for interruption (human-in-the-loop)
            if current_step == "deals_selected" or "interrupt" in str(event):
                logger.info("⏸️  Workflow interrupted for human input")
                
                # Display deals for selection
                notion_results = result.get("notion_results", [])
                if notion_results:
                    print("\n" + "=" * 70)
                    print("📊 DEALS FOUND - Please select deals to enrich")
                    print("=" * 70)
                    
                    for i, deal in enumerate(notion_results, 1):
                        print(f"\n[{i}] {deal['company']}")
                        print(f"    Sector: {deal.get('sector', 'N/A')} | "
                              f"Round: {deal.get('round', 'N/A')} | "
                              f"Amount: {deal.get('amount_raised', 'N/A')}")
                    
                    print("\n" + "=" * 70)
                    
                    # Get user input
                    selection = input("\nEnter deal numbers (e.g., 1,3,5) or 'all': ").strip()
                    feedback = input("Optional feedback (press Enter to skip): ").strip()
                    
                    # Resume with user input
                    user_input = {
                        "selection": selection,
                        "feedback": feedback if feedback else None
                    }
                    
                    logger.info(f"Resuming with user input: {user_input}")
                    
                    # Continue execution with Command
                    for event in graph.stream(
                        Command(resume=user_input),
                        config,
                        stream_mode="values"
                    ):
                        result = event
                        current_step = result.get("current_step", "unknown")
                        logger.info(f"Current step: {current_step}")
        
        # Final result
        logger.info("=" * 70)
        logger.info("WORKFLOW COMPLETED")
        logger.info("=" * 70)
        
        if result:
            # Display final summary
            print("\n" + "=" * 70)
            print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
            print("=" * 70)
            
            if result.get("workflow_complete"):
                print(f"\n📊 Summary:")
                print(f"   - Deals analyzed: {len(result.get('selected_deal_ids', []))}")
                print(f"   - Similar companies found: {result.get('total_similar_companies', 0)}")
                
                if result.get("drive_file_url"):
                    print(f"\n📄 Report: {result['drive_file_url']}")
                elif result.get("pdf_local_path"):
                    print(f"\n📄 Report (local): {result['pdf_local_path']}")
            
            # Display errors if any
            if result.get("errors"):
                print("\n⚠️  Errors encountered:")
                for error in result["errors"]:
                    print(f"   - [{error['node']}] {error['message']}")
            
            print("\n" + "=" * 70)
        
        return result
        
    except KeyboardInterrupt:
        logger.warning("Workflow interrupted by user")
        print("\n⚠️  Workflow interrupted by user")
        return None
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        print(f"\n❌ Error: {e}")
        raise


def interactive_mode():
    """
    Run the agent in interactive mode with conversation loop
    """
    print("\n" + "=" * 70)
    print("🤖 INVESTMENT AGENT - Interactive Mode")
    print("=" * 70)
    print("\nI help you find and analyze investment deals from your Notion database.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    thread_id = "interactive_session"
    
    while True:
        try:
            user_query = input("\n💬 Your query: ").strip()
            
            if user_query.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break
            
            if not user_query:
                print("⚠️  Please enter a query.")
                continue
            
            # Run workflow
            run_workflow(user_query, thread_id=thread_id)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'quit' to exit.")


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main entry point"""
    setup_logging()
    
    logger.info("Investment Agent starting...")
    
    # Validate configuration
    try:
        validate_config()
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease check your .env file and ensure all required API keys are set.")
        sys.exit(1)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        # Single query mode
        user_query = " ".join(sys.argv[1:])
        run_workflow(user_query)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()