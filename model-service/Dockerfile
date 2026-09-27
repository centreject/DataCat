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

COPY app ./app

# Weights (YOLO, Whisper, Qwen, text encoder) are not baked into the image: they are downloaded
# on first start into the /models volume and loaded offline afterwards.
ENV WEIGHTS_DIR=/models \
    MODEL_PROFILE=lite \
    PYTHONUNBUFFERED=1
VOLUME /models
EXPOSE 8000

# First start downloads ~10 GB of weights, so allow a long start period.
HEALTHCHECK --interval=15s --timeout=5s --start-period=900s --retries=3 \
    CMD python -c "import json,sys,urllib.request; sys.exit(json.load(urllib.request.urlopen('http://localhost:8000/health'))['status'] != 'ok')"

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
