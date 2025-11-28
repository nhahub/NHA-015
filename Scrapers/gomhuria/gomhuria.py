import os
import re
import time
import json
import random
import logging
import datetime
from typing import Set, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from dotenv import load_dotenv

import boto3
from botocore.exceptions import ClientError

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ---------------- CONFIG & ENV ----------------
load_dotenv()

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

if not AWS_BUCKET_NAME:
    raise RuntimeError("Set AWS_BUCKET_NAME in .env before running")

# Editable parameters
S3_PREFIX = "raw/arabic/gomhuria/"
S3_SEEN_KEY = f"{S3_PREFIX}seen_links.json"
OUTPUT_PREFIX = S3_PREFIX  

MAX_PAGES_PER_SECTION = 5
MAX_ARTICLES_PER_SECTION = 20
REQUEST_TIMEOUT = 30
PAGE_SLEEP = 1.0
ARTICLE_SLEEP_MIN = 0.8
ARTICLE_SLEEP_MAX = 1.6

BASE_DOMAIN = "https://www.gomhuriaonline.com"
# Section templates (the page index will be replaced by /Page/{page}/)
SECTIONS = {
    "أخبار": "https://www.gomhuriaonline.com/GomhuriaOnline-news/%D8%A3%D8%D9%D8%A8%D8%A7%D8%B1%20%D9%D85%D8%B5%D8%B1/1/Page/{page}/",

    "اخبار_alt": "https://www.gomhuriaonline.com/GomhuriaOnline-news/%D8%A3%D8%D8%A8%D8%A7%D8%B1%20%D9%D85%D8%B5%D8%B1/1/Page/{page}/",
    "تكنولوجيا": "https://www.gomhuriaonline.com/GomhuriaOnline-news/%D8%AA%D9%83%D9%86%D9%88%D9%84%D9%88%D8%AC%D9%8A%D8%A7%20%D8%A7%D9%84%D9%85%D8%B9%D9%84%D9%88%D9%85%D8%A7%D8%AA/16/Page/{page}/"
}

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("gomhuria_scraper")

# ---------------- UTILITIES ----------------
ARTICLE_URL_RE = re.compile(r"/Gomhuria/\d+\.html$")  # accept only urls ending with /Gomhuria/<digits>.html same as sections url pattern

JUNK_PHRASES = [
    "تابع بوابة الجمهورية", "اترك تعليق", "التصنيفات", "يمكنك مشاركة الخبر", "ShareFacebook",
    "ShareFacebookTwitterWhatsApp", "تابعونا", "تابع", "جوجل نيوز", "Google News", "Subscribe",
    "تابع بوابة", "تابع بوابة الجمهورية اون لاين", "تابع بوابة الجمهورية", "تابع بوابة",
    "مشاركة", "ترك تعليق"
]

def normalize_url(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return urljoin(BASE_DOMAIN, href)
    if not href.startswith("http"):
        return urljoin(BASE_DOMAIN, href)
    return href

def is_valid_article_url(href: str) -> bool:
    if not href:
        return False
    href = href.strip()
    
    try:
        parsed = urlparse(href)
    except Exception:
        return False
    if not parsed.path:
        return False
    
    path = parsed.path
    if ARTICLE_URL_RE.search(path):
        return True
    return False

def cleanup_text(t: str) -> str:
    if not t:
        return ""
    # Remove multiple whitespace & control chars
    t = re.sub(r"\s+", " ", t).strip()
    # Remove junk phrases anywhere in the text
    for p in JUNK_PHRASES:
        t = t.replace(p, " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t
# ---------------- TEXT SUMMARIZATION ---------------- (intial summary will be modifed later in process stage)
#it takes the first max_sentences from the text after splitting by Arabic punctuation so it is not a real summarization but to not keep the summary fild empty i did this

def generate_summary(text: str, max_sentences: int = 3) -> str:
    if not text:
        return ""
    # Split by Arabic punctuation 
    sentences = re.split(r'(?<=[\.\?!\؟\!])\s+|\n+', text)
    if len(sentences) <= max_sentences:
        return cleanup_text(" ".join(sentences)).strip()[:800]
    
    chosen = " ".join(s.strip() for s in sentences if s.strip())[:1600]
    
    pieces = re.split(r'(?<=[\.\?!\؟\!])\s+', chosen)
    return cleanup_text(" ".join(pieces[:max_sentences]))

# ---------------- S3 HELPERS ----------------
def init_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)

def load_seen_links_from_s3(s3_client) -> Set[str]:
    try:
        resp = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=S3_SEEN_KEY)
        data = json.loads(resp["Body"].read().decode("utf-8"))
        logger.info(f"Loaded {len(data)} seen links from S3")
        return set(data)
    except s3_client.exceptions.NoSuchKey:
        logger.info("No previous seen_links.json found (first run)")
        return set()
    except Exception as e:
        logger.warning(f"Failed to load seen links from S3: {e}")
        return set()

def save_seen_links_to_s3(s3_client, seen_links: Set[str]):
    try:
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=S3_SEEN_KEY,
            Body=json.dumps(list(seen_links), ensure_ascii=False, indent=2),
            ContentType="application/json"
        )
        logger.info(f"Saved {len(seen_links)} seen links to S3")
    except Exception as e:
        logger.error(f"Failed to save seen links: {e}")

def upload_articles_to_s3(s3_client, articles: List[dict]) -> bool:
    if not articles:
        logger.info("No articles to upload")
        return True
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    key = f"{OUTPUT_PREFIX}gomhuria_{ts}.json"
    try:
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=key,
            Body=json.dumps(articles, ensure_ascii=False, indent=2),
            ContentType="application/json"
        )
        logger.info(f"Uploaded {len(articles)} articles to s3://{AWS_BUCKET_NAME}/{key}")
        return True
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        return False

# ---------------- SELENIUM ----------------
def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # ---------------------------------------------------------
    # DOCKER CONFIGURATION
    # ---------------------------------------------------------
    chrome_bin = os.environ.get("CHROME_BIN")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")

    if chrome_bin and chromedriver_path:
        
        options.binary_location = chrome_bin
        service = Service(executable_path=chromedriver_path)
    else:
       
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())

    
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.set_page_load_timeout(REQUEST_TIMEOUT)
    return driver

# ---------------- EXTRACTION HELPERS ----------------
def extract_image_from_soup(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return normalize_url(og["content"])
    
    img = soup.select_one("img.img-fluid, div.carousel-inner img, img")
    if img and img.get("src"):
        return normalize_url(img.get("src"))
    return ""

def extract_published_date(soup: BeautifulSoup) -> str:
    
    meta_dt = soup.find("meta", {"property": "article:published_time"}) or soup.find("meta", {"name": "pubdate"})
    if meta_dt and meta_dt.get("content"):
        return meta_dt["content"]
    
    possible = soup.find(lambda t: t.name in ["time", "span", "div"] and t.get_text() and ("202" in t.get_text() or "نشر" in t.get_text() or "20" in t.get_text()))
    if possible:
        return possible.get_text(strip=True)
    return ""

def extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find(["h1"])
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    
    h3 = soup.find("h3")
    if h3 and h3.get_text(strip=True):
        return h3.get_text(strip=True)
    return ""

def merge_detail_blocks(soup: BeautifulSoup) -> str:
    """
    Collects all <div class="DetialsNews"> blocks, concatenates their text while removing
    junk blocks like youtube widget, carousels, google-news segments, related articles, share widgets.
    """
    
    for sel in ["script", "style", "nav", "header", "footer", "aside", ".YoutubeOneNews", ".YoutubeOneNews",
                ".carousel", ".carousel-inner", ".YoutubeOneNews", ".related-article-inside-body",
                ".masry-new-important-articles", ".masry-now-articles", ".YoutubeOneNews", ".YoutubeOneNews"]:
        for node in soup.select(sel):
            try:
                node.decompose()
            except Exception:
                pass

    parts = []
    
    detail_divs = soup.select("div.DetialsNews")
    if not detail_divs:
        
        possible = soup.select_one("div.article-body, div#content, div.content, article")
        if possible:
            detail_divs = [possible]

    for d in detail_divs:
        # Remove nested nodes that are noise inside the block (inside the article container itself gomhuria adds these things)
        for child_sel in ["div.YoutubeOneNews", "div.youtube", "div.share", "div.social", "div.comments",
                          ".YoutubeOneNews", ".YoutubeOneNews", "aside", ".carousel", ".carousel-inner",
                          ".YoutubeOneNews", "script", "style", ".YoutubeOneNews"]:
            for el in d.select(child_sel):
                try:
                    el.decompose()
                except Exception:
                    pass
        text = d.get_text(" ", strip=True)
        text = cleanup_text(text)
        if text:
            parts.append(text)

    # Combine parts in order
    full = " ".join(parts).strip()
    # Remove any leftovers of unwanted repeated phrases
    for p in JUNK_PHRASES:
        full = full.replace(p, " ")
    full = re.sub(r"\s+", " ", full).strip()
    return full

def extract_article_page(driver, url: str) -> Optional[dict]:
    try:
        driver.get(url)
        time.sleep(random.uniform(0.9, 1.6)) 
        soup = BeautifulSoup(driver.page_source, "lxml")

        # Clean global noisy selectors in page before extraction
        for sel in ["header", "footer", "nav", "aside", ".related-article-inside-body", ".YoutubeOneNews", ".YoutubeOneNews", ".share-widget"]:
            for tag in soup.select(sel):
                try:
                    tag.decompose()
                except Exception:
                    pass

        full_text = merge_detail_blocks(soup)
        if not full_text or len(full_text.split()) < 6:
            # maybe content loaded in other container or split; fall back to article body selector variations
            alt = soup.select_one("div#content, div.article-body, article")
            if alt:
                txt = cleanup_text(alt.get_text(" ", strip=True))
                if txt:
                    full_text = txt

        if not full_text or len(full_text) < 60:
            logger.debug(f"Article full_text too short for {url}")
            return None

        image_url = extract_image_from_soup(soup)
        published_date = extract_published_date(soup)
        title = extract_title(soup)

        summary = generate_summary(full_text, max_sentences=3)
        return {
            "full_text": full_text,
            "image_url": image_url or "",
            "published_date": published_date or "",
            "summary": summary,
            "title": title or ""
        }
    except Exception as e:
        logger.debug(f"extract_article_page error {e} for {url}")
        return None

def find_article_cards_on_listing(soup: BeautifulSoup) -> List[str]:
    """
    Heuristics to find article anchor hrefs on listing pages.
    Only accept hrefs matching our strict pattern.
    """
    anchors = []
    # Common card selectors
    for a in soup.select("a"):
        href = a.get("href")
        if not href:
            continue
        href_norm = normalize_url(href)
        if is_valid_article_url(href_norm):
            anchors.append(href_norm)

    # Additional heuristics: titles inside h3 a or h2 a
    for tag in soup.select("h3 a, h2 a, .title-medium-dark a, .title a"):
        href = tag.get("href")
        if href:
            href_norm = normalize_url(href)
            if is_valid_article_url(href_norm):
                anchors.append(href_norm)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for u in anchors:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique

# ---------------- SCRAPE SECTION ----------------
def scrape_section(driver, section_name: str, section_url_template: str, seen_links: Set[str]) -> List[dict]:
    results = []
    collected = 0
    for page in range(MAX_PAGES_PER_SECTION):
        page_url = section_url_template.format(page=page)
        try:
            logger.info(f"Fetching listing {section_name} page {page}: {page_url}")
            driver.get(page_url)
            time.sleep(PAGE_SLEEP + random.uniform(0.2, 0.8))
            soup = BeautifulSoup(driver.page_source, "lxml")
            # Find article cards
            article_links = find_article_cards_on_listing(soup)
            logger.info(f"Found {len(article_links)} candidate links on page {page}")
            if not article_links:
                # stop pagination early if no articles
                break

            for href in article_links:
                if collected >= MAX_ARTICLES_PER_SECTION:
                    break
                if href in seen_links:
                    logger.debug(f"Skipping seen {href}")
                    continue
                # skip if url path contains non-digit article id
                if not is_valid_article_url(href):
                    logger.debug(f"Rejected by URL filter: {href}")
                    continue
                logger.info(f"Scraping article: {href}")
                article_data = extract_article_page(driver, href)
                if not article_data:
                    logger.info(f"Skipped (no content) {href}")
                    seen_links.add(href)  # mark as seen to avoid reattempts
                    continue

                title = article_data.get("title") or ""
                
                if not title:
                    title_elem = soup.find("a", href=lambda x: x and href in normalize_url(x))
                    if title_elem:
                        title = title_elem.get_text(strip=True)

                item = {
                    "source": "GomhuriaOnline",
                    "language": "ar",
                    "category": section_name,
                    "title": title,
                    "url": href,
                    "summary": article_data.get("summary", ""),
                    "full_text": article_data.get("full_text", ""),
                    "image_url": article_data.get("image_url", ""),
                    "published_date": article_data.get("published_date", ""),
                    "scraped_at": datetime.datetime.utcnow().isoformat()
                }
                results.append(item)
                seen_links.add(href)
                collected += 1
                time.sleep(random.uniform(ARTICLE_SLEEP_MIN, ARTICLE_SLEEP_MAX))

            
            if collected >= MAX_ARTICLES_PER_SECTION:
                logger.info(f"Reached MAX_ARTICLES_PER_SECTION={MAX_ARTICLES_PER_SECTION} for {section_name}")
                break

        except Exception as e:
            logger.error(f"Error scraping listing page {page_url}: {e}")
           #moving on despite erros (يا جبل ميهزك ريح عادي غلطنا نرجع نكمل)
            continue

    return results

# ---------------- MAIN ----------------
def main():
    logger.info("Gomhuria scraper starting")
    s3 = init_s3_client()
    seen_links = load_seen_links_from_s3(s3)
    driver = init_driver()
    all_articles = []
    try:
        # iterate through sections map
        for name, template in SECTIONS.items():
            # skip the alt entry if duplicated by design
            if name.endswith("_alt"):
                continue
            # If template contains {page} okay, else fallback to original
            logger.info(f"Scraping section: {name}")
            articles = scrape_section(driver, name, template, seen_links)
            if articles:
                all_articles.extend(articles)
            #random pause between sections to avoid detection
            time.sleep(random.uniform(1.0, 2.0))
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    if all_articles:
        ok = upload_articles_to_s3(s3, all_articles)
        if ok:
            save_seen_links_to_s3(s3, seen_links)
            logger.info("Gomhuria pipeline completed and seen_links updated")
        else:
            logger.error("Upload failed; seen_links NOT updated")
    else:
        logger.info("No new articles collected this run")

if __name__ == "__main__":
    main()
