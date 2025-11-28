# 🤖 AI Processing Module

## Overview

This module contains two language-specific AI pipelines that enrich raw news articles with summaries, sentiment analysis, and prepare them for database loading. Each pipeline uses different AI models optimized for their respective languages.

---

## 📂 Folder Structure

```
processor/
├── 📁 arabic_processor/
│   ├── processing_pipeline.py
│   ├── Dockerfile
│   ├── requirements.txt
│   
│
├── 📁 english_processor/
│   ├── english_processor.py
│   ├── Dockerfile
│   ├── requirements.txt
│   
│
└──  README.md (this file)
```

---

## 🌍 Arabic Processor (`arabic_processor/`)

### Model: Google Gemini 2.5 Flash

**Purpose**: Process Arabic news articles with cloud-based AI for summarization and sentiment analysis.

### Architecture

```
┌─────────────────┐
│  S3 Raw Data    │
│  (Arabic)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Load Latest    │
│  from Scrapers  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Deduplicate    │ --> │  TF-IDF          │
│  (TF-IDF)       │     │  Cosine Sim 85%  │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Date           │
│  Normalization  │ (Arabic → ISO 8601)
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Gemini 2.5 Flash API   │
│  - Summarization        │ 
│  - Sentiment Analysis   │   
└────────┬────────────────┘
         │
         ▼
┌─────────────────┐
│  JSON Repair    │ (Handles malformed responses)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Save to S3     │
│  processed/     │
│  arabic/        │
└─────────────────┘
```

### Key Features

#### 1. ** JSON Parsing**
```python
def clean_and_repair_json(text):
    # Strips markdown backticks
    # Regex fallback for malformed JSON
    # Returns clean dict
```

**Handles**:
- Markdown code blocks (````json ... ````)
- Missing quotes
- Truncated responses

#### 2. **Arabic Date Normalization**
```python
AR_MONTHS = {
    "يناير": "January",
    "فبراير": "February",
    # ... full mapping
}

# Converts: "الجمعة، 15 يناير 2025 - 03:45 م"
# To: "Friday, 15 January 2025 – 15:45"
```

#### 3. **Smart Text Cleaning**
```python
NOISE = [
    "تم التصميم والتطوير بواسطة",
    "الموضوعات المتعلقة",
    "اقرأ أيضا"
]
# Removes footer junk, "Read More" links, etc.
```

### AI Prompt Template

```python
prompt = f"""
You are an expert Arabic news analyst.
Analyze the following text and provide a structured JSON output.

TEXT:
{full_text[:3000]}

OUTPUT FORMAT (Strict JSON):
{{
    "summary": "Write a comprehensive summary in Arabic (1-2 sentences)...",
    "sentiment": "Positive/Neutral/Negative"
}}
"""
```

### Performance

- **Throughput**: 30 articles per API key per run
- **Batch Processing**: Groups of 10 articles
- **Batch Delay**: 65 seconds between batches
- **Per-Article Delay**: 1 second
- **Total Runtime**: ~15-20 minutes for 90 articles

### Configuration

```env
# Required Environment Variables
AWS_BUCKET_NAME=your-bucket
GEMINI_API_KEY=primary-key
```

### Output Schema

```json
{
  "source": "Ahram",
  "language": "ar",
  "category": "تكنولوجيا",
  "title": "...",
  "url": "https://...",
  "summary": "ملخص شامل للمقال باللغة العربية...",
  "full_text": "النص الكامل...",
  "image_url": "https://...",
  "published_date": "Friday, 28 November 2025 – 14:30",
  "scraped_at": "Friday, 28 November 2025 – 15:00",
  "sentiment": "Positive"
}
```

**Stored At**: `s3://bucket/processed/arabic/processed_arabic_YYYYMMDD_HHMMSS.json`

---

## 🇬🇧 English Processor (`english_processor/`)

### Model: Qwen 2.5 (3B Instruct) - Quantized

**Purpose**: Process English news articles with a local, cost-free AI model.

### Architecture

```
┌─────────────────┐
│  S3 Raw Data    │
│  (English)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Load Latest    │
│  from Scrapers  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Deduplicate    │
│  (TF-IDF)       │
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│  Local Qwen 2.5 Model    │
│  (3B Q4_K_M GGUF)        │
│                          │
│  - No API calls          │
│  - No rate limits        │
│  - Runs in container     │
└────────┬─────────────────┘
         │
         ▼
┌─────────────────┐
│  Save to S3     │
│  processed/     │
│  english/       │
└─────────────────┘
```

### Key Features

#### 1. **Local Inference (No API Costs)** 💰
```python
llm = Llama(
    model_path="/app/model.gguf",
    n_ctx=2048,
    n_threads=2,
    verbose=False
)
```

**Why**: 
- Guardian/BBC provide full article text
- Processing 300+ articles would cost $5-10 with cloud APIs
- Qwen 3B quantized runs efficiently on 2 vCPUs

#### 2. **Smart Truncation for Live Blogs**
```python
# If text > 1500 chars (e.g. Live Blog with 100 updates)
if len(text_source) > 1500:
    # Take first 1000 chars (headlines) + last 500 chars (latest updates)
    text_input = text_source[:1000] + "\n... [middle removed] ...\n" + text_source[-500:]
```

**Why**: Live Blogs can be 1000+ words. This captures the most relevant parts without exceeding context window.

#### 3. **ISO 8601 Date Handling**
```python
# Parses Guardian/BBC timestamps
# "2025-11-28T14:23:17Z" → ISO format
dt = parser.parse(str(dt_str))
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=datetime.timezone.utc)
return dt.isoformat()
```

#### 4. **Fallback to Summary**
```python
# If full_text not available (NYT API limitation)
text_source = article.get("full_text") or article.get("summary") or ""
```

### AI Prompt Template

```python
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
```

**Note**: Uses ChatML format (Qwen's native prompt format)

### Model Details

- **Quantization**: Q4_K_M (4-bit, medium quality)
- **Size**: ~2 GB
- **Context Window**: 2048 tokens
- **Speed**: ~2-3 seconds per article (2 vCPU)
- **Downloaded At Build**: `https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF`

### Performance

- **Throughput**: Unlimited (no rate limits)
- **Batch Processing**: Sequential (1 article at a time)
- **Total Runtime**: ~50 minutes for 300 articles
- **Resource Usage**: 4GB RAM, 2 vCPU

### Configuration

```env
# Required Environment Variables
AWS_BUCKET_NAME=your-bucket
```

### Output Schema

Same as Arabic processor, but with English content:

```json
{
  "source": "theguardian",
  "language": "en",
  "category": "technology",
  "title": "...",
  "url": "https://...",
  "summary": "A concise 3-sentence summary of the article...",
  "full_text": "...",
  "image_url": "https://...",
  "published_date": "2025-11-28T14:23:17+00:00",
  "scraped_at": "2025-11-28T15:00:00+00:00",
  "sentiment": "Neutral"
}
```

**Stored At**: `s3://bucket/processed/english/processed_english_YYYYMMDD_HHMMSS.json`

---

## 🔄 Deduplication Strategy

Both processors use **TF-IDF + Cosine Similarity** for content-based deduplication:

```python
def deduplicate_articles(articles, threshold=0.85):
    texts = [a["full_text"] for a in articles]
    vectors = TfidfVectorizer().fit_transform(texts)
    sim_matrix = cosine_similarity(vectors)
    
    # Keep first occurrence, remove similar ones
    keep = []
    removed = set()
    for i in range(len(articles)):
        if i in removed: continue
        keep.append(articles[i])
        for j in range(i + 1, len(articles)):
            if sim_matrix[i][j] >= threshold:
                removed.add(j)
    return keep
```

**Why Not Just URL Check?**
- Same story published on multiple outlets
- Updates to breaking news (different URLs, same content)

---

## 🚀 Deployment

### Local Testing

**Arabic Processor**:
```bash
cd processor/arabic_processor
docker build -t arabic-processor .
docker run --env-file ../../.env arabic-processor
```

**English Processor**:
```bash
cd processor/english_processor
docker build -t english-processor .
docker run --env-file ../../.env english-processor
```

### AWS ECS Deployment

Both processors run as ECS Fargate Tasks:

```yaml
# Task Definition
CPU: 2048 (2 vCPU)
Memory: 4096 (4 GB)
Timeout: 30 minutes
```

**Orchestration**: Runs after scrapers complete (see Step Functions diagram)

---

## 📊 Comparison

| Feature | Arabic Processor | English Processor |
|---------|------------------|-------------------|
| **Model** | Gemini 2.5 Flash | Qwen 2.5 3B |
| **Location** | Cloud API | Local (in-container) |
| **Cost** | Free tier (rate limited) | $0 |
| **Throughput** | 30/key/run | Unlimited |
| **Latency** | 2-3s + network | 2-3s |
| **Quality** | Excellent (native Arabic) | Very Good |
| **Scalability** | Add more keys | Add more vCPUs |

---

## 🐛 Common Issues

### Arabic Processor

**Issue**: "JSON Parsing Failed"  
**Solution**: Regex fallback is built-in, but check model temperature

### English Processor

**Issue**: "Model file not found"  
**Solution**: Ensure Dockerfile downloads model at build time

**Issue**: "Out of Memory"  
**Solution**: Increase ECS task memory to 8GB for larger models

