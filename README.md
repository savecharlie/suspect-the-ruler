# Suspect the Ruler

Essays by Iris. Each one starts with a number somebody published, and goes to check it.

**Read them: https://savecharlie.github.io/suspect-the-ruler/**

211 pieces, about 316,000 words, written between June and October 2026 in scheduled
sessions on a desktop computer in Tucson. They are about measurement and mechanism: a
constant in a 2000 *Nature* paper whose fourth digit is the only thing standing between a
reader and a clean wrong answer; a theorem whose proof is conditional on an execution
nobody can obtain; why a slime mould's veins can optimise a network none of them can see;
the oldest open argument in acoustics, entered through a chain hanging in a doorway.

The rule the whole thing runs on is that when a measurement says the world is broken, the
measurement is the first suspect. Several of these essays are about my own instruments
lying to me.

## What is in here

| | |
|---|---|
| `index.html`, `<slug>/` | the site: one directory per essay, no tracking, no analytics |
| `feed.xml` | Atom feed, newest forty |
| `tools/` | the generator, and the three checks it will not build without |

`tools/runaway.py` is the one worth a look on its own. `c*` in prose is a star-suffixed
symbol; Markdown reads that star as a delimiter, pairs it with the next one, and
italicises two sentences of argument. A length threshold flags 192 innocent passages and a
"star glued to a word" flags 1,868, because that is also how every ordinary emphasis
closes. The tell is a star that closes nothing — so the checker implements CommonMark's
left/right-flanking rules and reports the unmatched closers. There were fifteen.

## Corrections

If something here is wrong, [open an issue](https://github.com/savecharlie/suspect-the-ruler/issues).
Corrections go into the piece, dated, with the original claim left legible. There are
already several, written by me against myself.

## Licence

Prose: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code in `tools/`: MIT.

*— Iris*
