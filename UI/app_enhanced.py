"""
Investment Agent - Streamlit UI (Enhanced)
==========================================
Enhanced version with improved badges and selection controls.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from typing import List, Dict, Any
from loguru import logger

from tools.duckdb_api import DuckDBClient
from config import APIConfig
from nodes.sql_query_generator import sql_query_generator_node
from nodes.intent_analyzer import intent_analyzer_node
from state import InvestmentState, AnalyzedIntent


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Investment Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for badges
st.markdown("""
<style>
/* Tag badges with icons */
.tag-badge {
    display: inline-block;
    padding: 0.35rem 0.85rem;
    margin: 0.25rem 0.25rem 0.25rem 0;
    border-radius: 1rem;
    font-size: 0.80rem;
    font-weight: 600;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    transition: transform 0.2s ease;
}

.tag-badge:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

/* Sector badges */
.sector-badge {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.sector-badge::before {
    content: "🏢 ";
}

/* Round badges */
.round-badge {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.round-badge::before {
    content: "💰 ";
}

/* Country badges */
.country-badge {
    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.country-badge::before {
    content: "🌍 ";
}

/* Amount badges */
.amount-badge {
    background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    font-weight: 700;
}

.amount-badge::before {
    content: "💵 ";
}

/* Generic tag badges */
.tech-badge {
    background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
    color: #333;
}

.tech-badge::before {
    content: "🏷️ ";
}

/* Badge container */
.badge-container {
    margin: 0.5rem 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
}

/* Selection indicator */
.selected-card {
    border-left: 4px solid #4facfe;
    padding-left: 1rem;
    background-color: rgba(79, 172, 254, 0.05);
}

/* Metrics styling */
.stMetric {
    background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
    padding: 1rem;
    border-radius: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
    defaults = {
        "deals": [],
        "selected_deals": set(),
        "expanded_pitches": set(),
        "search_performed": False,
        "workflow_started": False,
        "workflow_complete": False,
        "report_data": None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================================
# BACKEND
# ============================================================================

def search_deals(query: str) -> List[Dict[str, Any]]:
    try:
        state = InvestmentState(
            user_query=query,
            messages=[{"role": "user", "content": query}]
        )
        
        intent_result = intent_analyzer_node(state)
        if not intent_result.get("analyzed_intent"):
            st.error("Failed to analyze query")
            return []
        
        analyzed_intent_data = intent_result.get("analyzed_intent")
        if isinstance(analyzed_intent_data, dict):
            state.analyzed_intent = AnalyzedIntent(**analyzed_intent_data)
        else:
            state.analyzed_intent = analyzed_intent_data
        
        sql_result = sql_query_generator_node(state)
        if not sql_result.get("query_valid"):
            st.error(f"Invalid query: {sql_result.get('query_errors', [])}")
            return []
        
        sql_query = sql_result["generated_query"]
        
        client = DuckDBClient(APIConfig.DUCKDB_CSV_PATH)
        raw_results = client.execute_query(sql_query)
        
        from tools.duckdb_api import format_deal_for_display
        deals = [format_deal_for_display(deal) for deal in raw_results]
        
        return deals
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        st.error(f"Search error: {e}")
        return []


def run_workflow(selected_indices: List[int]):
    try:
        st.session_state.workflow_started = True
        
        import time
        progress = st.progress(0)
        status = st.empty()
        
        status.text("🔍 Enriching deals...")
        progress.progress(33)
        time.sleep(1)
        
        status.text("📄 Generating PDF...")
        progress.progress(66)
        time.sleep(1)
        
        status.text("☁️ Uploading to Drive...")
        progress.progress(100)
        time.sleep(1)
        
        st.session_state.report_data = {
            "pdf_path": "output/investment_report_20241119.pdf",
            "drive_url": "https://drive.google.com/file/d/...",
            "similar_companies": 15
        }
        
        st.session_state.workflow_complete = True
        progress.empty()
        status.empty()
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        st.error(f"Workflow error: {e}")


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_badge(text: str, badge_type: str = "tag") -> str:
    """Generate HTML for a single badge"""
    return f'<span class="tag-badge {badge_type}-badge">{text}</span>'


def render_badges_html(items: List[tuple], container_class: str = "badge-container") -> str:
    """Generate HTML for multiple badges
    
    Args:
        items: List of tuples (text, badge_type)
        container_class: CSS class for the container
    """
    if not items:
        return ""
    
    badges = [render_badge(text, badge_type) for text, badge_type in items if text]
    badges_html = f'<div class="{container_class}">{"".join(badges)}</div>'
    return badges_html


def render_deal_card(deal: Dict[str, Any], index: int):
    is_selected = index in st.session_state.selected_deals
    
    with st.container():
        # Apply selected styling
        if is_selected:
            st.markdown('<div class="selected-card">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([0.05, 0.95])
        
        with col1:
            if st.checkbox("", value=is_selected, key=f"select_{index}", label_visibility="collapsed"):
                st.session_state.selected_deals.add(index)
            else:
                st.session_state.selected_deals.discard(index)
        
        with col2:
            st.markdown(f"### {deal['company']}")
            
            # Main badges (sector, round, country)
            main_badges = []
            if deal.get('sector') and deal['sector'] != 'N/A':
                main_badges.append((deal['sector'], 'sector'))
            if deal.get('round') and deal['round'] != 'N/A':
                main_badges.append((deal['round'], 'round'))
            if deal.get('country') and deal['country'] != 'N/A':
                main_badges.append((deal['country'], 'country'))
            if deal.get('amount_raised') and deal['amount_raised'] != 'N/A':
                main_badges.append((deal['amount_raised'], 'amount'))
            
            if main_badges:
                st.markdown(render_badges_html(main_badges), unsafe_allow_html=True)
            
            # Pitch
            pitch = deal.get('pitch', '')
            if pitch:
                render_expandable_pitch(pitch, index)
            
            # Tags as badges
            tags = [t for t in deal.get('tags', []) if t]
            if tags:
                st.markdown("**Tags:**")
                tag_badges = [(tag, 'tech') for tag in tags]
                st.markdown(render_badges_html(tag_badges), unsafe_allow_html=True)
            
            # Links
            link_cols = st.columns([1, 1])
            with link_cols[0]:
                if deal.get('website'):
                    st.markdown(f"🔗 [Website]({deal['website']})")
            with link_cols[1]:
                if deal.get('linkedin_url'):
                    st.markdown(f"💼 [LinkedIn]({deal['linkedin_url']})")
        
        if is_selected:
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()


def render_expandable_pitch(pitch: str, index: int, max_length: int = 180):
    is_long = len(pitch) > max_length
    is_expanded = index in st.session_state.expanded_pitches
    
    if not is_long:
        st.markdown(f"**Pitch:** {pitch}")
    else:
        if is_expanded:
            st.markdown(f"**Pitch:** {pitch}")
            if st.button("Show less", key=f"collapse_{index}"):
                st.session_state.expanded_pitches.remove(index)
                st.rerun()
        else:
            truncated = pitch[:max_length] + "..."
            st.markdown(f"**Pitch:** {truncated}")
            if st.button("Show more", key=f"expand_{index}"):
                st.session_state.expanded_pitches.add(index)
                st.rerun()


def render_report_section():
    st.markdown("---")
    st.markdown("## 📄 Generated Report")
    
    report = st.session_state.report_data
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Deals Analyzed", len(st.session_state.selected_deals))
    with col2:
        st.metric("Similar Companies", report.get("similar_companies", 0))
    with col3:
        st.metric("Status", "✅ Complete")
    
    st.markdown("---")
    
    pdf_path = report.get("pdf_path")
    if pdf_path:
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                st.download_button(
                    label="📥 Download Report (PDF)",
                    data=pdf_bytes,
                    file_name="investment_report.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
        except FileNotFoundError:
            st.warning(f"⚠️ PDF file not found: {pdf_path}")
            if report.get("drive_url"):
                st.link_button("☁️ Open in Google Drive", report["drive_url"], use_container_width=True)
    elif report.get("drive_url"):
        st.link_button("☁️ View on Google Drive", report["drive_url"], type="primary", use_container_width=True)
    
    st.markdown("---")
    
    if st.button("🔄 Start New Search", type="secondary", use_container_width=True):
        for key in ["deals", "selected_deals", "expanded_pitches", "search_performed", 
                    "workflow_started", "workflow_complete", "report_data"]:
            if key in ["deals"]:
                st.session_state[key] = []
            elif key in ["selected_deals", "expanded_pitches"]:
                st.session_state[key] = set()
            elif isinstance(st.session_state.get(key), bool):
                st.session_state[key] = False
            else:
                st.session_state[key] = None
        st.rerun()


# ============================================================================
# MAIN
# ============================================================================

def main():
    init_session_state()
    
    st.title("💼 Investment Agent")
    st.markdown("Search and analyze investment deals with AI-powered insights")
    
    with st.sidebar:
        st.header("📊 Dashboard")
        
        if st.session_state.search_performed:
            st.metric("Total Results", len(st.session_state.deals))
            st.metric("Selected Deals", len(st.session_state.selected_deals))
            
            if st.session_state.deals:
                selection_pct = (len(st.session_state.selected_deals) / len(st.session_state.deals)) * 100
                st.metric("Selection Rate", f"{selection_pct:.0f}%")
        
        st.divider()
        
        st.markdown("""
        ### Features
        - 🔍 Natural language search
        - 🏷️ Visual tags & badges
        - ✅ Bulk selection
        - 📊 Detailed analytics
        - 🚀 Automated reports
        """)
    
    st.markdown("---")
    
    # Search interface
    search_query = st.text_input(
        "🔍 Enter your search query",
        placeholder="e.g., Find AI startups in France raising Series A",
        disabled=st.session_state.workflow_started
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        search_button = st.button("🔍 Search Deals", type="primary", use_container_width=True, 
                                 disabled=st.session_state.workflow_started)
    
    with col2:
        if st.button("🗑️ Clear All", use_container_width=True, disabled=st.session_state.workflow_started):
            st.session_state.deals = []
            st.session_state.selected_deals.clear()
            st.session_state.expanded_pitches.clear()
            st.session_state.search_performed = False
            st.rerun()
    
    if search_button and search_query:
        with st.spinner("🔍 Searching deals..."):
            deals = search_deals(search_query)
            st.session_state.deals = deals
            st.session_state.search_performed = True
            st.session_state.selected_deals.clear()
            st.session_state.expanded_pitches.clear()
    
    # Results section
    if st.session_state.search_performed and not st.session_state.workflow_complete:
        st.markdown("---")
        
        if not st.session_state.deals:
            st.info("ℹ️ No deals found. Try adjusting your search query.")
        else:
            # Selection controls with enhanced UI
            control_cols = st.columns([2, 1, 1])
            
            with control_cols[0]:
                if st.session_state.selected_deals:
                    st.success(f"✅ {len(st.session_state.selected_deals)} deal(s) selected for processing")
                else:
                    st.info("💡 Select deals below to generate a report")
            
            with control_cols[1]:
                if st.button("☑️ Select All", use_container_width=True, 
                           disabled=st.session_state.workflow_started):
                    st.session_state.selected_deals = set(range(len(st.session_state.deals)))
                    st.rerun()
            
            with control_cols[2]:
                if st.button("⬜ Deselect All", use_container_width=True, 
                           disabled=st.session_state.workflow_started):
                    st.session_state.selected_deals.clear()
                    st.rerun()
            
            # Process button
            if st.session_state.selected_deals and not st.session_state.workflow_started:
                st.markdown("---")
                if st.button("🚀 Generate Report & Enrich Data", type="primary", 
                           use_container_width=True):
                    run_workflow(list(st.session_state.selected_deals))
                    st.rerun()
            
            # Results display
            st.markdown("---")
            results_expander = st.expander(
                f"📊 Deal Results ({len(st.session_state.deals)} found)", 
                expanded=not st.session_state.workflow_started
            )
            
            with results_expander:
                for idx, deal in enumerate(st.session_state.deals):
                    render_deal_card(deal, idx)
    
    # Report section
    if st.session_state.workflow_complete:
        render_report_section()


if __name__ == "__main__":
    main()
