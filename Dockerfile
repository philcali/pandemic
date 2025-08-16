# Multi-stage Dockerfile for Pandemic monorepo
FROM node:24-alpine AS frontend-builder

# Build React frontend
WORKDIR /app/frontend
COPY packages/pandemic-console/src/frontend/package*.json ./
RUN npm ci --only=production

COPY packages/pandemic-console/src/frontend/ ./
RUN npm run build

FROM python:3.11-slim AS python-builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY packages/*/pyproject.toml packages/*/
RUN pip install --upgrade pip build

# Build Python packages
COPY packages/ packages/
COPY --from=frontend-builder /app/frontend/build packages/pandemic-console/src/pandemic_console/console/
RUN for pkg in packages/*/; do python -m build "$pkg"; done

FROM python:3.11-slim AS runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    systemd \
    && rm -rf /var/lib/apt/lists/*

# Create pandemic user
RUN useradd --create-home --shell /bin/bash pandemic

# Install built packages
COPY --from=python-builder /app/packages/*/dist/*.whl /tmp/wheels/
RUN pip install /tmp/wheels/*.whl && rm -rf /tmp/wheels

# Create directories
RUN mkdir -p /etc/pandemic /var/log/pandemic /opt/pandemic/infections
RUN chown -R pandemic:pandemic /etc/pandemic /var/log/pandemic /opt/pandemic

# Switch to pandemic user
USER pandemic
WORKDIR /home/pandemic

# Expose ports
EXPOSE 8080 8443 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Default command
CMD ["pandemic"]