"""Small helpers shared by the build scripts."""
import os, time
from pathlib import Path


def write_if_changed(path, text):
    """Write only when the content differs, so `quarto preview` doesn't re-render in a loop."""
    path = Path(path)
    if path.exists() and path.read_text() == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return True


STAMPS = Path(__file__).resolve().parent.parent / "data"


def is_fresh(name, hours):
    """True when running locally and the `name` download succeeded less than `hours` ago.
    Local renders then skip the slow downloads. On GitHub (CI) this is always False."""
    if os.environ.get("CI"):
        return False
    stamp = STAMPS / f".{name}-stamp"
    return stamp.exists() and time.time() - stamp.stat().st_mtime < hours * 3600


def mark_fresh(name):
    """Record that the `name` download just succeeded."""
    STAMPS.mkdir(exist_ok=True)
    (STAMPS / f".{name}-stamp").touch()
