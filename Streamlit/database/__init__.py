"""
Database module for connection and query management
"""
from .connection import get_engine, safe_read_sql, detect_table, get_metadata
from .queries import fetch_headlines, apply_filters, build_headlines_sql

__all__ = [
    'get_engine',
    'safe_read_sql',
    'detect_table',
    'get_metadata',
    'fetch_headlines',
    'apply_filters',
    'build_headlines_sql'
]
