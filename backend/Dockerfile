FROM python:3.12-slim-bookworm 

# Environment variables
ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  UV_PROJECT_ENVIRONMENT=/home/user/app/.venv \
  PATH="/home/user/app/.venv/bin:$PATH"

# Create a non-root user
RUN groupadd user && useradd --create-home --home-dir /home/user -g user user

# Install system dependencies
RUN apt-get update && apt-get install python3-dev gcc build-essential libpq-dev -y

# nginx is commented out — replaced by ALB which handles reverse proxying.
RUN apt-get install nginx -y

# Create nginx runtime directories and set permissions for non-root user
RUN mkdir -p /var/lib/nginx /var/log/nginx /run/nginx && \
  chown -R user:user /var/lib/nginx /var/log/nginx /run/nginx

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy application files
COPY pyproject.toml uv.lock /home/user/app/

# Set working directory
WORKDIR /home/user/app/

# Set permissions for the application directory
RUN chmod -R ugo+w /home/user/app/

# Install Python dependencies
RUN uv sync --frozen --no-install-project

# Set working directory for the backend
WORKDIR /home/user/app/backend

# Create logs directory and set permissions
RUN mkdir -p /home/user/app/logs && \
  chown -R user:user /home/user/app/logs && \
  chmod -R 755 /home/user/app/logs

# Copy backend code and scripts
COPY backend/ /home/user/app/backend

# Ensure scripts are executable
RUN chmod +x scripts/django-entrypoint.sh


COPY backend/nginx.conf /etc/nginx/conf.d/default.conf
COPY backend/nginx-main.conf /etc/nginx/nginx.conf

EXPOSE 8080

# Switch to non-root user
USER user

# Set ENTRYPOINT to the initialization script
ENTRYPOINT ["sh", "scripts/django-entrypoint.sh"]
