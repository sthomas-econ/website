#!/usr/bin/env python3
"""Turn sue_res.bib into the lists shown on the site (data/*.yml).

Sections come from the entry type:
  TechReport -> working papers   Article -> journal articles
  Book -> books                  InCollection/InProceedings -> chapters
Optional bib fields: abstract, url, month, pages, volume, number.
Home "Recent research" = entries dated within the last NEW_MONTHS months.
Blog posts come from blogs.yml (scripts/blogs.py); op-eds from opeds.yml (by hand)
and data/opeds_auto.yml (scripts/opeds.py).
"""
import difflib
import re
from datetime import date
from pathlib import Path

import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _util import write_if_changed

NEW_MONTHS = 6
ROOT = Path(__file__).resolve().parent.parent
MONTHS = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
SECTION = {"techreport": "working", "article": "journals", "book": "books",
           "incollection": "chapters", "inproceedings": "chapters"}


def _url(u):
    u = u.strip()
    if u.upper().startswith("DOI "):
        u = "https://doi.org/" + u[4:].strip()
    return u if u.startswith("http") else ""


def clean(s):
    s = re.sub(r"\s+", " ", s.replace("\\&", "&").replace("--", "–")).strip()
    s = s.replace("{\\'", "").replace("{", "").replace("}", "").replace("~", " ")
    return s.strip(" ,")


def parse(text):
    """Yield (type, key, fields) for each bib entry."""
    for m in re.finditer(r"^@(\w+)\s*\{\s*([^,\s]+)\s*,", text, re.M):
        depth, i = 1, m.end()
        start = i
        while depth and i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        body = text[start:i - 1]
        fields = {}
        for f in re.finditer(r"(\w+)\s*=\s*", body):
            j = f.end()
            if body[j:j + 1] == "{":
                d, k = 1, j + 1
                while d:
                    d += {"{": 1, "}": -1}.get(body[k], 0)
                    k += 1
                val = body[j + 1:k - 1]
            else:
                val = re.match(r"[^,\n]*", body[j:]).group().strip().strip('"')
            fields.setdefault(f.group(1).lower(), val)
        yield m.group(1).lower(), m.group(2), fields


def when(f):
    y = re.search(r"\d{4}", f.get("year", ""))
    y = int(y.group()) if y else 0
    mo = MONTHS.get(re.sub(r"[^a-z]", "", f.get("month", "").lower())[:3], 0)
    return y, mo


def people(authors):
    names = [clean(a) for a in re.split(r"\s+and\s+", authors)]
    return ", ".join(names)


def venue(kind, f):
    if kind == "article":
        v = clean(f.get("journal", ""))
        if f.get("volume"):
            v += f" {f['volume']}" + (f"({f['number']})" if f.get("number") else "")
        return v + (f", {clean(f['pages'])}" if f.get("pages") else "")
    if kind == "techreport":
        return clean(f.get("institution", ""))
    if kind == "book":
        return clean(f.get("publisher", ""))
    return ", ".join(clean(f[k]) for k in ("booktitle", "publisher") if f.get(k))


def _word(w):
    w = str(w)
    case = 0 if w.isupper() else re.I          # IT, NCLT, ESG are case-sensitive
    if w.endswith("*"):
        return re.compile(r"\b" + re.escape(w[:-1]) + r"\w*", case)
    return re.compile(r"\b" + re.escape(w) + r"(?:s|es)?\b", case)


TOPICS = {name: [_word(w) for w in words]
          for name, words in yaml.safe_load((ROOT / "topics.yml").read_text()).items()}


def topics_for(title, abstract="", labels=(), keywords=""):
    """Explicit bib keywords win; otherwise match the topic words against title, abstract and labels."""
    explicit = [k.strip() for k in re.split(r"[;,]", keywords) if k.strip() in TOPICS]
    if explicit:
        return explicit
    hay = " ".join([title, abstract, " ".join(labels)])
    return [name for name, pats in TOPICS.items() if any(p.search(hay) for p in pats)]


today = date.today()
cutoff = (today.year * 12 + today.month) - NEW_MONTHS
rows = []
entries = list(parse((ROOT / "sue_res.bib").read_text()))
by_key = {k: f for _, k, f in entries}
for kind, key, f in entries:
    for k, v in by_key.get(f.get("crossref", ""), {}).items():
        if k not in ("title", "author", "pages", "url", "abstract", "chapter"):
            f.setdefault(k, v)
    if kind not in SECTION or "title" not in f:
        continue
    y, mo = when(f)
    if not y:
        print(f"warning: no year, skipped: {key}")
        continue
    month_name = next((n.title() for n, i in MONTHS.items() if i == mo), "")
    rows.append({
        "section": SECTION[kind], "sort": y * 12 + mo, "year": str(y),
        "title": clean(f["title"]),
        "authors": people(f.get("author", f.get("editor", ""))) if kind != "book" or f.get("author") else "",
        "meta": " · ".join(x for x in (venue(kind, f), f"{month_name} {y}".strip()) if x),
        "url": _url(f.get("url", "")),
        "_key": key, "_published": clean(f.get("published", "")),
        "abstract": clean(f.get("abstract", "")),
        "topics": topics_for(clean(f["title"]), clean(f.get("abstract", "")), (), clean(f.get("keywords", ""))),
        "new": y * 12 + mo >= cutoff and mo > 0,  # used only for the Home "recent" list
        "_keywords": clean(f.get("keywords", "")),
    })

def load(*names):
    items = []
    for n in names:
        f = ROOT / n
        if f.exists():
            items += yaml.safe_load(f.read_text()) or []
    return items


seen_titles = set()
for names, section, label in ((("blogs.yml",), "blogs", "LEAP blog"),
                              (("opeds.yml", "data/opeds_auto.yml"), "opeds", None)):
    for post in load(*names):
        key = re.sub(r"\W", "", post["title"].lower())
        if (section, key) in seen_titles:
            continue
        seen_titles.add((section, key))
        mon, yr = post["date"].split()
        rows.append({
            "section": section, "sort": int(yr) * 12 + MONTHS[mon.lower()[:3]], "year": str(yr),
            "title": post["title"],
            "authors": "with " + post["coauthors"] if post.get("coauthors") else "",
            "meta": f"{label or post.get('outlet') or 'Op-ed'} · {post['date']}", "url": post["url"], "abstract": "",
            "topics": topics_for(post["title"], "", post.get("labels") or []),
            "_links": post.get("links") or [],
            "new": False,
        })

def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower())


def link_blogs_to_papers(rows):
    """A paper usually has an unveiling post on the LEAP blog. Pair them when the titles match closely,
    or when the post links to the paper and the titles are at least loosely alike."""
    papers = [r for r in rows if r["section"] in ("working", "journals")]
    for blog in (r for r in rows if r["section"] == "blogs"):
        for paper in papers:
            score = difflib.SequenceMatcher(None, _norm(blog["title"]), _norm(paper["title"])).ratio()
            slug = paper["url"].rstrip("/").rsplit("/", 1)[-1] if "xkdr.org/paper/" in paper["url"] else None
            linked = bool(slug) and any(slug in l for l in blog["_links"])
            if score >= 0.8 or (linked and score >= 0.4):
                paper.setdefault("related", []).append({"label": "LEAP blog post", "url": blog["url"]})
                if paper["url"]:
                    blog.setdefault("related", []).append({"label": LABEL_OF[paper["section"]], "url": paper["url"]})


LABEL_OF = {"working": "Working paper", "journals": "Journal article"}
link_blogs_to_papers(rows)


def prefer_journal_version(rows):
    """When a working paper was published as a journal article, show only the journal row.
    Same title, or  published = {key of the journal entry}  on the working paper in sue_res.bib.
    The journal row keeps a "Working paper" link to the earlier version."""
    journals = [r for r in rows if r["section"] == "journals"]
    drop = []
    for wp in (r for r in rows if r["section"] == "working"):
        for j in journals:
            same = difflib.SequenceMatcher(None, _norm(wp["title"]), _norm(j["title"])).ratio() >= 0.9
            if same or (wp["_published"] and wp["_published"] == j["_key"]):
                if wp["url"] and not any(x["url"] == wp["url"] for x in j.get("related", [])):
                    j.setdefault("related", []).append({"label": "Working paper", "url": wp["url"]})
                for x in wp.get("related", []):
                    if not any(y["url"] == x["url"] for y in j.setdefault("related", [])):
                        j["related"].append(x)
                drop.append(wp)
                break
    return [r for r in rows if r not in drop]


rows = prefer_journal_version(rows)
for pair in yaml.safe_load((ROOT / "links_manual.yml").read_text()) or []:
    blog = next((r for r in rows if r["section"] == "blogs" and r["url"].rstrip("/") == pair["blog"].rstrip("/")), None)
    paper = next((r for r in rows if r["section"] in LABEL_OF and pair["paper"].lower() in r["title"].lower()), None)
    if blog and paper and not any(x["url"] == blog["url"] for x in paper.get("related", [])):
        paper.setdefault("related", []).append({"label": "LEAP blog post", "url": blog["url"]})
        if paper["url"]:
            blog.setdefault("related", []).append({"label": LABEL_OF[paper["section"]], "url": paper["url"]})
    elif not (blog and paper):
        print(f"warning: links_manual.yml pair not found: {pair}", file=sys.stderr)
rows.sort(key=lambda r: -r["sort"])
out = ROOT / "data"
out.mkdir(exist_ok=True)


def dump(name, items):
    items = [{k: v for k, v in r.items() if k not in ("sort", "new", "_links", "_key", "_published", "_keywords")} for r in items]
    write_if_changed(out / f"{name}.yml", yaml.safe_dump(items, sort_keys=False, allow_unicode=True, width=10**6) if items else "[]\n")


for sec in ("working", "journals", "books", "chapters"):
    dump(sec, [r for r in rows if r["section"] == sec])
LABEL = {"working": "Working paper", "journals": "Journal article", "opeds": "Op-ed", "blogs": "Blog post"}
def research_row(r):
    types = [LABEL[r["section"]]]
    if any(x["label"] == "LEAP blog post" for x in r.get("related", [])):
        types.append("Blog post")        # a paper with an unveiling post also turns up under "Blog posts"
    return dict(r, type=LABEL[r["section"]], types=types)


# A blog post that belongs to a paper is shown on the paper (as a link), not as a second row.
dump("research", [research_row(r) for r in rows if r["section"] in LABEL and not (r["section"] == "blogs" and r.get("related"))])
SHELF = {"books": "Book", "chapters": "Chapter"}
dump("bookshelf", [dict(r, type=SHELF[r["section"]]) for r in rows if r["section"] in SHELF])
recent = [r for r in rows if r["new"] and r["section"] not in ("books", "blogs")] or rows[:3]
dump("recent", recent)


def make_item(it, project):
    """A hand-written entry (Dataset, Case study, ...) from the project's items list in projects.yml."""
    m = re.match(r"(\w{3})\w*\s+(\d{4})", str(it.get("date", "")))
    y = int(m.group(2)) if m else int(re.search(r"\d{4}", str(it.get("year", ""))).group())
    mo = MONTHS.get(m.group(1).lower(), 0) if m else 0
    return {"sort": y * 12 + mo, "year": str(y), "title": it["title"], "authors": it.get("authors", ""),
            "meta": it.get("meta") or (f"{m.group(1).title()} {y}" if m else ""), "url": it.get("url", ""),
            "abstract": it.get("abstract", ""), "topics": [], "type": it["type"], "types": [it["type"]]}


# Projects page: the lists are chosen by hand in projects.yml ("include" and "items"); nothing is matched automatically.
listed = [r for r in rows if r["section"] in {**LABEL, **SHELF} and not (r["section"] == "blogs" and r.get("related"))]
for slug, project in (yaml.safe_load((ROOT / "projects.yml").read_text()) or {}).items():
    chosen = []
    for inc in project.get("include") or []:
        hits = [r for r in listed if _norm(inc) == _norm(r["title"]) or inc.lower().rstrip("/") == r["url"].lower().rstrip("/")]
        if not hits:
            print(f"warning: {project['title']}: not found on Research or Books: {inc}", file=sys.stderr)
        chosen += [r for r in hits if r not in chosen]
    chosen = [dict(r, type=LABEL.get(r["section"]) or SHELF[r["section"]],
                   types=research_row(r)["types"] if r["section"] in LABEL else [SHELF[r["section"]]]) for r in chosen]
    dump(slug, sorted(chosen + [make_item(i, project) for i in project.get("items") or []], key=lambda r: -r["sort"]))
print(f"bib: {len(rows)} entries, {len(recent)} recent")
