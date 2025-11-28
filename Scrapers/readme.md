# 📰 News Scrapers Module


## Overview

This module contains containerized web scrapers that collect news articles from 6 major Arabic and English news sources. Each scraper is designed to run independently in AWS ECS Fargate, orchestrated by Step Functions for parallel execution.

---

## 📂 Folder Structure

```
Scrapers/
├── 📁 ahram/           # Al-Ahram (Arabic)
├── 📁 youm7/           # Youm7 (Arabic)
├── 📁 gomhuria/        # Al-Gomhuria (Arabic)
├── 📁 guardian/        # The Guardian (English)
├── 📁 BBC/             # BBC News (English)
├── 📁 nyt/             # New York Times (English)
└── readme.md           # This file
```

---

## 🔧 Individual Scraper Details

### 1. **Al-Ahram (ahram/)** 🇪🇬

**Source**: https://gate.ahram.org.eg  
**Method**: Selenium + BeautifulSoup  
**Language**: Arabic  

**Categories Scraped**:
- أخبار (News)
- رياضة (Sports)
- حوادث (Accidents)
- فن (Arts & Culture)
- تكنولوجيا (Technology)

**Technical Details**:
- Uses Selenium for JavaScript-heavy pages
- Extracts full article content from detail pages
- Handles cookie consent popups
- Implements date normalization for Arabic formats
- Output: `raw/arabic/ahram/ahram_YYYYMMDD_HHMMSS.json`

**Key Challenges Solved**:
- EU cookie banner injection (stripped via pattern matching)
- Dynamic content loading (scroll + wait)
- Date format variations (multiple Arabic patterns)

---

### 2. **Youm7 (youm7/)** 🇪🇬

**Source**: https://www.youm7.com  
**Method**: Selenium + BeautifulSoup  
**Language**: Arabic  

**Categories Scraped**:
- عاجل (Breaking News)
- سياسة (Politics)
- اقتصاد (Economy)
- رياضة (Sports)
- فن (Arts)
- تكنولوجيا (Technology)

**Technical Details**:
- Scrapes section listing pages with infinite scroll
- Extracts images from article pages
- Dual date extraction (card-level + article-level)
- Noise removal (footers, ads, related articles)
- Output: `raw/arabic/youm7/youm7_YYYYMMDD_HHMMSS.json`

**Key Features**:
- Aggressive scrolling (20 scrolls per section)
- Image fallback logic (card → article → placeholder)
- Cookie text detection and removal

---

### 3. **Al-Gomhuria (gomhuria/)** 🇪🇬

**Source**: https://www.gomhuriaonline.com  
**Method**: Selenium + BeautifulSoup  
**Language**: Arabic  

**Categories Scraped**:
- أخبار (News)
- تكنولوجيا (Technology)

**Technical Details**:
- Pagination support (5 pages per section)
- Strict URL pattern matching (`/Gomhuria/\d+\.html$`)
- Multi-detail-block content merging
- Junk phrase removal (share widgets, follow buttons)
- Output: `raw/arabic/gomhuria/gomhuria_YYYYMMDD_HHMMSS.json`

**Unique Approach**:
- Combines multiple content `<div class="DetialsNews">` blocks
- Regex-based article URL validation
- Pagination via URL template (`/Page/{page}/`)

---

### 4. **The Guardian (guardian/)** 🇬🇧

**Source**: [https://content.guardianapis.com ](https://open-platform.theguardian.com/) 
**Method**: Official API  
**Language**: English  

**Categories Scraped**:
- World
- Business
- Technology
- Culture
- Travel

**Technical Details**:
- Uses Guardian Content API
- Fetches full article text directly
- Paginated requests (50 items/page, max 4 pages)
- Hard limit: 300 most recent articles
- Output: `raw/english/theguardian/theguardian_YYYYMMDD_HHMMSS.json`

**Schema Normalization**:
```python
{
    "source": "theguardian",
    "language": "en",
    "category": "world",
    "title": "...",
    "url": "...",
    "summary": "trailText or standfirst",
    "full_text": "bodyText",
    "image_url": "thumbnail",
    "published_date": "formatted datetime",
    "scraped_at": "ISO timestamp"
}
```

---

### 5. **BBC News (BBC/)** 🇬🇧

**Source**: https://www.bbc.com/ 
**Method**: RSS Feeds + AMP Pages  
**Language**: English  

**Categories Scraped**:
- World
- Business
- Technology
- Science & Environment
- Health

**Technical Details**:
- Parses RSS XML feeds
- Fetches AMP versions for clean content
- Extracts Open Graph images
- Output: `raw/english/bbc/bbc_YYYYMMDD_HHMMSS.json`

**Key Strategy**:
- AMP URLs (`url + "/amp"`) provide cleaner HTML
- Fallback to `<main>` tag if `<article>` missing
- Skips video/live blog URLs

---

### 6. **New York Times (nyt/)** 🇺🇸

**Source**: https://developer.nytimes.com/apis
**Method**: Official API (Top Stories + Most Popular)  
**Language**: English  

**Categories Scraped**:
- World
- Home
- Politics
- Business
- Technology

**Technical Details**:
- Combines Top Stories API + Most Popular API
- Multiple popularity metrics: viewed, shared, emailed (1 & 7 days)
- Automatic deduplication by URL
- Output: `raw/english/newyork_times/nyt_YYYYMMDD_HHMMSS.json`

**Note**: NYT API does not provide full article text (only abstracts)

---

## 🚀 Deployment

### Prerequisites

```bash
# Environment Variables Required
AWS_BUCKET_NAME=your-s3-bucket
AWS_REGION=your-region
NYT_API_KEY=your-nyt-key
GUARDIAN_API_KEY=your-guardian-key
```

### Local Testing

```bash
# Test individual scraper
cd Scrapers/ahram
docker build -t ahram-scraper .
docker run --env-file ../../.env ahram-scraper
```

### AWS ECS Deployment

Each scraper is deployed as a separate ECS Task Definition.


```json
{
  "Type": "Parallel",
  "Branches": [
    {"StartAt": "ScrapeGomhuria", ...},
    {"StartAt": "ScrapeYoum7", ...},
    {"StartAt": "ScrapeAhram", ...},
    {"StartAt": "ScrapeGuardian", ...},
    {"StartAt": "ScrapeBBC", ...},
    {"StartAt": "ScrapeNYT", ...}
  ]
}
```

---

## 📊 Output Schema

All scrapers follow a unified JSON schema:

```json
{
  "source": "string",
  "language": "ar|en",
  "category": "string",
  "title": "string",
  "url": "string (unique)",
  "summary": "string",
  "full_text": "string",
  "image_url": "string|null",
  "published_date": "ISO 8601 string",
  "scraped_at": "ISO 8601 string"
}
```

### Storage Structure

```
s3://your-bucket/
└── raw/
    ├── arabic/
    │   ├── ahram/
    │   │   ├── ahram_20250528_120000.json
    │   │   └── seen_links.json
    │   ├── youm7/
    │   └── gomhuria/
    └── english/
        ├── theguardian/
        ├── bbc/
        └── newyork_times/
```

---


---

## 📈 Performance Metrics

| Scraper | Avg Runtime | Articles/Run | API Calls |
|---------|-------------|--------------|-----------|
| Ahram | 8-12 min | 50-100 | N/A |
| Youm7 | 10-15 min | 60-120 | N/A |
| Gomhuria | 6-10 min | 30-60 | N/A |
| Guardian | 2-3 min | 200-300 | ~20 |
| BBC | 3-5 min | 50-80 | ~5 |
| NYT | 1-2 min | 100-200 | ~10 |

---

## 🔄 Maintenance

### Adding a New Source

1. Create new folder: `Scrapers/newsource/`
2. Implement scraper following existing patterns
3. Add Dockerfile with required dependencies
4. Update Step Functions definition
5. Add ECS Task Definition 

### Updating Existing Scraper

1. Modify scraper logic in `source_scraper.py`
2. Test locally with Docker
3. Rebuild image: `docker build -t source-scraper:v2 .`
4. Push to ECR and update ECS task

---

## 📝 Notes

- **Selenium Scrapers** (Ahram, Youm7, Gomhuria): Require Chromium installed in container
- **API Scrapers** (Guardian, NYT): Require API keys in environment
- **RSS Scraper** (BBC): No authentication needed
- **Seen Links**: Stored in S3 to prevent re-scraping (48-hour window)

---
