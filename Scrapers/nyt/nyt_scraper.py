import requests
import json
import boto3
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

# --------------------------
# LOGGING CONFIG
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("nyt_scraper")

# Load env
load_dotenv()

NYT_API_KEY = os.getenv("NYT_API_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

if not NYT_API_KEY:
    raise RuntimeError("NYT_API_KEY is missing in .env")

S3_PATH = "raw/english/newyork_times/"

s3 = boto3.client("s3", region_name=AWS_REGION)


# ---------------------------
# Normalize NYT -> Unified Schema
# ---------------------------
def normalize_nyt_item(item, category):
    title = item.get("title")
    url = item.get("url")
    summary = item.get("abstract")
    published = item.get("published_date")

    # image extraction logic
    image_url = None
    if item.get("multimedia"):
        # Top Stories format
        image_url = item["multimedia"][0].get("url")
    elif item.get("media"):
        # Most Popular format
        try:
            image_url = item["media"][0]["media-metadata"][-1]["url"]
        except:
            pass

    normalized = {
        "source": "nytimes",
        "language": "en",
        "category": category,
        "title": title,
        "url": url,
        "summary": summary,
        "full_text": None, # NYT API does not provide full text
        "image_url": image_url,
        "published_date": published,
        "scraped_at": datetime.now(timezone.utc).isoformat()
    }
    return normalized


# ---------------------------
# Fetch NYT Top Stories
# ---------------------------
def fetch_top_stories(sections):
    articles = []
    for section in sections:
        logger.info(f"Fetching Top Stories: {section}")
        url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json"
        params = {"api-key": NYT_API_KEY}

        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code != 200:
                logger.error(f"Failed {section}: {res.status_code}")
                continue
                
            data = res.json()
            for item in data.get("results", []):
                articles.append(normalize_nyt_item(item, section))
                
        except Exception as e:
            logger.error(f"Error fetching {section}: {e}")

    return articles


# ---------------------------
# Fetch NYT Most Popular
# ---------------------------
def fetch_most_popular():
    articles = []
    logger.info("Fetching Most Popular articles...")

    for cat in ["viewed", "shared", "emailed"]:
        for per in [1, 7]: # 1 day and 7 days
            url = f"https://api.nytimes.com/svc/mostpopular/v2/{cat}/{per}.json"
            params = {"api-key": NYT_API_KEY}

            try:
                res = requests.get(url, params=params, timeout=10)
                if res.status_code != 200:
                    continue

                data = res.json()
                for item in data.get("results", []):
                    category = item.get("section", "general")
                    articles.append(normalize_nyt_item(item, category))
            except Exception as e:
                logger.error(f"Error fetching popular {cat}/{per}: {e}")

    return articles


# ---------------------------
# Deduplicate by URL
# ---------------------------
def dedupe_by_url(articles):
    # Using dictionary comprehension to keep the last occurrence of a URL
    unique = list({a["url"]: a for a in articles if a.get("url")}.values())
    logger.info(f"Deduplication: {len(articles)} -> {len(unique)} unique articles.")
    return unique


# ---------------------------
# Save to S3
# ---------------------------
def save_to_s3(data):
    if not data:
        logger.warning("No data to save.")
        return None
        
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    key = f"{S3_PATH}nyt_{timestamp}.json"

    try:
        s3.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=key,
            Body=json.dumps(data, ensure_ascii=False, indent=2),
            ContentType="application/json"
        )
        logger.info(f"Successfully uploaded to {key}")
        return key
    except Exception as e:
        logger.error(f"S3 Upload Failed: {e}")
        return None


# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    logger.info("Starting NYT Scraper...")

    top_news = fetch_top_stories(["world", "home", "politics", "business", "technology"])
    popular_news = fetch_most_popular()

    combined = dedupe_by_url(top_news + popular_news)

    if combined:
        save_to_s3(combined)
    
    logger.info("NYT Scraper Finished.")