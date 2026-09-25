# -*- coding: utf-8 -*-
"""Turn the Claude Design export into a production page.

Input : design/IV Therapy Phoenix.dc.html
Output: site/mobile-iv-therapy-phoenix-az/index.html

What it does, and why:

1. Strips the omelette canvas bootstrap, `support.js` and `image-slot.js`.
   Those are the Claude Design editor runtime (`__dcContentKeyed`, preview
   tokens, postMessage to claude.ai). None of it belongs on a client site.

2. Inlines a ~90 line vanilla reimplementation of the runtime instead, so the
   page is self-contained and portable to any path or CMS. It keeps its
   tabs, stepper and accordion with no dependency on Anthropic infrastructure.
       <sc-for list="{{ expr }}" as="x">   repeat
       <sc-if  value="{{ expr }}">         conditional
       {{ expr }}                          text + attribute interpolation
       onClick="{{ fn }}"                  event binding

3. Converts every <image-slot> into a real <figure><img> with the brand kit's
   alt-text rule applied, so the client drops in photo URLs and ships.

4. Removes em dashes per the house style rule. Each one is rewritten as a
   sentence, never find-and-replaced, because deleting the character alone
   leaves broken punctuation. En dashes become hyphens.

5. Adds the head the design has no opinion about: title, meta description,
   canonical, Open Graph, and FAQPage + MedicalBusiness JSON-LD.
"""
from __future__ import annotations
import io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "design", "IV Therapy Phoenix.dc.html")
RENDERED = os.path.join(ROOT, "design", "IV Therapy Phoenix.rendered.html")
OUT_DIR = os.path.join(ROOT, "site", "mobile-iv-therapy-phoenix-az")
OUT = os.path.join(OUT_DIR, "index.html")
ASSET_DIR = os.path.join(OUT_DIR, "assets")

CANONICAL = "https://thedripivinfusion.com/mobile-iv-therapy-phoenix-az"
TITLE = "IV Therapy in Phoenix, AZ | Mobile IV Drips Delivered by RNs"
DESC = ("Mobile IV therapy in Phoenix, AZ from The Drip IV Infusion. A licensed RN reaches "
        "most addresses in 60 minutes. Eight drips, $195 to $495. Book today.")

# ---- 4. punctuation, per sentence -----------------------------------------
DASH_FIXES = [
    ("The Total Prevention combines vitamin C, zinc and B-complex — booked ahead of travel",
     "The Total Prevention combines vitamin C, zinc and B-complex, booked ahead of travel"),
    ("17 years in air medical and flight nursing — the source of the habit",
     "17 years in air medical and flight nursing, the source of the habit"),
    ("Jenna, Karena and Kris cover the Phoenix rota — each a licensed RN",
     "Jenna, Karena and Kris cover the Phoenix rota, and each is a licensed RN"),
    ("at any point in its history — an eight-day triple-digit run",
     "at any point in its history, during an eight-day triple-digit run"),
    ("Queen Creek and San Tan Valley — see", "Queen Creek and San Tan Valley. See"),
    ("Phoenix, AZ 85016 — Mon", "Phoenix, AZ 85016. Mon"),
    ("are emergencies — call 911", "are emergencies: call 911"),
    ("before any elective infusion — it's arranged as part of your intake.",
     "before any elective infusion, and it is arranged as part of your intake."),
    ("elective IV hydration or nutrient infusion — in a clinic or in your Phoenix living room.",
     "elective IV hydration or nutrient infusion, whether in a clinic or in your Phoenix living room."),
    ("Sit, work or lie down — the line runs the same.",
     "Sit, work or lie down; the line runs the same."),
    ("$30 each</strong> — attach to any bag.",
     "$30 each</strong>, attaching to any bag."),
]
for _n in range(1, 9):
    DASH_FIXES.append((f"Step {_n} — ", f"Step {_n} - "))


# ---- 5b. the medical review byline -----------------------------------------
# The design leaves the reviewer as a placeholder because the client names them,
# not the designer. Brandon Lang is an RN and the CEO, so this is an internal
# clinical review rather than an independent or physician one. The byline states
# his actual credentials and role and claims nothing beyond them.
REVIEWER_NAME = "Brandon Lang, MSN, RN"
REVIEWER_ROLE = "Co-founder and Chief Executive Officer, The Drip IV Infusion"
REVIEW_DATE_ISO = "2026-09-25"
REVIEW_DATE_TEXT = "25 September 2026"

_OLD_NOTICE = (
    "Medically reviewed by [reviewer name, credentials, date]. IV therapy delivered by "
    "The Drip IV Infusion is a wellness service. It does not diagnose, treat, cure or "
    "prevent any disease, and it is not a substitute for emergency medical care. Heat "
    "exhaustion, heat stroke, chest pain, confusion, fainting, severe or persistent "
    "vomiting, or a temperature above 103F require 911 or an emergency department. Talk "
    "to your own physician before starting any infusion programme."
)
_NEW_NOTICE = (
    f"<strong>Medically reviewed by {REVIEWER_NAME}</strong>, {REVIEWER_ROLE}. "
    f"Last reviewed {REVIEW_DATE_TEXT}.<br><br>"
    "IV therapy from The Drip IV Infusion is a wellness service. It does not diagnose, "
    "treat, cure or prevent any disease, and it is not a substitute for emergency "
    "medical care.<br><br>"
    "<strong>Call 911 or go to an emergency department</strong> for chest pain, "
    "confusion, fainting, a seizure, hot dry skin, heat exhaustion or heat stroke, "
    "severe or persistent vomiting, or a temperature above 103F.<br><br>"
    "Every infusion runs under a valid order from a licensed prescriber, as Arizona "
    "requires. Talk to your own physician before booking, particularly if you are "
    "pregnant or manage a kidney, heart or blood pressure condition."
)
CONTENT_FIXES = [(_OLD_NOTICE, _NEW_NOTICE)]


# ---- 6. real photography from the client's own media library ---------------
# Every URL below was opened and looked at; the alt text says what the photo
# ACTUALLY shows, not what the design slot wished for. A slot with no honest
# match is left empty on purpose and renders as a labelled placeholder. There
# is no Phoenix outdoor, landmark, monsoon or hotel photography on the site,
# so those slots stay empty rather than captioning an office photo as a hiker.
U = "https://thedripivinfusion.com/wp-content/uploads"
PHOTOS = {
    "cannulation": (f"{U}/2026/05/DSC01345-6-scaled.jpg",
                    "Registered nurse from The Drip IV Infusion placing an IV line in a client's arm"),
    "workplace":   (f"{U}/2026/05/DSC01289-2-scaled.jpg",
                    "Nurse hanging an IV bag while a client keeps working through the infusion"),
    "vein-check":  (f"{U}/2026/05/DSC01489-1-scaled.jpg",
                    "Nurse assessing a vein before placing the line in the treatment room"),
    "vial-check":  (f"{U}/2026/05/DSC01438-3-scaled.jpg",
                    "Nurse checking a sealed medication vial before preparing an infusion"),
    "at-home":     (f"{U}/2024/11/screen_JGP-TheDrip-Dec22_Corbin_009-1024x683.jpg",
                    "Client receiving an IV infusion in an armchair at home"),
    "team":        (f"{U}/2026/04/IMG_0646-1-1-scaled.jpeg",
                    "The Drip IV Infusion nursing team in branded scrubs at the office"),
    "founders":    (f"{U}/2024/11/thedripivinfusion-brandonandcorbin-retina.webp",
                    "Brandon Lang and Corbin King, the registered nurses who founded The Drip IV Infusion"),
    "bag-myers":   (f"{U}/2024/11/thedripivinfusion-ivbag-myers-retina.webp",
                    "The Classic Myers IV bag"),
    "bag-revive":  (f"{U}/2024/11/thedripivinfusion-ivbag-revive@2X.webp",
                    "The RE:VIVE IV bag"),
    "bag-defender": (f"{U}/2024/11/thedripivinfusion-ivbag-defender-@2X.webp",
                     "The Defender IV bag"),
}
# slot id -> photo key. Slots absent from this map stay empty by design.
SLOT_IMAGES = {
    "hero-nurse": "cannulation",
    "trust-a": "workplace",
    "trust-b": "vein-check",
    "drip-myers": "bag-myers",
    "drip-hangover": "bag-revive",
    "gal-1": "cannulation",
    "gal-2": "at-home",
    "gal-3": "vein-check",
    "gal-4": "workplace",
    "gal-5": "team",
    "team-brandon": "founders",
    "safety-kit": "vial-check",
    "process-visual": "vein-check",
    "reserve-img": "at-home",
    "final-img": "team",
    # The cocktail carousel was removed in the 25 Sep design, so bag-0/1/5 are
    # gone. The Defender render now has no home; the remaining drip-* cards have
    # no matching product shot in the media library and stay empty.
}


def image_map_js() -> str:
    pairs = []
    for slot, key in SLOT_IMAGES.items():
        src, alt = PHOTOS[key]
        pairs.append('  %s: { src: %s, alt: %s%s }' % (
            json.dumps(slot), json.dumps(src), json.dumps(alt),
            ', eager: true' if slot == 'hero-nurse' else ''))
    return "window.DRIP_IMAGES = {\n" + ",\n".join(pairs) + "\n};"


def strip_editor_runtime(html: str) -> str:
    html = re.sub(r'<script data-omelette-injected>.*?</script>', '', html, flags=re.S)
    html = re.sub(r'<style data-omelette-injected>.*?</style>', '', html, flags=re.S)
    html = re.sub(r'<script[^>]*src="\./support\.js"[^>]*>\s*</script>', '', html)
    html = re.sub(r'<script[^>]*src="\./image-slot\.js"[^>]*>\s*</script>', '', html)
    return html


def convert_image_slots(html: str) -> str:
    """<image-slot id=".." shape=".." placeholder=".."> -> <figure><img>."""
    def repl(m):
        attrs = m.group(1)
        def a(name):
            g = re.search(name + r'="([^"]*)"', attrs)
            return g.group(1) if g else ""
        slot, alt = a("id"), a("placeholder")
        radius = "50%" if a("shape") == "circle" else "10px"
        # The element carries its OWN sizing, e.g. the 42px review avatars and
        # the Google mark: style="width:42px;height:42px;flex:0 0 auto". Dropping
        # it and forcing 100% blew those up to fill their container, which is
        # what pushed the star row out of the ratings pill. Our defaults go
        # first so the element's own declarations win the cascade.
        own = a("style").strip().rstrip(";")
        base = (f"margin:0;width:100%;height:100%;border-radius:{radius};overflow:hidden;"
                f"background:#F6F6F6;display:flex;align-items:center;justify-content:center")
        style = f"{base};{own}" if own else base
        return (
            f'<figure class="img-slot" data-slot="{slot}" style="{style}">'
            f'<img alt="{alt}" loading="lazy" decoding="async" '
            f'style="width:100%;height:100%;object-fit:cover;display:block" '
            f'onerror="this.style.display=\'none\';this.parentNode.classList.add(\'is-empty\')">'
            f'<figcaption class="img-slot-note">{alt}</figcaption></figure>'
        )
    html = re.sub(r'<image-slot([^>]*)>\s*</image-slot>', repl, html)
    return re.sub(r'<image-slot([^>]*)/?>', repl, html)


RUNTIME = r"""/* Minimal renderer for the four directives the page uses.
   Replaces Claude Design's support.js. No external dependencies. */
(function () {
  var MUST = /\{\{\s*([^}]+?)\s*\}\}/g;

  function get(scope, path) {
    var parts = String(path).split('.'), v = scope;
    for (var i = 0; i < parts.length; i++) {
      if (v == null) return undefined;
      v = v[parts[i]];
    }
    return v;
  }
  function interp(str, scope) {
    return str.replace(MUST, function (_, expr) {
      var v = get(scope, expr);
      return v == null ? '' : String(v);
    });
  }
  function soleBinding(str) {
    var m = /^\s*\{\{\s*([^}]+?)\s*\}\}\s*$/.exec(str);
    return m ? m[1] : null;
  }

  var SVG_NS = 'http://www.w3.org/2000/svg';
  var XLINK_NS = 'http://www.w3.org/1999/xlink';

  function render(node, scope, out, inSvg) {
    for (var i = 0; i < node.childNodes.length; i++) {
      var n = node.childNodes[i];

      if (n.nodeType === 3) {
        if (n.nodeValue.indexOf('{{') > -1) {
          out.appendChild(document.createTextNode(interp(n.nodeValue, scope)));
        } else {
          out.appendChild(n.cloneNode(false));
        }
        continue;
      }
      if (n.nodeType !== 1) continue;

      var tag = n.tagName.toLowerCase();

      if (tag === 'sc-for') {
        var list = get(scope, soleBinding(n.getAttribute('list') || '') || '');
        var as = n.getAttribute('as') || 'item';
        if (Array.isArray(list)) {
          for (var j = 0; j < list.length; j++) {
            var child = Object.create(scope);
            child[as] = list[j];
            child[as + 'Index'] = j;
            render(n, child, out, inSvg);
          }
        }
        continue;
      }

      if (tag === 'sc-if') {
        var cond = get(scope, soleBinding(n.getAttribute('value') || '') || '');
        if (cond) {
          render(n, scope, out, inSvg);
        } else {
          // Inactive tab panels stay in the DOM, hidden. Dropping them would put
          // the FAQ answers, the drip cards, the cost tables and the Arizona
          // scope detail behind a click and out of the served markup entirely.
          var keep = document.createElement('div');
          keep.hidden = true;
          keep.setAttribute('data-inactive-panel', '');
          render(n, scope, keep, inSvg);
          out.appendChild(keep);
        }
        continue;
      }

      // document.createElement puts <svg>/<path> in the HTML namespace, where
      // they have no intrinsic size and render at 0x0. Every icon, star and the
      // Google mark vanished because of this. Inside an <svg> subtree the
      // elements and their xlink attributes need the SVG namespace.
      var svgHere = inSvg || tag === 'svg';
      var el = svgHere ? document.createElementNS(SVG_NS, tag)
                       : document.createElement(tag);
      for (var k = 0; k < n.attributes.length; k++) {
        var at = n.attributes[k], name = at.name, val = at.value;
        if (/^hint-/.test(name)) continue;
        if (name === 'onclick' || name === 'onClick') {
          var fn = get(scope, soleBinding(val) || '');
          if (typeof fn === 'function') el.addEventListener('click', fn);
          continue;
        }
        var resolved = val.indexOf('{{') > -1 ? interp(val, scope) : val;
        if (svgHere && name.indexOf('xlink:') === 0) {
          el.setAttributeNS(XLINK_NS, name, resolved);
        } else {
          el.setAttribute(name, resolved);
        }
      }
      render(n, scope, el, svgHere);
      out.appendChild(el);
    }
  }

  window.DCLogic = function DCLogic() {};
  window.DCLogic.prototype.setState = function (patch) {
    var next = typeof patch === 'function' ? patch(this.state) : patch;
    for (var key in next) this.state[key] = next[key];
    this.paint();
  };
  function fillImages(root) {
    var map = window.DRIP_IMAGES || {};
    var slots = root.querySelectorAll('figure.img-slot[data-slot]');
    for (var i = 0; i < slots.length; i++) {
      var fig = slots[i], hit = map[fig.getAttribute('data-slot')];
      var img = fig.querySelector('img');
      if (!img) continue;
      if (hit) {
        if (hit.eager) { img.loading = 'eager'; img.setAttribute('fetchpriority', 'high'); }
        img.style.display = 'block';
        img.src = hit.src;
        if (hit.alt) img.alt = hit.alt;
        fig.classList.remove('is-empty');
      } else {
        img.removeAttribute('src');
        img.style.display = 'none';
        fig.classList.add('is-empty');
      }
    }
  }
  window.__dripFillImages = fillImages;

  window.DCLogic.prototype.paint = function () {
    var vals = this.renderVals();
    var frag = document.createDocumentFragment();
    render(this._tpl, vals, frag);
    this._root.textContent = '';
    this._root.appendChild(frag);
    fillImages(this._root);
  };
  window.DCLogic.prototype.mount = function (root, tplEl) {
    this._root = root;
    this._tpl = document.createElement('div');
    // Hydrate from the design template. #page already holds the design's own
    // rendered output, which is what a crawler and the first paint get.
    this._tpl.innerHTML = tplEl ? tplEl.innerHTML : root.innerHTML;
    this.paint();
  };
})();
"""

BOOT = """<script>
document.addEventListener('DOMContentLoaded', function () {
  new Component().mount(document.getElementById('page'),
                        document.getElementById('dc-tpl'));
});
</script>"""


def extract_faqs(component: str) -> list:
    """Read the component's own FAQ pairs so the schema cannot drift from the page."""
    block = re.search(r"const F = \[(.*?)\n    \];", component, re.S)
    if not block:
        return []
    pairs = re.findall(r"\[\s*'((?:[^'\\]|\\.)*)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*\]",
                       block.group(1), re.S)
    out = []
    for q, a in pairs:
        q = q.replace("\\'", "'").strip()
        a = a.replace("\\'", "'").strip()
        if q.endswith("?"):
            out.append((q, a))
    return out


def crawlable_panels(component: str) -> str:
    """Static, hidden markup for tab panels that swap a DATA ARRAY.

    `sc-if` panels are handled in the runtime (rendered hidden). But the Reasons
    and Why tabs swap `reasonSets[i]` / `whySets[i]` wholesale, so only the
    default slice ever reaches the DOM. That silently hides two thirds of the
    local Phoenix section, which is the part that earns this URL. Sets after the
    default are emitted here as static hidden markup: no JS, always in the
    served HTML, and no duplication of the slice that is already visible.
    """
    out = []

    m = re.search(r"const reasonSets = \[(.*?)\n    \];", component, re.S)
    if m:
        items = re.findall(r"\[\s*'((?:[^'\\]|\\.)*)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*\]",
                           m.group(1), re.S)
        blocks = re.split(r"\{\s*slot:", m.group(1))[1:]
        seen = 0
        for bi, blk in enumerate(blocks):
            pairs = re.findall(r"\[\s*'((?:[^'\\]|\\.)*)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*\]",
                               blk, re.S)
            if bi == 0:                      # default tab, already rendered
                seen += len(pairs)
                continue
            for t, d in pairs:
                out.append("<h3>%s</h3><p>%s</p>" % (t.replace("\\'", "'"),
                                                     d.replace("\\'", "'")))

    m = re.search(r"const whySets = \[(.*?)\n    \];", component, re.S)
    if m:
        groups = re.findall(r"\[((?:\s*'(?:[^'\\]|\\.)*'\s*,?)+)\]", m.group(1), re.S)
        for gi, g in enumerate(groups):
            if gi == 0:
                continue
            vals = re.findall(r"'((?:[^'\\]|\\.)*)'", g)
            out.append("<ul>" + "".join("<li>%s</li>" % v.replace("\\'", "'")
                                        for v in vals) + "</ul>")

    if not out:
        return ""
    return ('\n<div hidden data-crawlable-panels aria-hidden="true">\n'
            + "\n".join(out) + "\n</div>\n")


def head_block(faqs=()) -> str:
    page_ld = json.dumps({
        "@context": "https://schema.org", "@type": "MedicalWebPage",
        "name": TITLE, "url": CANONICAL, "description": DESC,
        "lastReviewed": REVIEW_DATE_ISO,
        "reviewedBy": {"@type": "Person", "name": REVIEWER_NAME,
                       "jobTitle": "Co-founder and Chief Executive Officer",
                       "worksFor": {"@type": "Organization",
                                    "name": "The Drip IV Infusion"}},
        "about": {"@type": "MedicalTherapy", "name": "Intravenous therapy"},
        "audience": {"@type": "Patient"},
    }, ensure_ascii=False)
    faq_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}}
                       for q, a in faqs],
    }, ensure_ascii=False)
    biz_ld = (
        '{"@context":"https://schema.org","@type":"MedicalBusiness",'
        '"name":"The Drip IV Infusion",'
        f'"url":"{CANONICAL}",'
        '"telephone":"+1-602-341-3511","email":"hello@thedripivinfusion.com",'
        '"priceRange":"$195-$495",'
        '"address":{"@type":"PostalAddress","streetAddress":"4531 N 16th St Ste 102",'
        '"addressLocality":"Phoenix","addressRegion":"AZ","postalCode":"85016","addressCountry":"US"},'
        '"areaServed":[{"@type":"City","name":"Phoenix"},{"@type":"City","name":"Scottsdale"},'
        '{"@type":"City","name":"Tempe"},{"@type":"City","name":"Mesa"},{"@type":"City","name":"Chandler"},'
        '{"@type":"City","name":"Gilbert"},{"@type":"City","name":"Queen Creek"},'
        '{"@type":"City","name":"San Tan Valley"}],'
        '"openingHoursSpecification":[{"@type":"OpeningHoursSpecification",'
        '"dayOfWeek":["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],'
        '"opens":"07:00","closes":"21:00"}]}'
    )
    return f'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<link rel="canonical" href="{CANONICAL}">
<meta property="og:type" content="website">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="{CANONICAL}">
<script type="application/ld+json">{biz_ld}</script>
<script type="application/ld+json">{page_ld}</script>
<script type="application/ld+json" id="faq-ld">{faq_ld}</script>'''


def clean_text(html, label):
    """Apply the house punctuation rule, refusing to build on anything unhandled."""
    for a, b in CONTENT_FIXES:
        html = html.replace(a, b)
    for a, b in DASH_FIXES:
        html = html.replace(a, b)
    html = html.replace("\u2013", "-")          # en dash -> hyphen
    left = html.count("\u2014")
    if left:
        print("REFUSING TO BUILD: %d em dash(es) left in %s, each needs its own rewrite:"
              % (left, label))
        for m in re.finditer("\u2014", html):
            print("   ...", html[max(0, m.start() - 60):m.start() + 60].replace("\n", " "))
        raise SystemExit(1)
    return html


def main() -> int:
    html = strip_editor_runtime(io.open(SRC, encoding="utf-8").read())
    html = clean_text(html, "the design template")
    html = convert_image_slots(html)
    html = re.sub(r"</?x-dc[^>]*>", "", html)   # same unwrap as the snapshot

    # The design's OWN rendering, captured from the standalone bundle after its
    # runtime finished. This ships as the static markup: faithful to the design,
    # and unlike the bundle it is real HTML rather than an "Unpacking..." shell
    # that rebuilds itself from blob URLs at runtime.
    snap = io.open(RENDERED, encoding="utf-8").read()
    snap_css = [c for c in re.findall(r"<style[^>]*>(.*?)</style>", snap, flags=re.S)
                if "@font-face" not in c]          # drop 904KB of base64 fonts
    # Strip CSS comments: they carry Anthropic's internal build notes (and an
    # em dash), which have no business on a client page.
    snap_css = [re.sub(r"/\*.*?\*/", "", c, flags=re.S) for c in snap_css]
    snap_css = [c.replace("x-dc{display:none!important}", "") for c in snap_css]
    snap_body = re.search(r"<body[^>]*>(.*?)</body>", snap, flags=re.S).group(1)
    snap_body = re.sub(r"<script.*?</script>", "", snap_body, flags=re.S)
    snap_body = re.sub(r"<style.*?</style>", "", snap_body, flags=re.S)
    snap_body = clean_text(snap_body, "the rendered snapshot")
    snap_body = convert_image_slots(snap_body)
    # The snapshot's content sits inside an <x-dc> wrapper that the design CSS
    # hides with `x-dc{display:none!important}` until its own runtime upgrades
    # the element. Unwrap it and drop the rule, rather than depend on a custom
    # element we are deliberately not shipping.
    snap_body = re.sub(r"</?x-dc[^>]*>", "", snap_body)

    page_css = "\n".join(snap_css)
    page_css += """
.img-slot-note{display:none}
.img-slot.is-empty{outline:1px dashed #B5DEF5}
.img-slot.is-empty .img-slot-note{display:block;padding:14px 18px;font:400 14px 'Source Sans 3',sans-serif;color:#5A79AD;text-align:center}
"""

    body = re.search(r'<body[^>]*>(.*?)</body>', html, flags=re.S).group(1)
    body = re.sub(r'<style>.*?</style>', '', body, flags=re.S)
    logic = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', body, flags=re.S)
    component = logic.group(1).strip() if logic else ""
    faqs = extract_faqs(component)
    body = re.sub(r'<script type="text/x-dc".*?</script>', '', body, flags=re.S)
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
             'family=Questrial&family=Source+Sans+3:wght@300;400;600;700&display=swap">')

    out = f"""<!doctype html>
<html lang="en">
<head>
{head_block(faqs)}
{fonts}
<style>
{page_css.strip()}
</style>
</head>
<body>
<div id="page">
{snap_body.strip()}
</div>
<template id="dc-tpl">
{body.strip()}
</template>
{crawlable_panels(component)}
<script>
{image_map_js()}
</script>
<script>
{RUNTIME}
</script>
<script>
{component}
</script>
{BOOT}
</body>
</html>
"""
    os.makedirs(OUT_DIR, exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)

    print("built", OUT, os.path.getsize(OUT), "bytes")
    print("runtime inlined:", len(RUNTIME), "chars (page is self-contained)")
    checks = [
        ("editor runtime", len(re.findall(r'src="\./(support|image-slot)\.js"', out))),
        ("slot element", out.count("<image-slot")),
        ("canvas bootstrap", out.count("data-omelette-injected")),
        ("em dash", out.count("—")),
        ("en dash", out.count("–")),
        # markup only: the runtime's own source legitimately contains "{{"
        ("unresolved binding",
         len(re.findall(r'\{\{(?![^}]*\}\})',
                        re.search(r'<div id="page">(.*?)\n</div>', out, re.S).group(1)))),
        ("local file ref", len(re.findall(r'(?:src|href)="\.?/(?!/)', out))),
    ]
    bad = [f"{n} ({c})" for n, c in checks if c]
    for name, count in checks:
        print(f"  {name:<20} {count}")
    if bad:
        print("FAILED:", ", ".join(bad))
        return 1
    print("OK: self-contained, no external file dependencies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
