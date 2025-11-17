"""
Formatting Utilities
====================
Helper functions for data formatting.
"""

from typing import Optional
from state import NotionDeal


def format_deal_for_display(deal: NotionDeal, index: Optional[int] = None) -> str:
    """
    Format a deal for console display
    
    Args:
        deal: NotionDeal object
        index: Optional index number
        
    Returns:
        Formatted string
    """
    prefix = f"[{index}] " if index else ""
    
    return (
        f"{prefix}{deal.company}\n"
        f"    Sector: {deal.sector or 'N/A'} | "
        f"Round: {deal.round or 'N/A'} | "
        f"Amount: {deal.amount_raised or 'N/A'} | "
        f"Country: {deal.country or 'N/A'}"
    )


def format_currency(amount: str) -> str:
    """
    Format currency amount (basic implementation)
    
    Args:
        amount: Amount string (e.g., "5M€")
        
    Returns:
        Formatted amount
    """
    if not amount:
        return "N/A"
    
    # Keep as-is for now (already formatted in Notion)
    return amount


def format_similarity_score(score: float) -> str:
    """
    Format similarity score as percentage
    
    Args:
        score: Similarity score (0-1)
        
    Returns:
        Formatted percentage string
    """
    return f"{score * 100:.0f}%"


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to max length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."