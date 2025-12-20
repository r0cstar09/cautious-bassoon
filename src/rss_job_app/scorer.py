from .azure_client import score_relevance_via_llm


def score_job_against_resume(job_text: str, master_resume_text: str) -> float:
    """Return a relevance score (0-1) using the chat model to rate similarity.

    Note: this makes an API call per score and is intentionally heavier than embeddings.
    """
    return score_relevance_via_llm(job_text, master_resume_text)
