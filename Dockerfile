FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libsndfile1 git \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces runs containers as uid 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH \
    TORCH_HOME=/home/user/.cache/torch
WORKDIR /home/user/app

# CPU-only torch first (much smaller than the CUDA build), then the rest
RUN pip install --no-cache-dir torch==2.5.1 torchaudio==2.5.1 \
        --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

EXPOSE 8501
# XSRF/CORS off: needed for st.file_uploader to work inside the HF Spaces iframe
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.enableXsrfProtection=false", "--server.enableCORS=false"]
