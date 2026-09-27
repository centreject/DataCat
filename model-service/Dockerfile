# DataCat model service: vision + STT + LLM behind one FastAPI process.
# Build:  docker build -t datacat-model model-service
# Run:    docker run --gpus all -p 8000:8000 -v datacat-models:/models datacat-model
FROM python:3.11-slim

# build-essential: torch 2.14 routes some ops to Triton, which JIT-compiles kernels with a C compiler.
# libgl1/libglib2.0-0: OpenCV (pulled in by Ultralytics).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run as an unprivileged user, not root. UID 1000 is the usual first user on Linux/WSL, so files the
# container writes into a bind-mounted host folder stay owned by that user instead of root.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /models /app/data \
    && chown app:app /models /app/data
COPY --chown=app:app app ./app
USER app

# Weights (YOLO, Whisper, Qwen, text encoder) are not baked into the image: they are downloaded
# on first start into the /models volume and loaded offline afterwards. HF_HOME keeps the Hugging
# Face hub cache and token there too, instead of the container's home directory.
ENV WEIGHTS_DIR=/models \
    HF_HOME=/models/huggingface \
    MODEL_PROFILE=lite \
    PYTHONUNBUFFERED=1
VOLUME /models
EXPOSE 8000

# First start downloads ~10 GB of weights. The start period only means early failures don't count;
# the container turns healthy as soon as loading finishes, so a long period costs nothing.
# "degraded" (e.g. LLM failed to load, keyword rules in use) still serves requests, so it counts as healthy.
HEALTHCHECK --interval=15s --timeout=5s --start-period=3600s --retries=3 \
    CMD python -c "import json,sys,urllib.request; sys.exit(json.load(urllib.request.urlopen('http://localhost:8000/health'))['status'] not in ('ok', 'degraded'))"

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
