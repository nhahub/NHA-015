import os
import re
import time
import json
import random
import logging
import datetime
from typing import Set, List
from urllib.parse import urljoin, urlparse

import boto3
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()

# ---------------- CONFIG ----------------
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")  
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
if not AWS_BUCKET_NAME:
    raise RuntimeError("Set AWS_BUCKET_NAME env var before running")

S3_PREFIX = "raw/arabic/ahram/"
S3_SEEN_LINKS_KEY = f"{S3_PREFIX}seen_links.json"

BASE_URL = "https://gate.ahram.org.eg"
MAX_ARTICLES_PER_SECTION = 20
SCROLLS_PER_SECTION = 5
REQUEST_TIMEOUT = 45 

SECTIONS = {
    "أخبار": "https://gate.ahram.org.eg/Portal/13/%D8%A3%D8%AE%D8%A8%D8%A7%D8%B1.aspx",
    "رياضة": "https://gate.ahram.org.eg/Portal/44/%D8%B1%D9%8A%D8%A7%D8%B6%D8%A9.aspx",
    "حوادث": "https://gate.ahram.org.eg/Portal/4/%D8%AD%D9%80%D9%88%D8%A7%D8%AF%D8%AB.aspx",
    "فن": "https://gate.ahram.org.eg/Portal/25/%D8%AB%D9%82%D8%A7%D9%81%D8%A9-%D9%88%D9%81%D9%86%D9%88%D9%86.aspx",
    "تكنولوجيا": "https://gate.ahram.org.eg/Portal/66/%D8%A7%D8%AA%D8%B5%D8%A7%D9%84%D8%A7%D8%AA-%D9%88%D8%AA%D9%83%D9%86%D9%88%D9%84%D9%88%D8%AC%D9%8A%D8%A7.aspx"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ahram_scraper")

DATE_RE = re.compile(
    r"(\d{1,2}/\d{1,2}/\d{2,4}.*?\d{1,2}:\d{2}:\d{2})|"      
    r"(\d{1,2}/\d{1,2}/\d{2,4})|"                           
    r"(آخر تحديث.*?)|"                                      
    r"(قبل\s+\d+\s+(ساعة|دقائق?|دقيقة|ثانية))",               
    flags=re.IGNORECASE
)

#Phrases that indicate the start of the Cookie Banner junk (bcz the server is in EU the ahram shows cookies banner)
COOKIE_JUNK_STARTERS = [
    "Some vendors may process your personal data",
    "Welcome Your personal data",
    "You can choose how your personal data is used",
    "TCF vendor",
    "Consent Manage options"
]

# ---------------- S3 HELPERS ----------------
def init_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)

def load_seen_links_from_s3(s3_client) -> Set[str]:
    try:
        resp = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=S3_SEEN_LINKS_KEY)
        data = json.loads(resp["Body"].read().decode("utf-8"))
        logger.info(f"Loaded {len(data)} seen links from S3")
        return set(data)
    except Exception:
        return set()

def save_seen_links_to_s3(s3_client, seen_links: Set[str]):
    try:
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=S3_SEEN_LINKS_KEY,
            Body=json.dumps(list(seen_links), ensure_ascii=False, indent=2),
            ContentType="application/json"
        )
    except Exception as e:
        logger.error(f"Failed to save seen links: {e}")

def upload_articles_to_s3(s3_client, articles: List[dict]) -> bool:
    if not articles:
        return True
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    key = f"{S3_PREFIX}ahram_{ts}.json"
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
    
    # Stealth settings
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-running-insecure-content")

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
def normalize_url(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return urljoin(BASE_URL, href)
    if not href.startswith("http"):
        return urljoin(BASE_URL, href)
    return href

def is_valid_article_url(href: str) -> bool:
    if not href:
        return False
    href = href.strip()
    if href.startswith("javascript:") or href.startswith("#"):
        return False
    parsed = urlparse(href)
    if parsed.netloc and "ahram" not in parsed.netloc:
        return False
    return True

def clean_text_remove_dates(text: str) -> str:
    if not text:
        return ""
    
    # Hard Stop: Cut off text if any cookie phrase appears
    for phrase in COOKIE_JUNK_STARTERS:
        if phrase in text:
            text = text.split(phrase)[0]
            
    t = DATE_RE.sub(" ", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def remove_junk_elements(soup: BeautifulSoup):
    
    selectors = [
        "aside", "nav", "footer", 
        "div[class*='related']", "div[class*='share']",
        ".fc-consent-root", ".fc-dialog-container",
        "div[id*='google']", ".adsbygoogle"
    ]
    for sel in selectors:
        for tag in soup.select(sel):
            tag.decompose()

def generate_summary(text: str, max_sentences: int = 3) -> str:
    if not text:
        return ""
    sentences = re.split(r'(?<=[\.\?\!\؟])\s+|\n+', text)
    if len(sentences) < 2:
        sentences = [text]
    summary = " ".join(s.strip() for s in sentences if s.strip())[:800]
    pieces = re.split(r'(?<=[\.\?\!\؟])\s+', summary)
    return " ".join(pieces[:max_sentences]).strip()

def extract_image_from_soup(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"]
    img = soup.select_one("img.img-fluid, img")
    if img and img.get("src"):
        return img["src"]
    return ""

def extract_article_page(driver, url: str) -> dict | None:
    try:
        driver.get(url)
        time.sleep(random.uniform(1.5, 2.5))
        soup = BeautifulSoup(driver.page_source, "lxml")

        # 1. DOM Cleaning
        remove_junk_elements(soup)

        container = soup.select_one("div#innerArticleContainer, div#ctl00_ctl00_ContentPlaceHolderMain_mainContent_pnlNews, article")
        if not container:
            container = soup

        paras = []
        for p in container.find_all("p"):
            txt = p.get_text(" ", strip=True)
            if not txt or len(txt.split()) < 4:
                continue
            
            # Skip paragraph if it contains English Cookie keywords
            if any(k in txt for k in COOKIE_JUNK_STARTERS):
                continue
                
            low = txt.lower()
            if any(k in low for k in ["تفضيلات", "المزيد", "اقرأ أيضا", "اتصل بنا", "cookies","د. محمد فايز فرحات"]):
                continue
            paras.append(txt)

        full_text = " ".join(paras).strip()
        
        # 2. String Cleaning 
        full_text = clean_text_remove_dates(full_text)
        
        if len(full_text) < 80:
            return None

        image_url = extract_image_from_soup(container) or extract_image_from_soup(soup)
        
        pub = ""
        meta_dt = soup.find("meta", {"property": "article:published_time"}) or soup.find("meta", {"name": "pubdate"})
        if meta_dt and meta_dt.get("content"):
            pub = meta_dt["content"]
        else:
            date_tag = soup.find(lambda t: t.name in ["time", "span"] and "202" in (t.get_text() or ""))
            if date_tag:
                pub = date_tag.get_text(strip=True)

        summary = generate_summary(full_text, max_sentences=3)
        return {"full_text": full_text, "image_url": image_url or "", "published_date": pub or "", "summary": summary}
    except Exception as e:
        return None

def find_main_cards(soup: BeautifulSoup) -> List[BeautifulSoup]:
    selectors = [
        "div.col-lg-12.d-flex.border-m.bg-contant-outer",
        "div.col-lg-3 + div.col-lg-9.bg-White-outer",
        "div.block-news", "div.sec-news", "div.news-box",
        ".news-item"
    ]
    cards = []
    for sel in selectors:
        found = soup.select(sel)
        if found:
            for f in found:
                cards.append(f)
    seen = set()
    unique = []
    for c in cards:
        key = (c.get_text()[:250] if c.get_text() else str(c)) 
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique

def scrape_section_maincards(driver, section_name: str, section_url: str, seen_links: Set[str]) -> List[dict]:
    results = []
    logger.info(f"Visiting Section: {section_name}")
    try:
        driver.get(section_url)
        time.sleep(2)
        
        # Check for firewall
        page_title = driver.title
        logger.info(f"Page Title: {page_title}")
        if "Access Denied" in page_title or "Security" in page_title:
             logger.error("BLOCKED BY FIREWALL")
             return []

        for _ in range(SCROLLS_PER_SECTION):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

        page = BeautifulSoup(driver.page_source, "lxml")
        main_cards = find_main_cards(page)
        
        logger.info(f"Found {len(main_cards)} cards in {section_name}")

        if not main_cards:
            main_cards = page.select("div.col-lg-12 a, div.top-news a")[:MAX_ARTICLES_PER_SECTION]

        collected = 0
        for card in main_cards:
            if collected >= MAX_ARTICLES_PER_SECTION:
                break
            a = card.find("a", href=True)
            if not a and card.name == "a":
                a = card
            if not a:
                continue
            href = normalize_url(a.get("href"))
            if not is_valid_article_url(href):
                continue
            if href in seen_links:
                continue

            title = ""
            if a.get("title"):
                title = a.get("title").strip()
            if not title:
                title = a.get_text(" ", strip=True)
            if not title or len(title) < 6:
                continue

            logger.info(f"Scraping: {href}")
            article_data = extract_article_page(driver, href)
            if not article_data:
                continue

            item = {
                "source": "Ahram",
                "language": "ar",
                "category": section_name,
                "title": title,
                "url": href,
                "summary": article_data["summary"],
                "full_text": article_data["full_text"],
                "image_url": article_data["image_url"],
                "published_date": article_data["published_date"],
                "scraped_at": datetime.datetime.utcnow().isoformat()
            }
            results.append(item)
            seen_links.add(href)
            collected += 1
            time.sleep(random.uniform(0.8, 1.4))
    except Exception as e:
        logger.error(f"Error scraping section {section_name}: {e}")
    return results

def main():
    logger.info("Ahram scraper starting...")
    s3 = init_s3_client()
    seen_links = load_seen_links_from_s3(s3)
    driver = init_driver()
    all_articles = []
    try:
        for name, url in SECTIONS.items():
            articles = scrape_section_maincards(driver, name, url, seen_links)
            all_articles.extend(articles)
            time.sleep(random.uniform(1.0, 2.0))
    finally:
        driver.quit()

    if all_articles:
        ok = upload_articles_to_s3(s3, all_articles)
        if ok:
            save_seen_links_to_s3(s3, seen_links)
            logger.info("Ahram pipeline completed and seen_links updated")
        else:
            logger.error("Upload failed; seen_links NOT updated")
    else:
        logger.info("No new Ahram articles collected this run")

if __name__ == "__main__":
    main()