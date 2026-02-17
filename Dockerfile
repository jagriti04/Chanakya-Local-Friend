# Dockerfile
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    npm && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and build tools to avoid issues with building wheels
RUN pip install --upgrade pip setuptools wheel

# Copy requirements first to leverage Docker cache
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# (Optional) Install any system dependencies needed by your tools
# RUN apt-get update && apt-get install -y ...

# Copy the rest of your application code into the container's /app directory
COPY . .

# (Optional) If your mcp_config_file.json or .env file are meant to be part of the image
# AND don't contain secrets, you could copy them. Otherwise, mount or use env vars at runtime.
# COPY mcp_config_file.json.example /app/mcp_config_file.json
# COPY .env.example /app/.env

# For deployment and HTTPS/SSL configuration (e.g., using a reverse proxy),
# please refer to the instructions in the README.md file.
EXPOSE 5001

CMD ["python", "chanakya.py"]