FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HOST=0.0.0.0
ENV LOG_LEVEL=INFO
ENV TRANSFORMERS_CACHE=/app/model_cache
ENV STT_MODEL=facebook/wav2vec2-base-960h
ENV DATA_DIR=/app/data

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/data /app/model_cache

# Copy requirements file first to leverage Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make sure the application has access to the directories
RUN chmod -R 777 /app/data /app/model_cache

# Expose the port
EXPOSE ${PORT}

# Run the application
CMD python main.py 