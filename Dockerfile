# ==============================================================================
# LegalCompass - All-in-One Multi-Stage Dockerfile (Frontend + Backend)
# ==============================================================================

# Stage 1: Build React + Vite Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Python 3.11 Backend
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-cache FastEmbed embedding model into image during build so runtime uploads don't stall
RUN python -c "from fastembed import TextEmbedding; list(TextEmbedding('BAAI/bge-small-en-v1.5').embed(['warmup']))"

# Copy backend app
COPY legalcompass-backend/app ./app

# Copy built frontend assets from Stage 1 into /app/dist
COPY --from=frontend-builder /app/dist ./dist

ENV PORT=8000
ENV ENVIRONMENT=production
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
