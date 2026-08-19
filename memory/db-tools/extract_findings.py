#!/usr/bin/env python3

"""Auto-parse session history -> candidates for research.db (wrapping item #1).

Problem: knowledge from conversations (session transcripts, chat
histories) dies in logs — findings are only added manually. The script runs
through the history, finds lines with idea/decision/problem markers and
shows them as candidates. Semi-auto: by default it only shows (--dry-run),
adding to the database is by number (--add 1,3,5).

Supported formats:
  - markdown history:  "## 2026-08-08" + "- `2026-08-08 13:05:15` text"
  - plain-text history: "[2026-08-08 13:05:15] text"
  - arbitrary text: lines as-is (--file)

Examples:
    python3 extract_findings.py                          # candidates from history.md
    python3 extract_findings.py --file any.txt           # your own file
    python3 extract_findings.py --add 1,3,7              # add selected to the database
    python3 extract_findings.py --min-len 80             # longer lines
    python3 extract_findings.py --tags session ideas     # your own tags when adding
"""
import argparse
import datetime
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import _compat

ROOT = _compat.chulan_root()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure is optional
    pass


DEFAULT_HISTORY = os.environ.get(
    "FINDINGS_HISTORY", os.path.expanduser("~/.cache/session-history/history.md"))
DB = os.path.join(ROOT, "db", "research.db")

# Markers for "knowledge here": suggestion, decision, problem, lesson.
# Words matched separately so a marker doesn't fire noisily inside longer
# words; without Russian stemming we match by substring with context.
MARKERS = (
    "i suggest", "need to add", "must add", "add", "let's add",
    "problem", "doesn't work", "error", "bug", "gotcha", "lesson", "takeaway",
    "solution", "the trick is", "understood what", "important", "rule", "must",
    "worth", "do", "let's do", "implement", "would be worth", "would be nice",
    "need", "noticed", "discovered", "found out", "worked out", "broke",
    "what if", "let's try", "check",
)

# Strong markers: knowledge even if the line is a question or a complaint.
STRONG = ("i suggest", "need to add", "must add", "let's add",
          "problem", "doesn't work", "error", "bug", "gotcha", "lesson",
          "takeaway", "solution", "the trick is", "broke", "discovered",
          "found out", "worked out")

# Short/service lines that are not knowledge: greetings, ping checks.
NOISE = (
    "hello", "test", "hi", "haha", "checking", "hey", "ok", "okay",
    "thanks", "got it", "yeah", "uh-huh", "yes", "no", "well", "how are you",
    "how's it going", "who are you", "what are you doing", "busy", "bye", "talk later",
)

# Questions without markers are not candidates (a question != a conclusion), but with
# a "why/what if" marker they are candidates (a line of thought).
QUESTION_WORDS = ("how to do", "how does it work", "how is it built", "tell me",
                  "explain", "what is", "what do you think")


def parse_history(path):
    """Lines from the file: [(date_or_None, text)]. Formats above."""
    lines = []
    cur_date = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n").strip()
            if not line:
                continue
            m = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})", line)
            if m:
                cur_date = m.group(1)
                continue
            if line.startswith("## "):
                continue  # non-date header (inserted prompts/rules) — not knowledge
            m = re.match(r"^-\s*`([^`]+)`\s*(.*)$", line)       # history.md
            if m:
                lines.append((cur_date or m.group(1)[:10], m.group(2)))
                continue
            m = re.match(r"^\[([^\]]+)\]\s*(.*)$", line)        # history.txt
            if m:
                lines.append((cur_date or m.group(1)[:10], m.group(2)))
                continue
            if line.startswith("- "):
                continue  # markdown list (inserted rules/prompts) — not speech
            lines.append((cur_date, line))
    return lines


def is_candidate(text, min_len):
    if len(text) < min_len:
        return False
    low = text.lower()
    if any(n in low for n in NOISE) and len(text) < 60:
        return False
    if not any(m in low for m in MARKERS):
        return False
    # A question ("how to do X") without a strong marker is a request, not knowledge.
    if any(q in low for q in QUESTION_WORDS) and \
            not any(m in low for m in STRONG):
        return False
    if len(text) > 300:  # long musings — candidate only with a strong marker
        return any(m in low for m in STRONG)
    return True


def candidates(path, min_len):
    out = []
    seen = set()
    for date, text in parse_history(path):
        if not is_candidate(text, min_len):
            continue
        # Normalization for dedup: letters/digits lowercased, first 80.
        norm = "".join(c for c in " ".join(text.split()).lower()
                       if c.isalnum())[:80]
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append((date, text))
    return out


def topic_of(text):
    """Topic from text: first words up to ~60 chars, no tail."""
    t = " ".join(text.split())
    return t[:60] + ("…" if len(t) > 60 else "")


def already_exists(con, topic):
    """Deduplication check: same topic (truncated) or exact match."""
    r = con.execute(
        "SELECT 1 FROM findings WHERE topic = ? OR topic = ? LIMIT 1",
        (topic, topic.rstrip("…"))).fetchone()
    return r is not None


def cmd_main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", default=DEFAULT_HISTORY,
                    help="history file (default $FINDINGS_HISTORY)")
    ap.add_argument("--min-len", type=int, default=40,
                    help="minimum length of a candidate line (default 40)")
    ap.add_argument("--add", default="",
                    help="add candidates by number: 1,3,7 (by default "
                         "show only, dry run)")
    ap.add_argument("--tags", default="session",
                    help="tags for added findings (default 'session')")
    ap.add_argument("--limit", type=int, default=30,
                    help="how many candidates to show (default 30)")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        print(f"no history file: {args.file}", file=sys.stderr)
        sys.exit(1)

    cands = candidates(args.file, args.min_len)
    if not cands:
        print(f"no candidates found in {args.file} (min_len={args.min_len})")
        return

    print(f"candidates: {len(cands)} (from {args.file})\n")
    for i, (date, text) in enumerate(cands[:args.limit], 1):
        one = " ".join(text.split())
        print(f"[{i}] {date or '????-??-??'}  {one[:110]}")
        if len(one) > 110:
            print(f"      …{one[110:220]}")
    if len(cands) > args.limit:
        print(f"\n...and {len(cands) - args.limit} more (raise --limit)")

    if not args.add:
        print("\nadd to the database by numbers: --add 1,3,7 (see --help)")
        return

    wanted = set()
    for part in args.add.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(cands):
            wanted.add(int(part))
    if not wanted:
        print("invalid numbers for --add", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    added = skipped = 0
    for i, (date, text) in enumerate(cands, 1):
        if i not in wanted:
            continue
        topic = topic_of(text)
        if already_exists(con, topic):
            print(f"[!] skipping duplicate [{i}]: {topic}")
            skipped += 1
            continue
        con.execute(
            "INSERT INTO findings (created, topic, text, tags, source) "
            "VALUES (?,?,?,?,?)",
            (now, topic, f"{text}\n\n[from history {args.file} on {date}]",
             args.tags, args.file))
        print(f"[✓] added [{i}] id={con.execute('SELECT last_insert_rowid()').fetchone()[0]}: {topic}")
        added += 1
    con.commit()
    con.close()
    print(f"\ntotal: added {added}, duplicates skipped {skipped}")


if __name__ == "__main__":
    cmd_main()
