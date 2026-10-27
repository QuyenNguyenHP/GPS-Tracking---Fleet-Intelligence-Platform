FROM python:3.12-slim
WORKDIR /workspace/backend
COPY backend/ ./
RUN pip install --no-cache-dir '.[postgres,test]'
COPY scripts/ /workspace/scripts/
COPY simulator/ /workspace/simulator/
ENV PYTHONPATH=/workspace/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
