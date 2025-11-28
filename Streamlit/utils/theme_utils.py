"""
Theme management system for Mokhber Intelligence Platform
Supports Dark (Midnight) and Light (Daylight) themes
"""
import streamlit as st


class ThemeManager:
    """Manages theme state and switching between dark and light modes"""
    
    def __init__(self):
        """Initialize theme manager"""
        self.init_theme()
    
    def init_theme(self):
        """Initialize the theme session state"""
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"
    
    def change_theme(self):
        """Callback to toggle the theme"""
        if st.session_state.theme == "dark":
            st.session_state.theme = "light"
        else:
            st.session_state.theme = "dark"
    
    def get_current_theme(self):
        """Get the current theme name"""
        return st.session_state.theme
    
    def is_dark_mode(self):
        """Check if current theme is dark"""
        return st.session_state.theme == "dark"
    
    def get_theme_css(self):
        """Returns the CSS string based on the current session state"""
        theme = st.session_state.theme
        
        if theme == "dark":
            # --- MIDNIGHT EDITION (NO CHANGES) ---
            variables = """
            /* Backgrounds */
            --bg-app: #0E1117;
            --bg-card: #1A1C24;
            
            /* Sidebar (Matches Dark Theme) */
            --bg-sidebar: #14161C;
            --sidebar-text: #F3F4F6;
            --sidebar-border: #2D3748;
            
            /* Text */
            --text-main: #F3F4F6;
            --text-muted: #9CA3AF;
            
            /* Borders */
            --border-color: #2D3748;
            --border-highlight: #4B5563;
            
            /* Brand Colors */
            --primary: #3B82F6;       
            --accent: #60A5FA;        
            --gold: #F59E0B;          
            --gold-dim: #B45309;
            
            /* Status Colors */
            --success: #10B981;
            --danger: #EF4444;
            --warning: #F59E0B;

            /* Shadows & Gradients */
            --shadow-glow: 0 0 20px rgba(59, 130, 246, 0.15);
            --shadow-card: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
            --header-bg: linear-gradient(180deg, #1A1C24 0%, #0E1117 100%);
            --header-icon-opacity: 0.2;
            
            --gradient-gold: linear-gradient(135deg, #F59E0B 0%, #B45309 100%);
            --gradient-blue: linear-gradient(135deg, #1E40AF 0%, #1E3A8A 100%);
            """
        else:
            # --- DAYLIGHT EDITION (OPTIMIZED PRO) ---
            variables = """
            /* Backgrounds - Subtle Depth */
            --bg-app: #F8FAFC;        /* Slate 50 - Very subtle off-white */
            --bg-card: #FFFFFF;       /* Pure White for cards to pop */
            
            /* Sidebar - FORCED DARK (Hybrid Look) */
            --bg-sidebar: #0F172A;    /* Slate 900 (Deep Navy Black) */
            --sidebar-text: #F1F5F9;  /* Slate 100 (White-ish) */
            --sidebar-border: #1E293B; /* Slate 800 */
            
            /* Text - High Contrast */
            --text-main: #020617;     /* Slate 950 (Virtually Black) */
            --text-muted: #475569;    /* Slate 600 (Dark Grey) */
            
            /* Borders - Crisp & Clean */
            --border-color: #CBD5E1;  /* Slate 300 */
            --border-highlight: #94A3B8; /* Slate 400 */
            
            /* Brand Colors - Deep & Professional */
            --primary: #1E3A8A;       /* Blue 900 (Royal Navy) */
            --accent: #2563EB;        /* Blue 600 (Vibrant Blue) */
            --gold: #B45309;          /* Amber 700 */
            --gold-dim: #78350F;
            
            /* Status Colors - Saturated */
            --success: #15803D;       /* Green 700 */
            --danger: #B91C1C;        /* Red 700 */
            --warning: #C2410C;       /* Orange 700 */

            /* Shadows - Elegant Diffusion */
            --shadow-glow: 0 4px 20px rgba(37, 99, 235, 0.1);
            --shadow-card: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
            
            --header-bg: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%);
            --header-icon-opacity: 0.08;
            
            --gradient-gold: linear-gradient(135deg, #B45309 0%, #92400E 100%);
            --gradient-blue: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%);
            """
        
        # Complete CSS
        css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Inter:wght@400;500;600;700;800;900&display=swap');
        
        :root {{
            {variables}
        }}
        
        /* --- Global Layout --- */
        .stApp {{
            background-color: var(--bg-app);
            color: var(--text-main);
            font-family: 'Inter', 'Cairo', sans-serif;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: var(--text-main) !important;
            font-family: 'Inter', 'Cairo', sans-serif;
            font-weight: 800;
            letter-spacing: -0.025em;
        }}
        
        /* --- HYBRID SIDEBAR (Always Dark) --- */
        section[data-testid="stSidebar"] {{
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--sidebar-border);
        }}
        
        /* Force White Text in Sidebar */
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stMarkdown {{
            color: var(--sidebar-text) !important;
        }}
        
        /* Sidebar Headers */
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: #FFFFFF !important; 
        }}
        
        /* Sidebar Input Fields - Dark Mode Style */
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] .stSelectbox > div > div,
        section[data-testid="stSidebar"] .stMultiSelect > div > div {{
            background-color: #1E293B !important;
            color: #FFFFFF !important;
            border-color: #334155 !important;
        }}
        
        /* Sidebar Buttons */
        section[data-testid="stSidebar"] button {{
            background-color: #334155 !important;
            color: #FFFFFF !important;
            border: 1px solid #475569 !important;
        }}
        section[data-testid="stSidebar"] button:hover {{
            background-color: #475569 !important;
            border-color: #64748B !important;
        }}
        
        /* --- UI Components --- */
        
        /* Enhanced Header */
        .mokhber-header {{
            background: var(--header-bg);
            padding: 2.5rem;
            border-radius: 16px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-glow);
            margin-bottom: 2.5rem;
            position: relative;
            overflow: hidden;
        }}
        
        .mokhber-header::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 3px;
            background: var(--gradient-gold);
            box-shadow: 0 2px 10px var(--gold);
        }}
        
        .mokhber-title {{
            font-size: 2.75rem;
            font-weight: 900;
            background: linear-gradient(90deg, var(--text-main) 0%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1.5px;
            margin-bottom: 0.5rem;
        }}
        
        .mokhber-subtitle {{
            color: var(--text-muted);
            font-size: 1.1rem;
            font-weight: 500;
        }}
        
        /* Metric Cards - Clean & Pop */
        .metric-card {{
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-card);
            position: relative;
            overflow: hidden;
            transition: all 0.2s ease;
            height: 100%;
        }}
        
        .metric-card:hover {{
            transform: translateY(-4px);
            border-color: var(--accent);
            box-shadow: 0 12px 24px -8px rgba(0,0,0,0.15);
        }}
        
        .metric-value {{
            font-size: 2.4rem;
            font-weight: 800;
            color: var(--text-main);
            line-height: 1.1;
            margin-bottom: 0.25rem;
            letter-spacing: -1px;
        }}
        
        .metric-label {{
            color: var(--text-muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 700;
        }}
        
        /* News Cards */
        .news-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            margin-bottom: 1.25rem;
            transition: all 0.2s ease;
            border-left: 4px solid var(--gold);
            display: flex;
            gap: 1.5rem;
            align-items: flex-start;
            box-shadow: var(--shadow-card);
        }}
        
        .news-card:hover {{
            border-color: var(--accent);
            transform: translateX(4px);
            box-shadow: 0 8px 16px -4px rgba(0,0,0,0.1);
        }}

        .news-content {{
            flex: 1;
            min-width: 0;
        }}

        .news-img-container {{
            width: 150px;
            height: 110px;
            flex-shrink: 0;
            border-radius: 8px;
            overflow: hidden;
            background-color: var(--bg-sidebar); 
            display: none;
            border: 1px solid var(--border-color);
        }}

        .news-img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }}
        
        .news-card:hover .news-img {{
            transform: scale(1.05);
        }}

        @media (max-width: 600px) {{
            .news-card {{
                flex-direction: column-reverse;
            }}
            .news-img-container {{
                width: 100%;
                height: 200px;
                display: block !important;
                margin-bottom: 1rem;
            }}
        }}
        
        .news-title {{
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--primary); 
            text-decoration: none;
            display: block;
            margin-bottom: 0.5rem;
            transition: color 0.2s;
            line-height: 1.3;
        }}
        
        .news-title:hover {{
            color: var(--accent);
            text-decoration: underline;
        }}
        
        .news-summary {{
            color: var(--text-muted);
            font-size: 0.95rem;
            line-height: 1.6;
        }}
        
        .news-meta {{
            display: flex; flex-wrap: wrap; gap: 0.75rem;
            margin-bottom: 0.75rem; align-items: center;
        }}
        
        /* Badges */
        .badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            display: inline-flex; align-items: center; gap: 0.35rem;
        }}
        
        .badge-source {{ background: rgba(59, 130, 246, 0.1); color: var(--primary); border: 1px solid var(--primary); }}
        .badge-category {{ background: rgba(245, 158, 11, 0.1); color: var(--gold); border: 1px solid var(--gold); }}
        .badge-positive {{ background: rgba(16, 185, 129, 0.1); color: var(--success); border: 1px solid var(--success); }}
        .badge-negative {{ background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid var(--danger); }}
        .badge-neutral {{ background: rgba(107, 114, 128, 0.1); color: var(--text-muted); border: 1px solid var(--text-muted); }}
        
        .badge-time {{
            color: var(--text-muted);
            font-size: 0.8rem;
            margin-left: auto;
            font-family: monospace;
            opacity: 0.8;
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            background-color: var(--bg-card);
            border-radius: 8px;
            padding: 0.5rem;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-card);
        }}
        
        .stTabs [data-baseweb="tab"] {{
            color: var(--text-muted);
            font-weight: 600;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: var(--primary) !important;
            color: #FFFFFF !important;
            border-radius: 6px;
        }}
        
        /* Filter Summary */
        .filter-summary {{
            background: rgba(96, 165, 250, 0.05);
            border: 1px solid var(--primary);
            color: var(--primary);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            font-weight: 500;
        }}
        
        /* Status Dot/Badge */
        .status-badge {{
            display: inline-flex; align-items: center; gap: 0.5rem;
            padding: 0.5rem 1rem; border-radius: 50px;
            font-size: 0.85rem; font-weight: 600;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            margin-top: 1rem;
            color: var(--text-main);
            box-shadow: var(--shadow-card);
        }}
        
        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: var(--bg-app); }}
        ::-webkit-scrollbar-thumb {{ background: var(--border-highlight); border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: var(--text-muted); }}
        
        mark {{
            background: var(--gold);
            color: #FFFFFF;
            padding: 0 4px;
            border-radius: 2px;
        }}
        
        .rtl {{ direction: rtl; text-align: right; font-family: 'Cairo', sans-serif; }}
        
        .mokhber-header > div > div:last-child {{ opacity: var(--header-icon-opacity); }}
        </style>
        """
        return css


theme_manager = ThemeManager()