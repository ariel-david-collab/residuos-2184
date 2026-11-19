# ---------- 1. Frontend: Rust -> WASM ----------
# rust:1-slim sigue la serie 1.x: el código usa la edición 2021 y no fija minor.
FROM rust:1-slim AS web

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# trunk precompilado (mucho más rápido que compilarlo)
ARG TRUNK=0.22.2
RUN curl -fsSL "https://github.com/trunk-rs/trunk/releases/download/v${TRUNK}/trunk-x86_64-unknown-linux-gnu.tar.gz" \
    | tar -xz -C /usr/local/bin \
 && trunk --version

RUN rustup target add wasm32-unknown-unknown

WORKDIR /web
COPY web/Cargo.toml web/Cargo.lock* ./
COPY web/index.html web/style.css ./
COPY web/src ./src
RUN trunk build --release --dist /out

# ---------- 2. Runtime: Python + ONNX ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY api ./api
COPY models ./models
COPY --from=web /out ./web/dist

RUN useradd --create-home --shell /usr/sbin/nologin app \
 && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=4s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"

CMD ["uvicorn", "app:app", "--app-dir", "api", "--host", "0.0.0.0", "--port", "8000"]
