import os
import json
import time
import datetime
import boto3
import logging
import pytz
import re
import numpy as np
from dateutil import parser
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from llama_cpp import Llama 
from dotenv import load_dotenv

# ===============================
# LOGGING
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("english_pipeline")

# ===============================
# CONFIG
# ===============================
load_dotenv()

BUCKET = os.getenv("AWS_BUCKET_NAME", "sentiment-data-lake")
RAW_PREFIX = "raw/english/"
OUT_PREFIX = "processed/english/"
SEEN_LINKS_KEY = "processed/english/seen_links.json"

# AI Model Settings
MODEL_PATH = "/app/model.gguf"

s3 = boto3.client("s3")

# ===============================
# LOAD LOCAL BRAIN (QWEN)
# ===============================
logger.info("🧠 Loading Local AI Model (Qwen 2.5)...")
try:
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=2048,
        n_threads=2, 
        verbose=False
    )
    logger.info("✅ Model Loaded!")
except Exception as e:
    logger.error(f"❌ Failed to load model: {e}")
    raise e

# ===============================
# HELPERS
# ===============================
def normalize_date(dt_str):
    """Parses English dates to ISO 8601 UTC"""
    if not dt_str: return None
    try:
        dt = parser.parse(str(dt_str))
        # If timezone naive, assume UTC (Guardian/BBC usually provide TZ)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.isoformat()
    except:
        return None

def list_scraper_subfolders(prefix):
    folders = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix, Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            folders.append(cp["Prefix"].replace(prefix, "").strip("/"))
    return folders

def list_json_files(prefix):
    files = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".json") and "seen" not in obj["Key"].lower():
                files.append({"Key": obj["Key"], "LastModified": obj["LastModified"]})
    return files

def load_raw_articles():
    articles = []
    folders = list_scraper_subfolders(RAW_PREFIX)
    logger.info(f"Scrapers found: {folders}")
    
    for folder in folders:
        prefix = f"{RAW_PREFIX}{folder}/"
        files = list_json_files(prefix)
        if not files: continue
        
        files.sort(key=lambda x: x["LastModified"], reverse=True)
        latest = files[0]["Key"]
        
        logger.info(f"Reading: {latest}")
        raw = s3.get_object(Bucket=BUCKET, Key=latest)
        try:
            data = json.loads(raw["Body"].read())
            
            # Handle dict (single item) vs list (multiple items)
            items = data if isinstance(data, list) else [data]
            
            for a in items:
                if "full_text" in a or "summary" in a:
                    # Normalize dates immediately
                    a["published_date"] = normalize_date(a.get("published_date"))
                    a["scraped_at"] = normalize_date(a.get("scraped_at"))
                    articles.append(a)
        except Exception as e:
            logger.error(f"Error reading {latest}: {e}")
            continue
            
    return articles

def load_seen_links():
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=SEEN_LINKS_KEY)
        return set(json.loads(obj["Body"].read().decode()))
    except: return set()

def save_seen_links(seen):
    s3.put_object(Bucket=BUCKET, Key=SEEN_LINKS_KEY, Body=json.dumps(list(seen)), ContentType="application/json")

def save_to_s3(articles):
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    key = f"{OUT_PREFIX}processed_english_{ts}.json"
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(articles), ContentType="application/json")
    logger.info(f"Saved {len(articles)} items to {key}")

# ===============================
# DEDUPLICATION (TF-IDF)
# ===============================
def deduplicate_articles(articles, threshold=0.85):
    if len(articles) <= 1: return articles
    
    # Use title + summary for dedupe signature
    texts = [(a.get("title") or "") + " " + (a.get("summary") or "") for a in articles]
    
    try:
        vectors = TfidfVectorizer().fit_transform(texts)
        sim_matrix = cosine_similarity(vectors)
        keep = []
        removed = set()
        for i in range(len(articles)):
            if i in removed: continue
            keep.append(articles[i])
            for j in range(i + 1, len(articles)):
                if sim_matrix[i][j] >= threshold: removed.add(j)
        logger.info(f"Deduplication removed {len(removed)} items.")
        return keep
    except: return articles

# ===============================
# AI ENRICHMENT (LOCAL QWEN)
# ===============================
def enrich_article(article):
    # Prefer full text, fallback to summary
    text_source = article.get("full_text") or article.get("summary") or ""
    if not text_source: return "", "Neutral"

    # SMART TRUNCATION LOGIC
    # If text is huge (e.g. Live Blog), take first 1000 chars + last 500 chars
    # This captures the "Headlines" and the "Latest Updates"
    if len(text_source) > 1500:
        text_input = text_source[:1000] + "\n... [middle removed] ...\n" + text_source[-500:]
    else:
        text_input = text_source

    prompt = f"""<|im_start|>system
You are a senior news analyst.
1. Summarize the text in 3 concise sentences. Focus on the main event.
2. Classify sentiment as: Positive, Neutral, or Negative.

Output format:
SUMMARY: ...
SENTIMENT: ...
<|im_end|>
<|im_start|>user
Text:
{text_input}
<|im_end|>
<|im_start|>assistant
"""
    try:
        # Increased context window slightly to 2048 in initialization
        # Max tokens 200 is enough for summary
        output = llm(prompt, max_tokens=200, stop=["<|im_end|>"], temperature=0.1)
        txt = output["choices"][0]["text"].strip()
        
        summary = ""
        sentiment = "Neutral"
        
        if "SUMMARY:" in txt:
            parts = txt.split("SUMMARY:")[1].split("SENTIMENT:")
            summary = parts[0].strip()
            if len(parts) > 1:
                sentiment = parts[1].strip()
        elif "SENTIMENT:" in txt:
             sentiment = txt.split("SENTIMENT:")[1].strip()
            
        # Fallback if AI returns original text as summary (rare hallucination)
        if not summary or len(summary) < 10:
             summary = text_source[:300] + "..."
            
        return summary, sentiment
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "", "Neutral"

# ===============================
# MAIN 
# ===============================
def main():
    logger.info("Starting English Pipeline...")
    
    articles = load_raw_articles()
    seen = load_seen_links()
    
    new_arts = [a for a in articles if a.get("url") not in seen]
    logger.info(f"New articles: {len(new_arts)}")
    
    if not new_arts: return

    new_arts = deduplicate_articles(new_arts)
    
    enriched = []
    for i, a in enumerate(new_arts):
        logger.info(f"Enriching {i+1}/{len(new_arts)}... ({a.get('source')})")
        summary, sentiment = enrich_article(a)
        a["summary"] = summary
        a["sentiment"] = sentiment
        enriched.append(a)
    
    save_to_s3(enriched)
    
    for a in enriched:
        if a.get("url"): seen.add(a["url"])
    
    save_seen_links(seen)
    logger.info("Pipeline Finished.")

if __name__ == "__main__":
    main()