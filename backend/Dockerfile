FROM python:3.12-slim
WORKDIR /app
# DejaVu ships the Cyrillic-capable TTF that reportlab registers for the
# generated profile PDF; without it the export would render as black boxes.
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
CMD ["sh","-c","alembic upgrade head && python scripts/seed.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
