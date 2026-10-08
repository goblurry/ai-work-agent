FROM python:3.11-slim
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY backend/requirements.txt backend/requirements-embedding.txt /tmp/requirements/
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r /tmp/requirements/requirements.txt -r /tmp/requirements/requirements-embedding.txt
RUN chown app:app /app
USER app
ENV HF_HOME=/home/app/.cache/huggingface EMBEDDING_MODE=local BGE_MODEL_PATH=/home/app/models/bge-m3 BGE_DEVICE=cpu COOKIE_SECURE=true COOKIE_SAMESITE=none
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-m3', revision='5617a9f61b028005a4858fdac845db406aefb181', local_dir='/home/app/models/bge-m3', ignore_patterns=['*.onnx', 'onnx/*'])"
COPY --chown=app:app backend/app backend/app
COPY --chown=app:app backend/scripts/build_course_index.py backend/scripts/build_course_index.py
COPY --chown=app:app backend/deploy/start.py backend/deploy/start.py
EXPOSE 7860
CMD ["python", "backend/deploy/start.py"]
