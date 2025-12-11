FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Node.js for Claude Code
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download spaCy Italian model (large)
RUN python -m spacy download it_core_news_lg

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p storage/attachments storage/repository storage/temp storage/chroma_db logs

# Expose port
EXPOSE 8001

# Default command (can be overridden by docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
