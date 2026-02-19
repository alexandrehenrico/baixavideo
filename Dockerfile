FROM python:3.11-slim

# Install ffmpeg and nodejs (JS runtime for yt-dlp)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create downloads folder
RUN mkdir -p downloads

# Expose port
EXPOSE 10000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "600", "--workers", "2", "--threads", "4", "app:app"]
