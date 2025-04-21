# Use a minimal base image
FROM python:3.11-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set workdir
WORKDIR /app

# System dependencies for audio processing and MySQL
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . .
COPY start.py .  

# Expose port for Railway
EXPOSE $PORT

# Use shell to ensure $PORT is interpreted correctly
CMD ["python", "start.py"]
