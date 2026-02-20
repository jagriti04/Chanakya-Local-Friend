# Getting Started with Chanakya

This guide will walk you through the process of setting up Chanakya and its dependencies.

## Prerequisites

Before you begin, ensure you have the following installed on your system(s):

1.  **Python:** Version 3.11 (Recommended for compatibility).
2.  **Docker & Docker Compose:** For running Chanakya and its dependent services (Ollama, STT, TTS, MCP Tools). This is the recommended way to run the dependencies.
3.  **`uv` (Optional but Recommended):** For fast Python environment setup if not using Docker for Chanakya itself. You can install it from [Astral's `uv` GitHub page](https://github.com/astral-sh/uv).
4.  **Ollama:** You need a running instance of Ollama.
    -   **Installation:** Visit [ollama.com](https://ollama.com/) for installation instructions.
    -   **Pulling Models:** You must pull the LLM models you intend to use. For example:
        ```bash
        ollama pull hf.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF:UD-Q4_K_XL
        ```
5.  **Node.js & npm/npx (for some MCP Tools):** Some of the external tools Chanakya can use are Node.js packages.
6.  **Git:** For cloning the repository.
7.  **(Optional) NVIDIA GPU & NVIDIA Container Toolkit:** If you plan to use GPU acceleration for Ollama, Coqui TTS, or Faster Whisper Server, you will need the appropriate drivers and the NVIDIA Container Toolkit for Docker.

## Installation

You can run Chanakya using two primary methods:

-   **Docker (Recommended for Deployment):** Encapsulates the application and its dependencies in a container for easy and consistent deployment.
-   **Local Python Environment (Recommended for Development):** Allows for direct interaction with the code for development and customization.

### Setting Up Dependent Services

Before you run Chanakya, you must have the dependent services (Ollama, STT, and TTS) running. The recommended way to run these is with Docker.

**1. Ollama (LLM Server):**
- Ensure your Ollama instance is running and accessible over the network. If you are running Ollama in Docker, make sure to expose its port (default 11434). For GPU support, use the `--gpus=all` flag.
  ```bash
  docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
  ```

**2. Faster Whisper Server (STT):**
- This service provides high-performance speech-to-text.
- We recommend using the official Docker Compose setup:
  ```bash
  # For CUDA (NVIDIA GPU):
  docker run -d --gpus=all --publish 8000:8000 --restart unless-stopped --volume ~/.cache/huggingface:/root/.cache/huggingface fedirz/faster-whisper-server:latest-cuda
  # For CPU:
  # docker run -d --publish 8000:8000 --restart unless-stopped --volume ~/.cache/huggingface:/root/.cache/huggingface fedirz/faster-whisper-server:latest-cpu
  ```
- This will start the STT server on port `8000`.

**3. Coqui TTS Server (TTS):**
- This service provides high-quality, human-like text-to-speech.
- The repository includes a Dockerfile for Coqui TTS in the `coqui_tts` directory.
  ```bash
  cd coqui_tts
  sudo docker build -t coqui-chanakya-tts .
  sudo docker run -d -p 5002:5002 --gpus all --restart unless-stopped --name coqui-tts-server coqui-chanakya-tts
  ```
- This will start the TTS server on port `5002`.

### Running Chanakya

Once the dependent services are running, you can start the Chanakya application.

**1. Clone the Repository:**
```bash
git clone https://github.com/Rishabh-Bajpai/Chanakya-Local-Friend.git
cd Chanakya-Local-Friend
```

**2. Configure Chanakya:**
- Before running the application, you need to create two configuration files:
  - `.env`: For environment variables.
  - `mcp_config_file.json`: For tool configuration.
- Copy the example files:
  ```bash
  cp .env.example .env
  cp mcp_config_file.json.example mcp_config_file.json
  ```
- Edit these files with your specific settings. Refer to the [Configuration](./configuration.md) page for a detailed explanation of all the options.

**3. Choose your deployment method:**

- **Option A: Docker (Recommended)**
  - Build the Docker image:
    ```bash
    sudo docker build -t chanakya-assistant .
    ```
  - Run the Docker container:
    ```bash
    sudo docker run --restart=always -d --network="host" --env-file .env -v Chanakya_data:/data_mount --name chanakya chanakya-assistant
    ```
  - The `--network="host"` flag allows the Chanakya container to easily access the other services running on your host machine.

- **Option B: Local Python Environment**
  - Create and activate a virtual environment using `uv`:
    ```bash
    uv venv --python 3.11
    source .venv/bin/activate
    ```
  - Install the required dependencies:
    ```bash
    uv pip install -r requirements.txt
    ```
  - Run the application:
    ```bash
    python chanakya.py
    ```

**4. Access Chanakya:**
- The application should now be available at `http://localhost:5001`.

**5. Enabling HTTPS for Microphone Access:**
- Modern browsers require a secure (HTTPS) connection to access the microphone. See the [Deployment](./deployment.md) guide for instructions on how to set up HTTPS with a self-signed certificate for local development or a reverse proxy for production.

## Personalizing Chanakya

To get the most out of Chanakya, it is recommended to edit its long-term memory to provide personalized responses. By adding key information about yourself, the assistant can tailor its answers and actions to your specific needs.

You can add memories through the web interface by clicking the **Manage Memories** (🧠) button. For example, adding memories like:
- `The user's name is [Your Name].`
- `The user's location is [Your City].`
- `The user takes medication X at 8 AM daily.`

This will allow Chanakya to give you more relevant and personalized responses. For more details, see the [Managing Memories](./memory-management.md) guide.
