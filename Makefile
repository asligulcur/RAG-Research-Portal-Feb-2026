# Makefile for Phase 2 RAG System
# One-command reproducibility

.PHONY: install ingest index query eval clean all report-pdf

# Install dependencies
install:
	pip install -r repo/requirements.txt

# Run full pipeline
all: ingest index eval

# Step 1: Ingest PDFs and create chunks
ingest:
	python src/ingest/run_ingestion.py

# Step 2: Build vector index
index:
	python src/rag/build_index.py

# Step 3: Run single query (example)
query:
	python src/rag/query.py "What are the main limitations of current RAG evaluation methods?"

# Step 4: Run full evaluation
eval:
	python src/eval/run_evaluation.py

# Convert final evaluation report to PDF (images included)
# Requires pandoc. If LaTeX missing, generates HTML — open in browser and Print → Save as PDF
report-pdf:
	./report/convert_to_pdf.sh

# Clean generated files
clean:
	rm -rf data/processed/*
	rm -rf logs/*
	rm -rf outputs/*
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Help
help:
	@echo "Phase 2 RAG System - Available commands:"
	@echo "  make install  - Install Python dependencies"
	@echo "  make ingest   - Parse PDFs and create chunks"
	@echo "  make index    - Build vector index"
	@echo "  make query    - Run example query"
	@echo "  make eval     - Run full evaluation"
	@echo "  make all      - Run complete pipeline"
	@echo "  make clean    - Remove generated files"
	@echo "  make report-pdf - Convert final evaluation report to PDF"
