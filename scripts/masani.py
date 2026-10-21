#!/usr/bin/env python3
"""Turn the Masani SVN notes into masani/<book>.qmd pages.

Usage: scripts/masani.py [path-to-svn-checkout]   (or set MASANI_DIR to that folder)
Default: export https://repositories.xkdr.org/svn/masani-readings, so no local copy is needed.

Each SVN folder holds markdown notes and, optionally, a book.yml
(title, author, date, cover). Without one, masani_meta.yml is used.
"""
import os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

import yaml  # pip install pyyaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _util import is_fresh, mark_fresh, write_if_changed

URL = "https://repositories.xkdr.org/svn/masani-readings"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "masani"

def export_notes():
    """Download the notes from SVN into a temporary folder. Returns it, or None if that is not possible.
    The repository needs a login: on this computer the saved SVN login is used; on GitHub the read-only
    login comes from the SVN_USER and SVN_PASSWORD secrets."""
    if not shutil.which("svn"):
        print("masani: the 'svn' program is not installed", file=sys.stderr)
        return None
    login = []
    if os.environ.get("SVN_USER"):
        login = ["--username", os.environ["SVN_USER"], "--password", os.environ.get("SVN_PASSWORD", ""), "--no-auth-cache"]
    dest = Path(tempfile.mkdtemp()) / "notes"
    for attempt in range(1, 4):                      # the server sometimes answers 5xx for a moment
        if subprocess.run(["svn", "export", "--quiet", "--non-interactive", *login, URL, str(dest)]).returncode == 0:
            return dest
        shutil.rmtree(dest, ignore_errors=True)
        if attempt < 3:
            time.sleep(5 * attempt)
    return None


# The generated pages in masani/ are saved in the repository, so the site can always be built from them.
# They are refreshed from SVN whenever the notes can be reached: here with a saved SVN login, on GitHub
# with the SVN_USER / SVN_PASSWORD secrets. A local checkout kept anywhere also works (argument or MASANI_DIR).
have_pages = any(OUT.glob("*.qmd"))
local = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MASANI_DIR")
src = Path(local).expanduser() if local else None
if src is None and have_pages and is_fresh("masani", 0.5):
    print("masani: using the pages built in the last 30 minutes")
    sys.exit(0)
if src is None and os.environ.get("CI") and not os.environ.get("SVN_USER"):
    if have_pages:
        print("masani: no SVN login on GitHub, using the saved Masani pages")
        sys.exit(0)
    sys.exit("error: no saved Masani pages and no SVN login, so the Masani books cannot be built")
if src is None:
    src = export_notes()
    if src is None:
        if have_pages:                               # keep the saved pages
            print("warning: SVN not reachable, using the saved Masani pages", file=sys.stderr)
            sys.exit(0)
        if os.environ.get("CI"):
            sys.exit("error: cannot reach the Masani SVN repository and there are no saved pages")
        print("warning: no access to the Masani notes; building the site without the Masani books", file=sys.stderr)
        sys.exit(0)
    mark_fresh("masani")

fallback = yaml.safe_load((ROOT / "masani_meta.yml").read_text())
OUT.mkdir(exist_ok=True)
keep = set()

for folder in sorted(p for p in src.iterdir() if p.is_dir() and not p.name.startswith(".")):
    meta = dict(fallback.get(folder.name, {}))
    if (folder / "book.yml").exists():
        meta.update(yaml.safe_load((folder / "book.yml").read_text()))
    if "title" not in meta:
        print(f"skip {folder.name}: no title (add book.yml)", file=sys.stderr)
        continue
    if meta.get("draft"):
        continue
    notes = "\n\n".join(m.read_text().strip() for m in sorted(folder.glob("*.md")))
    notes = re.sub(r"^#+ ", "### ", notes, flags=re.M)
    notes = re.sub(r"``(.+?)''", r"“\1”", notes, flags=re.S)  # TeX-style quotes
    notes = re.sub(r"`([^`\n]{1,200}?)'", r"“\1”", notes)
    files = [f for f in folder.iterdir() if f.suffix.lower() == ".pdf"]
    slug = folder.name.lower()
    extra = ""
    if files:
        (OUT / slug).mkdir(exist_ok=True)
        for f in files:
            if not (OUT / slug / f.name).exists():
                shutil.copy(f, OUT / slug / f.name)
        extra = "\n\n**Reading material:** " + ", ".join(f"[{f.name}]({slug}/{f.name})" for f in files)
    head = {
        "title": meta["title"],
        "subtitle": f"by {meta['author']}" if meta.get("author") else None,
        "description": meta.get("blurb"),
        "date": (str(meta.get("date", "")) + "-01")[:10] if len(str(meta.get("date", ""))) == 7 else str(meta.get("date", "")),
        "image": meta.get("cover"),
        "toc": False,
    }
    head = {k: v for k, v in head.items() if v}
    keep.add(f"{slug}.qmd")
    write_if_changed(OUT / f"{slug}.qmd",
        "---\n" + yaml.safe_dump(head, sort_keys=False, allow_unicode=True) + "---\n\n" + notes + extra + "\n")
    print("masani:", slug)
for old in OUT.glob("*.qmd"):
    if old.name not in keep:
        old.unlink()
