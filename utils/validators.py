"""
Validation Utilities
====================
Helper functions for data validation.
"""

from typing import Dict, Any, Tuple, List


def validate_notion_query(query: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a Notion query structure
    
    Args:
        query: Query dict to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check structure
    if not isinstance(query, dict):
        errors.append("Query must be a dictionary")
        return False, errors
    
    # Check for required fields
    if "filter" not in query and "sorts" not in query:
        errors.append("Query must contain 'filter' or 'sorts'")
    
    # Validate page_size
    if "page_size" in query:
        if not isinstance(query["page_size"], int):
            errors.append("page_size must be an integer")
        elif query["page_size"] > 100:
            errors.append("page_size cannot exceed 100")
    
    return len(errors) == 0, errors


def validate_similarity_score(score: float) -> bool:
    """
    Validate a similarity score
    
    Args:
        score: Similarity score
        
    Returns:
        True if valid
    """
    return isinstance(score, (int, float)) and 0.0 <= score <= 1.0


def validate_user_selection(
    selection: str,
    max_index: int
) -> Tuple[bool, List[int]]:
    """
    Validate and parse user selection string
    
    Args:
        selection: Selection string (e.g., "1,3,5" or "all")
        max_index: Maximum valid index
        
    Returns:
        Tuple of (is_valid, list_of_indices)
    """
    if selection.lower().strip() == "all":
        return True, list(range(1, max_index + 1))
    
    try:
        indices = [int(x.strip()) for x in selection.split(",") if x.strip()]
        
        # Validate indices
        if not indices:
            return False, []
        
        for idx in indices:
            if idx < 1 or idx > max_index:
                return False, []
        
        return True, indices
        
    except ValueError:
        return False, []