#!/usr/bin/env python3
"""Post newly live Serene Bay insights to the Google Business Profile.

    python3 post_to_gbp.py --since 2026-11-05            # post at most one
    python3 post_to_gbp.py --since 2026-11-05 --dry-run  # show what would post

A Business Profile post is public the moment it is made, so this only ever
posts an insight a human has already merged and that is live on the site:
  1. it is on the production branch (SERENE_LIVE_BRANCH, `beta`) of serene-2,
     not marked `hidden: true`, and dated on or after --since;
  2. its page on serenebay.ae answers 200;
  3. the profile does not already carry a post linking to it.

The profile's own post list is the record of what has been posted (check 3), so
a run that starts from an old checkout cannot post the same insight twice.
--since keeps the insights that predate the automation from being posted.

Failure protocol, as publish_post.py: any failed step posts
{"event":"run_failed"} to the webhook and exits non-zero.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

from publish_post import WEBHOOK, fail, teams_card

TOKEN_URL = "https://oauth2.googleapis.com/token"
POSTS_API = "https://mybusiness.googleapis.com/v4/accounts/{account}/locations/{location}/localPosts"
SITE = os.environ.get("SERENE_SITE_URL", "https://www.serenebay.ae").rstrip("/")
# Business Profile posts carry at most 1,500 characters of text.
SUMMARY_LIMIT = 1500


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        fail(f"{name} is not set (see .env.example and ROUTINE-gbp.md)")
    return value


def access_token() -> str:
    r = requests.post(TOKEN_URL, data={
        "client_id": env("GBP_CLIENT_ID"), "client_secret": env("GBP_CLIENT_SECRET"),
        "refresh_token": env("GBP_REFRESH_TOKEN"), "grant_type": "refresh_token",
    }, timeout=30)
    if r.status_code != 200:
        # invalid_grant almost always means the token was revoked or expired,
        # which happens after 7 days if the consent screen is still in Testing.
        fail(f"Google sign-in failed ({r.status_code}): {r.text[:300]}. If this says "
             "invalid_grant, run gbp_auth.py again and check the OAuth consent screen is "
             "'In production'.")
    return r.json()["access_token"]


def frontmatter(md: str) -> dict:
    """The flat key: value frontmatter the site uses, as publish_post.py reads it."""
    if not md.startswith("---"):
        return {}
    out = {}
    for line in md.split("---", 2)[1].splitlines():
        m = re.match(r"^([A-Za-z]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


def git(site: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=site, capture_output=True, text=True)
    if p.returncode != 0:
        fail(f"`git {' '.join(args[:3])}` failed in {site}: {(p.stderr or p.stdout).strip()[:300]}")
    return p.stdout


def live_insights(site: Path, branch: str, since: str) -> list[dict]:
    """Insights on the production branch, oldest first. Read from origin so the
    local checkout's own branch does not matter."""
    git(site, "fetch", "--quiet", "origin", branch)
    ref = f"origin/{branch}"
    posts = []
    for path in git(site, "ls-tree", "--name-only", ref, "content/insights/").split():
        if not path.endswith(".md"):
            continue
        fm = frontmatter(git(site, "show", f"{ref}:{path}"))
        if fm.get("hidden", "").lower() == "true" or fm.get("date", "") < since:
            continue
        posts.append({"slug": Path(path).stem, **fm})
    return sorted(posts, key=lambda p: p.get("date", ""))


def is_live(url: str) -> bool:
    try:
        r = requests.get(url, timeout=30, allow_redirects=True)
    except requests.RequestException:
        return False
    # The site redirects some unknown paths elsewhere, so a 200 alone is not
    # proof: the page has to declare this insight as its canonical address.
    return r.status_code == 200 and f'rel="canonical" href="{url}"' in r.text


def photo_url(slug: str) -> str:
    """A hero the profile can take. Business Profile photos are documented as JPG
    or PNG, and the site's heroes are WebP, so a post goes without a photo unless
    a JPG or PNG copy of the hero is live. The site answers 200 with an HTML page
    for a missing image, so the content type is what proves the file exists."""
    for ext, kind in (("jpg", "image/jpeg"), ("png", "image/png")):
        url = f"{SITE}/images/{slug}-hero.{ext}"
        try:
            r = requests.head(url, timeout=20, allow_redirects=True)
        except requests.RequestException:
            continue
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith(kind):
            return url
    return ""


def posted_urls(api: str, headers: dict) -> set[str]:
    """Every link the profile's existing posts point to."""
    urls, page = set(), ""
    while True:
        r = requests.get(api, headers=headers, timeout=30,
                         params={"pageSize": 100, **({"pageToken": page} if page else {})})
        if r.status_code != 200:
            fail(f"Listing the profile's posts failed ({r.status_code}): {r.text[:300]}")
        body = r.json()
        for post in body.get("localPosts", []):
            link = (post.get("callToAction") or {}).get("url", "")
            if link:
                urls.add(link.rstrip("/"))
        page = body.get("nextPageToken", "")
        if not page:
            return urls


def payload(post: dict, url: str, photo: str) -> dict:
    summary = f"{post['title']}\n\n{post.get('excerpt', '')}".strip()[:SUMMARY_LIMIT]
    body = {"languageCode": "en", "summary": summary, "topicType": "STANDARD",
            "callToAction": {"actionType": "LEARN_MORE", "url": url}}
    if photo:
        body["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": photo}]
    return body


def notify_posted(post: dict, url: str, search_url: str, photo: str) -> None:
    if not WEBHOOK:
        print("  warning: POWERAUTOMATE_WEBHOOK_URL is not set; Teams notification not sent",
              file=sys.stderr)
        return
    message = {"event": "gbp_posted", "client": "serene-bay", "slug": post["slug"],
               "title": post["title"], "url": url, "post_url": search_url}
    message.update(teams_card(
        "Insight posted to the Business Profile",
        [("Title", post["title"]), ("Site", "Serene Bay"), ("Article", url),
         ("Photo", "yes" if photo else "none (no JPG or PNG hero on the site)")],
        link=("See the post on Google", search_url) if search_url else ("Open the article", url)))
    try:
        requests.post(WEBHOOK, json=message, timeout=20).raise_for_status()
        print("  Teams notification sent")
    except Exception as exc:  # noqa: BLE001
        print(f"  warning: Teams notification failed: {exc}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=os.environ.get("GBP_POST_SINCE", ""),
                    help="only insights dated on or after this YYYY-MM-DD (or GBP_POST_SINCE)")
    ap.add_argument("--limit", type=int, default=1, help="most posts to make in one run")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be posted; posts nothing")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.since or ""):
        fail("--since (or GBP_POST_SINCE) must be a YYYY-MM-DD date, so older insights "
             "are not posted")

    site = Path(env("SERENE_REPO_PATH")).expanduser()
    branch = os.environ.get("SERENE_LIVE_BRANCH", "beta").strip() or "beta"
    candidates = live_insights(site, branch, args.since)
    print(f"{len(candidates)} insight(s) on {branch} dated {args.since} or later")

    have_creds = all(os.environ.get(k, "").strip() for k in
                     ("GBP_CLIENT_ID", "GBP_CLIENT_SECRET", "GBP_REFRESH_TOKEN",
                      "GBP_ACCOUNT_ID", "GBP_LOCATION_ID"))
    if args.dry_run and not have_creds:
        print("  (no Business Profile credentials: skipping the check against existing posts)")
        api, headers, done = "", {}, set()
    else:
        api = POSTS_API.format(account=env("GBP_ACCOUNT_ID"), location=env("GBP_LOCATION_ID"))
        headers = {"Authorization": f"Bearer {access_token()}"}
        done = posted_urls(api, headers)

    made = 0
    for post in candidates:
        if made >= args.limit:
            break
        url = f"{SITE}/insights/{post['slug']}"
        if url in done:
            continue
        if not is_live(url):
            print(f"  skip {post['slug']}: not live at {url} yet")
            continue
        photo = photo_url(post["slug"])
        body = payload(post, url, photo)
        if args.dry_run:
            print(f"  would post {post['slug']}: {body}")
            made += 1
            continue
        r = requests.post(api, headers=headers, json=body, timeout=60)
        if r.status_code != 200:
            fail(f"Posting {post['slug']} to the Business Profile failed "
                 f"({r.status_code}): {r.text[:300]}")
        search_url = r.json().get("searchUrl", "")
        print(f"  posted {post['slug']} -> {search_url or r.json().get('name', '')}")
        notify_posted(post, url, search_url, photo)
        made += 1

    if made == 0:
        print("nothing new to post")


if __name__ == "__main__":
    main()
