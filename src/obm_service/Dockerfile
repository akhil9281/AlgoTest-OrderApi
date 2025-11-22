# OBM Service Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy OBM service code
COPY . /app/obm_service

# Create data directory for WAL
RUN mkdir -p /app/data

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the OBM service
CMD ["python", "-m", "obm_service.main"]
