import os
import argparse
import json
import smtplib
import ssl
import subprocess
import re
from pathlib import Path
from typing import List
import shutil
import glob

from dotenv import load_dotenv

from .rss import fetch_feed
from .normalizer import normalize_entry
from .scorer import score_job_against_resume
from .azure_client import generate_application


load_dotenv()


def load_master_resume(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """Convert job title to a safe filename by removing/replacing invalid characters."""
    if not title:
        return "untitled_job"
    
    # Remove or replace invalid filename characters
    # Replace common problematic characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', title)
    # Replace multiple spaces/underscores with single underscore
    sanitized = re.sub(r'[\s_]+', '_', sanitized)
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_.')
    # Limit length
    sanitized = sanitized[:max_length]
    
    # If empty after sanitization, use fallback
    if not sanitized:
        sanitized = "untitled_job"
    
    return sanitized


def save_application(outdir: Path, job_title: str, app: dict):
    """Save resume and cover letter files in a folder named after the job title."""
    outdir.mkdir(parents=True, exist_ok=True)
    safe_title = sanitize_filename(job_title)
    # Create a folder for this job
    job_folder = outdir / safe_title
    job_folder.mkdir(parents=True, exist_ok=True)
    # Save files inside the job folder
    (job_folder / "resume.txt").write_text(app["resume"], encoding="utf-8")
    (job_folder / "cover_letter.txt").write_text(app["cover_letter"], encoding="utf-8")


def _convert_markdown_to_docx(md_path: Path) -> Path:
    """Convert a markdown file to docx. Returns path to created docx.

    Tries pypandoc, otherwise falls back to calling the `pandoc` CLI.
    """
    out_path = md_path.with_suffix(".docx")
    try:
        import pypandoc

        pypandoc.convert_file(str(md_path), "docx", outputfile=str(out_path))
        return out_path
    except Exception:
        pandoc_bin = shutil.which("pandoc")
        if not pandoc_bin:
            raise RuntimeError("pandoc not found; install pandoc or pypandoc to enable conversion")
        subprocess.run([pandoc_bin, "-f", "markdown", "-t", "docx", "-o", str(out_path), str(md_path)], check=True)
        return out_path


def _load_history(history_path: Path) -> List[str]:
    if not history_path.exists():
        return []
    try:
        return json.loads(history_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_history(history_path: Path, ids: List[str]):
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(ids, indent=2), encoding="utf-8")


def _send_email(subject: str, body: str):
    # Email configuration from environment variables
    email_from = os.getenv("EMAIL_FROM")
    email_to = os.getenv("EMAIL_TO")
    email_password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.mail.me.com")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    
    if not (email_from and email_to and email_password):
        print("Email credentials not fully set; skipping email")
        return

    message = f"Subject: {subject}\n\n{body}"

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(email_from, email_password)
            server.sendmail(email_from, email_to.split(","), message.encode("utf-8"))
        print("Sent summary email to", email_to)
    except Exception as e:
        print("Failed to send email:", e)


def main():
    p = argparse.ArgumentParser(description="Fetch RSS job posts and generate tailored applications.")
    p.add_argument("--feed", required=True, help="RSS/Atom feed URL to poll")
    p.add_argument("--master", default="sample_master_resume.md", help="Path to master resume (markdown/plain text) (default: sample_master_resume.md)")
    p.add_argument("--threshold", type=float, default=0.7, help="Similarity threshold (0-1) to generate apps")
    p.add_argument("--out", default="applications", help="Output directory")
    p.add_argument("--dry-run", action="store_true", help="Fetch and show jobs without calling the OpenAI API")
    p.add_argument("--to-docx", action="store_true", help="Convert generated markdown resumes and cover letters to DOCX (requires pandoc or pypandoc)")
    p.add_argument("--limit", type=int, default=None, help="Limit the number of jobs to process (useful for testing)")
    args = p.parse_args()

    master = load_master_resume(args.master)
    print(f"Using master resume: {args.master}")
    outdir = Path(args.out)

    history_path = outdir / ".history.json"
    prior_ids = _load_history(history_path)

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
    new_ids: List[str] = []
    generated_files: List[Path] = []

    job_count = 0
    for entry in fetch_feed(args.feed):
        if args.limit and job_count >= args.limit:
            print(f"Reached limit of {args.limit} jobs. Stopping.")
            break
        
        job = normalize_entry(entry)
        score = score_job_against_resume(job.get("content", ""), master)
        print(f"Job {job.get('title')} score={score:.3f}")
        job_count += 1
        if score >= args.threshold:
            job_title = job.get("title") or "Untitled Job"
            job_id = job.get("id") or job.get("link") or job_title
            safe_title = sanitize_filename(job_title)
            job_folder = outdir / safe_title
            
            # Check if folder already exists (duplicate job)
            if job_folder.exists() and job_folder.is_dir():
                print(f"  -> Skipping {job_title} (folder already exists)")
                # Still add to history to track we've seen it
                if str(job_id) not in prior_ids:
                    new_ids.append(str(job_id))
                continue
            
            print(f"  -> Generating application for {job.get('title')}")
            app = generate_application(job, master)
            save_application(outdir, job_title, app)
            resume_path = job_folder / "resume.txt"
            cover_path = job_folder / "cover_letter.txt"
            generated_files.extend([resume_path, cover_path])
            if str(job_id) not in prior_ids:
                new_ids.append(str(job_id))

            if args.to_docx:
                # convert each to docx immediately
                for md in (resume_path, cover_path):
                    try:
                        docx = _convert_markdown_to_docx(md)
                        print(f"Converted {md} -> {docx}")
                    except Exception as e:
                        print(f"Conversion failed for {md}: {e}")

    # update history
    all_ids = list(set(prior_ids + new_ids))
    _save_history(history_path, all_ids)

    # send email summary if EMAIL_* vars present and not dry-run
    if new_ids:
        subject = f"Job Application Generator: {len(new_ids)} new applications generated"
        lines = [f"Generated {len(new_ids)} new applications:"]
        for jid in new_ids:
            lines.append(f"- {jid}")
        body = "\n".join(lines)
        _send_email(subject, body)
    else:
        print("No new applications generated since last run.")


if __name__ == "__main__":
    main()
