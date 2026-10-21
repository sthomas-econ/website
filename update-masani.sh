#!/bin/sh
# For anyone with access to the Masani SVN repository: bring the site's Masani pages up to date and publish them.
# Usage:  ./update-masani.sh
cd "$(dirname "$0")"
git pull --ff-only || exit 1
rm -f data/.masani-stamp
python3 scripts/masani.py || exit 1
if [ -z "$(git status --porcelain masani)" ]; then
  echo "The Masani pages are already up to date."
  exit 0
fi
git add masani
git commit -m "Update Masani notes" && git push
