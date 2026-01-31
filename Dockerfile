FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    pypdf2 \
    pdfplumber \
    markdown

# Create working directory
WORKDIR /app

# Copy parser scripts
COPY parse_pdfs.py /app/
COPY parse_paper.py /app/

# Create volume mount points
VOLUME ["/pdfs", "/output"]

# Run the paper parser by default
CMD ["python", "parse_paper.py"]
