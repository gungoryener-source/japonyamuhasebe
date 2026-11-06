# tegaru-line-bot: FastAPI + yapay zekâsız fiş okuma (Tesseract jpn)
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# tessdata_best (LSTM, daha isabetli): 67 gerçek fişte tüm alanlar doğru oranı %45 → %70 (docs/OCR.md)
ARG TESSDATA_TAG=4.1.0
RUN mkdir -p /opt/tessdata \
 && for l in jpn eng osd; do \
      curl -fsSL -o /opt/tessdata/$l.traineddata \
        https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/${TESSDATA_TAG}/$l.traineddata; \
    done
ENV OCR_TESSDATA=/opt/tessdata

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
