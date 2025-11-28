# 💾 ETL Loader Module

## Overview

The Loader is the final stage of the data pipeline. It reads processed articles from S3, generates vector embeddings, performs semantic deduplication, and loads data into PostgreSQL with pgvector for similarity search.

---

## 📂 Folder Structure

```
loader/
├── etl_loader.py        # Main ETL script
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
└── readme.md           # This file
```

---

## 🏗️ Architecture

```
┌────────────────────────┐
│  S3 Processed Data     │
│  - arabic/             │
│  - english/            │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  Load Latest Files     │
│ (Most Recent Per Lang) │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐     ┌─────────────────────────┐
│  Generate Embeddings   │ --> │  Sentence Transformers  │
│  (384 dimensions)      │     │  MiniLM-L12 Multilingual│
└───────────┬────────────┘     └─────────────────────────┘
            │
            ▼
┌────────────────────────┐
│  Exact URL Check       │
│  (Primary Key)         │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐     ┌─────────────────────────┐
│  Semantic Check        │ --> │  Vector Similarity      │
│  (85% threshold)       │     │  Cosine Distance        │
│  (48-hour window)      │     │  pgvector <=> operator  │
└───────────┬────────────┘     └─────────────────────────┘
            │
            ▼
┌────────────────────────┐
│  Insert to PostgreSQL  │
│  + pgvector column     │
└────────────────────────┘
```

---

## 🧠 Semantic Deduplication

### Why It's Needed

Traditional deduplication (URL-based) misses:
- **Same story, different outlets**: "Egypt announces..." vs "مصر تعلن..."
- **Updates to breaking news**: URL changes but content is 90% similar
- **Rewrites**: Scrapers may extract slightly different text from same source

### How It Works

```python
def is_semantically_unique(cursor, vector, title):
    sql = """
    SELECT title, 1 - (embedding <=> %s) as similarity
    FROM news
    WHERE inserted_at > NOW() - INTERVAL '48 hours'
    ORDER BY similarity DESC
    LIMIT 1;
    """
    cursor.execute(sql, (np.array(vector),))
    result = cursor.fetchone()
    
    if result:
        existing_title, similarity = result
        if similarity >= 0.85:  # 85% threshold
            return False  # Duplicate
    
    return True  # Unique
```

**Key Points**:
- Uses pgvector's `<=>` operator (cosine distance)
- Only checks last 48 hours (performance optimization)
- Threshold: 85% similarity = duplicate
- Compares: `title + summary` embeddings

### Example Scenarios

**Scenario 1: Different languages, same story**
```
Article A: "Egypt signs trade deal with UAE"
Article B: "مصر توقع اتفاقية تجارية مع الإمارات"
Similarity: 92% → Duplicate (one is kept)
```

**Scenario 2: Minor updates**
```
Article A: "Breaking: 5 injured in Cairo accident"
Article B: "Breaking: 5 injured in Cairo accident, investigation underway"
Similarity: 88% → Duplicate
```

**Scenario 3: Different stories**
```
Article A: "Egypt announces new housing project"
Article B: "Egypt announces education reforms"
Similarity: 45% → Both kept
```

---

## 🔍 Embedding Model

### Sentence Transformers: `paraphrase-multilingual-MiniLM-L12-v2`

**Specifications**:
- **Dimensions**: 384
- **Languages**: 50+ (Arabic, English, French, etc.)
- **Speed**: ~10ms per embedding (CPU)
- **Quality**: Balanced (not SOTA but fast)

**Why This Model?**:
- ✅ Multilingual (handles Arabic + English in same space)
- ✅ Fast inference
- ✅ Good quality for news similarity
- ✅ Fits in pgvector (384D < 2000D limit)

**Alternatives Considered**:
- ❌ `text-embedding-ada-002` (OpenAI) - Costs money
- ❌ `e5-large` - Slower, English-only
- ❌ `multilingual-e5-base` - Larger, not significantly better

### Embedding Generation

```python
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Generate embedding from title + summary
text_blob = f"{title} {summary}"
vector = model.encode(text_blob).tolist()  # Returns [384] floats
```

---

## 🗄️ Database Schema

### Table: `news`

```sql
CREATE TABLE news (
    id SERIAL PRIMARY KEY,
    source TEXT,
    language TEXT,
    category TEXT,
    title TEXT,
    url TEXT UNIQUE,  -- Prevents exact URL duplicates
    summary TEXT,
    full_text TEXT,
    image_url TEXT,
    published_date TEXT,
    scraped_at TEXT,
    sentiment TEXT,
    embedding vector(384),  -- pgvector column
    inserted_at TIMESTAMP DEFAULT NOW()
);
```

### Index for Fast Vector Search

```sql
CREATE INDEX news_embedding_idx ON news 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

**Index Type**: IVFFlat (Inverted File with Flat Compression)
- **Lists**: 100 (number of clusters)
- **Trade-off**: Speed vs Accuracy (100 lists = good balance for 10k-100k rows)

**Performance**:
- Without index: 2-5 seconds (sequential scan)
- With index: 10-50ms (approximate nearest neighbor)

---

## 🔄 ETL Process

### Step 1: Ensure Table Exists

```python
def ensure_table_exists():
    # Enable vector extension
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Create table with vector column
    cur.execute("""
    CREATE TABLE IF NOT EXISTS news (
        ...
        embedding vector(384),
        ...
    );
    """)
    
    # Add index
    cur.execute("""
    CREATE INDEX IF NOT EXISTS news_embedding_idx 
    ON news USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
    """)
```

**Why First Run Needs Special Handling?**
- Chicken & egg: Can't register vector type before extension is created
- `register_vec=False` on first connection, then `register_vec=True`

### Step 2: Load Latest Files

```python
# Finds most recent processed file per language
ar_key = get_latest_processed("processed/arabic/")
eng_key = get_latest_processed("processed/english/")

# Loads both into one array
all_data = []
all_data.extend(load_json_from_s3(ar_key))
all_data.extend(load_json_from_s3(eng_key))
```

### Step 3: Process & Insert

```python
for row in rows:
    # 1. Exact URL check
    if url_exists(url):
        continue
    
    # 2. Generate embedding
    vector = model.encode(f"{title} {summary}").tolist()
    
    # 3. Semantic check
    if not is_semantically_unique(cursor, vector, title):
        continue  # Skip duplicate
    
    # 4. Insert
    cur.execute("""
    INSERT INTO news (..., embedding)
    VALUES (..., %s)
    """, (..., vector))
```

---

## 📊 Performance Metrics

### Typical Run Stats (300 articles)

```
Loaded: 300 articles from S3
Exact URL duplicates: 50 (skipped)
Semantic duplicates: 30 (skipped)
Inserted: 220 (73% unique)
Runtime: ~4-6 minutes
```

**Breakdown**:
- Load S3: 5 seconds
- Generate embeddings: 3 minutes (300 × 10ms)
- Vector searches: 1.5 minutes (250 × ~20ms)
- Inserts: 30 seconds

### Optimization Tips

**Speed Up Embedding Generation**:
```python
# Batch encode (faster than loop)
texts = [f"{r['title']} {r['summary']}" for r in rows]
vectors = model.encode(texts, batch_size=32)
```

**Tune Index**:
```sql
-- For larger datasets (>100k rows)
WITH (lists = 500)  -- More clusters = slower inserts, faster searches
```

---

## 🚀 Deployment

### Prerequisites

```env
# Database
RDS_HOST=your-postgres-instance.rds.amazonaws.com
RDS_PORT=5432
RDS_DB=news_db
RDS_USER=admin
RDS_PASSWORD=your-password

# S3
AWS_BUCKET_NAME=your-bucket
AWS_REGION=us-east-1
```

### Local Testing

```bash
cd loader
docker build -t etl-loader .
docker run --env-file ../.env etl-loader
```

### AWS ECS Deployment

```yaml
Task Definition:
  CPU: 2048 (2 vCPU)
  Memory: 4096 (4 GB)  # Model needs ~2GB, rest for data
  Timeout: 15 minutes
```

**Orchestration**: Runs after both processors complete (Step Functions)

---

## 🔧 Configuration

### Similarity Threshold

```python
SIMILARITY_THRESHOLD = 0.85  # Adjust based on needs
```

- **0.80-0.85**: Balanced (recommended)
- **0.90+**: Stricter (may keep more duplicates)
- **0.70-0.80**: Aggressive (may remove unique articles)

### Deduplication Window

```python
WHERE inserted_at > NOW() - INTERVAL '48 hours'
```

- **24h**: Faster, misses slow-breaking stories
- **48h**: Balanced (default)
- **7d**: Comprehensive, slower queries

---

## 🐛 Troubleshooting

### Issue: "Extension 'vector' does not exist"

**Solution**: 
```sql
-- Run manually as superuser
CREATE EXTENSION vector;
```

Or ensure Dockerfile enables it on first run.

### Issue: "Cannot register vector type"

**Solution**: Use `register_vec=False` on first connection, then `True` after extension is created.

### Issue: "Index creation takes forever"

**Solution**: 
- Create index AFTER bulk loading data
- Or use `CONCURRENTLY` (but blocks other queries)

### Issue: "Too many duplicates detected"

**Solution**: Lower threshold to 0.75 or reduce window to 24h.

---
