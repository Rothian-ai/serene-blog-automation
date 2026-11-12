---
name: insight-writing
description: Research, structure and write a Serene Bay insight as a markdown file with the frontmatter the site validates. Use when producing or editing a post for content/insights in the serene-2 repository.
---

# Writing a Serene Bay insight

An insight is a markdown file in `content/insights/<slug>.md` in the `serene-2`
repository. React Router prerenders it; `marked` renders the body into a
`.prose-serene` container. You write content only. Load the
`clients/serene-bay/branding` skill before drafting.

## Output format: markdown, not HTML

The Rothian pipeline emits styled WordPress HTML. This one does not. Emit
GitHub-flavoured markdown. `marked` supports headings, tables, lists,
blockquotes, bold, and links, and `.prose-serene` styles all of them. Raw HTML
in the body will render but carries no styling and is a mistake.

## Frontmatter — exact schema

The site's `Insight` interface is typed. A wrong `category` or `plate` is a
build error, not a soft failure.

```yaml
---
title: 'Title in sentence case, quoted'
category: Market Analysis    # Market Analysis | Buyer Guides | The Model | Journal
date: '2026-09-08'           # YYYY-MM-DD, quoted
readingTime: 6 min
excerpt: 'One or two sentences. This is the card copy and the meta description.'
image: /images/<slug>-hero.webp
plate: dusk                  # hero | render | stone | interior | dusk | glass
featured: 1                  # optional, lower sorts first on the index
---
```

- `category` must be one of the four exactly. `The Model` is for how the
  advisory works and how people are paid; `Market Analysis` for data;
  `Buyer Guides` for process; `Journal` sparingly.
- `plate` is the art-directed ground shown while the image loads and wherever
  the image is absent. Pick one that suits the subject.
- `hidden: true` takes a post out of the site and the sitemap without deleting
  it. The routine never sets it; a human may.
- `featured` only if the post should outrank existing ones on the index. Leave
  it out by default rather than fighting the current order.

## Structure

1. **Answer first.** The opening 150 to 200 words answer the question in the
   title outright. No throat-clearing, no scene-setting. A reader who stops
   after the first paragraph should already have the answer.
2. **`## ` sections.** Sentence case. The site builds nothing from them, so
   they exist for the reader. Six to nine is usual.
3. **At least one table.** Markdown tables render properly and are the format
   the house uses for anything comparative. Every figure in it carries a source.
4. **Sourcing inline.** Link the source at the figure, in the sentence that
   uses it: `[DLD transaction data](https://...)`. Leave outbound links plain
   markdown; the site does not add `nofollow`, so they are dofollow already.
5. **Close on substance.** No CTA, no summary of what you just said. The page
   appends its own conversation band. The last argued section ends the
   article; only the FAQ follows it.
6. **Frequently asked questions, always last.** Every insight ends with a
   `## Frequently asked questions` section. See the section below.

## Verify before you write

Client review asked for figures to be checked against the original source.
For every statistic, open the page it comes from (not a search summary) and
confirm four things: the number, the period it covers, whether it is a count
or a value, and what it includes (property types, off-plan resales, rentals,
mortgages, gifts). Also record what the source says its own data source is.

- If a page does not state a figure, do not use it. If a later source gives a
  figure for an earlier period, say whose figure it is and for which measure.
- Publishers disagree. When they do, show them side by side with their
  definitions, never average or pick the convenient one.
- Anything you calculate is labelled "our calculation", with the inputs shown.
  Percentages from rounded inputs are given as approximate.
- Keep the same number from being used for two different measures without
  saying so (a quarter's share and a month's share can both be 76 per cent).
- Say what a figure is not: a citywide average or share is not demand in one
  community or project. Where the source shows the contrast, name it.
- A broker or developer source is one informed view. Say so.

## Visuals and comparisons

Readers act on pictures and tables before paragraphs, so use them where the
content calls for one. Decide from the figures, not from habit:

1. **A chart** when the post has figures the reader must weigh against each
   other: a comparison between sources, a change over time, a share or a split.
   Make it with `make_charts.py` from `charts.json` and embed it as
   `![alt](/images/<slug>-chart-01.webp)` after the sentence or table it
   supports. Bars for a comparison between sources, stacked bars for a share or
   a composition, grouped bars for one measure from two publishers. Mark
   calculated figures hatched. One or two is usual. Never a decorative chart,
   and never a chart of a single number.
2. **A side-by-side table** whenever two or more options are compared: a
   waiver against a discount, one publisher against another, one fee schedule
   against another. Put the figure the reader will act on in a row of its own.
3. **Neither**, if the post is explanatory and has no such figures. Do not
   invent data to fill a visual slot.
4. **Plain explanation.** Define a technical term once, in a clause, then let
   the table or chart carry it. Cut a paragraph that explains what a table
   already shows.

## Frequently asked questions (required, markdown only)

Every insight closes with this section, written exactly like this:

```markdown
## Frequently asked questions

### When do off-plan service charges start in Dubai?

From the project's completion date, or from an earlier payment default,
under the [Rental Disputes Center's ruling](https://...).

### Can I refuse to pay while I dispute snagging?

No. Article 28 of Law No. 6 of 2019 ...
```

- The heading is exactly `## Frequently asked questions`. Not "Common
  questions", not "FAQs", not "FAQ". `publish_post.py` refuses anything else.
- It is the last `## ` section in the post. Nothing follows it.
- Four to seven questions, each a `### ` heading phrased the way a buyer
  would type it into a search box, ending in a question mark. Use the focus
  keyphrase in at least one question.
- Each answer is 40 to 90 words, answers in its first sentence, and stands on
  its own (search engines and AI answers quote it out of context). Link the
  source for any figure, as in the body.
- Add what the body does not already say: a follow-on question, an edge case,
  a "what if". Do not restate a paragraph as a question.
- Plain markdown only. No `<details>`, no HTML and no hand-written
  `schema.org/FAQPage` microdata. The site's insight route lifts this section
  out, shows it as an accordion (one question open at a time) and emits the
  FAQPage structured data itself, so authors write markdown and the route
  owns the presentation and the schema. Links in answers work inside the
  accordion.

## SEO and GEO

The site derives the page title and meta description from the frontmatter, so
the SEO surface is `title` and `excerpt`. Get the keyphrase into:

- the `title`
- the first 100 words of the body
- one `## ` heading
- the `excerpt`
- the `slug`
- the hero image `alt`, which is written in the image manifest

Keep `excerpt` between 120 and 156 characters so it works as a meta
description unmodified. Titles are specific and varied. Do not use "What UAE
X Must Know", "Must Do Now", or any close variant. Do not open a title with
"How to" more than occasionally.

## Deduplication

Before choosing a topic, read both:

1. `clients/serene-bay/blog-history.md` in this repository, and
2. the live `content/insights/` directory in the `serene-2` clone.

The repository is authoritative. Merge them into one exclusion list. Reject a
topic that repeats an existing title, angle, or focus keyphrase. Serene has
seven insights already and they cover escrow, snagging, assignment, broker
economics, project delay and the buying sequence; a new post has to add
something those do not say.

## Length

1,200 to 1,800 words. Long enough to be the best answer available, short
enough that every paragraph earns its place. Cut anything that restates.
