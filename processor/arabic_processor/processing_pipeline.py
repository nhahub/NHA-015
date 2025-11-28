import os
import json
import time
import datetime
import re
import boto3
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from dateutil import parser
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ===============================
# LOGGING
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("arabic_pipeline")

load_dotenv()

# ===============================
# CONFIGURATION
# ===============================
BUCKET = os.getenv("AWS_BUCKET_NAME")
RAW_PREFIX = "raw/arabic/"
OUT_PREFIX = "processed/arabic/"
SEEN_LINKS_KEY = "processed/arabic/seen_links.json"

# ===============================
# DYNAMIC KEY LOADER (THE FIX)
# ===============================
API_KEYS = []

# 1. Check for standard key
k_main = os.getenv("GEMINI_API_KEY")
if k_main: API_KEYS.append(k_main)

# 2. Check for numbered keys (1 to Infinity)
i = 1
while True:
    k = os.getenv(f"GEMINI_API_KEY_{i}")
    if not k:
        break # Stop searching when a number is missing
    API_KEYS.append(k)
    i += 1

if not API_KEYS:
    raise RuntimeError("No GEMINI_API_KEYs found in environment variables!")

logger.info(f"Loaded {len(API_KEYS)}")

# Adjust limit based on key count 

MAX_ARTICLES_PER_RUN = 30 * len(API_KEYS)
logger.info(f"Dynamic Limit set to: {MAX_ARTICLES_PER_RUN} articles/run")

MODEL_NAME = "gemini-2.5-flash"
BATCH_SIZE = 10
BATCH_SLEEP = 65

s3 = boto3.client("s3")

# ===============================
# HELPERS
# ===============================
AR_MONTHS = {
    "يناير": "January", "فبراير": "February", "مارس": "March", "أبريل": "April",
    "ابريل": "April", "مايو": "May", "يونيو": "June", "يوليو": "July",
    "أغسطس": "August", "اغسطس": "August", "سبتمبر": "September", "أكتوبر": "October",
    "اكتوبر": "October", "نوفمبر": "November", "ديسمبر": "December",
}
AR_DAYS = ["السبت","الأحد","الاحد","الاثنين","الإثنين","الثلاثاء","الاربعاء","الأربعاء","الخميس","الجمعة"]

def normalize_date(dt_str):
    if not dt_str: return None
    s = str(dt_str).strip()
    for d in AR_DAYS: s = s.replace(d + "،", "").replace(d, "")
    s = s.replace("ص", "AM").replace("م", "PM").replace("صباحا", "AM").replace("مساء", "PM")
    for ar, en in AR_MONTHS.items(): s = s.replace(ar, en)
    if "|" in s: s = s.replace("|", " ").replace("-", "/")
    try:
        cleaned = re.sub(r"[^\dT:\-+Z/ :APM]", "", s)
        dt = parser.parse(cleaned)
        return dt.strftime("%A, %d %B %Y – %H:%M")
    except: return None

def clean_text(t):
    NOISE = ["تم التصميم والتطوير بواسطة", "الموضوعات المتعلقة", "اقرأ أيضا"]
    if not t: return ""
    for p in NOISE: t = t.replace(p, "")
    return t.strip()

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

def load_raw_articles_most_recent():
    articles = []
    folders = list_scraper_subfolders(RAW_PREFIX)
    for folder in folders:
        prefix = f"{RAW_PREFIX}{folder}/"
        files = list_json_files(prefix)
        if not files: continue
        files.sort(key=lambda x: x["LastModified"], reverse=True)
        latest = files[0]["Key"]
        
        raw = s3.get_object(Bucket=BUCKET, Key=latest)
        try:
            data = json.loads(raw["Body"].read())
            items = data if isinstance(data, list) else [data]
            for a in items:
                if "full_text" in a:
                    a["full_text"] = clean_text(a["full_text"])
                    if not a.get("scraped_at"): a["scraped_at"] = datetime.datetime.utcnow().isoformat()
                    a["published_date"] = normalize_date(a.get("published_date"))
                    a["scraped_at"] = normalize_date(a.get("scraped_at"))
                    articles.append(a)
        except: continue
    return articles

def load_seen_links():
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=SEEN_LINKS_KEY)
        return set(json.loads(obj["Body"].read().decode("utf-8")))
    except: return set()

def save_seen_links(seen):
    s3.put_object(Bucket=BUCKET, Key=SEEN_LINKS_KEY, Body=json.dumps(list(seen), ensure_ascii=False).encode("utf-8"), ContentType="application/json")

def save_to_s3(articles):
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    key = f"{OUT_PREFIX}processed_arabic_{ts}.json"
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(articles, ensure_ascii=False, indent=2).encode("utf-8"), ContentType="application/json")
    logger.info(f"Saved → s3://{BUCKET}/{key}")

def deduplicate_articles(articles, threshold=0.85):
    if len(articles) <= 1: return articles
    texts = [a["full_text"] for a in articles]
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
        return keep
    except: return articles

# ===============================
# JSON REPAIR & AI ENRICHMENT
# ===============================
def generate_with_rotation(prompt):
    for index, key in enumerate(API_KEYS):
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.warning(f"Key {index+1} Failed: {e}")
            continue
    return None

def clean_and_repair_json(text):
    if not text: return None
    text = text.strip()
    if "```" in text:
        text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except:
        pass
    # Fallback Regex
    summary_match = re.search(r'"summary"\s*:\s*"(.*?)"', text, re.DOTALL)
    sentiment_match = re.search(r'"sentiment"\s*:\s*"(.*?)"', text, re.DOTALL)
    
    summary = summary_match.group(1) if summary_match else ""
    sentiment = sentiment_match.group(1) if sentiment_match else "Neutral"
    summary = summary.replace('"', "'")
    
    return {"summary": summary, "sentiment": sentiment}

def enrich_article(article):
    full_text = article.get("full_text", "").strip()
    if not full_text: return "", "Neutral"

    prompt = f"""
    You are an expert Arabic news analyst.
    Analyze the following text and provide a structured JSON output.
    
    TEXT:
    {full_text[:3000]}

    OUTPUT FORMAT (Strict JSON):
    {{
        "summary": "Write a comprehensive summary in Arabic (1-2 sentences). Use purely Arabic characters.",
        "sentiment": "Positive/Neutral/Negative"
    }}
    """

    txt = generate_with_rotation(prompt)
    data = clean_and_repair_json(txt)

    if not data: 
        return "", "Neutral"

    return data.get("summary", ""), data.get("sentiment", "Neutral")

# ===============================
# MAIN
# ===============================
def main():
    logger.info(f"Starting Arabic Pipeline (Keys: {len(API_KEYS)})...")
    
    articles = load_raw_articles_most_recent()
    seen = load_seen_links()
    
    new_arts = [a for a in articles if a.get("url") not in seen]
    logger.info(f"Found {len(new_arts)} unseen articles.")
    
    new_arts = deduplicate_articles(new_arts)

    if len(new_arts) > MAX_ARTICLES_PER_RUN:
        logger.info(f"Capping at {MAX_ARTICLES_PER_RUN}")
        new_arts = new_arts[:MAX_ARTICLES_PER_RUN]

    if not new_arts:
        logger.info("No articles to process.")
        return

    enriched = []
    total = len(new_arts)

    for i, a in enumerate(new_arts):
        logger.info(f"Processing {i+1}/{total}...")
        
        summary, sentiment = enrich_article(a)
        a["summary"] = summary
        a["sentiment"] = sentiment
        enriched.append(a)
        
        if (i + 1) % BATCH_SIZE == 0 and (i + 1) < total:
            time.sleep(BATCH_SLEEP)
        else:
            time.sleep(1) 

    save_to_s3(enriched)
    
    for a in enriched:
        if a.get("url"): seen.add(a["url"])
        
    save_seen_links(seen)
    logger.info("Done.")

if __name__ == "__main__":
    main()