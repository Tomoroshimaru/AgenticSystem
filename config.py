"""
Configuration Management
========================
Centralized configuration for API keys, parameters, and settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


# ============================================================================
# API KEYS & CREDENTIALS
# ============================================================================

class APIConfig:
    """API keys and credentials"""
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    
    DUCKDB_CSV_PATH: str = os.getenv(
        "DUCKDB_CSV_PATH",
        "./data/deal_radar - Database.csv"
    )
    
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    
    # Google Drive OAuth
    GOOGLE_CREDENTIALS_PATH: str = os.getenv(
        "GOOGLE_CREDENTIALS_PATH",
        "./oauth_credentials.json"
    )
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    # Langfuse credentials
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    @classmethod
    def validate(cls) -> bool:
        """Validate required config"""
        required = [
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
            ("SERPER_API_KEY", cls.SERPER_API_KEY),
        ]
        
        missing = [name for name, value in required if not value]
        
        if missing:
            raise ValueError(f"Missing: {', '.join(missing)}")
        
        csv_path = Path(cls.DUCKDB_CSV_PATH)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {cls.DUCKDB_CSV_PATH}")
        
        return True


# ============================================================================
# LLM CONFIGURATION
# ============================================================================

class LLMConfig:
    """LLM settings"""
    
    MODEL_NAME: str = APIConfig.OPENAI_MODEL
    TEMPERATURE_INTENT: float = 0.1
    TEMPERATURE_SQL: float = 0.0
    TEMPERATURE_ENRICHMENT: float = 0.3
    
    MAX_TOKENS_INTENT: int = 1000
    MAX_TOKENS_SQL: int = 1500
    MAX_TOKENS_ENRICHMENT: int = 2000
    
    MAX_RETRIES: int = 1
    RETRY_DELAY: float = 1.0


# ============================================================================
# WORKFLOW CONFIGURATION
# ============================================================================

class WorkflowConfig:
    """Workflow behavior"""
    
    MAX_NOTION_RESULTS: int = 10
    
    MIN_SIMILARITY_SCORE: float = 0.6
    MAX_SIMILAR_COMPANIES_PER_DEAL: int = 5
    WEB_SEARCH_TIMEOUT: int = 10
    
    MAX_RETRY_ATTEMPTS: int = 1
    CHECKPOINT_DB_PATH: str = "./checkpoints.db"


# ============================================================================
# SIMILARITY WEIGHTS
# ============================================================================

class SimilarityWeights:
    """Similarity calculation weights"""
    
    SECTOR_WEIGHT: float = 0.30
    ROUND_WEIGHT: float = 0.25
    TAGS_WEIGHT: float = 0.25
    PITCH_WEIGHT: float = 0.20
    
    @classmethod
    def validate_sum(cls) -> bool:
        total = sum([cls.SECTOR_WEIGHT, cls.ROUND_WEIGHT, cls.TAGS_WEIGHT, cls.PITCH_WEIGHT])
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
    
    @classmethod
    def setup(cls):
        cls.TEMP_DIR.mkdir(exist_ok=True, parents=True)
        cls.OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


# ============================================================================
# LOGGING
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
    try:
        APIConfig.validate()
        SimilarityWeights.validate_sum()
        PathConfig.setup()
        print("✅ Config validated")
        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        raise
