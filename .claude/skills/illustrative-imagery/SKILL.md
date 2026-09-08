---
name: illustrative-imagery
description: Generate the three illustrative images for a Serene Bay insight from the post's own words. Use before publishing a post that includes images.
---

# Illustrative imagery

Three images per post: one hero and two section images. They are generated from
the post's own sentences, converted to WebP, and written into the `serene-2`
clone as `public/images/<slug>-hero.webp`, `-01.webp`, `-02.webp`.

## Prompts come from the post, not from a template

Read the section the image will sit beside and build the prompt out of what
that section actually says. A prompt that could belong to any post produces an
image that belongs to none of them.

## Say nothing about how it looks

Do **not** put colour, lighting, medium, mood, finish or camera language in the
prompt. No "cinematic", "moody", "warm tones", "photorealistic", "8k",
"minimalist". Describe only the subject and its arrangement. Left to itself the
model varies the treatment between posts, which is the point: a run of posts
should not look stamped from one die.

This is the opposite of the usual instinct. Resist it.

## What may appear as text

A few words at most, as a label: an axis label, a stage name, a figure. Never a
sentence of body copy, never a paragraph, never a caption baked into the image.
Anything longer belongs in the markdown.

## Charts and diagrams are welcome, with one rule

A chart may only use figures that **appear in that section of the post**. If
the section says handover slipped by a median of seven months, the chart may
show seven months. It may not show a trend line the post never states, invent
a second series, or extrapolate. Never invent data.

If a section has no figures, do not make a chart for it. Make a diagram of the
mechanism it describes instead, or an image of the subject.

## Alt text

Written at generation time into the manifest, not left to the publisher. The
hero's alt carries the post's focus keyphrase; the section images describe what
they show. Alt text is a description, not a keyword list.

## Look at them before publishing

Open the generated files and actually look. The failure modes that matter are
invented numbers in a chart, unreadable mangled text, and an image that has
nothing to do with its section. Any of those and you regenerate that one image
rather than shipping it.

## Conversion is load-bearing

Pillow converts every PNG to WebP. If the conversion fails, the run is refused
rather than committing a raw PNG into the site repository. The site serves
these directly from `public/images/`, so weight is a live performance concern.
