#!/usr/bin/env python3
"""Render the data charts for a Serene Bay insight, deterministically.

Charts are drawn from the figures in charts.json (the same figures the post
prints), never by an image model, so a number cannot be misspelt or invented.
No API key is needed and INCLUDE_IMAGES does not affect it. Output is WebP in
<post-dir>/images/<slug>-chart-NN.webp, which publish_post.py copies to the site.

    python3 make_charts.py --post-dir clients/serene-bay/insight-14102026

charts.json:
{"slug": "<slug>", "charts": {"01": {
    "type": "hbar" | "stacked" | "grouped",
    "title": "What the chart shows, as a plain statement",
    "categories": ["A", "B"],
    "series": [{"name": "Off-plan", "values": [1, 2], "derived": false}],
    "prefix": "AED ", "suffix": "bn", "decimals": 1,
    "source": "Source line, shown under the chart",
    "alt": "Description for the markdown image"}}}

On a stacked chart, "derived_categories": [0] draws those bars hatched, to mark
figures the post calculated rather than quoted. A series may carry its own
"decimals". hbar takes one series; add "notes" (one
string per category) for a short label after the value.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image

# Brand tokens (serene-2 brand-assets/brand-tokens.md): warm ivory ground,
# ink text, navy and brass for the two series, silver for a third.
GROUND, INK, MUTED, GRID = "#F6F1E6", "#0B0A08", "#7D7568", "#DDD6C6"
SERIES = ["#0D1D3C", "#A97C2F", "#B7BCC2"]


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def setup_font() -> None:
    plt.rcParams["hatch.linewidth"] = 1.2
    names = {f.name for f in font_manager.fontManager.ttflist}
    for cand in ("Anek Latin", "Inter", "DejaVu Sans"):
        if cand in names:
            plt.rcParams["font.family"] = cand
            return


def fmt(v: float, c: dict, s: dict | None = None) -> str:
    d = (s or {}).get("decimals", c.get("decimals", 0))
    return f"{c.get('prefix', '')}{v:,.{d}f}{c.get('suffix', '')}"


def style(ax) -> None:
    ax.set_facecolor(GROUND)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=INK, length=0, labelsize=11)


def draw(c: dict, out: Path) -> None:
    cats, series = c["categories"], c["series"]
    kind = c["type"]
    fig, ax = plt.subplots(figsize=(8, 4.6 if kind != "hbar" else 0.9 + 0.8 * len(cats)), dpi=200)
    fig.patch.set_facecolor(GROUND)
    style(ax)

    def bar(fn, pos, vals, i, s, **kw):
        derived = s.get("derived")
        return fn(pos, vals, color=SERIES[i], edgecolor=GROUND if not derived else "#FFFFFF",
                  linewidth=2, hatch="////" if derived else None, label=s["name"], **kw)

    if kind == "hbar":
        vals = series[0]["values"]
        ys = range(len(cats))[::-1]
        for y, v, cat in zip(ys, vals, cats):
            ax.barh(y, v, color=SERIES[0], height=0.55)
        notes = c.get("notes", [""] * len(cats))
        top = max(vals)
        for y, v, n in zip(ys, vals, notes):
            ax.text(v + top * 0.015, y, fmt(v, c) + (f"   {n}" if n else ""),
                    va="center", color=INK, fontsize=11, fontweight="semibold")
        ax.set_yticks(list(ys)); ax.set_yticklabels(cats)
        ax.set_xlim(0, top * 1.55); ax.set_xticks([])
    else:
        import numpy as np
        x = np.arange(len(cats))
        if kind == "stacked":
            bottom = np.zeros(len(cats))
            for i, s in enumerate(series):
                v = np.array(s["values"], dtype=float)
                for xi, vi, bi, k in zip(x, v, bottom, range(len(cats))):
                    hatched = k in c.get("derived_categories", [])
                    ax.bar(xi, vi, bottom=bi, width=0.5, color=SERIES[i], linewidth=2,
                           edgecolor="#FFFFFF" if hatched else GROUND, hatch="////" if hatched else None,
                           label=s["name"] if k == 0 else None)
                grand = np.sum([q["values"] for q in series], axis=0).max()
                for xi, vi, bi in zip(x, v, bottom):
                    if vi > grand * 0.06:
                        hatched = list(x).index(xi) in c.get("derived_categories", [])
                        ax.text(xi, bi + vi / 2, fmt(vi, c), ha="center", va="center", fontsize=10,
                                fontweight="semibold", color=INK if hatched or i else "#FFFFFF",
                                bbox=dict(facecolor=GROUND, edgecolor="none", pad=3) if hatched else None)
                    else:  # too thin to hold a label: put it beside the bar
                        ax.text(xi + 0.28, bi + vi / 2, fmt(vi, c), ha="left", va="center", fontsize=10,
                                fontweight="semibold", color=INK)
                bottom += v
            for xi, t in zip(x, bottom):
                ax.text(xi, t * 1.015, fmt(t, c), ha="center", va="bottom", fontsize=11,
                        fontweight="semibold", color=INK)
            ax.set_ylim(0, bottom.max() * 1.12)
        else:  # grouped
            n = len(series); w = 0.8 / n
            top = max(max(s["values"]) for s in series)
            for i, s in enumerate(series):
                pos = x - 0.4 + w * (i + 0.5)
                bar(ax.bar, pos, s["values"], i, s, width=w * 0.92)
                for p, v in zip(pos, s["values"]):
                    ax.text(p, v + top * 0.015, fmt(v, c, s), ha="center", va="bottom",
                            fontsize=10, fontweight="semibold", color=INK)
            ax.set_ylim(0, top * 1.15)
        ax.set_xticks(x); ax.set_xticklabels(cats)
        ax.set_yticks([])
        if len(series) > 1:
            ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=10,
                      labelcolor=INK, ncol=len(series))
        if kind == "stacked":
            ax.set_xlim(-0.55, len(cats) - 1 + 1.15)

    fig.text(0.02, 0.975, c["title"], ha="left", va="top", fontsize=13, fontweight="semibold", color=INK)
    fig.text(0.02, 0.02, textwrap.fill(c["source"], 112), ha="left", va="bottom", fontsize=8.5, color=MUTED)
    fig.subplots_adjust(left=0.24 if kind == "hbar" else 0.04, right=0.97, top=0.80 if kind != "hbar" else 0.80, bottom=0.24)
    png = out.with_suffix(".png")
    fig.savefig(png, facecolor=GROUND)
    plt.close(fig)
    try:
        Image.open(png).convert("RGB").save(out, "WEBP", quality=88, method=6)
    except Exception as e:  # conversion is load-bearing, as for the AI images
        fail(f"WebP conversion failed for {out.name}: {e}")
    png.unlink()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-dir", required=True)
    post_dir = Path(ap.parse_args().post_dir)
    m = post_dir / "charts.json"
    if not m.exists():
        fail(f"no charts.json in {post_dir}")
    data = json.loads(m.read_text())
    slug = data.get("slug") or fail("charts.json has no slug")
    if not data.get("charts"):
        fail("charts.json has no charts")
    setup_font()
    out_dir = post_dir / "images"
    out_dir.mkdir(exist_ok=True)
    for key, c in data["charts"].items():
        for f in ("type", "title", "categories", "series", "source", "alt"):
            if f not in c:
                fail(f"chart {key} is missing '{f}'")
        for s in c["series"]:
            if len(s["values"]) != len(c["categories"]):
                fail(f"chart {key}: series '{s['name']}' length differs from categories")
        out = out_dir / f"{slug}-chart-{key}.webp"
        draw(c, out)
        print(f"  chart  {out.name}")
    print(f"\n{len(data['charts'])} charts ready in {out_dir}. Open them and check every number against the post.")


if __name__ == "__main__":
    main()
