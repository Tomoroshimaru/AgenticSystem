"""
Serper Web Search Client
=========================
Wrapper for Serper API to search the web for similar companies.
"""

import requests
from typing import List, Dict, Any, Optional
from loguru import logger

from config import APIConfig, WorkflowConfig


class SerperSearchClient:
    """Client pour effectuer des recherches web via Serper API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Serper client
        
        Args:
            api_key: Serper API key (defaults to config)
        """
        self.api_key = api_key or APIConfig.SERPER_API_KEY
        
        if not self.api_key:
            raise ValueError("Serper API key is required")
        
        self.base_url = "https://google.serper.dev/search"
        self.timeout = WorkflowConfig.WEB_SEARCH_TIMEOUT
        
        logger.info("Serper client initialized")
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        location: str = "fr"
    ) -> List[Dict[str, Any]]:
        """
        Perform a web search using Serper API
        
        Args:
            query: Search query
            num_results: Number of results to return
            location: Geographic location for search (default: France)
            
        Returns:
            List of search results
        """
        try:
            logger.info(f"Searching web for: '{query}'")
            
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "q": query,
                "num": num_results,
                "gl": location,  # Geographic location
                "hl": "fr",      # Language
            }
            
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            data = response.json()
            
            # Extract organic results
            results = data.get("organic", [])
            
            logger.info(f"Found {len(results)} search results")
            
            return self._parse_results(results)
            
        except requests.exceptions.Timeout:
            logger.error(f"Search timeout after {self.timeout}s")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Search request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return []
    
    def _parse_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """
        Parse Serper API results into a clean format
        
        Args:
            results: Raw Serper API results
            
        Returns:
            List of parsed results
        """
        parsed = []
        
        for result in results:
            try:
                parsed_result = {
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", 0),
                    "date": result.get("date", None)
                }
                
                parsed.append(parsed_result)
                
            except Exception as e:
                logger.warning(f"Failed to parse search result: {e}")
                continue
        
        return parsed
    
    def search_company_info(
        self,
        company_name: str,
        sector: Optional[str] = None,
        additional_keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for information about a specific company
        
        Args:
            company_name: Name of the company
            sector: Sector/industry
            additional_keywords: Additional search keywords
            
        Returns:
            List of search results about the company
        """
        # Build query
        query_parts = [company_name]
        
        if sector:
            query_parts.append(sector)
        
        if additional_keywords:
            query_parts.extend(additional_keywords)
        
        # Add common fundraising keywords
        query_parts.extend(["funding", "startup"])
        
        query = " ".join(query_parts)
        
        return self.search(query, num_results=5)
    
    def search_similar_companies(
        self,
        sector: str,
        round: Optional[str] = None,
        tags: Optional[List[str]] = None,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar companies based on criteria
        
        Args:
            sector: Sector/industry
            round: Funding round
            tags: List of tags/keywords
            country: Country/region
            
        Returns:
            List of search results
        """
        # Build query
        query_parts = [sector]
        
        if round:
            query_parts.append(round)
        
        query_parts.append("fundraising companies")
        
        if tags:
            query_parts.extend(tags[:2])  # Limit to 2 tags
        
        if country:
            query_parts.append(country)
        
        query = " ".join(query_parts)
        
        return self.search(query, num_results=10)


# Utility function for testing
def test_serper_connection() -> bool:
    """Test Serper API connection"""
    try:
        client = SerperSearchClient()
        
        results = client.search("test search", num_results=1)
        
        logger.info(f"✅ Serper connection successful. Got {len(results)} result(s)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Serper connection failed: {e}")
        return False