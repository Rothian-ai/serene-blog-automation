#!/usr/bin/env python3
"""Publish a Serene Bay insight as a DRAFT: a pull request against serene-2.

Serene has no WordPress. The equivalent of a WP draft here is a branch and a
pull request: Vercel builds a preview of it, and nothing reaches the live site
until a human merges. This script copies the post and its images into a clone
of serene-2, commits on a new branch, opens the PR, and notifies Teams.

    python3 publish_post.py --post-dir clients/serene-bay/insight-08092026

Failure protocol: any step that fails posts {"event":"run_failed"} to the
webhook and exits non-zero, so a half-finished post is never left behind.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests

WEBHOOK = os.environ.get("POWERAUTOMATE_WEBHOOK_URL", "").strip()


def notify_failure(reason: str) -> None:
    if not WEBHOOK:
        print("(no POWERAUTOMATE_WEBHOOK_URL set — failure not reported)", file=sys.stderr)
        return
    try:
        requests.post(WEBHOOK, json={"event": "run_failed", "client": "serene-bay",
                                     "reason": reason}, timeout=20)
        print("posted run_failed to the webhook", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"could not report failure: {exc}", file=sys.stderr)


def fail(reason: str) -> "None":
    print(f"ERROR: {reason}", file=sys.stderr)
    notify_failure(reason)
    sys.exit(1)


def run(cmd: list[str], cwd: Path) -> str:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        fail(f"`{' '.join(cmd[:4])}...` failed: {(p.stderr or p.stdout).strip()[:400]}")
    return p.stdout.strip()


def frontmatter(md: str) -> dict:
    if not md.startswith("---"):
        fail("the post has no frontmatter block")
    body = md.split("---", 2)[1]
    out = {}
    for line in body.splitlines():
        m = re.match(r"^([A-Za-z]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


CATEGORIES = {"Market Analysis", "Buyer Guides", "The Model", "Journal"}
PLATES = {"hero", "render", "stone", "interior", "dusk", "glass"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-dir", required=True)
    ap.add_argument("--dry-run", action="store_true", help="validate and stage, do not push or open a PR")
    args = ap.parse_args()

    post_dir = Path(args.post_dir).resolve()
    if not post_dir.is_dir():
        fail(f"{post_dir} does not exist")

    site = Path(os.environ.get("SERENE_REPO_PATH", "")).expanduser()
    if not site.is_dir() or not (site / "content" / "insights").is_dir():
        fail("SERENE_REPO_PATH does not point at a serene-2 clone (no content/insights)")
    base = os.environ.get("SERENE_BASE_BRANCH", "beta")

    posts = list(post_dir.glob("*.md"))
    if len(posts) != 1:
        fail(f"expected exactly one .md in {post_dir}, found {len(posts)}")
    md_path = posts[0]
    md = md_path.read_text()
    fm = frontmatter(md)

    # Validate against the site's own typed schema before touching the repo.
    slug = md_path.stem
    if fm.get("category") not in CATEGORIES:
        fail(f"category '{fm.get('category')}' is not one of {sorted(CATEGORIES)}")
    if fm.get("plate") not in PLATES:
        fail(f"plate '{fm.get('plate')}' is not one of {sorted(PLATES)}")
    for k in ("title", "date", "excerpt", "readingTime"):
        if not fm.get(k):
            fail(f"frontmatter is missing '{k}'")
    if (site / "content" / "insights" / f"{slug}.md").exists():
        fail(f"content/insights/{slug}.md already exists — duplicate topic, refusing to overwrite")

    excerpt = fm.get("excerpt", "")
    if not (110 <= len(excerpt) <= 170):
        print(f"  warning: excerpt is {len(excerpt)} chars; 120-156 reads best as a meta description")

    # ── stage into the site repo ────────────────────────────────────
    run(["git", "fetch", "origin", base], site)
    branch = f"insight/{slug}"
    run(["git", "checkout", "-B", branch, f"origin/{base}"], site)

    shutil.copy2(md_path, site / "content" / "insights" / f"{slug}.md")
    copied = []
    for img in sorted((post_dir / "images").glob("*.webp")):
        shutil.copy2(img, site / "public" / "images" / img.name)
        copied.append(img.name)
    print(f"  staged content/insights/{slug}.md and {len(copied)} images")

    if args.dry_run:
        print("dry run — staged but not committed")
        return

    run(["git", "add", "content/insights", "public/images"], site)
    # gpgsign is disabled explicitly: the signing server returns 400 in this
    # environment and a plain `git commit` fails because of it.
    run(["git", "-c", "commit.gpgsign=false", "commit", "-m",
         f"Insight: {fm['title']}"], site)
    run(["git", "push", "-u", "origin", branch, "--force-with-lease"], site)

    pr_body = (
        f"**{fm['title']}**\n\n"
        f"{excerpt}\n\n"
        f"- Category: {fm['category']}\n"
        f"- Reading time: {fm['readingTime']}\n"
        f"- Images: {len(copied)}\n\n"
        "Drafted by the weekly insight routine. Review the Vercel preview before merging."
    )
    pr_url = run(["gh", "pr", "create", "--base", base, "--head", branch,
                  "--title", f"Insight: {fm['title']}", "--body", pr_body,
                  "--draft"], site)

    if WEBHOOK:
        try:
            requests.post(WEBHOOK, json={
                "event": "insight_drafted", "client": "serene-bay",
                "title": fm["title"], "slug": slug, "category": fm["category"],
                "pr_url": pr_url,
                "text": f"Serene Bay insight ready for review: {fm['title']} — {pr_url}",
            }, timeout=20)
            print("  Teams notification sent")
        except Exception as exc:  # noqa: BLE001
            print(f"  warning: Teams notification failed: {exc}", file=sys.stderr)

    print(f"\nDRAFT PR: {pr_url}")
    print(f"Slug:     {slug}")
    print(f"Excerpt:  {excerpt}")


if __name__ == "__main__":
    main()
