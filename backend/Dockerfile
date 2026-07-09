# Backend Dockerfile for Open Karaoke Studio
# Supports FastAPI Backend and Celery Worker

FROM python:3.13-slim

# Install system dependencies for audio processing and PyTorch
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    gcc \
    g++ \
    python3-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Install heavy/stable dependencies first (these rarely change)
# This layer gets cached and won't rebuild when requirements.txt changes
RUN pip install --no-cache-dir \
    torch torchaudio \
    --index-url https://download.pytorch.org/whl/cu128 \
    && pip install --no-cache-dir \
    "numpy<2.0.0" \
    librosa \
    soundfile

# Copy requirements and install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Set Python path
ENV PYTHONPATH=/app/backend

# Environment variables for PyTorch/CUDA compatibility
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
ENV OMP_NUM_THREADS=1

# Add entrypoint script
COPY entrypoint.sh /app/backend/entrypoint.sh
RUN chmod +x /app/backend/entrypoint.sh

ENTRYPOINT ["/app/backend/entrypoint.sh"]

# Run the FastAPI server by default
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5123"]
