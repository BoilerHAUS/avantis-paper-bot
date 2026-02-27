FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APB_DATA_DIR=/var/lib/avantis-paper-bot/data

WORKDIR /app

# Install project + deps at build time (no runtime pip install)
COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install -U pip \
 && pip install . \
 && python -m compileall src/bot

RUN mkdir -p /var/lib/avantis-paper-bot/data
