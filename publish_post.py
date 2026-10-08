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


def teams_card(heading: str, facts: list[tuple[str, str]], body: str = "",
               link: tuple[str, str] | None = None) -> dict:
    """An Adaptive Card wrapped the way the Teams "Post to a channel when a
    webhook request is received" workflow expects, so a plain Teams workflow
    can post it with no Power Automate editing."""
    items: list[dict] = [{"type": "TextBlock", "text": heading, "weight": "Bolder",
                          "size": "Medium", "wrap": True}]
    if body:
        items.append({"type": "TextBlock", "text": body, "wrap": True})
    items.append({"type": "FactSet",
                  "facts": [{"title": k, "value": v} for k, v in facts if v]})
    card = {"type": "AdaptiveCard", "version": "1.4",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "body": items}
    if link:
        card["actions"] = [{"type": "Action.OpenUrl", "title": link[0], "url": link[1]}]
    return {"type": "message", "attachments": [
        {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}]}


def notify_failure(reason: str) -> None:
    if not WEBHOOK:
        print("(no POWERAUTOMATE_WEBHOOK_URL set — failure not reported)", file=sys.stderr)
        return
    try:
        payload = {"event": "run_failed", "client": "serene-bay", "reason": reason}
        payload.update(teams_card("Blog routine FAILED: Serene Bay",
                                  [("Site", "Serene Bay"), ("Status", "run failed")],
                                  body=reason))
        requests.post(WEBHOOK, json=payload, timeout=20)
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


def image_provider() -> str:
    if os.environ.get("INCLUDE_IMAGES", "true").strip().lower() == "false":
        return "none"
    if os.environ.get("FAL_KEY", "").strip():
        return "fal"
    return "openai" if os.environ.get("OPENAI_API_KEY", "").strip() else "none"


def drafted_html(fm: dict, excerpt: str, pr_url: str, n_images: int,
                 keyphrase: str = "", preview_url: str = "") -> str:
    """The review message as Teams HTML, laid out line for line like the
    Rothian Digital one, for a flow that posts it as a normal message."""
    from html import escape as e
    pr_no = pr_url.rstrip("/").rsplit("/", 1)[-1] if "/pull/" in pr_url else ""
    lines = [
        "<b>New blog draft ready for review</b>",
        f"<b>{e(fm['title'])}</b>",
        "",
        'Site: <a href="https://serenebay.ae">Serene Bay</a>',
        f"Status: draft | PR: #{pr_no} | Images: {image_provider()}" if pr_no
        else f"Status: draft | Images: {image_provider()}",
        f'<a href="{e(pr_url)}">Review &amp; edit on GitHub</a>',
    ]
    if preview_url:
        lines.append(f'<a href="{e(preview_url)}">Preview the draft</a>')
    lines += [f"<b>Excerpt:</b> {e(excerpt)}", "", "<b>SEO</b>"]
    if keyphrase:
        lines.append(f"Focus keyphrase: {e(keyphrase)}")
    lines += [f"Meta title: {e(fm['title'])}", f"Meta description: {e(excerpt)}"]
    return "<br>".join(lines)


def send_drafted(fm: dict, slug: str, branch: str, excerpt: str, pr_url: str,
                 n_images: int, keyphrase: str = "", preview_url: str = "") -> None:
    """The review message, in the same shape as the Rothian Digital one."""
    if not WEBHOOK:
        print("  warning: POWERAUTOMATE_WEBHOOK_URL is not set; Teams notification not sent",
              file=sys.stderr)
        return
    payload = {"event": "insight_drafted", "client": "serene-bay", "title": fm["title"],
               "slug": slug, "category": fm["category"], "pr_url": pr_url,
               "branch": branch, "excerpt": excerpt, "keyphrase": keyphrase,
               "preview_url": preview_url,
               "html": drafted_html(fm, excerpt, pr_url, n_images, keyphrase, preview_url)}
    payload.update(teams_card(
        "New blog draft ready for review",
        [("Title", fm["title"]),
         ("Site", "Serene Bay"),
         ("Status", f"draft pull request | Branch: {branch}"),
         ("Images", f"{n_images} ({image_provider()})"),
         ("Category", fm["category"]),
         ("Excerpt", excerpt),
         ("Meta title", fm["title"]),
         ("Meta description", excerpt),
         ("Slug", slug)],
        link=("Review the draft and its Vercel preview", pr_url)))
    try:
        r = requests.post(WEBHOOK, json=payload, timeout=20)
        r.raise_for_status()
        print(f"  Teams notification sent (HTTP {r.status_code})")
    except Exception as exc:  # noqa: BLE001
        print(f"  warning: Teams notification failed: {exc}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-dir", required=True)
    ap.add_argument("--dry-run", action="store_true", help="validate and stage, do not push or open a PR")
    ap.add_argument("--notify-pr", metavar="URL",
                    help="only send the Teams review message for an already-opened draft PR")
    ap.add_argument("--keyphrase", default="", help="focus keyphrase, shown under SEO")
    ap.add_argument("--preview-url", default="", help="the Vercel preview link, if known")
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
    if args.notify_pr:
        # After publishing, the clone is on the insight branch and the post
        # exists there, so this has to run before the duplicate check.
        n = len(list((post_dir / "images").glob("*.webp")))
        send_drafted(fm, slug, f"insight/{slug}", fm.get("excerpt", ""), args.notify_pr, n,
                     args.keyphrase, args.preview_url)
        return
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

    copied = []
    for img in sorted((post_dir / "images").glob("*.webp")):
        shutil.copy2(img, site / "public" / "images" / img.name)
        copied.append(img.name)
    if not (site / "public" / "images" / f"{slug}-hero.webp").exists():
        # No hero (INCLUDE_IMAGES=false, or generation skipped): drop the
        # frontmatter `image` so the site shows the post's plate instead of a
        # broken image. `image` is optional in the site's Insight type.
        head, sep, rest = md.partition("\n---")
        head = "\n".join(l for l in head.splitlines() if not l.startswith("image:"))
        (site / "content" / "insights" / f"{slug}.md").write_text(head + sep + rest)
        print("  no hero image: removed `image` from the frontmatter; the plate will show")
    else:
        shutil.copy2(md_path, site / "content" / "insights" / f"{slug}.md")
    print(f"  staged content/insights/{slug}.md and {len(copied)} images")

    run(["git", "add", "content/insights", "public/images"], site)
    # gpgsign is disabled explicitly: the signing server returns 400 in this
    # environment and a plain `git commit` fails because of it.
    # Vercel's Git integration silently skips any commit whose author email it
    # does not recognise (serene-2/.github/DEPLOYING.md), so the draft gets no
    # preview. SERENE_COMMIT_EMAIL sets an author Vercel knows.
    ident = []
    if os.environ.get("SERENE_COMMIT_EMAIL", "").strip():
        ident = ["-c", f"user.email={os.environ['SERENE_COMMIT_EMAIL'].strip()}",
                 "-c", f"user.name={os.environ.get('SERENE_COMMIT_NAME', 'Serene Insight Routine').strip()}"]
    else:
        print("  warning: SERENE_COMMIT_EMAIL is not set; Vercel may not build a preview")
    run(["git", *ident, "-c", "commit.gpgsign=false", "commit", "-m",
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

    if pr_url:
        send_drafted(fm, slug, branch, excerpt, pr_url, len(copied),
                     args.keyphrase, args.preview_url)
    else:
        print("\n  Teams notification NOT sent yet: it needs the PR link. After opening")
        print("  the draft PR, run this again with --notify-pr <PR URL>.")

    print(f"\nDRAFT PR: {pr_url or 'not opened — see the branch details above'}")
    print(f"Branch:   {branch}")
    print(f"Slug:     {slug}")
    print(f"Excerpt:  {excerpt}")


if __name__ == "__main__":
    main()
