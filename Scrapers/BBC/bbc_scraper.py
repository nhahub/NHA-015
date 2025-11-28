import requests
from bs4 import BeautifulSoup
import json
import datetime
import boto3
import logging
from dotenv import load_dotenv
import os
import time

# ---------------- LOGGING CONFIG ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bbc_scraper")

# ---------------- LOAD .ENV ----------------
load_dotenv()

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

if not AWS_BUCKET_NAME:
    raise RuntimeError("AWS_BUCKET_NAME is missing in .env")

# S3 Paths
S3_PREFIX = "raw/english/bbc/"
S3_SEEN_LINKS_KEY = f"{S3_PREFIX}seen_links.json"

# ---------------- BBC RSS FEEDS ----------------
BBC_FEEDS = {
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "health": "https://feeds.bbci.co.uk/news/health/rss.xml"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

# ---------------- AWS HELPERS ----------------
def init_s3():
    return boto3.client("s3", region_name=AWS_REGION)

def load_seen_links(s3):
    try:
        obj = s3.get_object(Bucket=AWS_BUCKET_NAME, Key=S3_SEEN_LINKS_KEY)
        data = json.loads(obj["Body"].read().decode())
        logger.info(f"Loaded {len(data)} seen links from S3.")
        return set(data)
    except s3.exceptions.NoSuchKey:
        logger.info("No previous seen links found. Starting fresh.")
        return set()
    except Exception as e:
        logger.warning(f"Could not load seen links: {e}")
        return set()

def save_seen_links(s3, seen):
    try:
        s3.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=S3_SEEN_LINKS_KEY,
            Body=json.dumps(list(seen)),
            ContentType="application/json"
        )
        logger.info(f"Updated seen_links.json ({len(seen)} total).")
    except Exception as e:
        logger.error(f"Failed to save seen links: {e}")

def upload_to_s3(s3, data, key):
    try:
        s3.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=key,
            Body=json.dumps(data, ensure_ascii=False, indent=2),
            ContentType="application/json"
        )
        logger.info(f"Successfully uploaded {len(data)} articles to {key}")
    except Exception as e:
        logger.error(f"S3 Upload failed: {e}")

# ---------------- HELPERS ----------------
def get_amp_url(url: str) -> str:
    """BBC AMP URL format"""
    if url.endswith("/"):
        return url + "amp"
    return url + "/amp"

def extract_full_text_amp(url):
    try:
        amp_url = get_amp_url(url)
        res = requests.get(amp_url, headers=HEADERS, timeout=10)
        
        if res.status_code != 200:
            logger.warning(f"Failed to fetch AMP: {res.status_code} - {amp_url}")
            return "", ""

        soup = BeautifulSoup(res.text, "html.parser")

        article_tag = soup.find("article")
        if not article_tag:
            # Fallback: try main content div
            article_tag = soup.find("main")
        
        if not article_tag:
            return "", ""

        paragraphs = [p.get_text(strip=True) for p in article_tag.find_all("p")]
        full_text = " ".join(paragraphs)

        og = soup.find("meta", property="og:image")
        image_url = og["content"] if og else ""

        return full_text.strip(), image_url
    except Exception as e:
        logger.warning(f"Error extracting content from {url}: {e}")
        return "", ""

# ---------------- MAIN SCRAPER ----------------
def scrape_bbc_amp(seen_links):
    all_articles = []

    for category, feed_url in BBC_FEEDS.items():
        logger.info(f"Fetching RSS for: {category}")

        try:
            rss = requests.get(feed_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(rss.text, "xml")
            items = soup.find_all("item")
            logger.info(f"Found {len(items)} items in RSS.")
        except Exception as e:
            logger.error(f"Failed to fetch RSS {feed_url}: {e}")
            continue

        for item in items[:10]: # Limit to 10 per section to be polite
            title = item.title.text.strip() if item.title else ""
            link = item.link.text.strip() if item.link else ""
            
            if not link or link in seen_links:
                continue

            # Skip irrelevant pages
            if "/live/" in link or "/av/" in link or "/videos/" in link:
                continue

            summary_raw = item.description.text if item.description else ""
            summary = BeautifulSoup(summary_raw, "html.parser").get_text().strip()
            published = item.pubDate.text.strip() if item.pubDate else ""

            logger.info(f"Scraping: {title[:50]}...")
            
            full_text, image_url = extract_full_text_amp(link)
            
            if not full_text or len(full_text) < 50:
                continue

            seen_links.add(link)

            article = {
                "source": "bbc",
                "language": "en",
                "category": category,
                "title": title,
                "url": link,
                "summary": summary,
                "full_text": full_text,
                "image_url": image_url,
                "published_date": published,
                "scraped_at": datetime.datetime.utcnow().isoformat()
            }

            all_articles.append(article)
            time.sleep(0.5) # Polite delay

    return all_articles

# ---------------- MAIN ----------------
def main():
    logger.info("Starting BBC AMP scraper...")

    s3 = init_s3()
    seen_links = load_seen_links(s3)

    articles = scrape_bbc_amp(seen_links)

    if not articles:
        logger.info("No new articles scraped this run.")
        return

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    s3_key = f"{S3_PREFIX}bbc_{timestamp}.json"

    upload_to_s3(s3, articles, s3_key)
    save_seen_links(s3, seen_links)

    logger.info("Pipeline finished successfully.")

if __name__ == "__main__":
    main()