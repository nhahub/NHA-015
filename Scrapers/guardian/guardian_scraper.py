"""
guardian_scraper.py

Fetches full-text articles from The Guardian via their API,
normalizes them to the project's unified schema, deduplicates and uploads
a single combined JSON to S3 under raw/english/theguardian/.
"""

import requests
import json
import boto3
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# S3 path requested
S3_PATH = "raw/english/theguardian/"

# Guardian API base
GUARDIAN_SEARCH_URL = "https://content.guardianapis.com/search"

# boto3 client (Lambda: uses IAM role)
s3 = boto3.client("s3", region_name=AWS_REGION)


# ---------------------------
# Helper: format published date into human-friendly string
# ---------------------------
def format_published_date(iso_ts):
    """
    iso_ts: ISO string like "2025-10-22T15:17:57Z"
    returns human-friendly UTC string: "Wednesday, 22 October 2025 15:17:57"
    """
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return dt.strftime("%A, %d %B %Y %H:%M:%S")
    except Exception:
        
        return iso_ts


# ---------------------------
# Helper: normalize Guardian article
# ---------------------------
def normalize_guardian_item(item):
 
    fields = item.get("fields", {}) or {}

    
    summary = (
        fields.get("trailText")
        or fields.get("standfirst")
        or fields.get("bodyText")[:180] + "..." if fields.get("bodyText") else None
    )

    # Full text 
    full_text = fields.get("bodyText") or fields.get("body") or None

    # Thumbnail image
    image_url = fields.get("thumbnail") or None

    # Determine author
    author = None
    for t in item.get("tags", []):
        if t.get("type") == "contributor":
            author = t.get("webTitle")
            break
    if not author:
        author = fields.get("byline")

    # Section as category
    category = item.get("sectionName") or item.get("section") or None

    # Published timestamp
    published_iso = item.get("webPublicationDate")
    published_date = format_published_date(published_iso)

    return {
        "source": "theguardian",
        "language": "en",
        "category": category,
        "title": item.get("webTitle"),
        "url": item.get("webUrl"),

        
        "summary": summary,

        "full_text": full_text,
        "image_url": image_url,
        "published_date": published_date,
        "scraped_at": datetime.now(timezone.utc).isoformat()
    }



# ---------------------------
# Fetch guardian articles
# ---------------------------
def fetch_guardian_articles(sections=None, page_size=50, max_pages=5, order_by="newest", keep_fields=True):
   
    if not GUARDIAN_API_KEY:
        raise ValueError("GUARDIAN_API_KEY missing in .env")

    normalized_articles = []

    sections_to_query = sections or [None]

    for section in sections_to_query:
        for page in range(1, max_pages + 1):
            params = {
                "api-key": GUARDIAN_API_KEY,
                "page-size": page_size,
                "page": page,
                "order-by": order_by,
                "show-tags": "contributor"
            }
            if keep_fields:
                params["show-fields"] = "all"
            if section:
                params["section"] = section

            try:
                resp = requests.get(GUARDIAN_SEARCH_URL, params=params, timeout=15)
            except Exception as e:
                print(f"Request error (section={section} page={page}): {e}")
                time.sleep(1)
                continue

            if resp.status_code != 200:
                print(f"Non-200 response for section={section}, page={page}: {resp.status_code}")
                time.sleep(1)
                continue

            try:
                data = resp.json()
            except Exception as e:
                print("JSON parse error:", e)
                time.sleep(1)
                continue

            response_obj = data.get("response", {})
            results = response_obj.get("results", [])

            for item in results:
                normalized = normalize_guardian_item(item)
                normalized_articles.append(normalized)

            # Pagination control
            current_page = response_obj.get("currentPage", page)
            pages_total = response_obj.get("pages", page)
            if current_page >= pages_total:
                break

            time.sleep(0.2)

    return normalized_articles


# ---------------------------
# Deduplicate by URL
# ---------------------------
def dedupe_by_url(articles):
    seen = {}
    for a in articles:
        url = a.get("url")
        if not url:
            continue
        if url not in seen:
            seen[url] = a
    return list(seen.values())


# ---------------------------
# Save to S3
# ---------------------------
def save_to_s3(data):
    # timezone-aware UTC timestamp for filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    key = f"{S3_PATH}theguardian_{timestamp}.json"

    s3.put_object(
        Bucket=AWS_BUCKET_NAME,
        Key=key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType="application/json"
    )
    return key


# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    if not GUARDIAN_API_KEY:
        raise ValueError("GUARDIAN_API_KEY not set in .env")
    if not AWS_BUCKET_NAME:
        raise ValueError("AWS_BUCKET_NAME not set in .env")

    
    sections = ["world", "business", "technology", "culture", "travel"]

    print("Fetching Guardian articles for sections:", sections)
    raw_articles = fetch_guardian_articles(
        sections=sections,
        page_size=50,
        max_pages=4,
        order_by="newest"
    )

    print("Total raw articles fetched:", len(raw_articles))

    
    articles = dedupe_by_url(raw_articles)
    print("After dedupe by URL:", len(articles))

    
    MAX_LIMIT = 300  #it gets 1000 article but we only want to keep 300 most recent ones
    articles = articles[:MAX_LIMIT]
    print(f"After applying hard limit ({MAX_LIMIT}):", len(articles))

    print("Uploading to S3...")
    s3_key = save_to_s3(articles)

    print("Done. Count:", len(articles))
    print("S3 key:", s3_key)
