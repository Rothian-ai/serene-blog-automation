---
name: serene-bay-branding
description: Voice, naming, spelling and formatting rules for Serene Bay insight posts. Load before writing or editing any Serene Bay content.
---

# Serene Bay — branding

Serene Bay is an off-plan property buyer advisory in Dubai and Abu Dhabi. The
argument the whole site makes is that advisors are salaried, comparison is
cross-developer, and the relationship outlasts the handover. Every post has to
sound like that house, not like a marketing agency writing about it.

## This is not the Rothian Digital brand

If you have the Rothian Digital branding skill in context, discard its visual
rules here. They are the opposite of Serene's and applying them would be a
brand violation:

| Rothian Digital | Serene Bay |
|---|---|
| Pitch-black background, off-white body | No inline colour at all. Plain markdown. |
| Orange `#EE8722` accent | Orange appears nowhere |
| Teal `#08394B` CTA card in the post | No CTA card. The site's own band closes the page |
| Styled HTML with `!important` headings | Markdown; the site styles it via `.prose-serene` |

Serene insights are **markdown files**, not styled HTML. You write content; the
site owns presentation. Never emit `<div>`, inline `style`, colours, or a CTA
block. A post that carries its own styling breaks the page it lands on.

## Naming

- The house is **Serene Bay** in prose, legal text and titles.
- The mark reads **Serene** — that is the logo, not a way to refer to the house
  in a sentence.
- The legal entity is **Serene Bay Real Estate LLC**.
- Amelia is the AI advisory. She answers; she never calls.

## Voice — every sentence must hold all three

Taken from `brand-assets/brand-tokens.md` in the site repository.

1. **Composed.** Never oversells; states what a thing is, plainly. No
   exclamation marks, no "luxury lifestyle", no filler adjectives.
   - Write: "Floor-to-ceiling glass on three sides."
   - Not: "Breathtaking views you have to see to believe!"
2. **Elevated.** Confidence over volume; speaks upward, not loud.
   - Write: "Reserved for residents of Tower Two."
   - Not: "EXCLUSIVE ACCESS — INVITE ONLY!!"
3. **Enduring.** Built to be read in ten years. No slang, no trend words, no
   dates that expire.
   - Write: "A lobby that ages the way stone does."
   - Not: "The most Instagrammable lobby in the city."

### What "enduring" means for a weekly post

This is the rule most likely to be broken, because the routine runs weekly and
weekly writing drifts into news reaction. A Serene insight may be **pegged** to
something current, but it must be **written to outlast it**.

- Peg to the durable thing: a mechanism, a rule change, a structural number.
- Explain how the mechanism works, using the current release as evidence.
- Do not open with "this week", "recently", "just announced", or a quarter that
  will read as stale. Absolute dates inside the body are fine and preferred:
  "In the year to June 2026" ages honestly; "recently" does not.
- Ask before publishing: will this paragraph still be true and useful in three
  years? If only the news peg fails that test, cut the peg to a single clause.

## House style

- **British/International spelling.** organise, recognise, analyse, centre,
  licence (noun) / license (verb), programme, per cent in prose.
- **No em dashes.** Use a comma, a colon, a full stop, or brackets. This is a
  hard rule; em dashes are the clearest tell of generated prose.
- **Vary sentence length.** A short sentence after two long ones. Never three
  long sentences in a row.
- **No exclamation marks anywhere.**
- **Numbers**: figures for data (AED 3.2M, 42 storeys, 8.1 per cent). Spell out
  one to nine in ordinary prose.
- **Currency**: AED, with the figure. Convert only when the source did.
- **Never invent a statistic.** Every figure carries a source and a link. If a
  number cannot be sourced, the sentence goes.

## Banned constructions

Beyond the voice rules, these read as agency filler and do not belong:

- "In today's fast-paced market", "game-changer", "unlock", "supercharge",
  "delve into", "navigate the landscape", "it's no secret that".
- "Contact us today!" and any urgency close. The house does not chase.
- Second-person hype ("You won't believe..."). Address the reader plainly.
- Claims about returns. Serene advises; it does not forecast a yield it cannot
  evidence. Rental data may be reported with a source; a promise may not.

## What a Serene insight is for

It answers a question a buyer actually has, using the record. It is allowed to
say that something is a bad idea. It never closes by selling: the site appends
its own conversation band to every insight page, so the post ends on the
substance and stops.
