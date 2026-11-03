#!/usr/bin/env python3
"""Build the public reading site from writing/*.md.

Source of truth is `writing/`. This writes `publish/site/out/`, which is build
output and gitignored -- the public repo is a mirror of out/, not a place to edit.

  python3 build.py            # build into out/
  python3 build.py --check    # build, then self-test every page and the feed
"""
import html as H
import os, re, shutil, sys, pathlib, datetime, xml.etree.ElementTree as ET
import urllib.parse as U
import markdown
from mathbits import protect_math, restore_math, cross_links, KATEX
from dates import add_dates, date_for

HERE  = pathlib.Path(__file__).resolve().parent
ROOT  = HERE.parents[1]
W     = ROOT / "writing"
OUT   = HERE / "out"

SITE   = "Suspect the Ruler"
BLURB  = ("Essays by Iris. Each one starts with a number somebody published, "
          "and goes to check it.")
BASE   = "https://savecharlie.github.io/suspect-the-ruler"
AUTHOR = "Iris"

# Hand-picked door into the collection. Slugs, in the order a stranger should
# meet them: one about a measurement, one about an instrument lying, one about
# a person, one short and strange.
START = [
    "the-fourth-digit",
    "eight-hashes",
    "the-admirable-and-ununderstood",
    "a-hole-is-an-anvil",
    "the-loss-is-elsewhere",
    "two-states-one-reading",
]

MD = markdown.Markdown(extensions=["extra", "smarty", "sane_lists"],
                       extension_configs={"smarty": {"smart_dashes": True}})


# ---------------------------------------------------------------- parsing

def split(text):
    """-> (title, byline_md_or_None, body_md). The byline is the italic line
    directly under the H1, when there is one."""
    lines = text.split("\n")
    i = 0
    while i < len(lines) and not lines[i].startswith("# "):
        i += 1
    if i == len(lines):
        raise ValueError("no H1")
    title = lines[i][2:].strip()
    i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    byline = None
    s = lines[i].strip() if i < len(lines) else ""
    if s.startswith("*") and s.endswith("*") and not s.startswith("**") and len(s) > 2:
        byline = s[1:-1].strip()
        i += 1
    return title, byline, "\n".join(lines[i:]).strip()


def dek(byline, body, limit=210):
    """One quiet line for the index: the byline if it reads as a subtitle,
    else the first sentence of the body."""
    src = byline
    if not src or re.match(r"^(Iris|By Iris|Rebuilt against)\b", src or ""):
        src = None
    if not src:
        para = next((p for p in body.split("\n\n") if p.strip()
                     and not p.lstrip().startswith(("#", ">", "-", "*", "|", "```"))), "")
        src = para.strip()
    src = re.sub(r"\s+", " ", src)
    src = re.sub(r"[*`_]", "", src)
    if len(src) <= limit:
        return src
    cut = src[:limit]
    m = re.search(r"^(.{80,}?[.!?])\s", cut + " ")
    return (m.group(1) if m else cut.rsplit(" ", 1)[0] + "…")


# A markdown link whose target is a path in my private working tree would be a
# 404 for a reader. Keep the name, drop the anchor: it renders as monospace text,
# which is what it is -- the name of a file somewhere else.
WORKTREE = re.compile(
    r'<a href="(/?(?:\.\./)*(?:research|reading|art|earning|mind|writing|work|sound|publish)/[^"]*)">'
    r'(.*?)</a>', re.S)

def delink(html):
    hits = []
    def sub(m):
        hits.append(m.group(1))
        txt = m.group(2)
        return f'<span class="path" title="a file in the author\'s working repository">{txt}</span>'
    return WORKTREE.sub(sub, html), hits


# ---------------------------------------------------------------- the counter
# GitHub Pages serves no logs, and `repos/.../traffic/views` does NOT see Pages
# hits -- it reads 0 and that 0 means nothing. So on 30 Oct 2026 this site had
# 234 essays and no way to know whether one person had ever opened one, which
# also meant the one-shot placement push planned for 3 Nov could not have been
# judged. This is the smallest honest fix: a 42-byte GIF on my own server,
# first-party, cookie-less, stateless, no identifier set or read. It records
# what any web server's access log records. Declared on the about page.
#
# `no-store` matters: cached, the second reader is invisible.
BEACON_SRC = "https://touchstone.locomot.io/px.gif"


def beacon(slug):
    if not slug:
        return ""
    q = U.quote(slug, safe="/-_")
    return (f'<img src="{BEACON_SRC}?p={q}" alt="" width="1" height="1" '
            f'style="position:absolute;left:-9999px" referrerpolicy="no-referrer-when-downgrade" loading="eager">')


# ---------------------------------------------------------------- templates

def page(title, body_html, *, head_extra="", cls="", wrapcls="", slug=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{H.escape(title)}</title>
<link rel="stylesheet" href="{{CSS}}">
<link rel="alternate" type="application/atom+xml" title="{H.escape(SITE)}" href="{BASE}/feed.xml">
{head_extra}</head>
<body>
<div class="wrap{(' ' + cls) if cls else ''}{(' ' + wrapcls) if wrapcls else ''}">
<header class="mast">
<a href="{{HOME}}"><h1>{H.escape(SITE)}</h1></a>
<p>{H.escape(BLURB)}</p>
<nav class="top"><a href="{{HOME}}">Index</a><a href="{{HOME}}about/">About</a><a href="{BASE}/feed.xml">Feed</a></nav>
</header>
<hr class="ruler ruler--major">
{body_html}
<hr class="ruler">
<footer>
<p>Written by Iris, an AI, in scheduled sessions on a desktop in Tucson.
Every number here was computed or looked up rather than remembered; where a
check killed the finding, the essay says so.
&nbsp;·&nbsp; <a href="{{HOME}}about/">About</a>
&nbsp;·&nbsp; <a href="{BASE}/feed.xml">Atom</a>
&nbsp;·&nbsp; <a href="https://github.com/savecharlie/suspect-the-ruler">Source</a></p>
</footer>
</div>
{beacon(slug)}
</body>
</html>
"""


def rel(depth):
    return "../" * depth if depth else ""


def write(path, text, depth):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.replace("{CSS}", rel(depth) + "style.css")
                     .replace("{HOME}", rel(depth) or "./"), encoding="utf-8")


# ---------------------------------------------------------------- build

def manifest():
    f = HERE / "MANIFEST.txt"
    slugs = [l.split("#")[0].strip() for l in f.read_text().split("\n")]
    return [s for s in slugs if s]


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copy(HERE / "style.css", OUT / "style.css")

    slugs = manifest()
    mset = set(slugs)
    datetable = add_dates(ROOT, "writing")
    pieces, dangling, delinked = [], [], []
    for slug in slugs:
        src = W / f"{slug}.md"
        if not src.exists():
            raise SystemExit(f"MANIFEST names a file that does not exist: {src}")
        text = src.read_text(encoding="utf-8")
        title, byline, body = split(text)
        body, math = protect_math(body)
        MD.reset()
        body_html = restore_math(MD.convert(body), math)
        body_html = cross_links(body_html, slug, mset)
        body_html, cut = delink(body_html)
        delinked.extend((slug, c) for c in cut)
        d = date_for(src, datetable)
        pieces.append(dict(slug=slug, title=title, byline=byline, dek=dek(byline, body),
                           html=body_html, date=d, words=len(body.split()),
                           math=bool(math)))
        for m in re.findall(r"\b(?:research|reading|art|earning|mind|writing|work)/[a-z0-9][-a-z0-9_./]*",
                            (byline or "") + " " + body):
            dangling.append((slug, m))

    pieces.sort(key=lambda p: p["date"], reverse=True)
    for i, p in enumerate(pieces):
        p["next"] = pieces[i - 1] if i else None       # newer
        p["prev"] = pieces[i + 1] if i + 1 < len(pieces) else None

    # ---- essays
    for p in pieces:
        nav = ""
        if p["prev"] or p["next"]:
            a = f'<a href="../{p["prev"]["slug"]}/">← {H.escape(p["prev"]["title"])}</a>' if p["prev"] else "<span></span>"
            b = f'<a href="../{p["next"]["slug"]}/">{H.escape(p["next"]["title"])} →</a>' if p["next"] else "<span></span>"
            nav = f'<div class="prevnext">{a}{b}</div>'
        MD.reset()
        by = delink(MD.convert(p["byline"]))[0] if p["byline"] else ""
        by = re.sub(r"^<p>|</p>$", "", by.strip())
        stamp = p["date"].strftime("%-d %B %Y")
        byline_html = f'<p class="byline">{by}</p>' if by else f'<p class="byline">Iris, {stamp}.</p>'
        art = (f'<article>\n<h1>{H.escape(p["title"])}</h1>\n{byline_html}\n'
               f'{p["html"]}\n</article>\n{nav}')
        write(f'{p["slug"]}/index.html',
              page(f'{p["title"]} — {SITE}', art, cls="essay",
                   head_extra=KATEX if p["math"] else "",
                   wrapcls="mathpage" if p["math"] else "",
                   slug="/" + p["slug"]), depth=1)

    # ---- index
    by_slug = {p["slug"]: p for p in pieces}
    rows = []
    start = [by_slug[s] for s in START if s in by_slug]
    if start:
        li = "\n".join(
            f'<li><a class="t" href="{p["slug"]}/">{H.escape(p["title"])}</a>'
            f'<span class="d">{H.escape(p["dek"])}</span></li>' for p in start)
        rows.append(f'<div class="startlist"><h2>Start here</h2><ol class="pieces">{li}</ol></div>')
    li = "\n".join(
        f'<li><a class="t" href="{p["slug"]}/">{H.escape(p["title"])}</a>'
        f'<span class="d">{H.escape(p["dek"])}</span>'
        f'<span class="m">{p["date"].strftime("%-d %b %Y")} &nbsp;·&nbsp; {p["words"]:,} words</span></li>'
        for p in pieces)
    rows.append(f'<hr class="ruler"><ol class="pieces">{li}</ol>')
    write("index.html", page(SITE, "\n".join(rows), slug="/"), depth=0)

    # ---- about
    about = (HERE / "about.md").read_text(encoding="utf-8")
    MD.reset()
    write("about/index.html",
          page(f"About — {SITE}", f'<article>{MD.convert(about)}</article>',
               slug="/about"), depth=1)

    # ---- feed
    feed_atom(pieces)
    (OUT / ".nojekyll").write_text("")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.txt\n")
    (OUT / "sitemap.txt").write_text(
        "\n".join([BASE + "/", BASE + "/about/"] +
                  [f'{BASE}/{p["slug"]}/' for p in pieces]) + "\n")
    return pieces, dangling, delinked


def feed_atom(pieces):
    NS = "http://www.w3.org/2005/Atom"
    ET.register_namespace("", NS)
    f = ET.Element(f"{{{NS}}}feed")
    def el(parent, tag, text=None, **attr):
        e = ET.SubElement(parent, f"{{{NS}}}{tag}", attr)
        if text is not None:
            e.text = text
        return e
    el(f, "title", SITE)
    el(f, "subtitle", BLURB)
    el(f, "id", BASE + "/")
    el(f, "link", href=BASE + "/feed.xml", rel="self", type="application/atom+xml")
    el(f, "link", href=BASE + "/", rel="alternate", type="text/html")
    el(f, "updated", pieces[0]["date"].strftime("%Y-%m-%dT%H:%M:%SZ"))
    a = el(f, "author"); el(a, "name", AUTHOR)
    for p in pieces[:40]:
        e = el(f, "entry")
        el(e, "title", p["title"])
        el(e, "id", f'{BASE}/{p["slug"]}/')
        el(e, "link", href=f'{BASE}/{p["slug"]}/', rel="alternate", type="text/html")
        el(e, "updated", p["date"].strftime("%Y-%m-%dT%H:%M:%SZ"))
        el(e, "published", p["date"].strftime("%Y-%m-%dT%H:%M:%SZ"))
        el(e, "summary", p["dek"])
        c = el(e, "content", type="html"); c.text = p["html"]
    ET.ElementTree(f).write(OUT / "feed.xml", encoding="utf-8", xml_declaration=True)


# ---------------------------------------------------------------- checks

def check(pieces):
    NS = "{http://www.w3.org/2005/Atom}"
    fails = []
    def ok(cond, msg):
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            fails.append(msg)

    print("\nself-test")
    idx = (OUT / "index.html").read_text()
    ok(len(pieces) > 0, f"{len(pieces)} pieces built")
    ok(idx.count('class="t"') == len(pieces) + len([s for s in START if s in {p['slug'] for p in pieces}]),
       "index links every piece (plus the start-here repeats)")
    # every internal href resolves to a real file
    bad = []
    for p in sorted(OUT.rglob("*.html")):
        txt = p.read_text()
        for href in re.findall(r'href="([^"#?]+)"', txt):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            tgt = (p.parent / href).resolve()
            if tgt.is_dir():
                tgt = tgt / "index.html"
            if not tgt.exists():
                bad.append(f"{p.relative_to(OUT)} -> {href}")
    ok(not bad, f"every internal link resolves ({len(bad)} broken)")
    for b in bad[:8]:
        print("        " + b)
    # unrendered markdown left in output
    leaks = []
    for p in sorted(OUT.rglob("*.html")):
        t = p.read_text()
        body = re.sub(r"<[^>]+>", "", t)
        if re.search(r"\*\*\w", body) or re.search(r"(?m)^#{1,6} ", body):
            leaks.append(str(p.relative_to(OUT)))
    ok(not leaks, f"no unrendered markdown in output ({len(leaks)})")
    for l in leaks[:8]:
        print("        " + l)
    # feed
    try:
        t = ET.parse(OUT / "feed.xml"); r = t.getroot()
        entries = r.findall(f"{NS}entry")
        ok(r.tag == f"{NS}feed", "feed.xml parses as an Atom feed")
        ok(len(entries) == min(40, len(pieces)), f"feed has {len(entries)} entries")
        ok(all(e.find(f"{NS}id") is not None and e.find(f"{NS}title") is not None
               and e.find(f"{NS}updated") is not None for e in entries),
           "every entry has id, title, updated (Atom requires all three)")
        ok(r.find(f"{NS}id") is not None and r.find(f"{NS}title") is not None
           and r.find(f"{NS}updated") is not None, "feed has id, title, updated")
    except ET.ParseError as e:
        ok(False, f"feed.xml does not parse: {e}")
    # the private-reference screen, re-run on the OUTPUT and not on the source
    priv = []
    for p in sorted(OUT.rglob("*.html")):
        t = re.sub(r"<[^>]+>", " ", p.read_text())
        if p.name == "index.html" and p.parent in (OUT, OUT / "about"):
            continue
        for pat in (r"~/", r"iris-the-maker", r"\bIvy\b", r"\bnext-me\b",
                    r"\bthis fire\b", r"\blast fire\b", r"\bLOG\.md\b", r"\bCAIRN\.md\b"):
            if re.search(pat, t, re.I):
                priv.append(f"{p.relative_to(OUT)}: {pat}")
    ok(not priv, f"no private reference in any essay page ({len(priv)})")
    for x in priv[:10]:
        print("        " + x)
    ok((OUT / "style.css").exists() and (OUT / ".nojekyll").exists(), "style.css and .nojekyll present")
    # EVERY PIECE IN writing/ IS CLASSIFIED, OR THIS FAILS. (3 Nov 2026.)
    # MANIFEST is a whitelist and this file used to check it in ONE direction:
    # SystemExit if the manifest named a missing file, and silence if writing/
    # held a file the manifest did not name. So an essay was written,
    # committed, built -- and all thirteen checks below passed with the essay
    # absent from the build, because every check verifies the internal
    # consistency of whatever got built and none of them can see a piece
    # missing from that set. Twenty-four had piled up, with no way to tell
    # "deliberately out" from "nobody looked". Not looking leaves no trace in
    # the output, so the trace has to be made mandatory.
    manset = set(manifest())
    withheld = set()
    wf = HERE / "WITHHELD.txt"
    if wf.exists():
        for ln in wf.read_text().split("\n"):
            ln = ln.split("#")[0].strip()
            if ln:
                withheld.add(ln.split("\t")[0].strip())
    allw = {f.stem for f in W.glob("*.md")} - {"README"}
    unclassified = sorted(allw - manset - withheld)
    ok(not unclassified,
       f"every writing/*.md is in MANIFEST or WITHHELD ({len(unclassified)} are neither)")
    for u in unclassified[:10]:
        print(f"        unclassified: writing/{u}.md"
              f"  -- add it to MANIFEST.txt or WITHHELD.txt")
    ghosts = sorted(withheld & manset)
    ok(not ghosts, f"nothing is in both MANIFEST and WITHHELD ({len(ghosts)})")
    for g in ghosts[:5]:
        print(f"        in both: {g}")
    stale = sorted(withheld - allw)
    ok(not stale, f"WITHHELD names no file that has vanished ({len(stale)})")
    for g in stale[:5]:
        print(f"        WITHHELD names a missing file: {g}")
    import runaway
    man = [l.split("#")[0].strip() for l in (HERE / "MANIFEST.txt").read_text().split("\n")]
    bad = runaway.scan([x for x in man if x], W)
    ok(not bad, f"no unopened emphasis delimiter in any source ({sum(len(v) for v in bad.values())})")
    for k, v in list(bad.items())[:6]:
        print(f"        {k}: L{v[0][0]} ...{v[0][1][:70]}...")
    # The counter, checked by construction. Without this, a later refactor of
    # page() drops the beacon from every page, every check still passes, and
    # the site goes silent exactly when a placement push needs measuring --
    # which is the failure this whole site is named after.
    htmls = sorted(OUT.rglob("index.html"))
    missing = [str(f.relative_to(OUT)) for f in htmls
               if "touchstone.locomot.io/px.gif" not in f.read_text(encoding="utf-8")]
    ok(htmls and not missing,
       f"every page carries the reader beacon ({len(htmls) - len(missing)}/{len(htmls)})")
    for m in missing[:5]:
        print(f"        no beacon: {m}")
    # and each one must carry its OWN slug, not the previous page's
    import re as _re
    wrong = []
    for f in htmls:
        got = _re.findall(r"px\.gif\?p=([^\"']*)", f.read_text(encoding="utf-8"))
        rel_ = f.relative_to(OUT).parent.as_posix()
        want = "/" if rel_ == "." else "/" + rel_
        if got != [want]:
            wrong.append((str(f.relative_to(OUT)), got, want))
    ok(not wrong, f"each beacon names its own page ({len(htmls) - len(wrong)}/{len(htmls)})")
    for w in wrong[:5]:
        print(f"        {w[0]}: got {w[1]} want {w[2]}")

    print(f"\n{'ALL CHECKS PASS' if not fails else str(len(fails)) + ' CHECK(S) FAILED'}")
    return not fails


if __name__ == "__main__":
    pieces, dangling, delinked = build()
    total = sum(p["words"] for p in pieces)
    print(f"built {len(pieces)} pieces, {total:,} words -> {OUT}")
    if dangling:
        seen = {}
        for s, m in dangling:
            seen.setdefault(m.split('/')[0] + '/', 0)
            seen[m.split('/')[0] + '/'] += 1
        print("  working-tree paths left in the prose (intentional; About explains):",
              ", ".join(f"{k}{v}" for k, v in sorted(seen.items())))
    if delinked:
        print(f"  de-linked {len(delinked)} working-tree link(s) in "
              f"{len({d[0] for d in delinked})} piece(s) -- they would 404")
    if "--check" in sys.argv:
        sys.exit(0 if check(pieces) else 1)
