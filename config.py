"""
Configuration Management
========================
Centralized configuration for API keys, parameters, and settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()


# ============================================================================
# API KEYS & CREDENTIALS
# ============================================================================

class APIConfig:
    """API keys and credentials"""
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    
    # DuckDB / Data
    DUCKDB_CSV_PATH: str = os.getenv(
        "DUCKDB_CSV_PATH",
        "./data/deal_radar - Database.csv"
    )
    
    # Serper (Web Search)
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    
    # Google Drive
    GOOGLE_CREDENTIALS_PATH: str = os.getenv(
        "GOOGLE_CREDENTIALS_PATH",
        "./credentials.json"
    )
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required API keys are present"""
        required = [
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
            ("SERPER_API_KEY", cls.SERPER_API_KEY),
        ]
        
        missing = [name for name, value in required if not value]
        
        if missing:
            raise ValueError(
                f"Missing required API keys/config: {', '.join(missing)}"
            )
        
        # Validate CSV path exists
        csv_path = Path(cls.DUCKDB_CSV_PATH)
        if not csv_path.exists():
            raise FileNotFoundError(
                f"CSV file not found: {cls.DUCKDB_CSV_PATH}"
            )
        
        return True


# ============================================================================
# LLM CONFIGURATION
# ============================================================================

class LLMConfig:
    """Configuration for LLM calls"""
    
    # Model settings
    MODEL_NAME: str = APIConfig.OPENAI_MODEL
    TEMPERATURE_INTENT: float = 0.1  # Low temp for intent analysis
    TEMPERATURE_SQL: float = 0.0     # Zero temp for SQL generation
    TEMPERATURE_ENRICHMENT: float = 0.3  # Moderate for web analysis
    
    # Token limits
    MAX_TOKENS_INTENT: int = 1000
    MAX_TOKENS_SQL: int = 1500
    MAX_TOKENS_ENRICHMENT: int = 2000
    
    # Retry settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0  # seconds


# ============================================================================
# WORKFLOW CONFIGURATION
# ============================================================================

class WorkflowConfig:
    """Configuration for workflow behavior"""
    
    # Notion fetch limits
    MAX_NOTION_RESULTS: int = 10
    
    # Enrichment settings
    MIN_SIMILARITY_SCORE: float = 0.6
    MAX_SIMILAR_COMPANIES_PER_DEAL: int = 5
    WEB_SEARCH_TIMEOUT: int = 10  # seconds per deal
    
    # Retry limits
    MAX_RETRY_ATTEMPTS: int = 3
    
    # Checkpointing
    CHECKPOINT_DB_PATH: str = "./checkpoints.db"


# ============================================================================
# SIMILARITY WEIGHTS
# ============================================================================

class SimilarityWeights:
    """Weights for similarity calculation"""
    
    SECTOR_WEIGHT: float = 0.30
    ROUND_WEIGHT: float = 0.25
    TAGS_WEIGHT: float = 0.25
    PITCH_WEIGHT: float = 0.20
    
    @classmethod
    def validate_sum(cls) -> bool:
        """Ensure weights sum to 1.0"""
        total = (
            cls.SECTOR_WEIGHT +
            cls.ROUND_WEIGHT +
            cls.TAGS_WEIGHT +
            cls.PITCH_WEIGHT
        )
        assert abs(total - 1.0) < 0.01, f"Weights must sum to 1.0, got {total}"
        return True


# ============================================================================
# FILE PATHS
# ============================================================================

class PathConfig:
    """File system paths"""
    
    PROJECT_ROOT: Path = Path(__file__).parent
    TEMP_DIR: Path = PROJECT_ROOT / "temp"
    OUTPUT_DIR: Path = PROJECT_ROOT / "output"
    
    # Create directories if they don't exist
    @classmethod
    def setup(cls):
        """Create necessary directories"""
        cls.TEMP_DIR.mkdir(exist_ok=True, parents=True)
        cls.OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

class LogConfig:
    """Logging settings"""
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>"
    )


# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate all configuration"""
    try:
        APIConfig.validate()
        SimilarityWeights.validate_sum()
        PathConfig.setup()
        print("✅ Configuration validated successfully")
        return True
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        raise


# Auto-validate on import
if __name__ != "__main__":
    # Only validate if not running as script
    pass