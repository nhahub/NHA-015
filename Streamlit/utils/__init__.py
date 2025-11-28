"""
Utility functions for data processing, text analysis, date handling, and theme management
"""
from .date_utils import try_parse_datestr, unified_date_display, arabic_to_english_datestr
from .text_utils import (
    get_stopwords,
    get_top_keywords,
    get_top_bigrams,
    is_rtl_text,
    highlight_text
)
from .data_processing import (
    generate_demo_data,
    calculate_sentiment_metrics,
    enrich_dataframe_for_analysis
)
from .theme_utils import ThemeManager, theme_manager

__all__ = [
    # Date utils
    'try_parse_datestr',
    'unified_date_display',
    'arabic_to_english_datestr',
    # Text utils
    'get_stopwords',
    'get_top_keywords',
    'get_top_bigrams',
    'is_rtl_text',
    'highlight_text',
    # Data processing
    'generate_demo_data',
    'calculate_sentiment_metrics',
    'enrich_dataframe_for_analysis',
 
]
