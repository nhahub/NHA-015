"""
UI components and styling for the application
"""
from .styles import inject_custom_css
from .components import (
    render_header,
    render_sidebar,
    render_filter_summary,
    render_metrics_row,
    render_news_card
)
from .charts import (
    create_volume_sentiment_timeline,
    create_sentiment_pie_chart,
    create_top_sources_bar,
    create_category_pie_chart,
    create_sentiment_heatmap,
    create_hourly_sentiment_chart,
    create_category_trend_chart,
    create_bigrams_bar_chart,
    create_weekday_volume_chart,
    create_weekend_pie_chart
)

__all__ = [
    # Styles
    'inject_custom_css',
    # Components
    'render_header',
    'render_sidebar',
    'render_filter_summary',
    'render_metrics_row',
    'render_news_card',
    # Charts
    'create_volume_sentiment_timeline',
    'create_sentiment_pie_chart',
    'create_top_sources_bar',
    'create_category_pie_chart',
    'create_sentiment_heatmap',
    'create_hourly_sentiment_chart',
    'create_category_trend_chart',
    'create_bigrams_bar_chart',
    'create_weekday_volume_chart',
    'create_weekend_pie_chart'
]