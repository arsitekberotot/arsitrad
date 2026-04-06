FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Gemma 4 model (optional — can be mounted as volume)
# ENV HF_HUB_ENABLE_HF_TRANSFER=1
# RUN python -c "from transformers import AutoModelForCausalLM; AutoModelForCausalLM.from_pretrained(\"google/gemma-4-2b-it\")"

# Copy project files
COPY . .

# Create data directories
RUN mkdir -p data/sni_corpus data/regulations data/processed

# Expose Gradio port
EXPOSE 7860

# Run
CMD ["python", "demo.py"]