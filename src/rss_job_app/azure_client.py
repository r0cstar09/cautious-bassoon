import os
import openai
from typing import List
import re


def _init_openai():
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_type = os.getenv("AZURE_OPENAI_API_TYPE", "azure")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    if not api_key or not api_base:
        raise RuntimeError("Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables")
    openai.api_type = api_type
    openai.api_key = api_key
    openai.api_base = api_base
    openai.api_version = api_version


def get_embedding(text: str) -> List[float]:
    """Get embedding vector for text using Azure OpenAI embedding deployment.

    Requires env var AZURE_OPENAI_EMBEDDING_DEPLOYMENT to be set to deployment name.
    """
    raise RuntimeError("Embeddings were removed from this build. Use LLM scoring instead.")


def score_relevance_via_llm(job_text: str, master_resume: str) -> float:
    """Ask the chat model to rate relevance between job and resume. Returns score 0.0-1.0.

    Uses `AZURE_OPENAI_CHAT_DEPLOYMENT` for the model deployment.
    """
    _init_openai()
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    if not deployment:
        raise RuntimeError("Set AZURE_OPENAI_CHAT_DEPLOYMENT environment variable")

    prompt = (
        "You are an assistant that rates how well a candidate's master resume matches a job posting.\n"
        "Given the job posting and master resume, return a single numeric relevance score between 0 and 1,"
        " where 1 means perfect match and 0 means no relevance. Return only the numeric value (e.g. 0.82)"
    )

    messages = [
        {"role": "system", "content": "You are a strict scorer that outputs only a numeric score between 0 and 1."},
        {
            "role": "user",
            "content": f"Job posting:\n{job_text}\n\nMaster resume:\n{master_resume}\n\n{prompt}",
        },
    ]

    resp = openai.ChatCompletion.create(engine=deployment, messages=messages, max_tokens=10)
    text = resp["choices"][0]["message"]["content"].strip()

    # Try to extract a float from the model output
    m = re.search(r"([0-1](?:\.[0-9]+)?)", text)
    if not m:
        try:
            return float(text)
        except Exception:
            return 0.0
    try:
        val = float(m.group(1))
    except Exception:
        val = 0.0
    # Clamp to [0,1]
    return max(0.0, min(1.0, val))


def generate_application(job: dict, master_resume: str) -> dict:
    """Generate tailored resume and cover letter using Azure OpenAI chat deployment.

    Requires env var AZURE_OPENAI_CHAT_DEPLOYMENT for the chat model deployment.
    """
    _init_openai()
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    if not deployment:
        raise RuntimeError("Set AZURE_OPENAI_CHAT_DEPLOYMENT environment variable")

    # load prompts from env if provided, otherwise inline
    resume_prompt = os.getenv("RESUME_PROMPT") or (
        "Create a tailored resume from the master resume focusing on the job posting. Return only the resume text."
    )
    cover_prompt = os.getenv("COVER_LETTER_PROMPT") or (
        "Write a concise, persuasive cover letter tailored to the job posting and the applicant's master resume. Return only the cover letter text."
    )

    job_text = job.get("content") or job.get("title")

    # Generate resume
    messages = [
        {"role": "system", "content": "You are an expert resume writer."},
        {"role": "user", "content": f"Job posting:\n{job_text}\n\nMaster resume:\n{master_resume}\n\n{resume_prompt}"},
    ]
    resp_resume = openai.ChatCompletion.create(engine=deployment, messages=messages, max_tokens=1200)
    resume_text = resp_resume["choices"][0]["message"]["content"].strip()

    # Generate cover letter
    messages = [
        {"role": "system", "content": "You are an expert cover letter writer."},
        {"role": "user", "content": f"Job posting:\n{job_text}\n\nMaster resume:\n{master_resume}\n\n{cover_prompt}"},
    ]
    resp_cover = openai.ChatCompletion.create(engine=deployment, messages=messages, max_tokens=800)
    cover_text = resp_cover["choices"][0]["message"]["content"].strip()

    return {"resume": resume_text, "cover_letter": cover_text}
