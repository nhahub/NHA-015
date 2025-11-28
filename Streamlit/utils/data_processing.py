"""
Data processing and demo data generation
"""
import pandas as pd
from datetime import datetime, timedelta
from config.settings import Config
from utils.date_utils import try_parse_datestr


def generate_demo_data():
    """Generate demo data for testing without database"""
    now = datetime.now(tz=Config.CAIRO_TZ)
    rows = []
    
    titles = [
        "Egyptian Economy Shows Strong Growth in Q4 2024",
        "New Infrastructure Projects Announced in Alexandria",
        "Technology Sector Sees Record Investment in Cairo",
        "Education Reforms Gain Momentum Across the Nation",
        "Tourism Numbers Reach Pre-Pandemic Levels",
        "Healthcare Initiative Launches in Rural Areas",
        "Green Energy Projects Transform Suez Region",
        "Cultural Festival Celebrates Egyptian Heritage",
        "Sports Academy Opens in Giza",
        "Agricultural Exports Hit All-Time High",
        "Digital Transformation Accelerates in Government",
        "New University Campus Opens in Aswan",
        "Transportation Network Expansion Continues",
        "Environmental Protection Measures Strengthen",
        "Youth Employment Program Shows Success",
        "Scientific Research Breakthrough Announced",
        "Real Estate Market Shows Stability",
        "Food Security Initiative Expands",
        "International Trade Agreements Signed",
        "Community Development Projects Launch"
    ]
    
    sources = ["Al-Ahram", "Egypt Today", "Daily News Egypt", "Ahram Online", "Egypt Independent"]
    categories = ["Economy", "Politics", "Technology", "Culture", "Sports"]
    sentiments = ["positive", "neutral", "positive", "neutral", "positive"]
    languages = ["ar", "en", "en", "ar", "en"]
    
    for i in range(20):
        rows.append({
            "id": i + 1,
            "title": titles[i],
            "image_url": f"https://picsum.photos/seed/{i+100}/200/200",
            "summary": f"Detailed analysis of recent developments in Egypt's {categories[i % 5].lower()} sector, highlighting key achievements and future prospects for growth and development.",
            "source": sources[i % 5],
            "category": categories[i % 5],
            "sentiment": sentiments[i % 5],
            "url": "#",
            "language": languages[i % 5],
            "published_date": (now - timedelta(hours=i * 2)).isoformat(),
            "scraped_at": (now - timedelta(hours=i * 2)).isoformat()
        })
    
    df = pd.DataFrame(rows)
    df['published_dt'] = df['published_date'].apply(try_parse_datestr)
    df['published_display'] = df['published_dt'].apply(
        lambda d: d.strftime("%a, %d %b %Y %H:%M") if d else "Unknown"
    )
    
    return df


def calculate_sentiment_metrics(df):
    """
    Calculate sentiment metrics from DataFrame
    Returns dict with counts and percentages
    """
    if df.empty or 'sentiment' not in df.columns:
        return {
            'total': 0,
            'positive': 0,
            'negative': 0,
            'neutral': 0,
            'pos_rate': 0,
            'neg_rate': 0,
            'neu_rate': 0,
            'sentiment_score': 0
        }
    
    total = len(df)
    pos = int((df['sentiment'].str.lower() == 'positive').sum())
    neg = int((df['sentiment'].str.lower() == 'negative').sum())
    neu = total - pos - neg
    
    pos_rate = (pos / total * 100) if total > 0 else 0
    neg_rate = (neg / total * 100) if total > 0 else 0
    neu_rate = (neu / total * 100) if total > 0 else 0
    
    sentiment_score = ((pos - neg) / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'positive': pos,
        'negative': neg,
        'neutral': neu,
        'pos_rate': pos_rate,
        'neg_rate': neg_rate,
        'neu_rate': neu_rate,
        'sentiment_score': sentiment_score
    }


def enrich_dataframe_for_analysis(df):
    """
    Add derived columns for analytics
    Returns enriched DataFrame
    """
    if df.empty:
        return df
    
    viz_df = df.copy()
    
    # Extract date parts
    viz_df['date'] = viz_df['published_dt'].dt.date
    viz_df['hour'] = viz_df['published_dt'].dt.hour
    viz_df['weekday'] = viz_df['published_dt'].dt.day_name()
    
    # Normalize sentiment
    viz_df['sentiment_lower'] = viz_df['sentiment'].str.lower()
    
    # Add weekend flag
    viz_df['is_weekend'] = viz_df['weekday'].isin(['Friday', 'Saturday'])
    
    return viz_df