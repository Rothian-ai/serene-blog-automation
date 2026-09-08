#!/bin/bash
# Cloud environment setup script for the Serene Bay insight routine.
# Paste this into the environment's "Setup script" box.
#
# The Rothian environment runs `npm install` because that repo is Node. This
# one is Python, and it also needs a clone of the site repository: the routine
# checks out ONE repo (this one), but publishing writes into serene-2.
set -euo pipefail

pip install -r requirements.txt

# The site repo, cloned to whatever SERENE_REPO_PATH points at.
# GITHUB_TOKEN comes from the environment; git over HTTPS works even though the
# GitHub REST API is proxy-blocked.
TARGET="${SERENE_REPO_PATH:-/tmp/serene-2}"
if [ ! -d "$TARGET/.git" ]; then
  git clone --depth 50 \
    "https://x-access-token:${GITHUB_TOKEN}@github.com/luismayrina/serene-2.git" \
    "$TARGET"
fi

# Commit identity for the branch this routine pushes.
git -C "$TARGET" config user.name  "Serene Insight Routine"
git -C "$TARGET" config user.email "noreply@serenebay.ae"

echo "setup complete: $(python3 -c 'import PIL,requests;print("Pillow+requests ok")')"
echo "site clone: $TARGET"
