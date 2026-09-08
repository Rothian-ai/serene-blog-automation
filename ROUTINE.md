# Serene Bay — Weekly Insight (routine prompt)

Paste the block below into the Claude routine's **Instructions**. Suggested
configuration, mirroring the Digital routine:

- **Trigger:** every Monday, 14:00 GMT+5:30 (offset a few minutes off the hour)
- **Runs with:** `<owner>/serene-blog-automation`
- **Environment:** the environment holding `OPENAI_API_KEY`,
  `POWERAUTOMATE_WEBHOOK_URL`, `SERENE_REPO_PATH`, `SERENE_BASE_BRANCH`
- **Keep it a DRAFT:** the routine opens a draft pull request. It never merges.

---

Research and write ONE insight for the client on the most useful current
development in UAE off-plan property. Open it as a DRAFT pull request. Never
merge, and never publish to the live site.

CONTEXT
- Client: Serene Bay (serenebay.ae), an off-plan property buyer advisory in
  Dubai and Abu Dhabi. Salaried advisors, cross-developer comparison, a
  relationship that outlasts the handover.
- Serene has NO WordPress. The blog is markdown in `content/insights/` in the
  `luismayrina/serene-2` repository, prerendered by React Router on Vercel.
  A draft here means a branch and a draft pull request, which Vercel previews.
- This repository (`serene-blog-automation`) is connected to the routine and
  cloned into the working directory. A clone of `serene-2` is at
  `$SERENE_REPO_PATH`.
- Commit with `git -c commit.gpgsign=false commit`; a plain `git commit` fails
  because the signing server returns 400. The pull request is opened with the
  `gh` CLI. Calling the GitHub REST API directly is blocked by the proxy and
  returns 403; the GitHub MCP tools work if you need them.
- Date: use today's date for the post folder (`insight-DDMMYYYY`) and the
  frontmatter `date`. The filename is the slug: `<descriptive-slug>.md`.
- Env vars: SERENE_REPO_PATH, SERENE_BASE_BRANCH, OPENAI_API_KEY,
  INCLUDE_IMAGES (true|false, default true), POWERAUTOMATE_WEBHOOK_URL.
- Run `pip install -r requirements.txt` before publishing. Pillow is
  load-bearing: every image is converted to WebP and the run is refused if that
  conversion fails.

READ THESE SKILLS FIRST (do not work from memory)
- `.claude/skills/insight-writing/SKILL.md` — structure, frontmatter schema,
  SEO, dedup, length
- `.claude/skills/illustrative-imagery/SKILL.md` — how the images are built
- `clients/serene-bay/branding/SKILL.md` — voice, spelling, what NOT to style

PIPELINE (prepare everything, publish last — no throwaway scripts)
0. Dedup before choosing a topic. Read `clients/serene-bay/blog-history.md`
   AND list `$SERENE_REPO_PATH/content/insights/`, reading the `title` and
   `category` of every file. Merge both into one exclusion list; the
   repository is authoritative. Pick a subject that repeats no existing title,
   angle or focus keyphrase.
1. Research with web search. Capture real, current statistics and their source
   URLs. Prefer DLD, RERA, ADREC, the developer's own filings and the
   established property press. Never use a figure you cannot link.
2. Write the post as markdown into `clients/serene-bay/insight-DDMMYYYY/<slug>.md`
   with the frontmatter the site validates (title, category, date,
   readingTime, excerpt, image, plate). Answer-first opening, at least one
   markdown table, sources linked inline at the figure they support.
3. Write `images.json` in the same folder: three entries (`hero`, `01`, `02`),
   each with a `prompt` built from that section's own words and an `alt`.
   Then generate:
       python3 generate_images.py --post-dir clients/serene-bay/insight-DDMMYYYY
   Open the WebP files and look at them before publishing.
4. Publish the draft:
       python3 publish_post.py --post-dir clients/serene-bay/insight-DDMMYYYY
   Validates the frontmatter against the site's typed schema, copies the post
   and images into the serene-2 clone, commits on `insight/<slug>`, opens a
   DRAFT pull request, and posts the Teams notification.
5. After the pull request exists, append a row to
   `clients/serene-bay/blog-history.md` and commit the post folder plus the
   updated history to THIS repository.

REQUIREMENTS
- The subject must connect to what Serene actually does, so the advisory reads
  as the natural source of the answer. Never write a sales pitch.
- Evergreen with a current peg. Anchor to a real development, but write so the
  post still reads in three years. The brand rule is "no dates that expire":
  absolute dates in the body are fine, "this week" and "recently" are not.
- Answer-first opening (roughly the first 200 words), at least one data table,
  and sources linked inline. Outbound links are plain markdown and therefore
  dofollow already.
- Markdown only. No inline HTML, no colours, no CTA card, no FAQ microdata:
  the site owns presentation and emits its own structured data. This is the
  single biggest difference from the Rothian Digital pipeline.
- Titles: specific and varied. Do NOT use "What UAE X Must Know / Must Do Now"
  or any close variant.
- Images: illustrative, built from the post's own words. Do NOT put colour,
  lighting, medium or mood in the prompts, so the look varies between posts.
  Keep text inside an image to a few words such as a label. Charts are welcome
  but may only use figures that actually appear in that section. Never invent
  data.
- SEO: keyphrase in the title, the first 100 words, one `## ` heading, the
  excerpt, the slug and the hero image alt. Keep the excerpt 120 to 156
  characters so it works unmodified as the meta description.
- Humanise: no em dashes, British/International spelling, varied sentence
  length, no exclamation marks.

DELIVER
- Confirm the Teams notification was sent, and give the draft pull request URL,
  the slug, the category, and the excerpt as it will be used for the meta
  description.
- If the repository cannot be accessed or any required step fails, do NOT open
  a half-finished pull request. Stop and POST a clearly-flagged failure event
  to POWERAUTOMATE_WEBHOOK_URL (for example
  `{"event":"run_failed","reason":"<what failed>"}`) so the run surfaces as
  errored for troubleshooting.
