import os
import importlib
from typing import List
import re


def _init_openai():
    # import openai lazily so running in --dry-run doesn't require the package
    openai = importlib.import_module("openai")

    # Require modern SDK (AzureOpenAI client class available in openai>=1.0.0).
    if not hasattr(openai, "AzureOpenAI"):
        raise RuntimeError(
            "openai package installed does not appear to be the modern SDK.\n"
            "Please upgrade: pip install --upgrade openai (requires openai>=1.0.0)."
        )

    # Azure OpenAI configuration from environment variables
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    
    if not api_key or not api_base:
        raise RuntimeError(
            "Missing required Azure OpenAI credentials. "
            "Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables."
        )

    # For Azure OpenAI with modern SDK, use AzureOpenAI client (not OpenAI client)
    # The azure_endpoint should be the base URL without trailing slash
    # AzureOpenAI automatically constructs the correct API paths
    azure_endpoint = api_base.rstrip("/")
    client = openai.AzureOpenAI(
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version=api_version
    )
    globals()["openai_client"] = client
    globals()["openai"] = openai
    globals()["api_version"] = api_version


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
    # Get deployment name from environment variable
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    if not deployment:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENT environment variable is required")

    messages = [
        {
            "role": "system", 
            "content": "You output only numbers. Respond with a single decimal number between 0.0 and 1.0. No text, no explanation, just the number."
        },
        {
            "role": "user",
            "content": f"Score (0.0-1.0):\n\nJob: {job_text[:800]}\n\nResume: {master_resume[:800]}\n\nScore:"
        },
    ]

    # Use new client API when available, otherwise try legacy module API
    client = globals().get("openai_client")
    if not client:
        raise RuntimeError("OpenAI client not initialized; ensure openai>=1.0.0 is installed and _init_openai() ran successfully")
    try:
        resp = client.chat.completions.create(
            model=deployment, 
            messages=messages, 
            max_completion_tokens=200
        )
        # Handle potential None content
        choice = resp.choices[0]
        content = choice.message.content
        
        # Check finish reason
        finish_reason = getattr(choice, 'finish_reason', None)
        
        if content is None:
            print(f"Warning: Model returned None content. Finish reason: {finish_reason}")
            return 0.0
        
        text = content.strip() if content else ""
        
        # If response was truncated, try to extract what we have
        if finish_reason == "length":
            print(f"Warning: Response was truncated (hit token limit). Partial response: '{text}'")
            # Still try to parse what we got - might be a partial number
        
        # Debug: print the raw response if empty
        if not text:
            print(f"Warning: Model returned empty string. Finish reason: {finish_reason}, Content type: {type(content)}")
            return 0.0
    except Exception as e:
        msg = str(e)
        if "Incorrect API key" in msg or "platform.openai.com" in msg or "invalid_api_key" in msg or "401" in msg:
            raise RuntimeError(
                "Authentication to OpenAI failed.\n"
                "If you are using Azure OpenAI, ensure `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` are set to your Azure resource key and endpoint (not an OpenAI platform key).\n"
                "If you are using OpenAI platform keys, set OPENAI_API_KEY and do not set AZURE_OPENAI_ENDPOINT.\n"
                f"Details: {msg}"
            )
        raise

    # Try to extract a float from the model output
    # Look for decimal numbers between 0 and 1 (e.g., 0.75, 0.82, 1.0, 0.5)
    # More flexible pattern: matches 0-1 with optional decimal part
    patterns = [
        r"0\.\d+",  # Matches 0.xx
        r"1\.0+",   # Matches 1.0, 1.00, etc.
        r"1",       # Matches just 1
        r"0",       # Matches just 0
        r"\b0?\.\d+\b",  # Matches .75, .82, etc.
    ]
    
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            try:
                val = float(m.group(0))
                # Clamp to [0,1] and return
                return max(0.0, min(1.0, val))
            except (ValueError, AttributeError):
                continue
    
    # If no pattern matched, try to convert the whole text to float
    try:
        val = float(text)
        return max(0.0, min(1.0, val))
    except (ValueError, TypeError):
        # If all else fails, print debug info and return 0.0
        print(f"Warning: Could not parse score from model response: '{text}'")
        return 0.0


def generate_application(job: dict, master_resume: str) -> dict:
    """Generate tailored resume and cover letter using Azure OpenAI chat deployment.

    Requires env var AZURE_OPENAI_CHAT_DEPLOYMENT for the chat model deployment.
    """
    _init_openai()
    # Get deployment name from environment variable
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    if not deployment:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENT environment variable is required")

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
    client = globals().get("openai_client")
    if not client:
        raise RuntimeError("OpenAI client not initialized; ensure openai>=1.0.0 is installed and _init_openai() ran successfully")
    try:
        resp_resume = client.chat.completions.create(model=deployment, messages=messages, max_completion_tokens=2000)
        resume_text = resp_resume.choices[0].message.content.strip()
    except Exception as e:
        msg = str(e)
        if "Incorrect API key" in msg or "platform.openai.com" in msg or "invalid_api_key" in msg or "401" in msg:
            raise RuntimeError(
                "Authentication to OpenAI failed while generating resume.\n"
                "If you are using Azure OpenAI, ensure `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` are set to your Azure resource key and endpoint (not an OpenAI platform key).\n"
                f"Details: {msg}"
            )
        raise

    # Generate cover letter
    messages = [
        {"role": "system", "content": "You are an expert cover letter writer."},
        {"role": "user", "content": f"Job posting:\n{job_text}\n\nMaster resume:\n{master_resume}\n\n{cover_prompt}"},
    ]
    if not client:
        raise RuntimeError("OpenAI client not initialized; ensure openai>=1.0.0 is installed and _init_openai() ran successfully")
    try:
        resp_cover = client.chat.completions.create(model=deployment, messages=messages, max_completion_tokens=1500)
        cover_text = resp_cover.choices[0].message.content.strip()
    except Exception as e:
        msg = str(e)
        if "Incorrect API key" in msg or "platform.openai.com" in msg or "invalid_api_key" in msg or "401" in msg:
            raise RuntimeError(
                "Authentication to OpenAI failed while generating cover letter.\n"
                "If you are using Azure OpenAI, ensure `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` are set to your Azure resource key and endpoint (not an OpenAI platform key).\n"
                f"Details: {msg}"
            )
        raise

    return {"resume": resume_text, "cover_letter": cover_text}
