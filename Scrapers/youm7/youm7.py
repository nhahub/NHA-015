import os
import time
import json
import random
import datetime
import boto3
import logging
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# ======================================================
# LOGGING
# ======================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ======================================================
# CONFIG
# ======================================================
MAX_ARTICLES_PER_SECTION = 30
SCROLLS_PER_SECTION = 20

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")  
AWS_REGION = os.getenv("AWS_REGION")
if not AWS_BUCKET_NAME:
    raise RuntimeError("Set AWS_BUCKET_NAME env var before running")

S3_PREFIX = "raw/arabic/youm7/"
S3_SEEN_LINKS_KEY = f"{S3_PREFIX}seen_links.json"

SECTIONS = {
    "عاجل": "https://www.youm7.com/Section/أخبار-عاجلة/65/1",
    "سياسة": "https://www.youm7.com/Section/سياسة/319/1",
    "اقتصاد": "https://www.youm7.com/Section/اقتصاد-وبورصة/297/1",
    "رياضة": "https://www.youm7.com/Section/رياضة/298/1",
    "فن": "https://www.youm7.com/Section/فن/48/1",
    "تكنولوجيا": "https://www.youm7.com/Section/علوم-و-تكنولوجيا/328/1",
}

# Noise phrases to strip from full_text
NOISE_PATTERNS = [
    "تم التصميم والتطوير بواسطة",
    "الموضوعات المتعلقة",
    "موضوعات متعلقة",
    "اقرأ أيضا",
    "اقرأ ايضا",
    "تابعونا",
    "Welcome Your personal data",
    "TCF vendor",
    "Consent Manage options"
]


# ======================================================
# AWS FUNCTIONS
# ======================================================
def init_s3():
    return boto3.client("s3", region_name=AWS_REGION)


def load_seen_links(s3):
    try:
        obj = s3.get_object(Bucket=AWS_BUCKET_NAME, Key=S3_SEEN_LINKS_KEY)
        links = json.loads(obj["Body"].read().decode("utf-8"))
        return set(links)
    except:
        return set()


def save_seen_links(s3, seen):
    try:
        s3.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=S3_SEEN_LINKS_KEY,
            Body=json.dumps(list(seen), ensure_ascii=False, indent=2),
            ContentType="application/json"
        )
    except Exception as e:
        logger.error(f"Failed to save seen links: {e}")


# ======================================================
# SELENIUM DRIVER
# ======================================================
def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
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
    return driver


# ======================================================
# CLEANERS
# ======================================================
def clean_text(txt):
    if not txt:
        return ""

    for n in NOISE_PATTERNS:
        txt = txt.replace(n, "")
    
    # Hard Stop for Cookie Text
    cookie_start = "Welcome Your personal data will be processed"
    if cookie_start in txt:
        txt = txt.split(cookie_start)[0]

    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def remove_junk_elements(soup):
    junk_selectors = [
        ".fc-consent-root", 
        ".fc-dialog-container", 
        ".fc-dialog-overlay",
        "div[id*='google_ads']",
        ".adsbygoogle",
        ".related-articles",
        ".article-footer"
    ]
    for sel in junk_selectors:
        for tag in soup.select(sel):
            tag.decompose()
    return soup

# ======================================================
# SCRAPE FULL ARTICLE CONTENT 
# ======================================================
def scrape_full_article(driver, url):
    try:
        driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "lxml")
        soup = remove_junk_elements(soup)

        # 1. Image
        og = soup.find("meta", property="og:image")
        image_page = og["content"] if og else ""

        # 2. Date Extraction 
        # Try Meta tag first 
        date_str = ""
        meta_date = soup.find("meta", property="article:published_time")
        if meta_date:
            date_str = meta_date.get("content", "")
        
        # If no meta, try visible span
        if not date_str:
            vis_date = soup.select_one("span.writeDate, span.newsDate")
            if vis_date:
                date_str = vis_date.get_text(strip=True)

        # 3. Content
        container = soup.select_one("div.newsStory") or soup.select_one("div#articleBody") 
        if not container:
             container = soup.find("body")

        paras = container.find_all("p")
        clean_paragraphs = []
        for p in paras:
            text = p.get_text(strip=True)
            if "Welcome Your personal data" in text or "TCF vendor" in text:
                continue
            clean_paragraphs.append(text)

        text_body = " ".join(clean_paragraphs)
        text_body = clean_text(text_body)

        if len(text_body) < 40:
            return text_body, image_page, date_str

        return text_body, image_page, date_str

    except Exception as e:
        logger.error(f"Full article scrape failed: {e}")
        return "", "", ""


# ======================================================
# SCRAPE SECTION PAGE 
# ======================================================
def scrape_section(driver, name, url, seen):
    logger.info(f"Navigating to section: {name}")
    try:
        driver.get(url)
        time.sleep(3)

        for _ in range(SCROLLS_PER_SECTION):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "lxml")
        soup = remove_junk_elements(soup)

        cards = soup.find_all("div", class_="col-xs-12 bigOneSec")
        cards = cards[:MAX_ARTICLES_PER_SECTION]
        
        if not cards:
            logger.warning(f"No cards found for section {name}")

        base = "https://www.youm7.com"
        results = []

        for card in cards:
            try:
                title_tag = card.find("h3").find("a")
                title = title_tag.get_text(strip=True)
                link = title_tag["href"]

                if not link.startswith("http"):
                    link = base + link

                if link in seen:
                    continue

                # Card image
                img_tag = card.find("img")
                card_image = img_tag["src"] if img_tag else ""

                # Card summary
                desc = card.find("p")
                summary = desc.get_text(strip=True) if desc else ""

                # Card Date (Outer)
                date_tag = card.find("span", class_="newsDate2")
                card_date = date_tag.get_text(strip=True) if date_tag else ""

                logger.info(f"Scraping article: {link}")
                
                # Scrape full text, image, AND INNER DATE
                full_text, article_image, inner_date = scrape_full_article(driver, link)

                if len(full_text) < 50:
                    continue

                img_final = article_image if article_image else card_image
                
                # Use inner date if found, otherwise fallback to card date
                final_date = inner_date if inner_date else card_date

                article = {
                    "source": "youm7",
                    "language": "ar",
                    "category": name,
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "full_text": full_text,
                    "image_url": img_final,
                    "published_date": final_date,
                    "scraped_at": datetime.datetime.utcnow().isoformat()
                }

                results.append(article)
                seen.add(link)
                time.sleep(1)

            except Exception as e:
                logger.warning(f"Error scraping card: {e}")
                continue

        return results
    except Exception as e:
        logger.error(f"Error scraping section {name}: {e}")
        return []


# ======================================================
# MAIN PIPELINE
# ======================================================
def main():
    logger.info("Youm7 scraper starting...")
    s3 = init_s3()
    seen = load_seen_links(s3)

    driver = init_driver()
    all_articles = []

    try:
        for name, url in SECTIONS.items():
            arts = scrape_section(driver, name, url, seen)
            if arts:
                all_articles.extend(arts)
                logger.info(f"Collected {len(arts)} articles from {name}")
    finally:
        driver.quit()

    if all_articles:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = f"{S3_PREFIX}youm7_{ts}.json"

        try:
            s3.put_object(
                Bucket=AWS_BUCKET_NAME,
                Key=key,
                Body=json.dumps(all_articles, ensure_ascii=False, indent=2),
                ContentType="application/json"
            )
            save_seen_links(s3, seen)
            logger.info(f"Pipeline SUCCESS. Uploaded {len(all_articles)} articles to {key}")
        except Exception as e:
            logger.error(f"Upload failed: {e}")
    else:
        logger.info("NO NEW ARTICLES SCRAPED.")


if __name__ == "__main__":
    main()