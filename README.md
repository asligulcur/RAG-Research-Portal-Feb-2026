# Phase 3 - Research-Grade RAG System

## Project Overview
This repository contains a Research-Grade RAG (Retrieval-Augmented Generation) system built for Small Language Models (SLMs) research.

**Main Research Question**: What are the performance gaps and comparative advantages of small language models (<7B parameters) versus large language models, and what technical advances would enable small models to match or surpass larger models in specific domains?

### Sub-Questions
1. **Performance Gaps**: Where do small models currently underperform large models, and by how much?
2. **Current Advantages**: In which tasks or contexts do small models already match or exceed large models?
3. **Technical Enablers**: What techniques most effectively close the performance gap?
4. **Deployment Benefits**: What practical advantages give small models structural benefits?
5. **Fundamental Limits**: What do scaling laws suggest about the limits of small vs. large models?
6. **Future Pathways**: What innovations could enable small models to surpass large models in reasoning tasks?

## Quick Start (5-minute setup)

### Prerequisites
- Python 3.9+
- pip
- OpenAI API key (for generation)

### Option 1: Automated Setup (Recommended for Graders)
```bash
# 1. Extract the submission
unzip "PHASE_3_SUBMISSION.zip"
cd "PHASE 3 SUBMISSION"

# 2. Create .env file with your API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 3. Run the automated setup script (installs deps + runs evaluation)
./setup_and_run.sh
```

**Note**: Make sure you're in the `PHASE 3 SUBMISSION` directory before running `./setup_and_run.sh`. If you're in the parent directory, use: `cd "PHASE 3 SUBMISSION" && ./setup_and_run.sh`

The script will:
- Create a virtual environment
- Install all dependencies (required for Phase 3 portal)
- Run the full evaluation (25 queries)
- Show results location

**Note**: Full evaluation (25 queries) takes approximately 5–10 minutes due to API rate limits. Results appear in the Evaluation Dashboard after completion.

After this, run `./run_app.sh` to start the Phase 3 portal.

### Option 2: Manual Setup
```bash
# 1. Navigate to directory
cd "PHASE 3 SUBMISSION"

# 2. Create venv and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r repo/requirements.txt

# 3. Set up environment variables
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 4. (Optional) Run evaluation
python src/eval/run_evaluation.py
```

After this, run `./run_app.sh` to start the Phase 3 portal.

### Phase 3: Personal Research Portal (Streamlit UI)

**Run Option 1 or 2 first** to install dependencies. Then start the portal:

```bash
# From PHASE 3 SUBMISSION directory (after running Option 1 or 2):
./run_app.sh
# Or: streamlit run src/app/app.py
```

The portal provides: Search & Ask, Research Threads, Artifact Generator (Evidence Table, Annotated Bibliography, Synthesis Memo), Evaluation Dashboard, Source Library, Export Center.

### Additional Commands
```bash
# Run a single query
python src/rag/query.py "How do small models compare to large models on reasoning tasks?"

# Optional: Rebuild corpus from scratch (if you modify PDFs)
python src/ingest/run_ingestion.py     # Re-parse PDFs
python src/rag/embeddings.py           # Re-create embeddings
```

**Note**: The corpus (30 papers) and embeddings (2,813 chunks) are already prepared and included. You can run evaluation immediately after setup.

## Project Structure
```
PHASE 3 SUBMISSION/
├── repo/
│   ├── README.md              # This file
│   └── requirements.txt       # Python dependencies
├── requirements.txt           # Root deps (includes repo/requirements.txt)
├── .env.example               # Environment variable template
├── .streamlit/                # Streamlit config (config.toml)
├── Makefile                   # One-command run paths
├── setup_and_run.sh           # Automated setup script
├── run_app.sh                 # Run Phase 3 Streamlit portal
├── .gitignore                 # Git configuration
├── data/
│   ├── raw/                   # Downloaded PDFs (30 sources)
│   ├── processed/             # Parsed text and chunks
│   └── data_manifest.csv      # Source metadata
├── src/
│   ├── app/                   # Phase 3: Streamlit portal (Search & Ask, Artifacts, Evaluation, Export)
│   ├── ingest/                # PDF parsing and chunking
│   ├── rag/                   # Retrieval and generation
│   └── eval/                  # Evaluation queries and metrics
├── scripts/
│   └── generate_report_artifacts.py  # Generate report artifacts (k=10)
├── logs/                      # System logs (eval_runs/, ingestion_log.json)
├── outputs/                   # Evaluation results, artifacts, threads
│   ├── embeddings/            # Chunk embeddings and metadata
│   ├── artifacts/            # Portal-generated artifacts (evidence table, memo, bib)
│   ├── threads/              # Saved research threads
│   └── evaluation_results_*.json  # Evaluation run results
├── report/                    # Evaluation reports and documentation
│   ├── final_evaluation_report.md   # Final report (Phase 2+3)
│   ├── final_evaluation_report.html
│   ├── phase2_evaluation_report.md  # Phase 2 evaluation report
│   ├── phase2_evaluation_report.html
│   ├── artifacts/             # Curated artifacts (llama_small_models_*)
│   ├── images/                # Architecture diagrams
│   ├── README.md              # Report conversion instructions
│   ├── Phase 2 Evaluation Report.pdf
│   └── Phase 2 RAG System Diagram - Asli Gulcur.pdf  # System architecture diagram
└── appendix/                  # Additional documentation
    └── ai_usage_log.md        # AI tools disclosure
```

## Corpus Overview
- **30 peer-reviewed papers** from arXiv (manual curation; script + manual download). Domain: Small Language Models (<7B) — architectures, evaluation, optimization, training.
- **Raw PDFs**: If `data/raw/` is empty, run the download script in `src/ingest/`. Full metadata: `data/data_manifest.csv`.

## Key Features
- ✅ **Trust behaviors**: Refuses to fabricate citations (100% flagging); graceful refusal when no evidence matches.
- ✅ **Citation-backed answers**: GPT-4; `[Source: X, Chunk: Y]` format; citation chips; status strip; amber/red warnings for partial or invalid citations.
- ✅ **Phase 3 portal**: Search & Ask, Evidence Explorer, Research Threads, Artifact Generator (Evidence Table, Annotated Bibliography, Synthesis Memo), Evaluation Dashboard, Source Library, Export Center. Navigation: Generate Artifact pre-fills; Resume Query from Threads.
- ✅ **LLM API guard**: Exponential backoff on 429, 1 req/sec throttle. See `src/rag/llm_guard.py`.
- ✅ **Retrieval**: Section-aware chunking; metadata filtering (year, tags, model type)
- ✅ **Logging**: Queries, retrieved chunks, prompt versions.

## Evaluation
- **Query set**: 25 queries (10 direct, 8 synthesis, 7 edge cases)
- **Metrics**: Groundedness (citation accuracy) + Answer Relevance (topical alignment)
- **Trust Behavior**: Tested with 5 adversarial queries, 100% flagging rate achieved
- See `report/final_evaluation_report.md` for full analysis (includes trust behavior improvement iteration)

## Attribution
**Author**: Asli Gulcur  
**Date**: February 2026  
**Course**: AI Model Development — Phase 1 + Phase 2 + Phase 3  

## AI Usage Disclosure
See `appendix/ai_usage_log.md` for AI tools used in development.
