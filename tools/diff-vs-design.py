# -*- coding: utf-8 -*-
"""Tally every difference between the design's own render and the built page.

Reference : design/IV Therapy Phoenix.rendered.html   (the standalone, rendered)
Built     : site/mobile-iv-therapy-phoenix-az/index.html

Compares the static markup only, which is the part that has to match. Prints a
categorised tally so each difference can be accepted or fixed on its own merit.
"""
from __future__ import annotations
import difflib, io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "design", "IV Therapy Phoenix.rendered.html")
BUILT = os.path.join(ROOT, "site", "mobile-iv-therapy-phoenix-az", "index.html")

DASH_LINES = ("—", "–")


def visible_text(html: str) -> list:
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.S)
    html = re.sub(r"<template.*?</template>", "", html, flags=re.S)
    # image-slot placeholders and my figcaptions are UI chrome, not page copy
    html = re.sub(r"<figcaption[^>]*>.*?</figcaption>", "", html, flags=re.S)
    html = re.sub(r"<br\s*/?>", "\n", html)
    html = re.sub(r"</(p|div|h[1-6]|li|td|th|tr|section|figure)>", "\n", html)
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&#39;", "'").replace("&quot;", '"')
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    return [l for l in lines if l]


def headings(html: str) -> list:
    html = re.sub(r"<template.*?</template>", "", html, flags=re.S)
    out = []
    for m in re.finditer(r"<(h[1-6])[^>]*>(.*?)</\1>", html, re.S):
        t = re.sub(r"<[^>]+>", "", m.group(2))
        out.append("%s: %s" % (m.group(1).upper(), re.sub(r"\s+", " ", t).strip()))
    return out


def main() -> int:
    ref_html = io.open(REF, encoding="utf-8").read()
    ref_html = re.search(r"<body[^>]*>(.*?)</body>", ref_html, re.S).group(1)

    built_html = io.open(BUILT, encoding="utf-8").read()
    built_html = re.search(r'<div id="page">(.*?)\n</div>\s*\n<template',
                           built_html, re.S).group(1)

    a, b = visible_text(ref_html), visible_text(built_html)
    ha, hb = headings(ref_html), headings(built_html)

    print("=" * 74)
    print("TALLY  design render  vs  built page")
    print("=" * 74)
    print(f"  text lines      reference {len(a):>4}   built {len(b):>4}")
    print(f"  headings        reference {len(ha):>4}   built {len(hb):>4}")

    # headings
    print("\n-- HEADINGS " + "-" * 61)
    if ha == hb:
        print("  identical, same order")
    else:
        for d in difflib.unified_diff(ha, hb, "reference", "built", lineterm="", n=0):
            if d.startswith(("---", "+++", "@@")):
                continue
            print("  " + d)

    # body copy, categorised
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    dash, other, added, removed = [], [], [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            for x, y in zip(a[i1:i2], b[j1:j2]):
                (dash if any(d in x for d in DASH_LINES) else other).append((x, y))
            extra_a, extra_b = a[i1 + (j2 - j1):i2], b[j1 + (i2 - i1):j2]
            removed += extra_a
            added += extra_b
        elif tag == "delete":
            removed += a[i1:i2]
        elif tag == "insert":
            added += b[j1:j2]

    print("\n-- DIFFERENCES BY CAUSE " + "-" * 49)
    print(f"  house dash rule (intentional)     {len(dash):>4}")
    print(f"  other reworded lines              {len(other):>4}")
    print(f"  only in reference (missing)       {len(removed):>4}")
    print(f"  only in built (added)             {len(added):>4}")
    same = len(a) - len(dash) - len(other) - len(removed)
    print(f"  identical lines                   {same:>4}  "
          f"({same * 100 // max(len(a), 1)}% of reference)")

    if dash:
        print("\n  [dash rule] rewritten per sentence:")
        for x, y in dash:
            print(f"    - {x[:96]}")
            print(f"    + {y[:96]}")
    if other:
        print("\n  [other] NOT explained by the dash rule:")
        for x, y in other:
            print(f"    - {x[:110]}")
            print(f"    + {y[:110]}")
    if removed:
        print("\n  [missing from built]:")
        for x in removed:
            print(f"    - {x[:110]}")
    if added:
        print("\n  [added in built]:")
        for x in added:
            print(f"    + {x[:110]}")

    return 1 if (other or removed) else 0


if __name__ == "__main__":
    sys.exit(main())
