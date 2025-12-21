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
    p.add_argument("--master", default="sample_master_resume.md", help="Path to master resume (markdown/plain text) (default: sample_master_resume.md)")
    p.add_argument("--threshold", type=float, default=0.7, help="Similarity threshold (0-1) to generate apps")
    p.add_argument("--out", default="applications", help="Output directory")
    p.add_argument("--dry-run", action="store_true", help="Fetch and show jobs without calling the OpenAI API")
    args = p.parse_args()

    master = load_master_resume(args.master)
    print(f"Using master resume: {args.master}")
    outdir = Path(args.out)

    if args.dry_run:
        print("Dry run: fetching feed and displaying job previews (no API calls)")
        for entry in fetch_feed(args.feed):
            job = normalize_entry(entry)
            job_id = job.get("id") or job.get("link") or job.get("title")
            print("-" * 40)
            print(f"Title: {job.get('title')}")
            print(f"ID: {job_id}")
            content = job.get("content") or "(no content)"
            preview = content.replace('\n', ' ')[:400]
            print(f"Preview: {preview}")
        return

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
