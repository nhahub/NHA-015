"""
Live Feed page - displays news articles
"""
import math
import streamlit as st
from ui.components import render_news_card


def render_live_feed(df, display_limit, search_q):
    """Render live news feed with pagination"""
    st.markdown("### 📰 Latest Headlines")
    
    if df.empty:
        st.info("🔍 No articles found. Try adjusting your filters or timeframe.")
        return
    
    # Sort controls
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"**Showing {min(len(df), display_limit)} of {len(df):,} articles**")
    with col2:
        sort = st.selectbox(
            "Sort by",
            ["Newest first", "Oldest first", "Source A→Z"],
            label_visibility="collapsed"
        )
    
    # Apply sorting
    if sort == "Newest first":
        df_sorted = df.sort_values('published_dt', ascending=False)
    elif sort == "Oldest first":
        df_sorted = df.sort_values('published_dt', ascending=True)
    else:
        df_sorted = df.sort_values('source', ascending=True)
    
    # Pagination
    per_page = min(int(display_limit), 200)
    total_pages = max(1, math.ceil(len(df_sorted) / per_page))
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    start = (page - 1) * per_page
    
    # Render cards
    for _, row in df_sorted.iloc[start:start + per_page].iterrows():
        render_news_card(row, highlight_term=search_q if search_q else None)
    
    if len(df_sorted) > display_limit:
        st.info(f"📄 Showing page {page} of {total_pages}.")