"""
Notion API Client
=================
Wrapper for Notion API to query the fundraising database.
"""

import json
import requests
from typing import List, Dict, Any, Optional
from notion_client import Client
from loguru import logger

from config import APIConfig
from state import NotionDeal


class NotionAPIClient:
    """Client pour interagir avec l'API Notion"""
    
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        """
        Initialize Notion client
        """
        api_key = api_key or APIConfig.NOTION_API_KEY
        database_id = database_id or APIConfig.NOTION_DATABASE_ID
        
        if not api_key or not database_id:
            raise ValueError("Notion API key and database ID are required")
        
        # Stocker les valeurs AVANT de créer le client
        self.api_key = api_key
        self.database_id = database_id
        self.client = Client(auth=api_key)
        
        logger.info("Notion client initialized")

    def query_database(
        self,
        filter_query: Dict[str, Any],
        max_results: int = 10
    ) -> List[NotionDeal]:
        """Query the Notion database with filters"""
        try:
            logger.info(f"Querying Notion database")
            
            url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            
            payload = {
                "page_size": min(max_results, 100)
            }
            
            if "filter" in filter_query:
                payload["filter"] = filter_query["filter"]
            if "sorts" in filter_query:
                payload["sorts"] = filter_query["sorts"]
            
            logger.info(f"Payload sent to Notion: {json.dumps(payload, indent=2)}")

            response = requests.post(url, json=payload, headers=headers)
            if not response.ok:
                logger.error(f"Notion API error response: {response.text}")
            response.raise_for_status()
            
            data = response.json()
            deals = self._parse_results(data.get("results", []))
            
            logger.info(f"Found {len(deals)} deals")
            return deals[:max_results]
            
        except Exception as e:
            logger.error(f"Error querying Notion database: {e}")
            raise
            
    def _parse_results(self, results: List[Dict]) -> List[NotionDeal]:
        """
        Parse Notion API results into NotionDeal objects
        
        Args:
            results: Raw Notion API results
            
        Returns:
            List of NotionDeal objects
        """
        deals = []
        
        for result in results:
            try:
                properties = result.get("properties", {})
                
                deal = NotionDeal(
                    id=result.get("id", ""),
                    company=self._extract_rich_text(properties.get("company", {})),
                    website=self._extract_rich_text(properties.get("website", {})),
                    country=self._extract_rich_text(properties.get("country", {})),
                    sector=self._extract_rich_text(properties.get("Sector", {})),
                    tag_1=self._extract_rich_text(properties.get("Tag 1", {})),
                    tag_2=self._extract_rich_text(properties.get("Tag 2", {})),
                    tag_3=self._extract_rich_text(properties.get("Tag 3", {})),
                    amount_raised=self._extract_rich_text(properties.get("Amount raised", {})),
                    round=self._extract_rich_text(properties.get("Round", {})),
                    pitch=self._extract_rich_text(properties.get("Pitch", {})),
                )
                
                deals.append(deal)
                
            except Exception as e:
                logger.warning(f"Failed to parse Notion result: {e}")
                continue
        
        return deals
    
    def _extract_rich_text(self, property_obj: Dict) -> Optional[str]:
        """
        Extract text from Notion rich_text property
        
        Args:
            property_obj: Notion property object
            
        Returns:
            Extracted text or None
        """
        try:
            rich_text = property_obj.get("rich_text", [])
            if rich_text and len(rich_text) > 0:
                return rich_text[0].get("plain_text", "")
            return None
        except Exception:
            return None
    
    def validate_query(self, query: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate a Notion query structure
        
        Args:
            query: Query dict to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if "filter" not in query and "sorts" not in query:
            errors.append("Query must contain 'filter' or 'sorts'")
        
        # Validate filter structure
        if "filter" in query:
            filter_obj = query["filter"]
            
            if "and" in filter_obj:
                conditions = filter_obj["and"]
                if not isinstance(conditions, list):
                    errors.append("'and' must be a list of conditions")
                
                for i, condition in enumerate(conditions):
                    if "property" not in condition:
                        errors.append(f"Condition {i} missing 'property' field")
                    if "rich_text" not in condition:
                        errors.append(f"Condition {i} missing 'rich_text' field")
            
            elif "or" in filter_obj:
                conditions = filter_obj["or"]
                if not isinstance(conditions, list):
                    errors.append("'or' must be a list of conditions")
        
        # Validate sorts
        if "sorts" in query:
            sorts = query["sorts"]
            if not isinstance(sorts, list):
                errors.append("'sorts' must be a list")
            
            for i, sort in enumerate(sorts):
                if "property" not in sort:
                    errors.append(f"Sort {i} missing 'property' field")
                if "direction" not in sort:
                    errors.append(f"Sort {i} missing 'direction' field")
                elif sort["direction"] not in ["ascending", "descending"]:
                    errors.append(f"Sort {i} has invalid direction")
        
        # Validate page_size
        if "page_size" in query:
            if not isinstance(query["page_size"], int) or query["page_size"] > 100:
                errors.append("page_size must be an integer <= 100")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("Query validation passed")
        else:
            logger.warning(f"Query validation failed: {errors}")
        
        return is_valid, errors


# Utility function for testing
def test_notion_connection() -> bool:
    """Test Notion connection and database access"""
    try:
        client = NotionAPIClient()
        
        # Simple query to test connection
        test_query = {
            "page_size": 1
        }
        
        results = client.query_database(test_query, max_results=1)
        
        logger.info(f"✅ Notion connection successful. Found {len(results)} test result(s)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Notion connection failed: {e}")
        return False