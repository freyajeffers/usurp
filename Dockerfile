FROM python:3.14-slim

# Install system build deps needed for indexed-zstd / camoufox on ARM
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential clang llvm pkg-config git curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock /app/
COPY . /app

RUN python -m pip install --upgrade pip
# Install editable with dev extras to run tests and linters
RUN python -m pip install --no-cache-dir -e '.[dev]'

EXPOSE 8000

CMD ["uvicorn", "usurp.main:app", "--host", "0.0.0.0", "--port", "8000"]
