"""eval/results_io.py — shared append-only JSON result store for all kit evals.

save_result(path=None) writes into the timestamped shared store
(eval/results/, one JSON per run, git-tracked); save_result(path=<explicit>)
writes exactly that file instead. load_runs() reads the store sorted by UTC.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "eval" / "results"


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


def _dump(doc: dict, target: Path) -> None:
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                      encoding="utf-8", newline="\n")


def save_result(kind: str, model_slug: str, payload: dict,
                path: Path | None = None) -> Path:
    """path=None -> shared store (timestamped name); path given -> exact file."""
    utc = datetime.now(timezone.utc)
    doc = {"kind": kind, "model": _slug(model_slug),
           "utc": utc.isoformat(timespec="seconds"), **payload}
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        _dump(doc, path)
        return path
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{kind}-{_slug(model_slug)}-{utc:%Y%m%d-%H%M}UTC"
    target = RESULTS_DIR / f"{base}.json"
    n = 1
    while target.exists():
        n += 1
        target = RESULTS_DIR / f"{base}-{n}.json"
    _dump(doc, target)
    return target


def load_runs(kind: str | None = None) -> list[dict]:
    if not RESULTS_DIR.exists():
        return []
    out = []
    for p in sorted(RESULTS_DIR.glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        try:
            doc["_path"] = str(p.relative_to(ROOT))
        except ValueError:            # patched RESULTS_DIR (tests) — keep absolute
            doc["_path"] = str(p)
        out.append(doc)
    out.sort(key=lambda d: d["utc"])
    return out
