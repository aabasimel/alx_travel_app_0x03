FROM python:3.11-slim

# Create app directory
RUN mkdir -p /app
WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends && apt-get install -y postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements first for caching
COPY requirements.txt /app/


# Create virtual environment and install dependencies
RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install -r requirements.txt

# Copy rest of the app
COPY . /app/

# Make entrypoint executable
COPY entrypoint /app/entrypoint
RUN chmod +x /app/entrypoint

# Use virtualenv in PATH
ENV PATH="/venv/bin:$PATH"


ENTRYPOINT [ "/app/entrypoint" ]



