"""Find emphasis that the writer never opened.

`c*` in prose is a star-suffixed symbol -- the critical value, the optimum.
Markdown reads that star as a delimiter, pairs it with the next one, and
italicises everything between; in the first essay I looked at that was two
sentences of argument, set in italic, saying nothing I meant by it.

A LONG <em> IS NOT THE TELL. This corpus has deliberate italic passages of
eighty words, and a length threshold flagged 192 of them. Neither is "a star
glued to a word" -- that is also the closing half of every ordinary emphasis,
and it matched 1,868 times. The tell is a star that closes nothing: walk the
paragraph, call a star an opener when whitespace is on its left and a closer
when a word is, and report the closers with no opener waiting.
"""
import re, sys, pathlib

FENCE  = re.compile(r"(?s)```.*?```")
# 4-space / tab indented code: `\u03c6*` in an equation block is not prose.
INDENT = re.compile(r"(?m)^(?: {4}|\t).*$")
INLINE = re.compile(r"`[^`\n]+`")
MATH   = re.compile(r"(?s)\$\$.+?\$\$|(?<!\$)\$[^$\n]{1,400}\$")


def _blank(md):
    """Code and math replaced by 'x', so offsets AND flanking are preserved.

    Spaces were wrong: blanking `$p$` turned `*$p$-integer*` into `*   -integer*`,
    whose opening star is followed by whitespace and therefore cannot open --
    so the real closer looked like an orphan. The filler has to be a word
    character, because that is what the deleted text was."""
    def z(m):
        return "x" * (m.end() - m.start())
    return MATH.sub(z, INLINE.sub(z, INDENT.sub(z, FENCE.sub(z, md))))


PUNCT = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~\u2014\u2013\u2018\u2019\u201c\u201d\u2026")


def _flank(s, i, j):
    """CommonMark left/right-flanking for the delimiter run s[i:j]."""
    before = s[i - 1] if i else " "
    after  = s[j] if j < len(s) else " "
    bws, aws = before.isspace(), after.isspace()
    bp,  ap  = before in PUNCT, after in PUNCT
    left  = (not aws) and ((not ap) or bws or bp)
    right = (not bws) and ((not bp) or aws or ap)
    return left, right


def orphans(md):
    """-> [(line, context)] for every '*' run that can close and has nothing open."""
    text = _blank(md)
    out = []
    for para in re.finditer(r"(?s).+?(?:\n\s*\n|$)", text):
        base, s = para.start(), para.group(0)
        stack, i = [], 0
        while i < len(s):
            if s[i] != "*" or (i and s[i - 1] == "\\"):
                i += 1
                continue
            j = i
            while j < len(s) and s[j] == "*":
                j += 1
            if j - i >= 2:                      # ** / *** : strong, left alone
                i = j
                continue
            left, right = _flank(s, i, j)
            if right and stack:
                stack.pop()
            elif left:
                stack.append(i)
            elif right:
                off = base + i
                out.append((md.count("\n", 0, off) + 1,
                            md[max(0, off - 50):off + 50].replace("\n", " ")))
            i = j
    return out


def scan(slugs, writing):
    bad = {}
    for s in slugs:
        o = orphans((writing / f"{s}.md").read_text())
        if o:
            bad[s] = o
    return bad


if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    W = here.parents[1] / "writing"
    slugs = [l.split("#")[0].strip() for l in (here / "MANIFEST.txt").read_text().split("\n")]
    bad = scan([x for x in slugs if x], W)
    for s, o in bad.items():
        print(f"\n{s}  ({len(o)})")
        for ln, ctx in o[:5]:
            print(f"   L{ln}: ...{ctx}...")
    n = sum(len(v) for v in bad.values())
    print(f"\n{n} unopened emphasis delimiter(s) in {len(bad)} piece(s)")
    sys.exit(1 if n else 0)
