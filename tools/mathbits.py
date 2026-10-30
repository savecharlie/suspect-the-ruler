"""Math and cross-reference handling for the site build.

Markdown eats LaTeX: `$[x^{p-1}](F^lF')$` becomes an anchor whose href is
`F^lF'`. So every math span comes out before conversion and goes back after,
and KaTeX is loaded only on the pages that contain math -- the other 195 pages
are HTML and CSS with no script at all.
"""
import re

_FENCE   = re.compile(r"(?s)```.*?```")
_INDENT  = re.compile(r"(?m)^(?: {4}|\t).*$")
_INLINE  = re.compile(r"`[^`\n]+`")
_DISPLAY = re.compile(r"(?s)\$\$.+?\$\$")
_MATH    = re.compile(r"(?<![\\$])\$(?!\s)([^$\n]{1,400}?)(?<!\\)\$(?!\d)")


def _code_spans(md):
    return [m.span() for rx in (_FENCE, _INDENT, _INLINE) for m in rx.finditer(md)]


def protect_math(md):
    """-> (md with @@MATHn@@ tokens, [raw math strings]). Code is left alone."""
    math = []

    def run(rx, text):
        keep = _code_spans(text)

        def repl(m):
            if any(a <= m.start() < b for a, b in keep):
                return m.group(0)
            math.append(m.group(0))
            return "@@MATH%d@@" % (len(math) - 1)
        return rx.sub(repl, text)

    md = run(_DISPLAY, md)
    md = run(_MATH, md)
    return md, math


def restore_math(html, math):
    for i, raw in enumerate(math):
        esc = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = html.replace("@@MATH%d@@" % i, esc)
    return html


def cross_links(html, self_slug, manifest_set):
    """A markdown link to another essay's .md file becomes a link to its page."""
    def sub(m):
        target = m.group(1)[:-3]
        if target in manifest_set and target != self_slug:
            return '<a href="../%s/">' % target
        return m.group(0)
    return re.sub(r'<a href="([a-z0-9][-a-z0-9_]*\.md)">', sub, html)


_CDN = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist"
_AUTORENDER = (
    "renderMathInElement(document.body,{delimiters:["
    "{left:'$$',right:'$$',display:true},"
    "{left:'$',right:'$',display:false}],throwOnError:false});"
)

KATEX = (
    '<link rel="stylesheet" href="%(cdn)s/katex.min.css" crossorigin="anonymous">\n'
    '<script defer src="%(cdn)s/katex.min.js" crossorigin="anonymous"></script>\n'
    '<script defer src="%(cdn)s/contrib/auto-render.min.js" crossorigin="anonymous" '
    'onload="%(run)s"></script>\n'
) % {"cdn": _CDN, "run": _AUTORENDER}
