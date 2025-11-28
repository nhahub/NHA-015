FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bbc_scraper.py .

CMD ["python", "bbc_scraper.py"]