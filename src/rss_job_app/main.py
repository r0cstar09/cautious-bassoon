import os
import argparse
from pathlib import Path
from .rss import fetch_feed
from .normalizer import normalize_entry
from .scorer import score_job_against_resume
from .azure_client import generate_application


def load_master_resume(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_application(outdir: Path, job_id: str, app: dict):
    outdir.mkdir(parents=True, exist_ok=True)
    base = outdir / (job_id.replace("/", "_")[:120])
    (base.with_suffix(".resume.txt")).write_text(app["resume"], encoding="utf-8")
    (base.with_suffix(".cover.txt")).write_text(app["cover_letter"], encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Fetch RSS job posts and generate tailored applications.")
    p.add_argument("--feed", required=True, help="RSS/Atom feed URL to poll")
    p.add_argument("--master", required=True, help="Path to master resume (markdown/plain text)")
    p.add_argument("--threshold", type=float, default=0.7, help="Similarity threshold (0-1) to generate apps")
    p.add_argument("--out", default="applications", help="Output directory")
    args = p.parse_args()

    master = load_master_resume(args.master)
    outdir = Path(args.out)

    for entry in fetch_feed(args.feed):
        job = normalize_entry(entry)
        score = score_job_against_resume(job.get("content", ""), master)
        print(f"Job {job.get('title')} score={score:.3f}")
        if score >= args.threshold:
            print(f"  -> Generating application for {job.get('title')}")
            app = generate_application(job, master)
            job_id = job.get("id") or job.get("link") or job.get("title")
            save_application(outdir, str(job_id), app)


if __name__ == "__main__":
    main()
