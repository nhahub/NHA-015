# 📊 Mokhber Intelligence Dashboard

![Dashboard Overview](/media/dashboard_output_1.png)

## Overview

The Streamlit dashboard is the user-facing component of Mokhber Intelligence. It provides real-time analytics, interactive visualizations, and advanced filtering capabilities for exploring news sentiment across Arabic and English sources.

---

## 📂 Folder Structure

```
Streamlit/
├── 📄 app.py                    # Main entry point
│
├── 📁 config/
│   ├── __init__.py
│   └── settings.py              # Configuration management
│
├── 📁 database/
│   ├── __init__.py
│   ├── connection.py            # DB connection & pooling
│   └── queries.py               # SQL builders & fetchers
│
├── 📁 ui/
│   ├── __init__.py
│   ├── styles.py                # CSS injection
│   ├── components.py            # Reusable UI elements
│   └── charts.py                # Plotly chart generators
│
├── 📁 utils/
│   ├── __init__.py
│   ├── data_processing.py       # Data transformations
│   ├── date_utils.py            # Date parsing & formatting
│   ├── text_utils.py            # NLP helpers
│   └── theme_utils.py           # Theme management
│
├── 📁 views/
│   ├── __init__.py
│   ├── live_feed.py             # Live Feed tab
│   ├── analytics.py             # Analytics tab
│   └── export.py                # Export tab
│
├── requirements.txt             # Python dependencies
└── readme.md                    # This file
```

---

## 🎨 Features

### 1. **Dual Theme System**

**Midnight Mode (Dark)** - Default high-contrast theme
**Daylight Mode (Light)** - Professional light theme

Theme switching is instant without page reload.
![White Theme](/media/white_theme.png)

**Implementation**: `utils/theme_utils.py`
```python
theme_manager.change_theme()  # Toggles between modes
theme_manager.is_dark_mode()  # Returns bool
```

### 2. **Live Feed Tab**

![Live Feed](/media/dashboard_output_2.png)

**Features**:
- Real-time article cards with images
- RTL support for Arabic content
- Pagination (50 articles per page)
- Search with highlighting
- Sorting: Newest/Oldest/Source A→Z

**Card Components**:
- Title (clickable link)
- Summary (300 chars)
- Source, Category, Sentiment badges
- Published date (Cairo timezone)
- Thumbnail image with fallback

**Search**: Highlights matching terms in yellow

### 3. **Advanced Analytics Tab**

![Analytics Tab](/media/dashboard_output_4.png)

#### Sentiment Intelligence Metrics

![Sentiment Metrics](/media/dashboard_output_5.png)

- **Total Articles**: Dynamic count
- **Positive/Neutral/Negative**: Count + percentage
- **Avg Source Score**: Mean sentiment across sources
- **Positive Rate**: Percentage of positive articles



#### Category Trends Evolution

- Line chart showing top 5 categories over time
- Interactive legend (click to hide/show)

#### Deep Sentiment Analysis

**Sentiment Heatmap**
- Category vs Sentiment crossover
- Color intensity = article count

**Hourly Sentiment Rhythm**
- Sentiment score by hour of day (0-23)
- Identifies peak positive/negative times

**Sentiment Extremes**
- Most positive day (date + count)
- Most negative day (date + count)

#### Content Intelligence

**N-Gram Analysis**
- Top 15 bigrams (2-word phrases)
- Filters stopwords (Arabic + English)

**Sentiment Highlights**
- Clickable positive article previews
- Clickable negative article previews

#### Week Publication Volume
![Chart](/media/dashboard_output_6.png)

- **Weekday Volume**: Bar chart (Mon-Sun)
- **Weekend vs Weekday**: Pie chart split

### 4. **Export Tab**

**Formats**:
- CSV (Excel-compatible)
- JSON (for APIs)

**Includes**: All filtered data with full schema

---

## 🔌 Database Integration

### Connection Pooling

```python
@st.cache_resource(ttl=600)
def get_engine():
    return create_engine(
        Config.get_db_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5
    )
```

**Benefits**:
- Reuses connections (10x faster than creating new ones)
- Auto-recovery on connection loss
- Handles AWS RDS timeouts

### Query Optimization

```python
# Fetch with limit and pagination
SELECT * FROM news
WHERE 1=1
  AND published_dt > NOW() - INTERVAL '30 days'
  AND (title ILIKE %search% OR summary ILIKE %search%)
ORDER BY scraped_at DESC
LIMIT 2000
```

**Performance**:
- Index on `scraped_at` (used in ORDER BY)
- Parameterized queries (prevents SQL injection)
- Client-side filtering for fine-grained control

### Demo Mode

If database is unavailable, generates 20 sample articles:
```python
if not Config.is_db_configured():
    df = generate_demo_data()
```

---

## 🎯 Advanced Filtering

### Filter Options

1. **Timeframe Presets**
   - Last 24h / 7 days / 30 days / Custom

2. **Sources** (Multi-select)
   - Al-Ahram, Youm7, Gomhuria, Guardian, BBC, NYT

3. **Categories** (Multi-select)
   - Economy, Politics, Technology, Sports, Culture, etc.

4. **Languages**
   - Arabic (ar) / English (en)

5. **Sentiment**
   - Positive / Neutral / Negative

### Filter Implementation

```python
def apply_filters(df, filters):
    if filters.get('sources'):
        df = df[df['source'].isin(filters['sources'])]
    
    if filters.get('categories'):
        df = df[df['category'].isin(filters['categories'])]
    
    # ... other filters
    return df
```

**Active Filter Summary**: Shows count of each filter type applied

---

## 📈 Charting System

### Plotly Configuration

All charts use dynamic theming:

```python
def update_chart_layout(fig, height=400):
    colors = get_colors()  # Theme-aware palette
    
    fig.update_layout(
        template=get_template(),  # Dark/Light
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=colors['text']),
        # ... more styling
    )
    
    # Force axis text colors (critical for light mode)
    fig.update_xaxes(tickfont=dict(color=colors['text']))
    fig.update_yaxes(tickfont=dict(color=colors['text']))
```

**Why This Matters**: Default Plotly light mode uses gray text, which is illegible on white backgrounds.

### Chart Types Used

| Chart | Library | Purpose |
|-------|---------|---------|
| Timeline | `make_subplots` | Volume + Sentiment dual-axis |
| Pie Charts | `go.Pie` | Sentiment/Category distribution |
| Bar Charts | `go.Bar` | Source rankings, N-grams |
| Line Charts | `px.line` | Category trends over time |
| Heatmaps | `px.imshow` | Sentiment × Category matrix |

---

## 🛠️ Data Processing Pipeline

### Date Normalization

```python
def try_parse_datestr(s):
    # Handles:
    # - ISO 8601: "2025-11-28T14:23:17Z"
    # - Arabic formats: "الجمعة، 15 يناير 2025"
    # - Unix timestamps
    # - Fuzzy parsing with dateutil
    
    cleaned = arabic_to_english_datestr(s)
    dt = dateparser.parse(cleaned, fuzzy=True)
    return dt.astimezone(Config.CAIRO_TZ)
```

**Output**: `"Wed, 28 Nov 2025 14:23"`

### Text Analysis

**RTL Detection**:
```python
def is_rtl_text(text):
    return any("\u0600" <= c <= "\u06FF" for c in text)
```

**Search Highlighting**:
```python
def highlight_text(text, search_term):
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)
```

### Sentiment Metrics

```python
def calculate_sentiment_metrics(df):
    total = len(df)
    pos = (df['sentiment'].str.lower() == 'positive').sum()
    neg = (df['sentiment'].str.lower() == 'negative').sum()
    neu = total - pos - neg
    
    sentiment_score = ((pos - neg) / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'positive': pos,
        'negative': neg,
        'neutral': neu,
        'pos_rate': pos / total * 100,
        'sentiment_score': sentiment_score
    }
```

---

## 🚀 Deployment

### Local Development

```bash
cd Streamlit
pip install -r requirements.txt

# Set environment variables
export RDS_HOST=localhost
export RDS_PORT=5432
export RDS_DB=news_db
export RDS_USER=admin
export RDS_PASSWORD=password

# Run dashboard
streamlit run app.py
```

**Access**: http://localhost:8501

### Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py", "--server.port=8501"]
```

```bash
docker build -t mokhber-dashboard .
docker run -p 8501:8501 --env-file .env mokhber-dashboard
```

### AWS Deployment Options

#### Option 1: ECS Fargate
```yaml
Task Definition:
  CPU: 512 (0.5 vCPU)
  Memory: 1024 (1 GB)
  Port: 8501
  Health Check: /healthz
```

#### Option 2: App Runner
- Easier than ECS
- Auto-scaling
- Built-in HTTPS
- Direct GitHub integration

#### Option 3: EC2 + Docker
- Most control
- Requires manual management
- Use Nginx reverse proxy

---

## 🎨 Customization

### Adding a New Chart

1. **Create chart function** in `ui/charts.py`:
```python
def create_my_new_chart(viz_df):
    fig = px.bar(...)
    update_chart_layout(fig)
    return fig
```

2. **Use in view** (`views/analytics.py`):
```python
fig = create_my_new_chart(viz_df)
st.plotly_chart(fig, use_container_width=True)
```

### Adding a New Page/Tab

1. **Create module** in `views/my_new_page.py`:
```python
def render_my_page(df):
    st.markdown("### My New Page")
    # ... your code
```

2. **Import and add tab** in `app.py`:
```python
from views.my_new_page import render_my_page

tabs = st.tabs(["Live Feed", "Analytics", "My New Page"])
with tabs[2]:
    render_my_page(df)
```

### Modifying Theme Colors

Edit `utils/theme_utils.py`:
```python
# In get_theme_css()
variables = """
    --primary: #YOUR_COLOR;
    --accent: #YOUR_ACCENT;
    --text-main: #YOUR_TEXT;
"""
```

---

## 🐛 Common Issues

### Issue: "Connection to database failed"

**Solution**: Check RDS security group allows inbound on port 5432 from your IP.

### Issue: "Charts not rendering"

**Solution**: Clear browser cache, restart Streamlit.

### Issue: "Arabic text displays as boxes"

**Solution**: Ensure `'Cairo'` font is loaded in CSS:
```css
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
```

### Issue: "Light mode text is invisible"

**Solution**: This was fixed by forcing `color: #000000` for text in light mode. Update to latest `ui/charts.py`.

---

## 📊 Performance Optimization

### Caching Strategy

```python
@st.cache_resource(ttl=600)  # 10 minutes
def get_engine():
    # Database connection

@st.cache_data(ttl=300)  # 5 minutes
def fetch_headlines(...):
    # Query results

@st.cache_data(ttl=600)
def detect_table():
    # Schema inspection
```

**Why TTL?**
- Data updates every ~2 hours (scheduled pipeline)
- No need to cache forever
- Balance freshness vs speed

### Lazy Loading

```python
# Don't load images until card is rendered
<img loading="lazy" src="..." />
```

### Pagination

```python
# Load max 2000 rows from DB
# Display 50 per page in UI
per_page = 50
start = (page - 1) * per_page
df.iloc[start:start + per_page]
```

---


## 🚀 Future Enhancements
- [ ] **User Authentication**
- [ ] **Custom Dashboards**: Save filter presets
- [ ] **Alerts**: Email notifications for specific keywords/sentiments
- [ ] **Mobile App**: React Native wrapper
- [ ] **PDF Reports**: Automated daily/weekly summaries

---
