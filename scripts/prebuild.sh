#!/bin/sh
# Runs before every render: pull in everything that changes by itself.
set -e
python3 scripts/check_grid.py  # styles must follow the Carbon 2x grid
python3 scripts/masani.py   # Masani notes from SVN
python3 scripts/blogs.py    # LEAP blog posts
python3 scripts/opeds.py    # op-eds found automatically
python3 scripts/bib.py      # research lists from sue_res.bib
