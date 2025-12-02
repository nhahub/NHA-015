import os
import json
import psycopg2
import boto3
import logging
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector

# --------------------------
# LOGGING CONFIG
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("etl_rds_loader")

load_dotenv()

# --------------------------
# CONFIG
# --------------------------
PG_HOST = os.getenv("RDS_HOST")
PG_PORT = os.getenv("RDS_PORT", "5432")
PG_DB = os.getenv("RDS_DB")
PG_USER = os.getenv("RDS_USER")
PG_PASSWORD = os.getenv("RDS_PASSWORD")

AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
S3_BUCKET = os.getenv("AWS_BUCKET_NAME", "sentiment-data-lake")

SIMILARITY_THRESHOLD = 0.85 

s3 = boto3.client("s3", region_name=AWS_REGION)

logger.info("Loading the model (MiniLM-L12)...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
logger.info("Model Loaded.")

# -------------------------------------------------
# DATABASE HELPERS 
# -------------------------------------------------
def get_pg_conn(register_vec=True):
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DB
    )
    
    if register_vec:
        try:
            register_vector(conn)
        except Exception as e:
            logger.warning(f"Could not register vector type (First Run?): {e}")
    
    return conn

def ensure_table_exists():
    conn = get_pg_conn(register_vec=False)
    cur = conn.cursor()
    
     
    logger.info("Enabling 'vector' extension...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()

    
    register_vector(conn)
    
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS news (
        id SERIAL PRIMARY KEY,
        source TEXT,
        language TEXT,
        category TEXT,
        title TEXT,
        url TEXT UNIQUE,
        summary TEXT,
        full_text TEXT,
        image_url TEXT,
        published_date TEXT,
        scraped_at TEXT,
        sentiment TEXT,
        embedding vector(384),
        inserted_at TIMESTAMP DEFAULT NOW()
    );
    """
    cur.execute(create_sql)

    
    try:
        cur.execute("ALTER TABLE news ADD COLUMN IF NOT EXISTS embedding vector(384);")
    except Exception as e:
        conn.rollback()
        logger.warning(f"Migration notice: {e}")
    
    
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS news_embedding_idx ON news USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")
    except:
        conn.rollback()

    conn.commit()
    cur.close()
    conn.close()

# -------------------------------------------------
# SEMANTIC CHECK
# -------------------------------------------------
def is_semantically_unique(cursor, vector, title):
    sql = """
    SELECT title, 1 - (embedding <=> %s) as similarity
    FROM news
    WHERE inserted_at > NOW() - INTERVAL '48 hours'
    ORDER BY similarity DESC
    LIMIT 1;
    """
    
    try:
        cursor.execute(sql, (np.array(vector),))
        result = cursor.fetchone()

        if result:
            existing_title, similarity = result
            if similarity >= SIMILARITY_THRESHOLD:
                logger.info(f"🚫 Duplicate (Sim: {similarity:.2f}): '{title[:30]}...'")
                return False 
    except Exception as e:
        logger.warning(f"Vector search failed (Skipping dedupe): {e}")
        return True # Assume unique if DB error to avoid data loss

    return True 

# -------------------------------------------------
# READERS
# -------------------------------------------------
def get_latest_processed(prefix):
    objs = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
    if "Contents" not in objs: return None

    files = [f for f in objs["Contents"] if f["Key"].endswith(".json") and "seen_links" not in f["Key"]]
    if not files: return None

    files.sort(key=lambda x: x["LastModified"], reverse=True)
    return files[0]["Key"]

def load_json_from_s3(key):
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return json.loads(obj["Body"].read().decode("utf-8"))

# -------------------------------------------------
# INSERT LOOP
# -------------------------------------------------
def process_and_insert(rows):
    if not rows: return
    logger.info(f"Processing {len(rows)} articles...")

     
    conn = get_pg_conn(register_vec=True)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for row in rows:
        url = row.get("url")
        title = row.get("title", "") or ""
        summary = row.get("summary", "") or ""
        
        # 1. Exact Check (URL)
        cur.execute("SELECT 1 FROM news WHERE url = %s", (url,))
        if cur.fetchone():
            skipped += 1
            continue 

        # 2. Semantic Check
        text_blob = f"{title} {summary}"
        vector = model.encode(text_blob).tolist()

        if not is_semantically_unique(cur, vector, title):
            skipped += 1
            continue

        # 3. Insert
        sql = """
        INSERT INTO news (
            source, language, category, title, url, summary, full_text,
            image_url, published_date, scraped_at, sentiment, embedding
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        cur.execute(sql, (
            row.get("source"),
            row.get("language"),
            row.get("category"),
            title,
            url,
            summary,
            row.get("full_text"),
            row.get("image_url"),
            row.get("published_date"),
            row.get("scraped_at"),
            row.get("sentiment"),
            vector
        ))
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"Batch Complete. Inserted: {inserted} | Skipped: {skipped}")

# -------------------------------------------------
# MAIN
# -------------------------------------------------
def run_etl():
    logger.info("Starting Smart ETL...")
    ensure_table_exists()

    all_data = []
    
    ar_key = get_latest_processed("processed/arabic/")
    if ar_key:
        logger.info(f"Loading Arabic: {ar_key}")
        all_data.extend(load_json_from_s3(ar_key))

    eng_key = get_latest_processed("processed/english/")
    if eng_key:
        logger.info(f"Loading English: {eng_key}")
        all_data.extend(load_json_from_s3(eng_key))

    if not all_data:
        logger.info("No data found.")
        return

    process_and_insert(all_data)
    logger.info("ETL Finished.")

if __name__ == "__main__":
    run_etl()
