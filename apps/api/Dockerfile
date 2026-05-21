FROM python:3.11-slim

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source as the `api` package so relative imports resolve correctly.
# PYTHONPATH /workspace/api lets sibling top-level packages (agent_runtime)
# be found; /workspace (CWD, added by uvicorn) lets `import api` work.
COPY . ./api/
ENV PYTHONPATH=/workspace/api

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
