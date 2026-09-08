# serene-blog-automation

Weekly insight automation for **Serene Bay** (serenebay.ae), modelled on the
`wp-blogs-automation` routine used for Rothian Digital.

## The one structural difference

Rothian Digital publishes to WordPress. **Serene Bay has no WordPress.** Its
blog is markdown in `content/insights/` in the `luismayrina/serene-2`
repository, prerendered by React Router and served from Vercel.

So the publish step is the one thing that could not be copied across:

| Rothian Digital (WordPress) | Serene Bay (this repo) |
|---|---|
| WP draft post over the REST API + JWT | Draft pull request against `serene-2` |
| Yoast focus keyphrase and meta fields | Frontmatter `title` and `excerpt` |
| WebP featured image uploaded to the media library | `public/images/<slug>-hero.webp` |
| `wp-admin` edit URL | Pull request URL and its Vercel preview |
| Styled HTML with brand colours and a CTA card | Plain markdown; the site styles it |

Everything else is mirrored: dedup before topic choice, researched statistics
with sources, three illustrative images, Teams notification, the failure
protocol, the history log, and the commit at the end.

## Layout

```
ROUTINE.md                              the prompt to paste into the routine
.claude/skills/insight-writing/         structure, frontmatter schema, SEO, dedup
.claude/skills/illustrative-imagery/    how the three images are built
clients/serene-bay/branding/            voice, spelling, what NOT to style
clients/serene-bay/blog-history.md      dedup ledger, seeded with the 7 live insights
generate_images.py                      OpenAI images, converted to WebP
publish_post.py                         stages into serene-2 and opens the draft PR
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in, then keep it out of git
gh auth login             # publish_post.py opens the PR with the gh CLI
```

`SERENE_REPO_PATH` must point at a clone of `serene-2`. The publish step writes
into that clone, so it should be a working clone you are happy to have branches
created in.

## Running a post by hand

```bash
python3 generate_images.py --post-dir clients/serene-bay/insight-08092026
python3 publish_post.py  --post-dir clients/serene-bay/insight-08092026 --dry-run
python3 publish_post.py  --post-dir clients/serene-bay/insight-08092026
```

`--dry-run` validates the frontmatter against the site's typed schema and
stages the files without committing, pushing or opening a pull request.

## Guardrails

- The post is never merged. `publish_post.py` opens a **draft** PR only.
- It refuses to overwrite an existing insight, so a repeated topic stops the run.
- It validates `category` and `plate` against the site's union types before
  touching the repository, because a wrong value is a build failure not a typo.
- WebP conversion failure aborts the run rather than committing a raw PNG.
- Any failure posts `{"event":"run_failed", ...}` to the Teams webhook.
