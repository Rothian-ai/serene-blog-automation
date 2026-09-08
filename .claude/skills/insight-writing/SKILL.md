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
   appends its own conversation band.

## No FAQ microdata

The Rothian brief asks for `schema.org/FAQPage` microdata. Do not add it here.
The body is markdown, structured data for the site is emitted centrally from
`app/root.tsx`, and hand-written microdata in a post body would be unstyled
markup that duplicates what the route already declares. If an FAQ helps the
reader, write it as a `## Common questions` section with `### ` questions.

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
