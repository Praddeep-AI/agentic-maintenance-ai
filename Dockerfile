FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY agentic_maintenance/requirements.txt ./agentic_maintenance/requirements.txt
RUN pip install --no-cache-dir -r agentic_maintenance/requirements.txt

# Copy full project
COPY . .

# Expose Streamlit port
EXPOSE 8501

ENV PYTHONPATH=/app
CMD ["streamlit", "run", "agentic_maintenance/dashboard/app.py", \
     "--server.address", "0.0.0.0", "--server.port", "8501"]
