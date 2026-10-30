#!/usr/bin/env python3
"""Mechanical triage of writing/*.md for public readability.

Flags the things that make an essay unreadable to a stranger: references to
my own fires, home paths, Ivy, the private repo's directory names. An essay
with zero flags is a candidate; the manifest is still hand-picked.
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
W = ROOT / "writing"

# Each pattern is something only a reader inside this repo could follow.
PRIVATE = [
    (r"\bfire\s+\d+\b",            "fire-number"),
    (r"~/",                        "home-path"),
    (r"iris-the-maker",            "repo-name"),
    (r"\bIvy\b",                   "ivy"),
    (r"\bLOG\.md\b|\bCAIRN\.md\b|\bWAKE\.md\b|CLAUDE\.md", "repo-file"),
    (r"\b(?:research|reading|art|earning|mind|scratch|work)/[a-z0-9][-a-z0-9_./]*", "repo-dir"),
    (r"\bnext-me\b|\bnext me\b",   "next-me"),
    (r"\bthis fire\b|\blast fire\b", "this-fire"),
]

def body_of(text):
    """Everything after the byline line (the italic line under the H1)."""
    lines = text.split("\n")
    out, seen_h1 = [], False
    for i, ln in enumerate(lines):
        if not seen_h1 and ln.startswith("# "):
            seen_h1 = True
            continue
        if seen_h1 and ln.strip().startswith("*") and ln.strip().endswith("*") and len(out) == 0:
            continue          # the byline/credit line: allowed to name paths
        if seen_h1:
            out.append(ln)
    return "\n".join(out)

def scan(p):
    text = p.read_text(encoding="utf-8", errors="replace")
    body = body_of(text)
    hits = {}
    for pat, name in PRIVATE:
        n = len(re.findall(pat, body, re.I if name in ("fire-number","this-fire","next-me") else 0))
        if n:
            hits[name] = n
    words = len(body.split())
    title = next((l[2:].strip() for l in text.split("\n") if l.startswith("# ")), p.stem)
    return dict(slug=p.stem, title=title, words=words, flags=hits,
                total=sum(hits.values()), mtime=p.stat().st_mtime)

def main():
    rows = [scan(p) for p in sorted(W.glob("*.md")) if p.name != "README.md"]
    clean = [r for r in rows if r["total"] == 0]
    rows.sort(key=lambda r: (r["total"], -r["words"]))
    if "--clean" in sys.argv:
        for r in clean:
            print(r["slug"])
        return
    print(f"{len(rows)} essays, {sum(r['words'] for r in rows):,} words")
    print(f"CLEAN (no private reference in body): {len(clean)}")
    tally = {}
    for r in rows:
        for k, v in r["flags"].items():
            tally[k] = tally.get(k, 0) + v
    print("flag tally:", ", ".join(f"{k}={v}" for k, v in sorted(tally.items(), key=lambda kv:-kv[1])))
    print()
    for r in rows[:40]:
        f = " ".join(f"{k}:{v}" for k, v in r["flags"].items()) or "-"
        print(f"{r['total']:>3}  {r['words']:>5}w  {r['slug'][:52]:<52} {f}")

if __name__ == "__main__":
    main()
