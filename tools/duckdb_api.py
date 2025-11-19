"""
DuckDB API Tool
===============
Interface for querying CSV data using DuckDB SQL engine.
"""

import duckdb
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger


class DuckDBClient:
    """DuckDB client for CSV queries"""
    
    def __init__(self, csv_path: str):
        """
        Initialize DuckDB client
        
        Args:
            csv_path: Path to CSV file
        """
        self.csv_path = Path(csv_path)
        
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        logger.info(f"DuckDB client initialized with: {csv_path}")
    
    def execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query on CSV data
        
        Args:
            sql_query: SQL query string
            
        Returns:
            List of dictionaries (rows)
        """
        try:
            # Connect to DuckDB (in-memory)
            conn = duckdb.connect(':memory:')
            
            # Register CSV as a table
            table_name = "deals"
            conn.execute(f"""
                CREATE TABLE {table_name} AS 
                SELECT * FROM read_csv_auto('{self.csv_path}', header=True)
            """)
            
            logger.info(f"Executing SQL query: {sql_query[:100]}...")
            
            # Execute user query
            result = conn.execute(sql_query).fetchall()
            
            # Get column names
            columns = [desc[0] for desc in conn.description]
            
            # Convert to list of dicts
            results = [
                dict(zip(columns, row))
                for row in result
            ]
            
            conn.close()
            
            logger.info(f"Query returned {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"DuckDB query failed: {e}")
            raise
    
    def get_schema(self) -> Dict[str, str]:
        """
        Get CSV schema (column names and types)
        
        Returns:
            Dictionary of column_name -> data_type
        """
        try:
            conn = duckdb.connect(':memory:')
            
            # Load CSV and get schema
            conn.execute(f"""
                CREATE TABLE temp AS 
                SELECT * FROM read_csv_auto('{self.csv_path}', header=True)
            """)
            
            schema = conn.execute("DESCRIBE temp").fetchall()
            
            schema_dict = {col[0]: col[1] for col in schema}
            
            conn.close()
            
            return schema_dict
            
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            raise
    
    def validate_query(self, sql_query: str) -> tuple[bool, Optional[str]]:
        """
        Validate SQL query without executing it
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            conn = duckdb.connect(':memory:')
            
            # Register table
            conn.execute(f"""
                CREATE TABLE deals AS 
                SELECT * FROM read_csv_auto('{self.csv_path}', header=True)
            """)
            
            # Try to prepare query (doesn't execute)
            conn.execute(f"EXPLAIN {sql_query}")
            
            conn.close()
            
            return True, None
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Query validation failed: {error_msg}")
            return False, error_msg


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_deal_for_display(deal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a deal dictionary for display/processing
    
    Args:
        deal: Raw deal dictionary from DuckDB
        
    Returns:
        Formatted deal dictionary
    """
    return {
        'company': deal.get('Company', 'N/A'),
        'website': deal.get('Website', ''),
        'linkedin_url': deal.get('Linkedin_URL', ''),
        'country': deal.get('Country', 'N/A'),
        'founding_year': deal.get('Founding_Year', 'N/A'),
        'sector': deal.get('Sector 1', 'N/A'),
        'sector_2': deal.get('Sector 2', ''),
        'tags': [
            deal.get('Tag 1', ''),
            deal.get('Tag 2', ''),
            deal.get('Tag 3', ''),
            deal.get('Tag 4', ''),
            deal.get('Tag 5', '')
        ],
        'round': deal.get('Round', 'N/A'),
        'amount_raised': deal.get('Amount_Raised', 'N/A'),
        'pitch': deal.get('Pitch', ''),
        'investors': deal.get('Investors', ''),
        'spotted_date': deal.get('Spotted_Date', ''),
        'source_urls': [
            deal.get('Source 1', ''),
            deal.get('Source 2', ''),
            deal.get('Source 3', '')
        ]
    }


def test_connection(csv_path: str) -> bool:
    """
    Test DuckDB connection and CSV loading
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        True if successful
    """
    try:
        client = DuckDBClient(csv_path)
        
        # Test query
        results = client.execute_query("SELECT COUNT(*) as count FROM deals")
        
        count = results[0]['count']
        logger.info(f"✓ DuckDB connection successful - {count} deals in database")
        
        # Get schema
        schema = client.get_schema()
        logger.info(f"✓ Schema loaded - {len(schema)} columns")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ DuckDB connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Test the client
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    
    from config import PathConfig
    
    csv_path = PathConfig.PROJECT_ROOT / "data" / "deal_radar - Database.csv"
    
    print("Testing DuckDB client...")
    
    if test_connection(str(csv_path)):
        print("\n✅ DuckDB client working correctly")
        
        # Example query
        client = DuckDBClient(str(csv_path))
        
        print("\nTesting sample query...")
        results = client.execute_query("""
            SELECT Company, Sector_1, Round, Amount_Raised 
            FROM deals 
            WHERE Sector_1 = 'Fintech'
            LIMIT 3
        """)
        
        print(f"\nFound {len(results)} Fintech deals:")
        for deal in results:
            print(f"  - {deal['Company']}: {deal['Round']} - {deal['Amount_Raised']}")
    else:
        print("\n❌ DuckDB client test failed")
