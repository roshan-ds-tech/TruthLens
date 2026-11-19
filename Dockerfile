# TruthLens analysis API: the image the Hugging Face Space builds (CPU only, models baked in).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

# ffmpeg for media, pango for WeasyPrint PDFs, GL/glib for OpenCV, fonts for the report
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1 fonts-dejavu-core \
        libgl1 libglib2.0-0 libegl1 libgles2 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces run the container as uid 1000
RUN useradd -m -u 1000 user
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
# CPU-only torch first, so the pinned requirements do not pull in CUDA wheels
RUN TORCH=$(grep -E '^torch==' backend/requirements.txt | cut -d= -f3) \
    && pip install "torch==${TORCH}" --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r backend/requirements.txt

COPY backend backend
COPY validation/results validation/results
COPY validation/synth.py validation/run_validation.py validation/

# Model files are downloaded once at build time; at runtime analysis is offline.
RUN python backend/scripts/fetch_models.py && chown -R user:user /app

USER user
ENV TRUTHLENS_MODE=hosted \
    TRUTHLENS_DATA=/home/user/data \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    HOME=/home/user
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/api/health')"
CMD ["sh", "-c", "cd backend && exec python -m uvicorn app.main:app --host 0.0.0.0 --port 7860 --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
