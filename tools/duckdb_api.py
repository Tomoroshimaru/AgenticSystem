"""
DuckDB API Tool
===============
Interface for querying CSV data using DuckDB SQL engine.
"""

import duckdb
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import date
from loguru import logger


class DuckDBClient:
    """DuckDB client for CSV queries"""
    
    def __init__(self, csv_path: str):
        """Initialize DuckDB client"""
        self.csv_path = Path(csv_path)
        
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        logger.info(f"DuckDB client initialized with: {csv_path}")
    
    def execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query on CSV data"""
        try:
            conn = duckdb.connect(':memory:')
            
            conn.execute(f"""
                CREATE TABLE deals AS 
                SELECT * FROM read_csv_auto('{self.csv_path}', header=True)
            """)
            
            logger.info(f"Executing SQL query: {sql_query[:100]}...")
            
            result = conn.execute(sql_query).fetchall()
            columns = [desc[0] for desc in conn.description]
            
            results = [dict(zip(columns, row)) for row in result]
            
            conn.close()
            logger.info(f"Query returned {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"DuckDB query failed: {e}")
            raise
    
    def get_schema(self) -> Dict[str, str]:
        """Get CSV schema"""
        try:
            conn = duckdb.connect(':memory:')
            
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
        """Validate SQL query"""
        try:
            conn = duckdb.connect(':memory:')
            
            conn.execute(f"""
                CREATE TABLE deals AS 
                SELECT * FROM read_csv_auto('{self.csv_path}', header=True)
            """)
            
            conn.execute(f"EXPLAIN {sql_query}")
            conn.close()
            
            return True, None
            
        except Exception as e:
            logger.warning(f"Query validation failed: {e}")
            return False, str(e)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _to_str(value: Any) -> str:
    """Convert any value to string, handling None and dates"""
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def format_deal_for_display(deal: Dict[str, Any]) -> Dict[str, Any]:
    """Format deal dictionary with proper type conversions"""
    
    # Filter empty tags
    tags = [
        _to_str(deal.get(f'Tag {i}', ''))
        for i in range(1, 6)
    ]
    tags = [t for t in tags if t]  # Remove empty strings
    
    # Filter empty source URLs
    source_urls = [
        _to_str(deal.get(f'Source {i}', ''))
        for i in range(1, 4)
    ]
    source_urls = [s for s in source_urls if s]  # Remove empty strings
    
    return {
        'company': _to_str(deal.get('Company', 'N/A')),
        'website': _to_str(deal.get('Website', '')),
        'linkedin_url': _to_str(deal.get('Linkedin_URL', '')),
        'country': _to_str(deal.get('Country', 'N/A')),
        'founding_year': _to_str(deal.get('Founding_Year', '')),
        'sector': _to_str(deal.get('Sector 1', 'N/A')),
        'sector_2': _to_str(deal.get('Sector 2', '')),
        'tags': tags,
        'round': _to_str(deal.get('Round', 'N/A')),
        'amount_raised': _to_str(deal.get('Amount_Raised', 'N/A')),
        'pitch': _to_str(deal.get('Pitch', '')),
        'investors': _to_str(deal.get('Investors', '')),
        'spotted_date': _to_str(deal.get('Spotted_Date', '')),
        'source_urls': source_urls
    }


def test_connection(csv_path: str) -> bool:
    """Test DuckDB connection"""
    try:
        client = DuckDBClient(csv_path)
        
        results = client.execute_query("SELECT COUNT(*) as count FROM deals")
        count = results[0]['count']
        logger.info(f"✓ DuckDB connection successful - {count} deals")
        
        schema = client.get_schema()
        logger.info(f"✓ Schema loaded - {len(schema)} columns")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    
    from config import PathConfig
    
    csv_path = PathConfig.PROJECT_ROOT / "data" / "deal_radar - Database.csv"
    
    print("Testing DuckDB client...")
    
    if test_connection(str(csv_path)):
        print("\n✅ DuckDB client working")
        
        client = DuckDBClient(str(csv_path))
        
        print("\nTesting sample query...")
        results = client.execute_query("""
            SELECT Company, "Sector 1", Round, Amount_Raised 
            FROM deals 
            WHERE "Sector 1" = 'Fintech'
            LIMIT 3
        """)
        
        print(f"\nFound {len(results)} Fintech deals:")
        for deal in results:
            print(f"  - {deal['Company']}: {deal['Round']} - {deal['Amount_Raised']}")
    else:
        print("\n❌ Test failed")
