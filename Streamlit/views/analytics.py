"""
Analytics page - advanced visualizations and insights
"""
import streamlit as st
import html
import json
import numpy as np
from utils.text_utils import get_top_bigrams
from ui.charts import (
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

def parse_embedding(val):
    
    if val is None: return None
    try:
        if isinstance(val, str):
            return np.array(json.loads(val))
        if isinstance(val, list):
            return np.array(val)
    except:
        return None
    return None

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_semantic_highlights(df, top_n=5):
    """
    Returns top unique stories based on semantic similarity.
    Prevents duplicate stories from clogging the feed.
    """
    if df.empty: return df
    
    # 1. Sort by Newest first 
    if 'published_dt' in df.columns:
        df = df.sort_values('published_dt', ascending=False)
    
    # 2. Semantic Deduplication
    unique_indices = []
    seen_vectors = []
    
    
    has_embeddings = 'embedding' in df.columns and df['embedding'].notna().any()
    
    for idx, row in df.iterrows():
        if len(unique_indices) >= top_n:
            break
            
        is_duplicate = False
        
        if has_embeddings:
            vec = parse_embedding(row.get('embedding'))
            if vec is not None:
               
                for seen_vec in seen_vectors:
                    score = cosine_similarity(vec, seen_vec)
                    if score > 0.85: 
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    seen_vectors.append(vec)
        
        if not is_duplicate:
            unique_indices.append(idx)
            
    return df.loc[unique_indices]


def render_analytics(viz_df, metrics):
    """Render analytics dashboard"""
    st.markdown("### 📊 Analytics Dashboard")
    
    
    
    pos_highlights = get_semantic_highlights(viz_df[viz_df['sentiment_lower'] == 'positive'])
    neg_highlights = get_semantic_highlights(viz_df[viz_df['sentiment_lower'] == 'negative'])

    #DROP EMBEDDING (Cleanup)
    
    clean_df = viz_df.drop(columns=['embedding'], errors='ignore')

    if clean_df.empty:
        st.info("📊 No data available for analysis.")
        return
    
    
    render_sentiment_section(clean_df, metrics)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    
    render_timeseries_section(clean_df)
    
    st.divider()
    
    
    render_deep_sentiment_section(clean_df)
    
    st.divider()
    
  
    render_category_trends_section(clean_df)
    
    st.divider()
    
   
    render_distribution_section(clean_df)
    
    st.divider()
    
    
    render_content_intelligence_section(clean_df, pos_highlights, neg_highlights)
    
    st.divider()
    
    
    render_WeekdayVolume_section(clean_df)


def render_sentiment_section(viz_df, metrics):
    """Render sentiment intelligence metrics"""
    st.markdown("#### 🎭 Sentiment Intelligence")
    
    s1, s2, s3, s4 = st.columns(4)
    
    def sent_metric(val, label, sub, color):
        return f"""
        <div class="metric-card" style="padding: 1rem;">
            <div style="font-size: 1.8rem; font-weight:800; color:{color}">{val}</div>
            <div style="font-size:0.8rem; color:#9CA3AF;">{label}</div>
            <div style="font-size:0.7rem; color:#6B7280;">{sub}</div>
        </div>
        """
    
    s1.markdown(sent_metric(metrics['positive'], "Positive", f"{metrics['pos_rate']:.1f}%", "#10B981"), unsafe_allow_html=True)
    s2.markdown(sent_metric(metrics['neutral'], "Neutral", f"{metrics['neu_rate']:.1f}%", "#9CA3AF"), unsafe_allow_html=True)
    s3.markdown(sent_metric(metrics['negative'], "Negative", f"{metrics['neg_rate']:.1f}%", "#EF4444"), unsafe_allow_html=True)
    
    # Avg Sentiment
    avg_src_score = 0
    if not viz_df.empty:
        avg_src_score = viz_df.groupby('source').apply(
            lambda x: ((x['sentiment_lower'] == 'positive').sum() - 
                       (x['sentiment_lower'] == 'negative').sum()) / len(x) * 100
        ).mean()
    
    sc_color = "#10B981" if avg_src_score > 0 else "#EF4444"
    s4.markdown(sent_metric(f"{avg_src_score:+.1f}", "Avg Source Score", "Mean Index", sc_color), unsafe_allow_html=True)


def render_timeseries_section(viz_df):
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("**📈 Volume & Sentiment Timeline**")
        fig = create_volume_sentiment_timeline(viz_df)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**🎭 Sentiment Share**")
        fig = create_sentiment_pie_chart(viz_df)
        st.plotly_chart(fig, use_container_width=True)


def render_deep_sentiment_section(viz_df):
    st.markdown("#### 🧠 Deep Sentiment Analysis")
    ds_c1, ds_c2 = st.columns(2)
    with ds_c1:
        st.markdown("**🌡️ Sentiment Heatmap (Category vs. Sentiment)**")
        fig = create_sentiment_heatmap(viz_df)
        st.plotly_chart(fig, use_container_width=True)
    with ds_c2:
        st.markdown("**⏰ Hourly Sentiment Rhythm**")
        fig = create_hourly_sentiment_chart(viz_df)
        st.plotly_chart(fig, use_container_width=True)
    st.divider()
    render_sentiment_extremes(viz_df)


def render_sentiment_extremes(viz_df):
    st.markdown("#### ⚡ Sentiment Extremes")
    daily_sent_counts = viz_df.groupby(['date', 'sentiment_lower']).size().unstack(fill_value=0)
    
    most_pos_date, most_pos_val = None, 0
    most_neg_date, most_neg_val = None, 0
    
    if not daily_sent_counts.empty:
        if 'positive' in daily_sent_counts.columns:
            most_pos_date = daily_sent_counts['positive'].idxmax()
            most_pos_val = daily_sent_counts['positive'].max()
        if 'negative' in daily_sent_counts.columns:
            most_neg_date = daily_sent_counts['negative'].idxmax()
            most_neg_val = daily_sent_counts['negative'].max()
    
    se_c1, se_c2 = st.columns(2)
    with se_c1:
        date_str = most_pos_date.strftime('%a, %d %b') if most_pos_date else "N/A"
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #10B981;">
            <div style="color: #10B981; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; margin-bottom: 0.5rem;">😊 Most Positive Day</div>
            <div class="metric-value">{date_str}</div>
            <div style="color: #9CA3AF; font-size: 0.9rem;">{most_pos_val} positive articles</div>
        </div>""", unsafe_allow_html=True)
    with se_c2:
        date_str = most_neg_date.strftime('%a, %d %b') if most_neg_date else "N/A"
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #EF4444;">
            <div style="color: #EF4444; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; margin-bottom: 0.5rem;">😞 Most Negative Day</div>
            <div class="metric-value">{date_str}</div>
            <div style="color: #9CA3AF; font-size: 0.9rem;">{most_neg_val} negative articles</div>
        </div>""", unsafe_allow_html=True)


def render_category_trends_section(viz_df):
    st.markdown("#### 📈 Category Trends Evolution")
    fig = create_category_trend_chart(viz_df, top_n=5)
    st.plotly_chart(fig, use_container_width=True)


def render_distribution_section(viz_df):
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**📰 Top Sources**")
        fig = create_top_sources_bar(viz_df, top_n=10)
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        st.markdown("**🏷️ Top Categories**")
        fig = create_category_pie_chart(viz_df, top_n=10)
        st.plotly_chart(fig, use_container_width=True)


def render_content_intelligence_section(viz_df, pos_highlights, neg_highlights):
    """Render content intelligence analysis"""
    st.markdown("#### 📝 Content Intelligence (N-Grams)")
    ci_c1, ci_c2 = st.columns(2)
    
    titles_list = viz_df['title'].astype(str).tolist()
    
    with ci_c1:
        st.markdown("**🔠 Top Contextual Bigrams (2-Word Phrases)**")
        df_bigrams = get_top_bigrams(titles_list, top_n=15)
        if not df_bigrams.empty:
            fig = create_bigrams_bar_chart(df_bigrams)
            if fig: st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for bigram analysis.")
    
    with ci_c2:
        st.markdown("**📰 Sentiment Extremes Feed**")
        render_sentiment_highlights_cards(pos_highlights, neg_highlights)


def render_sentiment_highlights_cards(pos_arts, neg_arts):
    """Render clean highlights without summary"""
    col_pos, col_neg = st.columns(2)
    
    with col_pos:
        st.markdown("##### ✅ Positive Highlights")
        if not pos_arts.empty:
            for _, r in pos_arts.iterrows():
                title = html.escape(str(r.get('title', 'No Title'))[:100])
                url = html.escape(str(r.get('url', '#')))
                source = html.escape(str(r.get('source', 'Unknown')))
                date_display = r.get('published_display', '')

                st.markdown(f"""
                <div style="padding: 12px; border-left: 3px solid #10B981; background: rgba(16, 185, 129, 0.05); margin-bottom: 10px; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.15);">
                    <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 6px; line-height: 1.3;">
                        <a href="{url}" target="_blank" style="text-decoration: none; color: inherit;">{title}</a>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.75rem; color: #10B981; font-weight: 600; background: rgba(16,185,129,0.1); padding: 2px 6px; border-radius: 4px;">{source}</span>
                        <span style="font-size: 0.7rem; color: var(--text-muted); font-family: monospace; opacity: 0.8;">{date_display}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No positive articles found.")
    
    with col_neg:
        st.markdown("##### ⚠️ Negative Highlights")
        if not neg_arts.empty:
            for _, r in neg_arts.iterrows():
                title = html.escape(str(r.get('title', 'No Title'))[:100])
                url = html.escape(str(r.get('url', '#')))
                source = html.escape(str(r.get('source', 'Unknown')))
                date_display = r.get('published_display', '')

                st.markdown(f"""
                <div style="padding: 12px; border-left: 3px solid #EF4444; background: rgba(239, 68, 68, 0.05); margin-bottom: 10px; border-radius: 6px; border: 1px solid rgba(239, 68, 68, 0.15);">
                    <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 6px; line-height: 1.3;">
                        <a href="{url}" target="_blank" style="text-decoration: none; color: inherit;">{title}</a>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.75rem; color: #EF4444; font-weight: 600; background: rgba(239,68,68,0.1); padding: 2px 6px; border-radius: 4px;">{source}</span>
                        <span style="font-size: 0.7rem; color: var(--text-muted); font-family: monospace; opacity: 0.8;">{date_display}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No negative articles found.")


def render_WeekdayVolume_section(viz_df):
    st.markdown("#### 📅 Weekday Publication Volume")
    wd_c1, wd_c2 = st.columns(2)
    with wd_c1:
        st.markdown("**Publishing Volume by Weekday**")
        fig = create_weekday_volume_chart(viz_df)
        st.plotly_chart(fig, use_container_width=True)
    with wd_c2:
        st.markdown("**Weekend vs. Weekday Activity**")
        fig = create_weekend_pie_chart(viz_df)
        st.plotly_chart(fig, use_container_width=True)
