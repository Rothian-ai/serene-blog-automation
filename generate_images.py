#!/usr/bin/env python3
"""Generate the three illustrative images for a Serene Bay insight.

Reads the post folder's images.json manifest (written by the routine from the
post's own words), calls the OpenAI image API, and converts every result to
WebP. Conversion is load-bearing: a PNG that will not convert aborts the run
rather than reaching the site repository.

    python3 generate_images.py --post-dir clients/serene-bay/insight-08092026
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

import requests
from PIL import Image

# Two providers, chosen by whichever key the environment actually carries.
# The Rothian routine prompt names OPENAI_API_KEY, but the live cloud
# environment carries FAL_KEY, so support both rather than betting on one.
OPENAI_API = "https://api.openai.com/v1/images/generations"
OPENAI_MODEL = "gpt-image-1"
FAL_API = "https://fal.run/fal-ai/flux/dev"

OPENAI_SIZES = {"hero": "1536x1024", "01": "1024x1024", "02": "1024x1024"}
FAL_SIZES = {"hero": "landscape_16_9", "01": "square_hd", "02": "square_hd"}


def fail(msg: str) -> "None":
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_manifest(post_dir: Path) -> dict:
    m = post_dir / "images.json"
    if not m.exists():
        fail(f"no images.json in {post_dir}. The routine writes it from the post's own words.")
    data = json.loads(m.read_text())
    for key in ("hero", "01", "02"):
        if key not in data.get("images", {}):
            fail(f"images.json is missing the '{key}' entry")
        if not data["images"][key].get("prompt"):
            fail(f"images.json '{key}' has no prompt")
        if not data["images"][key].get("alt"):
            fail(f"images.json '{key}' has no alt text")
    return data


def provider() -> tuple[str, str]:
    """(name, key). FAL wins when both are set: it is what the environment has."""
    fal = os.environ.get("FAL_KEY", "").strip()
    if fal:
        return "fal", fal
    openai = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai:
        return "openai", openai
    fail("neither FAL_KEY nor OPENAI_API_KEY is set")
    raise SystemExit(1)  # unreachable, for the type checker


def generate(prompt: str, key_slot: str, name: str, api_key: str) -> bytes:
    if name == "fal":
        r = requests.post(
            FAL_API,
            headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
            json={"prompt": prompt, "image_size": FAL_SIZES.get(key_slot, "square_hd"),
                  "num_images": 1},
            timeout=180,
        )
        if r.status_code != 200:
            fail(f"fal.ai returned {r.status_code}: {r.text[:300]}")
        images = r.json().get("images") or []
        if not images:
            fail("fal.ai returned no image")
        return requests.get(images[0]["url"], timeout=120).content

    r = requests.post(
        OPENAI_API,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": OPENAI_MODEL, "prompt": prompt,
              "size": OPENAI_SIZES.get(key_slot, "1024x1024"), "n": 1},
        timeout=180,
    )
    if r.status_code != 200:
        fail(f"OpenAI returned {r.status_code}: {r.text[:300]}")
    payload = r.json()["data"][0]
    if "b64_json" in payload:
        return base64.b64decode(payload["b64_json"])
    return requests.get(payload["url"], timeout=120).content


def to_webp(png: bytes, out: Path) -> None:
    """Convert to WebP. Refuse the run if this fails: no raw PNG ships."""
    try:
        tmp = out.with_suffix(".png")
        tmp.write_bytes(png)
        with Image.open(tmp) as im:
            im.convert("RGB").save(out, "WEBP", quality=86, method=6)
        tmp.unlink()
    except Exception as exc:  # noqa: BLE001 - any failure here must stop the run
        fail(f"WebP conversion failed for {out.name}: {exc}")
    if not out.exists() or out.stat().st_size == 0:
        fail(f"WebP conversion produced nothing for {out.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-dir", required=True)
    ap.add_argument("--force", action="store_true", help="regenerate images that already exist")
    args = ap.parse_args()

    if os.environ.get("INCLUDE_IMAGES", "true").lower() == "false":
        print("INCLUDE_IMAGES=false — skipping image generation.")
        return

    post_dir = Path(args.post_dir)
    if not post_dir.is_dir():
        fail(f"{post_dir} does not exist")
    name, api_key = provider()
    print(f"image provider: {name}")

    manifest = load_manifest(post_dir)
    slug = manifest.get("slug") or post_dir.name
    out_dir = post_dir / "images"
    out_dir.mkdir(exist_ok=True)

    for key, entry in manifest["images"].items():
        out = out_dir / f"{slug}-{key}.webp"
        if out.exists() and not args.force:
            print(f"  reuse  {out.name}")
            continue
        print(f"  build  {out.name}")
        to_webp(generate(entry["prompt"], key, name, api_key), out)

    print(f"\n{len(manifest['images'])} images ready in {out_dir}")
    print("Open them and look at them before publishing:")
    print(f"  open {out_dir}")


if __name__ == "__main__":
    main()
