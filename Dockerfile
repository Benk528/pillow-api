FROM python:3.13.1 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Create virtual environment and install dependencies
RUN python -m venv .venv
COPY requirements.txt ./
RUN .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements.txt

FROM python:3.13.1-slim
WORKDIR /app

# Copy venv and app files
COPY --from=builder /app/.venv .venv/
COPY . .

# Expose port 8080 (optional, for clarity)
EXPOSE 8080

# Start FastAPI app with uvicorn
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]