#!/bin/bash
# Cloud environment setup for the Serene Bay insight routine.
# Paste the whole of this into the environment's "Setup script" box.
#
# Two things this has to survive, learned the hard way:
#
# 1. This runs BEFORE the routine's repository is checked out, so
#    `pip install -r requirements.txt` fails with "No such file or directory".
#    The packages are therefore named explicitly rather than read from the file.
#
# 2. No `set -e`. A setup script that aborts takes the whole session with it,
#    and none of the work here is worth losing a run over: the routine can
#    install anything missing itself. Failures are reported, not fatal.
set -uo pipefail

echo "--- python dependencies ---"
# Named explicitly: requirements.txt is not on disk yet at this point.
python3 -m pip install --quiet --disable-pip-version-check \
  Pillow requests python-frontmatter PyYAML \
  && echo "ok: Pillow, requests, python-frontmatter, PyYAML" \
  || echo "WARN: pip install failed; the routine should retry it after checkout"

echo "--- site repository ---"
# publish_post.py writes the post and images into this clone, then pushes a
# branch. The routine only checks out its own repo, so serene-2 is fetched here.
TARGET="${SERENE_REPO_PATH:-/tmp/serene-2}"
REPO="github.com/luismayrina/serene-2.git"

if [ -d "$TARGET/.git" ]; then
  echo "ok: $TARGET already present"
elif [ -n "${GITHUB_TOKEN:-}" ]; then
  # serene-2 is private, so a token is required unless the session's own git
  # credentials happen to cover it.
  git clone --depth 50 "https://x-access-token:${GITHUB_TOKEN}@${REPO}" "$TARGET" \
    && echo "ok: cloned $TARGET" \
    || echo "ERROR: clone failed even with GITHUB_TOKEN; check the token has repo scope and can read luismayrina/serene-2"
else
  git clone --depth 50 "https://${REPO}" "$TARGET" \
    && echo "ok: cloned $TARGET without a token" \
    || echo "ERROR: clone failed and GITHUB_TOKEN is not set; serene-2 is private"
fi

if [ -d "$TARGET/.git" ]; then
  git -C "$TARGET" config user.name  "Serene Insight Routine"
  git -C "$TARGET" config user.email "noreply@serenebay.ae"
fi

echo "--- setup finished ---"
