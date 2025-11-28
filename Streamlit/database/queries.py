"""
SQL query builders and data fetching
"""
import logging
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.connection import safe_read_sql
from utils.date_utils import try_parse_datestr, unified_date_display
from config.settings import Config

logger = logging.getLogger("mokhber.queries")


def build_headlines_sql(table, cols):
    col_lookup = {c.lower(): c for c in cols}
    col_map = {}
    
    
    target_fields = [
        "id", "title", "summary", "source", "category", 
        "sentiment", "url", "language", "published_date", 
        "scraped_at", "image_url", "embedding"
    ]
    
    for field in target_fields:
        if field in col_lookup:
            col_map[field] = col_lookup[field]
        else:
            col_map[field] = f"NULL AS {field}"
    
    order_col = col_lookup.get("scraped_at", "id")
    
    sql = f"""
    SELECT {col_map['id']} AS id,
           {col_map['title']} AS title,
           {col_map['summary']} AS summary,
           {col_map['source']} AS source,
           {col_map['category']} AS category,
           {col_map['sentiment']} AS sentiment,
           {col_map['url']} AS url,
           {col_map['language']} AS language,
           {col_map['published_date']} AS published_date,
           {col_map['scraped_at']} AS scraped_at,
           {col_map['image_url']} AS image_url,
           {col_map['embedding']} AS embedding
    FROM {table}
    WHERE 1=1
    """
    return sql, order_col


@st.cache_data(ttl=Config.DATA_CACHE_TTL)
def fetch_headlines(table, cols, start_days=30, limit=2000, search=None):
    """Fetch and normalize headlines from database"""
    
    # 1. Build Query 
    base_sql, order_col = build_headlines_sql(table, cols)
    params = {}
    col_lookup = {c.lower(): c for c in cols}
    
    # 2. Search Filtering
    search_clause = ""
    if search:
        has_title = "title" in col_lookup
        has_summary = "summary" in col_lookup
        
        if has_title or has_summary:
            params["search"] = f"%{search}%"
            if has_title and has_summary:
                search_clause = " AND (title ILIKE :search OR summary ILIKE :search)"
            elif has_title:
                search_clause = " AND title ILIKE :search"
            elif has_summary:
                search_clause = " AND summary ILIKE :search"
    
    # 3. Fetch Data 
    safe_limit = int(limit) + 500
    final_sql = base_sql + search_clause + f" ORDER BY {order_col} DESC LIMIT :limit"
    params["limit"] = safe_limit
    
    df = safe_read_sql(final_sql, params=params)
    
    if df.empty:
        return df
    
    # 4. Normalize Data Types & Dates
    df = normalize_dataframe(df)
    
    # 5. Date Filtering 
    if not df.empty and 'published_dt' in df.columns:
        cutoff_date = datetime.now(tz=Config.CAIRO_TZ) - timedelta(days=int(start_days))
        df = df[df['published_dt'] >= cutoff_date]
        
        
        df = df.head(int(limit))
    
    return df


def normalize_dataframe(df):
    """Normalize and clean DataFrame columns"""
    
    # Fill NaNs to prevent UI errors
    df['title'] = df['title'].astype(str).fillna("").replace("nan", "")
    df['summary'] = df['summary'].astype(str).fillna("").replace("nan", "")
    df['source'] = df['source'].astype(str).fillna("Unknown")
    df['category'] = df['category'].astype(str).fillna("General")
    df['sentiment'] = df['sentiment'].astype(str).fillna("neutral")
    df['image_url'] = df['image_url'].astype(str).fillna("").replace("nan", "")
    
    
    def parse_row_pub(r):
        pub = r.get('published_date')
        scraped = r.get('scraped_at')
        dt_pub = try_parse_datestr(pub) if pub else None
        dt_scraped = try_parse_datestr(scraped) if scraped else None
        
       
        return dt_pub if dt_pub is not None else dt_scraped
    
    df['published_dt'] = df.apply(parse_row_pub, axis=1)
    
    
    df['published_display'] = df.apply(
        lambda r: unified_date_display(
            r.get('published_date') or "", 
            fallback=r.get('published_dt')
        ), 
        axis=1
    )
    
    return df


def apply_filters(df, filters):
    """Apply filters to DataFrame"""
    if df.empty or not filters:
        return df
    
    out = df.copy()
    
    if filters.get('sources'):
        out = out[out['source'].isin(filters['sources'])]
    
    if filters.get('categories'):
        out = out[out['category'].isin(filters['categories'])]
    
    if filters.get('languages'):
        if 'language' in out.columns:
            out = out[out['language'].isin(filters['languages'])]
    
    if filters.get('sentiments'):
        out = out[out['sentiment'].str.lower().isin([s.lower() for s in filters['sentiments']])]
    
    return out
