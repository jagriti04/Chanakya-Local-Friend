# Deployment

This guide covers the different ways you can deploy and run the Chanakya voice assistant.

## Option 1: Docker (Recommended)

Using Docker is the recommended method for deploying Chanakya as it provides a consistent and isolated environment.

### Prerequisites

-   Docker and Docker Compose installed.
-   Your dependent services (Ollama, STT, TTS) are running and accessible from the machine where you will run the Chanakya container.
-   You have created and configured your `.env` and `mcp_config_file.json` files.

### Steps

1.  **Build the Docker Image:**
    From the root of the project directory, run the following command:
    ```bash
    sudo docker build -t chanakya-assistant .
    ```

2.  **Run the Docker Container:**
    ```bash
    sudo docker run --restart=always -d --network="host" --env-file .env -v Chanakya_data:/data_mount --name chanakya chanakya-assistant
    ```

### Command Explanation

-   `--restart=always`: Ensures the container will restart automatically if it crashes or if the system reboots.
-   `-d`: Runs the container in detached mode (in the background).
-   `--network="host"`: This is a crucial setting. It makes the container share the host's network stack, allowing it to easily connect to services running on `localhost` on your host machine (like Ollama, STT, or TTS).
-   `--env-file .env`: Passes all the variables from your `.env` file to the container.
-   `-v Chanakya_data:/data_mount`: Mounts a volume for persistent data.
-   `--name chanakya`: Assigns a name to the container for easy management.

## Option 2: Local Python Environment (for Development)

This method is ideal for developers who want to work on the Chanakya codebase directly.

### Prerequisites

-   Python 3.12.2+
-   `uv` (recommended) or `pip`
-   Your dependent services (Ollama, STT, TTS) are running and accessible.
-   You have created and configured your `.env` and `mcp_config_file.json` files.

### Steps

1.  **Create and Activate Virtual Environment:**
    Using `uv`:
    ```bash
    uv venv --python 3.12.2
    source .venv/bin/activate
    ```

2.  **Install Dependencies:**
    ```bash
    uv pip install -e .[dev]
    ```

3.  **Run the Application:**
    ```bash
    python chanakya.py
    ```

## Enabling HTTPS for Microphone Access

Modern web browsers require a secure (HTTPS) connection to allow web pages to access the microphone.

### Method A: Self-Signed Certificate (for Local Development)

This is the simplest way to enable HTTPS for local testing.

1.  **Generate the Certificate:**
    The repository includes a script to generate a self-signed certificate.
    ```bash
    python scripts/generate_cert.py
    ```
    This will create a `certs` directory with `cert.pem` and `key.pem` files.

2.  **Run the Application:**
    Start Chanakya as you normally would. The Flask server will automatically detect the certificate and start with HTTPS.

3.  **Trust the Certificate in Your Browser:**
    When you navigate to `https://localhost:5001`, your browser will show a privacy warning. You must accept the risk to proceed.

### Method B: Reverse Proxy (for Production)

Using a reverse proxy like Nginx or Caddy is the standard way to handle HTTPS in a production environment. The reverse proxy manages the SSL certificates (e.g., from Let's Encrypt) and forwards traffic to the Chanakya application, which can run on standard HTTP.

**General Steps:**

1.  **Run Chanakya:** Start the Chanakya application on its default port (`5001`) without any SSL context.
2.  **Set Up Reverse Proxy:**
    -   Configure your reverse proxy (e.g., Nginx Proxy Manager, Caddy) to create a new proxy host.
    -   **Domain:** Your public domain (e.g., `chanakya.your-domain.com`).
    -   **Scheme:** `http`.
    -   **Forward Hostname/IP:** The IP address of the machine running Chanakya.
    -   **Forward Port:** `5001`.
    -   **Enable WebSocket Support:** This is critical for the voice communication to work.
3.  **Enable SSL:**
    -   In your reverse proxy's SSL settings, request a new SSL certificate (e.g., using Let's Encrypt).
    -   Enable "Force SSL" and "HTTP/2 Support".

After saving, you can access Chanakya securely at your public domain.
