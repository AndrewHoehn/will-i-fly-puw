# Use official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (if any needed for sqlite/builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a directory for the persistent database volume
# Fly.io will mount the volume here if configured
RUN mkdir -p /data

# Expose the port Fly.io expects (usually 8080)
EXPOSE 8080

# Run the application
# We bind to 0.0.0.0 so external traffic can reach the container
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
