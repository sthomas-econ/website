#!/usr/bin/env python3
"""Refresh blogs.yml (repo root) from the LEAP blog.

LEAP labels each post "author: <name>", so the label feed gives posts and co-authors.
Exceptions (posts to skip or add) live in blogs_manual.yml.
blogs.yml is committed, so if LEAP cannot be reached the last saved list is used.
"""
import html, json, re, sys, urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _util import is_fresh, mark_fresh, write_if_changed

ROOT = Path(__file__).resolve().parent.parent
FEED = ("https://blog.theleapjournal.org/feeds/posts/default/-/author%3A%20Susan%20Thomas"
        "?alt=json&max-results=500")
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
out = ROOT / "blogs.yml"
if out.exists() and is_fresh("blogs", 0.25):
    print("blogs: using the list fetched in the last 15 minutes")
    sys.exit(0)

try:
    req = urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0"})
    entries = json.load(urllib.request.urlopen(req, timeout=15))["feed"].get("entry", [])
except Exception as e:
    print(f"warning: LEAP feed unavailable ({e}); keeping {'existing' if out.exists() else 'NO'} blog list", file=sys.stderr)
    sys.exit(0)

def byline_authors(body):
    """Names from the post's own "by A, B and C." line (LEAP's author labels miss some co-authors)."""
    m = re.search(r"(?:^|[>\n])\s*by\s+(.+?)(?:</p>|<br|</div>|\n\n)", body[:900], re.S | re.I)
    if not m:
        return None
    line = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1)))).strip().rstrip(".")
    names = [n.strip() for n in re.split(r",\s*(?:and\s+)?|\s+and\s+", line) if n.strip()]
    if not names or len(line) > 200 or any(len(n.split()) > 5 for n in names):
        return None
    return [n for n in names if n != "Susan Thomas"]


manual = yaml.safe_load((ROOT / "blogs_manual.yml").read_text()) or {}
skip = set(manual.get("skip") or [])
posts = []
for e in entries:
    url = next(l["href"] for l in e["link"] if l["rel"] == "alternate").replace("http://", "https://")
    title = e["title"]["$t"].strip()
    if url in skip or title.lower().startswith("author:"):
        continue
    co = byline_authors(e.get("content", {}).get("$t", ""))
    if co is None:   # no readable byline: fall back to LEAP's author labels
        co = [c["term"][8:] for c in e.get("category", [])
              if c["term"].startswith("author: ") and c["term"] != "author: Susan Thomas"]
    y, m = e["published"]["$t"][:7].split("-")
    links = sorted({h.replace("http://", "https://") for h in re.findall(r'href=["\']([^"\']+)["\']', e.get("content", {}).get("$t", ""))
                    if re.search(r"xkdr\.org/paper|ssrn\.com|repec\.org/p/", h)})
    labels = [c["term"] for c in e.get("category", []) if not c["term"].startswith("author:")]
    posts.append({"title": title, "url": url, "year": y, "date": f"{MON[int(m) - 1]} {y}", "coauthors": ", ".join(co), "labels": labels, "links": links})
have = {p["url"] for p in posts}
for p in manual.get("add") or []:
    if p["url"] not in have:
        posts.append({"title": p["title"], "url": p["url"], "year": p["date"].split()[-1],
                      "date": p["date"], "coauthors": p.get("coauthors", ""), "labels": p.get("labels", [])})
mark_fresh("blogs")
write_if_changed(out, "# Refreshed automatically from the LEAP blog on every build. Do not edit; use blogs_manual.yml.\n" + yaml.safe_dump(posts, sort_keys=False, allow_unicode=True, width=10**6))
print(f"blogs: {len(posts)} posts")
