#!/usr/bin/env python3
"""Find Susan's newspaper op-eds automatically -> data/opeds_auto.yml.

Two sources, both read-only and public:
  * XKDR's opinion list (xkdr.org/discourse-list): pieces bylined "Susan Thomas"
  * Ajay Shah's media archive (mayin.org): recent columns whose byline names her
Older or other pieces go in opeds.yml by hand. If a site is down this simply finds fewer.
"""
import html, re, sys, time, urllib.request
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _util import is_fresh, mark_fresh, write_if_changed

ROOT = Path(__file__).resolve().parent.parent
MON = "jan feb mar apr may jun jul aug sep oct nov dec".split()
OUTLETS = ["Business Standard", "Indian Express", "Economic Times", "Financial Express", "Hindustan Times",
           "Mint", "The Hindu BusinessLine", "The Hindu", "BQ Prime", "ThePrint", "NDTV Profit", "Bar & Bench"]
HOSTS = {"bqprime.com": "BQ Prime", "theprint.in": "ThePrint", "ndtvprofit.com": "NDTV Profit",
         "barandbench.com": "Bar & Bench", "ideasforindia.in": "Ideas for India",
         "business-standard.com": "Business Standard", "indianexpress.com": "Indian Express"}
YEARS_BACK = 1
BUDGET = 600 if __import__("os").environ.get("CI") else 40   # seconds for the media-archive scan
START = time.time()
OUT = ROOT / "data" / "opeds_auto.yml"
if OUT.exists() and is_fresh("opeds", 24):
    print("op-eds: using the copy saved in the last 24 hours")
    sys.exit(0)


def get(url, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=10).read().decode("utf8", "replace")
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def text(h):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


def month_year(d):  # "11 May 2025" / "6 February 2025" -> "May 2025"
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?,?\s+(\d{4})", d)
    return f"{m.group(2).title()} {m.group(3)}" if m else None


found = []
try:  # XKDR opinion list
    for p in re.split(r'<div class="col-xl-3 col-lg-4 col-md-6 mb-4">', get("https://www.xkdr.org/discourse-list"))[1:]:
        t = text(p)
        m = re.match(r"Op-ed (.+?) (\d{2} \w{3} \d{4}) By (.+)$", t)
        if m and m.group(3).strip() == "Susan Thomas":
            url = re.search(r'href="([^"]+)"', p).group(1)
            host = re.sub(r"^www\.", "", re.sub(r"https?://([^/]+).*", r"\1", url))
            found.append({"title": m.group(1), "outlet": HOSTS.get(host, host), "date": month_year(m.group(2)), "url": url, "coauthors": ""})
except Exception as e:
    print(f"warning: XKDR list unavailable ({e})", file=sys.stderr)

try:  # Ajay Shah's archive, recent years only
    base = "https://www.mayin.org/ajayshah/MEDIA/"
    for y in range(date.today().year - YEARS_BACK, date.today().year + 1):
        idx = get(f"{base}{y}/index.html")
        for href in set(re.findall(r'<li>\s*<a href="([^"#:]+\.html)"', idx)):
            if href == "index.html":
                continue
            if time.time() - START > BUDGET:
                print("op-eds: time budget reached, stopping the archive scan", file=sys.stderr)
                break
            time.sleep(0.3)
            try:
                t = text(get(f"{base}{y}/{href}"))[:700]
            except Exception:
                continue
            m = re.search(r"^(.*?) \1 by (.+?) ((?:%s)) ?, (\d{1,2} \w+ \d{4})" % "|".join(map(re.escape, OUTLETS)), t)
            if m and "Susan Thomas" in m.group(2):
                co = [a for a in re.split(r", | and ", m.group(2)) if a and a != "Susan Thomas"]
                found.append({"title": m.group(1), "outlet": m.group(3), "date": month_year(m.group(4)),
                              "url": f"{base}{y}/{href}", "coauthors": ", ".join(co)})
except Exception as e:
    print(f"warning: media archive unavailable ({e})", file=sys.stderr)

seen, out = set(), []
for f in found:
    k = re.sub(r"\W", "", f["title"].lower())
    if f["date"] and k not in seen:
        seen.add(k); out.append(f)
mark_fresh("opeds")
write_if_changed(OUT, yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=10**6) if out else "[]\n")
print(f"op-eds: {len(out)} found automatically")
