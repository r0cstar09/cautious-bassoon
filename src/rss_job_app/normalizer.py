from typing import Dict

def normalize_entry(entry) -> Dict:
    """Normalize a feedparser entry into a simple job dict."""
    content = ""
    if hasattr(entry, "summary"):
        content = entry.summary
    elif hasattr(entry, "content") and entry.content:
        # feedparser content is a list of dicts
        content = entry.content[0].value if isinstance(entry.content, list) else entry.content

    job = {
        "id": getattr(entry, "id", getattr(entry, "link", None)),
        "title": getattr(entry, "title", ""),
        "link": getattr(entry, "link", ""),
        "published": getattr(entry, "published", ""),
        "company": getattr(entry, "author", ""),
        "location": getattr(entry, "location", ""),
        "content": content,
    }
    return job
