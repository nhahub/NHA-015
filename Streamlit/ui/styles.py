"""
CSS styles for Mokhber Intelligence Platform
Now uses theme_manager for dynamic theming
"""
import streamlit as st
from utils.theme_utils import theme_manager


def inject_custom_css():
    """
    Inject custom CSS styling into Streamlit app
    Uses theme_manager to get theme-aware CSS
    """
    # Get CSS from theme manager
    css = theme_manager.get_theme_css()
    st.markdown(css, unsafe_allow_html=True)


def inject_custom_css_legacy():
    """
    Legacy CSS injection (kept for reference)
    Use inject_custom_css() instead which supports theming
    """
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Inter:wght@400;500;600;700;800;900&display=swap');
    
    :root {
        /* Dark Theme Palette */
        --bg-app: #0E1117;
        --bg-card: #1A1C24;
        --bg-sidebar: #14161C;
        
        --primary: #3B82F6;
        --accent: #60A5FA;
        --gold: #F59E0B;
        --gold-dim: #B45309;
        
        --text-main: #F3F4F6;
        --text-muted: #9CA3AF;
        
        --border-color: #2D3748;
        --border-highlight: #4B5563;
        
        --success: #10B981;
        --danger: #EF4444;
        --warning: #F59E0B;

        --shadow-glow: 0 0 20px rgba(59, 130, 246, 0.15);
        --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        
        --gradient-gold: linear-gradient(135deg, #F59E0B 0%, #B45309 100%);
        --gradient-blue: linear-gradient(135deg, #1E40AF 0%, #1E3A8A 100%);
    }
    
    /* Global Overrides */
    .stApp {
        background-color: var(--bg-app);
        color: var(--text-main);
        font-family: 'Inter', 'Cairo', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-main) !important;
        font-family: 'Inter', 'Cairo', sans-serif;
    }
    
    /* Enhanced Header */
    .mokhber-header {
        background: linear-gradient(180deg, #1A1C24 0%, #0E1117 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow-glow);
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    
    .mokhber-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 2px;
        background: var(--gradient-gold);
        box-shadow: 0 0 15px var(--gold);
    }
    
    .mokhber-title {
        font-size: 2.5rem;
        font-weight: 900;
        background: linear-gradient(90deg, #FFFFFF 0%, #93C5FD 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
        margin-bottom: 0.5rem;
    }
    
    .mokhber-subtitle {
        color: var(--text-muted);
        font-size: 1.1rem;
        font-weight: 500;
    }
    
    /* Status Badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid var(--border-color);
        margin-top: 1rem;
    }
    
    .status-dot {
        width: 8px; height: 8px; border-radius: 50%;
        box-shadow: 0 0 8px currentColor;
    }

    /* Metric Cards */
    .metric-card {
        background: var(--bg-card);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow-card);
        position: relative;
        overflow: hidden;
        transition: transform 0.2s, border-color 0.2s;
        height: 100%;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: var(--border-highlight);
        box-shadow: 0 10px 20px -5px rgba(0,0,0,0.4);
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--text-main);
        line-height: 1.2;
        margin-bottom: 0.25rem;
    }
    
    .metric-label {
        color: var(--text-muted);
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    
    /* News Cards */
    .news-card {
        background: var(--bg-card);
        border-radius: 12px;
        padding: 1.25rem;
        border: 1px solid var(--border-color);
        margin-bottom: 1rem;
        transition: all 0.2s ease;
        border-left: 4px solid var(--gold);
    }
    
    .news-card:hover {
        border-color: var(--accent);
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    
    .news-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #60A5FA;
        text-decoration: none;
        display: block;
        margin-bottom: 0.75rem;
        transition: color 0.2s;
    }
    
    .news-title:hover {
        color: #93C5FD;
        text-decoration: underline;
    }
    
    .news-summary {
        color: #D1D5DB;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    .news-meta {
        display: flex; flex-wrap: wrap; gap: 0.75rem;
        margin-bottom: 0.75rem; align-items: center;
    }
    
    /* Badges */
    .badge {
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-flex; align-items: center; gap: 0.25rem;
    }
    
    .badge-source { background: rgba(59, 130, 246, 0.2); color: #93C5FD; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-category { background: rgba(245, 158, 11, 0.2); color: #FCD34D; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-positive { background: rgba(16, 185, 129, 0.2); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-negative { background: rgba(239, 68, 68, 0.2); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-neutral { background: rgba(107, 114, 128, 0.2); color: #D1D5DB; border: 1px solid rgba(107, 114, 128, 0.3); }
    
    .badge-time {
        color: var(--text-muted);
        font-size: 0.8rem;
        margin-left: auto;
        font-family: monospace;
    }
    
    /* Filter Summary */
    .filter-summary {
        background: rgba(96, 165, 250, 0.1);
        border: 1px solid rgba(96, 165, 250, 0.2);
        color: #93C5FD;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    
    /* RTL Support */
    .rtl { direction: rtl; text-align: right; font-family: 'Cairo', sans-serif; }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: var(--bg-app); }
    ::-webkit-scrollbar-thumb { background: var(--border-highlight); border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
    
    mark {
        background: rgba(245, 158, 11, 0.3);
        color: #FCD34D;
        padding: 0 2px;
        border-radius: 2px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)