"""
Chart generation functions for Mokhber Intelligence Platform
All Plotly chart configurations in one place
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.theme_utils import theme_manager

# --- Theme Helpers ---

def get_template():
    """Get Plotly template based on current theme"""
    return "plotly_dark" if theme_manager.is_dark_mode() else "plotly_white"

def get_colors():
    """Get dynamic high-contrast color palette"""
    is_dark = theme_manager.is_dark_mode()
    return {
        'main': '#60A5FA' if is_dark else '#1E3A8A',      # Light Blue vs Royal Navy
        'accent': '#F59E0B' if is_dark else '#B45309',    # Gold vs Dark Amber
        'bar_fill': 'rgba(59, 130, 246, 0.3)' if is_dark else 'rgba(30, 58, 138, 0.6)',
        # Text Colors - PURE BLACK for Light Mode
        'text': '#F3F4F6' if is_dark else '#000000',      
        'text_muted': '#9CA3AF' if is_dark else '#000000', 
        # Grid Lines - Darker for visibility
        'grid': 'rgba(255, 255, 255, 0.1)' if is_dark else 'rgba(0, 0, 0, 0.2)'
    }

def get_gradient_scale():
    """Get visible gradient scale for light mode"""
    if theme_manager.is_dark_mode():
        return 'Purples'
    else:
        # High contrast blue gradient (Visible Blue -> Deep Navy)
        return [[0, '#3B82F6'], [1, '#0F172A']]

def update_chart_layout(fig, height=400, show_legend=False):
    """Apply strict high-contrast styling to any chart"""
    c = get_colors()
    
    # Global Font Settings
    fig.update_layout(
        template=get_template(),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(t=30, b=20, l=40, r=40),
        font=dict(family="Inter, sans-serif", size=12, color=c['text']),
        showlegend=show_legend,
        hoverlabel=dict(
            bgcolor=c['text'],
            font_color='#FFFFFF' if not theme_manager.is_dark_mode() else '#000000',
            bordercolor=c['text']
        ),
        # Force Legend Text Color
        legend=dict(
            font=dict(color=c['text'])
        ),
        # Force ColorAxis (Heatmap/Bar scale) Text Color
        coloraxis_colorbar=dict(
            title_font=dict(color=c['text']),
            tickfont=dict(color=c['text'])
        )
    )
    
    # Apply Axis Colors Globally (Ticks, Titles, Grids)
    axis_style = dict(
        title_font=dict(color=c['text'], size=13, weight='bold'),
        tickfont=dict(color=c['text'], size=11),
        gridcolor=c['grid'],
        zerolinecolor=c['grid'],
        linecolor=c['text'], # Axis line itself
        showline=True
    )
    
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)

# --- Chart Functions ---

def create_volume_sentiment_timeline(viz_df):
    daily = viz_df.groupby('date').size().reset_index(name='count')
    sent_daily = viz_df.groupby('date').apply(
        lambda x: ((x['sentiment_lower'] == 'positive').sum() - 
                   (x['sentiment_lower'] == 'negative').sum()) / len(x) * 100
    ).reset_index(name='score')
    
    c = get_colors()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(
            x=daily['date'], y=daily['count'], name='Volume',
            marker_color=c['bar_fill'],
            hovertemplate='Date: %{x}<br>Articles: %{y}<extra></extra>'
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=sent_daily['date'], y=sent_daily['score'], name='Sentiment Index',
            line=dict(color=c['accent'], width=3),
            mode='lines+markers',
            hovertemplate='Date: %{x}<br>Sentiment: %{y:.1f}<extra></extra>'
        ),
        secondary_y=True
    )
    
    update_chart_layout(fig, show_legend=True)
    fig.update_layout(legend=dict(orientation="h", y=1.1, x=0))
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Article Count", secondary_y=False)
    fig.update_yaxes(title_text="Sentiment Score", secondary_y=True)
    
    return fig


def create_sentiment_pie_chart(viz_df):
    
    clean_df = viz_df.copy()
    if 'embedding' in clean_df.columns:
        clean_df = clean_df.drop(columns=['embedding'])
        
    counts = clean_df['sentiment_lower'].value_counts()
    is_dark = theme_manager.is_dark_mode()
    
    colors = []
    for sentiment in counts.index:
        if 'pos' in sentiment:
            colors.append('#10B981' if is_dark else '#15803D')
        elif 'neg' in sentiment:
            colors.append('#EF4444' if is_dark else '#B91C1C')
        else:
            colors.append('#9CA3AF' if is_dark else '#64748B')
    
    fig = go.Figure(data=[go.Pie(
        labels=counts.index.str.title(),
        values=counts.values,
        marker=dict(colors=colors),
        hole=0.6,
        textfont=dict(color='#FFFFFF'), 
        
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    update_chart_layout(fig, show_legend=True)
    fig.update_layout(legend=dict(orientation="h", y=0, x=0.5, xanchor='center'))
    
    return fig


def create_top_sources_bar(viz_df, top_n=10):
    top_src = viz_df['source'].value_counts().head(top_n)
    c = get_colors()
    
    fig = go.Figure(go.Bar(
        x=top_src.values,
        y=top_src.index,
        orientation='h',
        marker=dict(
            color=top_src.values,
            colorscale=get_gradient_scale(),
            showscale=False
        ),
        # Explicit text color for bar labels if they exist
        textfont=dict(color=c['text']),
        hovertemplate='<b>%{y}</b><br>Articles: %{x}<extra></extra>'
    ))
    
    update_chart_layout(fig)
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Article Count")
    
    return fig


def create_category_pie_chart(viz_df, top_n=10):
    top_cat = viz_df['category'].value_counts().head(top_n)
    
    colors = px.colors.sequential.RdBu if theme_manager.is_dark_mode() else px.colors.qualitative.Bold
    
    fig = px.pie(
        names=top_cat.index,
        values=top_cat.values,
        hole=0.4,
        color_discrete_sequence=colors
    )
    
    fig.update_traces(
        textfont=dict(color='#FFFFFF'), # White text on colored slices
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )
    update_chart_layout(fig, show_legend=True)
    
    return fig


def create_sentiment_heatmap(viz_df):
    heatmap_data = pd.crosstab(viz_df['category'], viz_df['sentiment_lower'])
    
    for col in ['positive', 'neutral', 'negative']:
        if col not in heatmap_data.columns:
            heatmap_data[col] = 0
    
    heatmap_data = heatmap_data[['positive', 'neutral', 'negative']]
    
    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Sentiment", y="Category", color="Articles"),
        x=heatmap_data.columns,
        y=heatmap_data.index,
        color_continuous_scale='RdBu_r',
        aspect="auto"
    )
    
    update_chart_layout(fig)
    return fig


def create_hourly_sentiment_chart(viz_df):
    hourly_score = viz_df.groupby('hour').apply(
        lambda x: ((x['sentiment_lower'] == 'positive').sum() - 
                   (x['sentiment_lower'] == 'negative').sum()) / len(x) if len(x) > 0 else 0
    ).reset_index(name='score')
    
    c = get_colors()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hourly_score['hour'],
        y=hourly_score['score'],
        mode='lines+markers',
        line=dict(color=c['main'], width=3, shape='spline'),
        fill='tozeroy',
        fillcolor=c['bar_fill'],
        marker=dict(size=8, color=c['main']),
        hovertemplate='Hour: %{x}:00<br>Sentiment: %{y:.2f}<extra></extra>'
    ))
    
    update_chart_layout(fig)
    fig.update_layout(
        xaxis=dict(title="Hour of Day", tickmode='linear', dtick=2, range=[-0.5, 23.5]),
        yaxis=dict(title="Sentiment Score")
    )
    
    return fig


def create_category_trend_chart(viz_df, top_n=5):
    top_cats = viz_df['category'].value_counts().head(top_n).index.tolist()
    cat_trend_df = viz_df[viz_df['category'].isin(top_cats)].groupby(['date', 'category']).size().reset_index(name='count')
    
    fig = px.line(
        cat_trend_df,
        x='date', y='count', color='category', markers=True,
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    
    fig.update_traces(hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Articles: %{y}<extra></extra>')
    
    update_chart_layout(fig, show_legend=True)
    fig.update_layout(
        xaxis_title="Date", 
        yaxis_title="Article Count",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center', title_text="")
    )
    
    return fig


def create_bigrams_bar_chart(df_bigrams):
    if df_bigrams.empty:
        return None
    
    fig = px.bar(
        df_bigrams,
        x='Count', y='Phrase', orientation='h', color='Count',
        color_continuous_scale=get_gradient_scale()
    )
    
    fig.update_traces(hovertemplate='<b>%{y}</b><br>Frequency: %{x}<extra></extra>')
    
    update_chart_layout(fig)
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Frequency")
    
    return fig


def create_weekday_volume_chart(viz_df):
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    wd_counts = viz_df['weekday'].value_counts().reindex(days_order).fillna(0)
    
    fig = px.bar(
        x=wd_counts.index, y=wd_counts.values, color=wd_counts.values,
        color_continuous_scale=get_gradient_scale()
    )
    
    fig.update_traces(hovertemplate='<b>%{x}</b><br>Articles: %{y}<extra></extra>')
    
    update_chart_layout(fig, height=350)
    fig.update_layout(xaxis_title=None, yaxis_title="Article Count")
    
    return fig


def create_weekend_pie_chart(viz_df):
    is_weekend = viz_df['weekday'].isin(['Friday', 'Saturday'])
    weekend_counts = is_weekend.value_counts().rename({True: 'Weekend', False: 'Weekday'})
    
    c = get_colors()
    fig = px.pie(
        names=weekend_counts.index,
        values=weekend_counts.values,
        hole=0.5,
        color_discrete_sequence=[c['main'], c['accent']]
    )
    
    fig.update_traces(
        textfont=dict(color='#FFFFFF'), 
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )
    update_chart_layout(fig, height=350)
    
    return fig
