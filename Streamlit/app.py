"""
Mokhber Intelligence Platform - Main Application
Entry point for Streamlit app
"""
import logging
import streamlit as st
from utils.theme_utils import theme_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mokhber")

# Import configuration
from config.settings import Config

# Import database functions
from database.connection import detect_table, get_metadata, get_engine
from database.queries import fetch_headlines, apply_filters

# Import utilities
from utils.data_processing import (
    generate_demo_data, 
    calculate_sentiment_metrics,
    enrich_dataframe_for_analysis
)

# Import UI components
from ui.styles import inject_custom_css
from ui.components import (
    render_header,
    render_sidebar,
    render_metrics_row,
    render_filter_summary
)

# Import page modules
from views.live_feed import render_live_feed
from views.analytics import render_analytics
from views.export import render_export


def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title=Config.APP_TITLE,
        page_icon=Config.APP_ICON,
        layout=Config.LAYOUT,
        initial_sidebar_state="expanded"
    )



def main():
    """Main application logic"""
    # Configure page
    configure_page()
    theme_manager.init_theme()
    
    # Inject custom CSS
    inject_custom_css()
   
    
    
    # Detect database connection
    table, cols = detect_table()
    db_connected = (get_engine() is not None) and (table is not None)
    
    # Render header
    render_header(db_connected, table)
    
    # Render sidebar and get filter settings
    filters, search_q, days_back, display_limit = render_sidebar(get_metadata())
    
    # Fetch data
    if db_connected:
        df = fetch_headlines(table, cols, start_days=days_back, limit=Config.MAX_QUERY_LIMIT, search=search_q)
        if filters:
            df = apply_filters(df, filters)
    else:
        logger.warning("Database not connected, using demo data")
        df = generate_demo_data()
        
        # Apply filters to demo data
        if filters:
            df = apply_filters(df, filters)
        
        # Apply search to demo data
        if search_q:
            mask = df['title'].str.contains(search_q, case=False, na=False) | \
                   df['summary'].str.contains(search_q, case=False, na=False)
            df = df[mask]
    
    # Show active filters
    if filters:
        render_filter_summary(filters)
    
    # Calculate metrics
    metrics = calculate_sentiment_metrics(df)
    sources_count = df['source'].nunique() if 'source' in df.columns else 0
    categories_count = df['category'].nunique() if 'category' in df.columns else 0
    
    # Render metrics
    render_metrics_row(metrics, sources_count, categories_count)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Create tabs
    tabs = st.tabs(["📰 Live Feed", "📊 Advanced Analytics", "💾 Export & Reports"])
    
    # Render tab content
    with tabs[0]:
        render_live_feed(df, display_limit, search_q)
    
    with tabs[1]:
        viz_df = enrich_dataframe_for_analysis(df)
        render_analytics(viz_df, metrics)
    
    with tabs[2]:
        render_export(df)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; color:#6B7280; padding:2rem;">
        <div style="margin-bottom:0.5rem;">🦅 <strong>Mokhber Intelligence</strong> </div>
        <div style="font-size:0.8rem;">Real-time Analytics • Built from Alexandria to the world</div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
