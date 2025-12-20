# RSS -> Azure OpenAI Application Generator

This project fetches job postings from an RSS/Atom feed, normalizes them, scores each job for relevance against a master resume using embeddings, and for sufficiently relevant jobs generates a tailored resume and cover letter via Azure OpenAI.

Setup

1. Create a Python venv and install dependencies:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Environment variables (required):

- `AZURE_OPENAI_API_KEY` — your Azure OpenAI key
- `AZURE_OPENAI_ENDPOINT` — your Azure OpenAI endpoint (e.g. https://your-resource.openai.azure.com)
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` — deployment name for embeddings
- `AZURE_OPENAI_CHAT_DEPLOYMENT` — deployment name for chat/completions

Optional:
- `AZURE_OPENAI_API_VERSION` — default 2023-05-15

Usage

Run the CLI with a feed and a master resume:

   python -m src.rss_job_app.main --feed "https://example.com/jobs.rss" --master sample_master_resume.md --threshold 0.7 --out applications

Files

- `src/rss_job_app/rss.py` — fetch RSS entries
- `src/rss_job_app/normalizer.py` — normalize feed entries to job dicts
- `src/rss_job_app/scorer.py` — compute embedding similarity scores
- `src/rss_job_app/azure_client.py` — Azure OpenAI wrapper for embeddings and generation
- `src/rss_job_app/main.py` — orchestrator CLI

Notes

- The scoring uses the chat model to rate relevance (embeddings removed). This increases API calls because the app will call the chat model once per job to compute a score; set `--threshold` accordingly.
- For production, consider batching, caching, or switching back to embeddings to reduce cost and latency. Also add retry/error handling and rate-limit safeguards.
