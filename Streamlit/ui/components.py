"""
Reusable UI components for Mokhber Intelligence Platform
"""
import html
import streamlit as st
from utils.text_utils import is_rtl_text, highlight_text
from utils.theme_utils import theme_manager

def render_theme_toggle():
    """Render the theme toggle button"""
    is_dark = theme_manager.is_dark_mode()
    btn_label = "☀️ Switch to Daylight" if is_dark else "🌑 Switch to Midnight"
    if st.button(btn_label, use_container_width=True):
        theme_manager.change_theme()
        st.rerun()
    st.markdown("---")

def render_header(db_connected, table_name=None):
    """Render application header with connection status"""
    status_text = "Connected" if db_connected else "Disconnected"
    dot_color = "var(--success)" if db_connected else "var(--danger)"
    table_info = f'<span style="color: var(--text-muted); margin-left: 8px; font-size:0.8em;">({table_name})</span>' if table_name else ''
    
    st.markdown(f"""
    <div class="mokhber-header">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div class="mokhber-title">🦅 Mokhber Intelligence</div>
                <div class="mokhber-subtitle">Advanced News Analytics & Sentiment Intelligence Platform</div>
                <div class="status-badge">
                    <div class="status-dot" style="background-color: {dot_color}; box-shadow: 0 0 10px {dot_color};"></div>
                    <span style="color: var(--text-main);">{status_text}</span>
                    {table_info}
                </div>
            </div>
            <div style="font-size: 4rem;">🦅</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar(metadata):
    """Render sidebar with filters and theme toggle"""
    with st.sidebar:
        render_theme_toggle()
        st.markdown("### ⚙️ Configuration")
        
        time_preset = st.radio(
            "📅 Timeframe",
            ["Last 24h", "Last 7 days", "Last 30 days", "Custom"],
            index=2,
            horizontal=False
        )
        
        if time_preset == "Last 24h":
            days_back = 1
        elif time_preset == "Last 7 days":
            days_back = 7
        elif time_preset == "Last 30 days":
            days_back = 30
        else:
            days_back = st.slider("Custom Days", 1, 180, 30)
        
        display_limit = st.number_input("Display Limit", min_value=10, max_value=500, value=50, step=10)
        
        st.divider()
        st.markdown("### 🔍 Search & Filters")
        
        search_q = st.text_input("🔎 Search", placeholder="Search in titles & summaries...")
        
        sources = metadata.get('sources', [])
        with st.expander("📰 Sources", expanded=False):
            sel_sources = st.multiselect("Select sources", options=sources, key="sources")
        
        cats = metadata.get('categories', [])
        with st.expander("🏷️ Categories", expanded=False):
            sel_cats = st.multiselect("Select categories", options=cats, key="categories")
        
        langs = metadata.get('languages', [])
        with st.expander("🌐 Languages", expanded=False):
            sel_langs = st.multiselect("Select languages", options=langs, key="languages")
        
        with st.expander("😊 Sentiment", expanded=False):
            sel_sents = st.multiselect(
                "Select sentiments",
                options=["positive", "neutral", "negative"],
                key="sentiments"
            )
        
        st.divider()
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("🗑️ Clear Filters", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    filters = {}
    if sel_sources: filters['sources'] = sel_sources
    if sel_cats: filters['categories'] = sel_cats
    if sel_langs: filters['languages'] = sel_langs
    if sel_sents: filters['sentiments'] = sel_sents
    
    return filters, search_q, days_back, display_limit


def render_filter_summary(filters):
    """Display active filters summary"""
    filter_parts = []
    if filters.get('sources'): filter_parts.append(f"{len(filters['sources'])} sources")
    if filters.get('categories'): filter_parts.append(f"{len(filters['categories'])} categories")
    if filters.get('languages'): filter_parts.append(f"{len(filters['languages'])} languages")
    if filters.get('sentiments'): filter_parts.append(f"{len(filters['sentiments'])} sentiments")
    
    st.markdown(f"""
    <div class="filter-summary">
        <strong>🎯 Active Filters:</strong> {' • '.join(filter_parts)}
    </div>
    """, unsafe_allow_html=True)


def render_metrics_row(metrics, sources_count, categories_count):
    """Render KPI metrics row"""
    k1, k2, k3, k4, k5 = st.columns(5)
    
    # Uses CSS variable --text-main so it flips to Black in light mode
    def metric_card_html(icon, value, label, color="var(--text-main)"):
        return f"""
        <div class="metric-card">
            <div style="font-size: 1.5rem; position: absolute; top: 1rem; right: 1rem; opacity: 0.2;">{icon}</div>
            <div class="metric-value" style="color: {color};">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
        """
    
    k1.markdown(metric_card_html("📊", f"{metrics['total']:,}", "Total Articles"), unsafe_allow_html=True)
    k2.markdown(metric_card_html("📰", sources_count, "Sources"), unsafe_allow_html=True)
    k3.markdown(metric_card_html("🏷️", categories_count, "Categories"), unsafe_allow_html=True)
    
    sent_color = "var(--success)" if metrics['sentiment_score'] > 0 else "var(--danger)" if metrics['sentiment_score'] < 0 else "var(--text-muted)"
    k4.markdown(metric_card_html("😊", f"{metrics['sentiment_score']:+.1f}", "Sentiment Score", sent_color), unsafe_allow_html=True)
    k5.markdown(metric_card_html("📈", f"{metrics['pos_rate']:.1f}%", "Positive Rate", "var(--success)"), unsafe_allow_html=True)


def render_news_card(row, highlight_term=None):
    """Render individual news card with image support"""
    title = str(row.get('title') or "No title")
    summary = str(row.get('summary') or "")[:500]
    src = str(row.get('source') or "Unknown")
    cat = str(row.get('category') or "General")
    sent = str(row.get('sentiment') or "neutral").lower()
    url = row.get('url') or "#"
    display = row.get('published_display') or ""
    
    img_url = row.get('image_url')
    if not isinstance(img_url, str) or img_url.lower() in ['nan', 'none', '', 'null']:
        img_url = None
    
    fallback_img = "https://placehold.co/150x100/2D3748/A0AEC0?text=No+Image"
    display_img = img_url if img_url and len(img_url) > 5 else fallback_img

    badge_sent = "badge-neutral"
    sent_icon = "😐"
    if "pos" in sent:
        badge_sent = "badge-positive"
        sent_icon = "😊"
    elif "neg" in sent:
        badge_sent = "badge-negative"
        sent_icon = "😞"
    
    is_rtl = is_rtl_text(title)
    dir_cls = "rtl" if is_rtl else ""
    
    if highlight_term:
        title = highlight_text(title, highlight_term)
        summary = highlight_text(summary, highlight_term)
    else:
        title = html.escape(title)
        summary = html.escape(summary)
    
    html_block = f"""
<div class="news-card {dir_cls}">
  <div class="news-content">
    <div class="news-meta">
      <span class="badge badge-source">📰 {html.escape(src)}</span>
      <span class="badge badge-category">🏷️ {html.escape(cat)}</span>
      <span class="badge {badge_sent}">{sent_icon} {sent.title()}</span>
      <span class="badge-time">🕐 {display}</span>
    </div>
    <a class="news-title" href="{html.escape(str(url))}" target="_blank">{title}</a>
    <div class="news-summary">{summary}</div>
  </div>
  
  <div class="news-img-container" style="display: block;">
     <img src="{display_img}" 
          class="news-img" 
          loading="lazy" 
          onerror="this.onerror=null;this.src='{fallback_img}';"
          alt="News Image">
  </div>
</div>
"""
    st.markdown(html_block, unsafe_allow_html=True)
