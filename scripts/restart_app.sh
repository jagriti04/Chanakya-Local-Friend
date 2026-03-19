#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Stopping container 'chanakya' (if it exists)..."
docker stop chanakya || true

echo "Removing container 'chanakya' (if it exists)..."
docker rm chanakya || true

echo "Building new image 'chanakya-assistant'..."
docker build -t chanakya-assistant .

echo "Starting container 'chanakya'..."
docker run --restart=always -d --network="host" --env-file .env --name chanakya chanakya-assistant

echo "Restart completed successfully!"
