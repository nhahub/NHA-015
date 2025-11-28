"""
Configuration management for Mokhber Intelligence Platform
"""
import os
from datetime import timedelta, timezone
import zoneinfo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # App Settings
    APP_TITLE = "Mokhber — Intelligence Platform"
    APP_ICON = "🦅"
    LAYOUT = "wide"
    
    # Database Configuration
    RDS_HOST = os.getenv("RDS_HOST")
    RDS_PORT = int(os.getenv("RDS_PORT", 5432))
    RDS_DB = os.getenv("RDS_DB", "postgres")
    RDS_USER = os.getenv("RDS_USER")
    RDS_PASSWORD = os.getenv("RDS_PASSWORD")
    
    # AWS Configuration
    AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
    AWS_REGION = os.getenv("AWS_REGION", None)
    
    # Timezone
    try:
        CAIRO_TZ = zoneinfo.ZoneInfo("Africa/Cairo")
    except Exception:
        CAIRO_TZ = timezone(timedelta(hours=2))
    
    # Cache Settings
    CACHE_TTL = 600  # 10 minutes
    DATA_CACHE_TTL = 300  # 5 minutes
    
    # Query Limits
    DEFAULT_DAYS_BACK = 30
    MAX_QUERY_LIMIT = 2000
    DEFAULT_DISPLAY_LIMIT = 50
    
    # Demo Mode
    DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
    
    @classmethod
    def is_db_configured(cls):
        """Check if database is properly configured"""
        return bool(cls.RDS_HOST and cls.RDS_USER and cls.RDS_PASSWORD)
    
    @classmethod
    def get_db_url(cls):
        """Get database connection URL"""
        from sqlalchemy.engine.url import URL
        return URL.create(
            "postgresql+psycopg2",
            username=cls.RDS_USER,
            password=cls.RDS_PASSWORD,
            host=cls.RDS_HOST,
            port=cls.RDS_PORT,
            database=cls.RDS_DB,
        )