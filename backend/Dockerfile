FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /srv

# sentence-transformers (for RAG embeddings) pulls in torch as a transitive dependency.
# Installed via plain PyPI, torch's default wheel drags in several GB of NVIDIA CUDA
# runtime packages (cuBLAS/cuDNN/nvshmem/...) that are dead weight here — this container
# never touches a GPU. Installing the official CPU-only build first satisfies that
# dependency before requirements.txt ever gets a chance to resolve the CUDA variant.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN playwright install --with-deps chromium

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
