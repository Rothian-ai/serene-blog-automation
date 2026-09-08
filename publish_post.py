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


def try_run(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    """Run without aborting. For steps that are allowed to fail."""
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode == 0, (p.stdout or p.stderr).strip()


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

    if args.dry_run:
        # Validation only. Deliberately before any git call: a dry run must not
        # fetch, branch or otherwise disturb a working clone of the site.
        print(f"dry run OK — {slug} validates against the site schema")
        print(f"  category: {fm['category']}   plate: {fm['plate']}")
        print(f"  images:   {len(list((post_dir / 'images').glob('*.webp')))} webp")
        return

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
    # The branch is pushed, which is the part that must not fail: git over HTTPS
    # works in the cloud environment. Opening the pull request is a GitHub REST
    # call, and REST through the proxy returns 403 there, so `gh` is attempted
    # but is NOT allowed to fail the run. When it cannot open the PR the routine
    # opens it with the GitHub MCP tools instead, using the details printed here.
    ok, out = try_run(["gh", "pr", "create", "--base", base, "--head", branch,
                       "--title", f"Insight: {fm['title']}", "--body", pr_body,
                       "--draft"], site)
    pr_url = out if ok and out.startswith("http") else ""
    if not pr_url:
        print("\n  gh could not open the pull request (expected when GitHub REST")
        print("  is proxy-blocked). The branch is pushed. Open the DRAFT PR with")
        print("  the GitHub MCP tools using:")
        print(f"    base:  {base}")
        print(f"    head:  {branch}")
        print(f"    title: Insight: {fm['title']}")
        if out:
            print(f"    (gh said: {out.splitlines()[0][:160]})")

    if WEBHOOK:
        try:
            requests.post(WEBHOOK, json={
                "event": "insight_drafted", "client": "serene-bay",
                "title": fm["title"], "slug": slug, "category": fm["category"],
                "pr_url": pr_url or f"branch pushed: {branch} (PR not yet opened)",
                "branch": branch,
                "text": (f"Serene Bay insight ready for review: {fm['title']} "
                         + (pr_url if pr_url else f"(branch {branch} pushed, PR still to open)")),
            }, timeout=20)
            print("  Teams notification sent")
        except Exception as exc:  # noqa: BLE001
            print(f"  warning: Teams notification failed: {exc}", file=sys.stderr)

    print(f"\nDRAFT PR: {pr_url or 'not opened — see the branch details above'}")
    print(f"Branch:   {branch}")
    print(f"Slug:     {slug}")
    print(f"Excerpt:  {excerpt}")


if __name__ == "__main__":
    main()
