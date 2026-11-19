FROM caddy:2-alpine AS proxy

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 \
    KERAS_BACKEND=torch OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tesseract-ocr libgl1 libgles2 libegl1 libglib2.0-0 libgomp1 \
    libsm6 libxext6 libxrender1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
# Use the official CPU wheels; avoid shipping gigabytes of unused CUDA runtimes.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && pip install --no-cache-dir -r requirements.txt
COPY --from=proxy /usr/bin/caddy /usr/bin/caddy
COPY *.py style.css ./
COPY assets/ assets/
COPY data/ data/
COPY models/ models/
COPY pages/ pages/
COPY translations/ translations/
COPY docs/ docs/
COPY .streamlit/config.toml .streamlit/config.toml
COPY deploy/ deploy/
RUN useradd --create-home --uid 10001 medpredict && mkdir -p /data && chown -R medpredict:medpredict /app /data
USER medpredict
EXPOSE 7860
CMD ["python", "deploy/start.py"]
