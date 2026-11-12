# Secure research-data pipeline (synthetic data)
# Builds and runs the full pipeline end to end inside the container.
# Outputs land in /app/outputs; mount a host directory to keep them:
#   docker run --rm -v "$PWD/outputs:/app/outputs" secure-research-data-pipeline

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/ ./pipeline/
COPY run_pipeline.py .

RUN mkdir -p /app/data/raw /app/outputs

ENTRYPOINT ["python", "run_pipeline.py"]
CMD ["--rows", "1200", "--seed", "42"]
