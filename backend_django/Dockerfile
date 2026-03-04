FROM python:3.9-slim

WORKDIR /app

# Install system dependencies needed for compiling certain python packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

COPY . .

EXPOSE 8000

# Wait for db script or direct start. We will use gunicorn for prod.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
