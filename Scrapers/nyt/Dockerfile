FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY nyt_scraper.py .

CMD ["python", "nyt_scraper.py"]