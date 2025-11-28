"""
Database connection and query execution
"""
import logging
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from config.settings import Config

logger = logging.getLogger("mokhber.database")

@st.cache_resource(ttl=Config.CACHE_TTL)
def get_engine():
    """Create and cache database engine"""
    if not Config.is_db_configured():
        logger.warning("Database not configured")
        return None
    
    try:
        engine = create_engine(
            Config.get_db_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5
        )
        logger.info("Database engine created successfully")
        return engine
    except Exception as e:
        logger.exception("Failed to create database engine: %s", e)
        return None


def safe_read_sql(query, params=None):
    """Safely execute SQL query and return DataFrame"""
    eng = get_engine()
    if eng is None:
        logger.warning("No database engine available")
        return pd.DataFrame()
    
    try:
        with eng.connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)
        return df
    except Exception as e:
        logger.exception("SQL error: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=Config.DATA_CACHE_TTL)
def detect_table():
    """Detect available news table and its columns"""
    eng = get_engine()
    if eng is None:
        return None, set()
    
    try:
        insp = inspect(eng)
        candidates = ["news", "news_articles", "articles", "news_table"]
        
        # Check predefined candidates
        for cand in candidates:
            if insp.has_table(cand):
                cols = {c["name"] for c in insp.get_columns(cand)}
                logger.info(f"Found table: {cand} with {len(cols)} columns")
                return cand, cols
        
        # Fallback: search for any table with 'news' in name
        for t in insp.get_table_names():
            if "news" in t.lower():
                cols = {c["name"] for c in insp.get_columns(t)}
                logger.info(f"Found fallback table: {t}")
                return t, cols
        
        logger.warning("No suitable table found")
        return None, set()
    except Exception as e:
        logger.exception("detect_table failed: %s", e)
        return None, set()


def get_metadata():
    """Fetch distinct sources, categories, and languages"""
    table, _ = detect_table()
    if table is None:
        # Return demo metadata
        return {
            "sources": ["Al-Ahram", "Egypt Today", "Daily News Egypt", "Ahram Online"],
            "categories": ["Economy", "Politics", "Technology", "Culture"],
            "languages": ["ar", "en"]
        }
    
    try:
        meta_sql = f"SELECT DISTINCT source, category, language FROM {table} LIMIT 5000"
        meta_df = safe_read_sql(meta_sql)
        
        return {
            "sources": sorted(meta_df['source'].dropna().unique()) if not meta_df.empty else [],
            "categories": sorted(meta_df['category'].dropna().unique()) if not meta_df.empty else [],
            "languages": sorted(meta_df['language'].dropna().unique()) if not meta_df.empty else []
        }
    except Exception as e:
        logger.exception("Failed to fetch metadata: %s", e)
        return {"sources": [], "categories": [], "languages": []}