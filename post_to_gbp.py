#!/usr/bin/env python3
"""Post newly live insights to a Google Business Profile.

    python3 post_to_gbp.py --since 2026-11-05            # post at most one
    python3 post_to_gbp.py --since 2026-11-05 --dry-run  # show what would post

Two sources, one per profile:
  - Serene Bay (default): insights in the serene-2 repository at SERENE_REPO_PATH.
  - Any site with a sitemap (--sitemap, or GBP_SITEMAP_URL), such as
    https://www.rothian.com/sitemap.xml: pages under GBP_PATH_PREFIX
    (default /insights/), read for their title, description, publish date and
    og:image. GBP_SITE_NAME names the site in Teams messages.

A Business Profile post is public the moment it is made, so this only ever
posts an insight that is already live on the site:
  1. Serene Bay: it is on the production branch (SERENE_LIVE_BRANCH, `beta`)
     of serene-2, not marked `hidden: true`, and its page on serenebay.ae
     declares itself canonical. Sitemap: its page is listed and answers 200.
  2. it is dated on or after --since;
  3. the profile does not already carry a post linking to it.

The profile's own post list is the record of what has been posted (check 3), so
a run that starts from an old checkout cannot post the same insight twice.
--since keeps the insights that predate the automation from being posted.

Failure protocol, as publish_post.py: any failed step posts
{"event":"run_failed"} to the webhook and exits non-zero.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import requests

from publish_post import WEBHOOK, teams_card

TOKEN_URL = "https://oauth2.googleapis.com/token"
POSTS_API = "https://mybusiness.googleapis.com/v4/accounts/{account}/locations/{location}/localPosts"
SITE = os.environ.get("SERENE_SITE_URL", "https://www.serenebay.ae").rstrip("/")
SITE_NAME = os.environ.get("GBP_SITE_NAME", "Serene Bay").strip() or "Serene Bay"
# Business Profile posts carry at most 1,500 characters of text.
SUMMARY_LIMIT = 1500


def fail(reason: str) -> "None":
    """As publish_post.fail, but naming the site being posted for: this script
    also serves profiles other than Serene Bay's."""
    print(f"ERROR: {reason}", file=sys.stderr)
    if WEBHOOK:
        message = {"event": "run_failed", "client": SITE_NAME, "reason": reason}
        message.update(teams_card(f"Business Profile poster FAILED: {SITE_NAME}",
                                  [("Site", SITE_NAME), ("Status", "run failed")], body=reason))
        try:
            requests.post(WEBHOOK, json=message, timeout=20)
            print("posted run_failed to the webhook", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            print(f"could not report failure: {exc}", file=sys.stderr)
    else:
        print("(no POWERAUTOMATE_WEBHOOK_URL set; failure not reported)", file=sys.stderr)
    sys.exit(1)


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


def meta(page: str, key: str) -> str:
    """A <meta property|name="key" content="..."> value, in either attribute order."""
    for pattern in (rf'<meta (?:property|name)="{re.escape(key)}" content="([^"]*)"',
                    rf'<meta content="([^"]*)" (?:property|name)="{re.escape(key)}"'):
        m = re.search(pattern, page)
        if m:
            return html.unescape(m.group(1)).strip()
    return ""


def sitemap_insights(sitemap: str, prefix: str, since: str) -> list[dict]:
    """Pages under `prefix` listed in the sitemap, read from the live site, oldest
    first. A page that does not answer 200 or carries no publish date is skipped:
    without a date it cannot be held to --since."""
    r = requests.get(sitemap, timeout=30)
    if r.status_code != 200:
        fail(f"Reading the sitemap {sitemap} failed ({r.status_code})")
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as exc:
        fail(f"The sitemap {sitemap} is not valid XML: {exc}")
    locs = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
    posts = []
    for url in locs:
        path = urlparse(url).path
        if not path.startswith(prefix) or path.rstrip("/") == prefix.rstrip("/"):
            continue
        try:
            page = requests.get(url, timeout=30)
        except requests.RequestException:
            continue
        if page.status_code != 200:
            continue
        date = (meta(page.text, "article:published_time")
                or (re.search(r'"datePublished":"([^"]+)"', page.text) or [None, ""])[1])[:10]
        if not date or date < since:
            continue
        title = meta(page.text, "og:title")
        # og:title usually ends " | Site name"; the post needs the article's own title.
        title = title.rsplit(" | ", 1)[0] if " | " in title else title
        posts.append({"slug": path.rstrip("/").rsplit("/", 1)[-1], "title": title,
                      "excerpt": meta(page.text, "og:description") or meta(page.text, "description"),
                      "date": date, "url": url.rstrip("/"), "image": meta(page.text, "og:image")})
    return sorted(posts, key=lambda p: p["date"])


def is_live(url: str) -> bool:
    try:
        r = requests.get(url, timeout=30, allow_redirects=True)
    except requests.RequestException:
        return False
    # The site redirects some unknown paths elsewhere, so a 200 alone is not
    # proof: the page has to declare this insight as its canonical address.
    return r.status_code == 200 and f'rel="canonical" href="{url}"' in r.text


def is_photo(url: str) -> bool:
    """Business Profile photos are documented as JPG or PNG. serenebay.ae answers
    200 with an HTML page for a missing image, so the content type is what proves
    the file exists."""
    try:
        r = requests.head(url, timeout=20, allow_redirects=True)
    except requests.RequestException:
        return False
    return r.status_code == 200 and r.headers.get("Content-Type", "").startswith(
        ("image/jpeg", "image/png"))


def photo_url(slug: str) -> str:
    """A Serene Bay hero the profile can take. The site's heroes are WebP, so a
    post goes without a photo unless a JPG or PNG copy of the hero is live."""
    for ext in ("jpg", "png"):
        url = f"{SITE}/images/{slug}-hero.{ext}"
        if is_photo(url):
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
    message = {"event": "gbp_posted", "client": SITE_NAME, "slug": post["slug"],
               "title": post["title"], "url": url, "post_url": search_url}
    message.update(teams_card(
        "Insight posted to the Business Profile",
        [("Title", post["title"]), ("Site", SITE_NAME), ("Article", url),
         ("Photo", "yes" if photo else "none (no JPG or PNG image on the site)")],
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
    ap.add_argument("--sitemap", default=os.environ.get("GBP_SITEMAP_URL", ""),
                    help="read insights from this sitemap instead of serene-2 (or GBP_SITEMAP_URL)")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.since or ""):
        fail("--since (or GBP_POST_SINCE) must be a YYYY-MM-DD date, so older insights "
             "are not posted")

    if args.sitemap:
        prefix = os.environ.get("GBP_PATH_PREFIX", "/insights/").strip() or "/insights/"
        candidates = sitemap_insights(args.sitemap, prefix, args.since)
        print(f"{len(candidates)} page(s) under {prefix} in {args.sitemap} "
              f"dated {args.since} or later")
    else:
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
        if args.sitemap:
            # Already fetched from the live site by sitemap_insights.
            url = post["url"]
            if url in done:
                continue
            photo = post["image"] if post["image"] and is_photo(post["image"]) else ""
        else:
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
