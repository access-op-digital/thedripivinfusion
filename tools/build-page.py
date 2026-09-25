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
import io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "design", "IV Therapy Phoenix.dc.html")
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
        radius = "10px" if a("shape") != "circle" else "50%"
        return (
            f'<figure class="img-slot" data-slot="{slot}" '
            f'style="margin:0;width:100%;height:100%;border-radius:{radius};overflow:hidden;'
            f'background:#F6F6F6;display:flex;align-items:center;justify-content:center">'
            f'<img src="" alt="{alt}" loading="lazy" decoding="async" '
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

  function render(node, scope, out) {
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
            render(n, child, out);
          }
        }
        continue;
      }

      if (tag === 'sc-if') {
        var cond = get(scope, soleBinding(n.getAttribute('value') || '') || '');
        if (cond) render(n, scope, out);
        continue;
      }

      var el = document.createElement(tag);
      for (var k = 0; k < n.attributes.length; k++) {
        var at = n.attributes[k], name = at.name, val = at.value;
        if (/^hint-/.test(name)) continue;
        if (name === 'onclick' || name === 'onClick') {
          var fn = get(scope, soleBinding(val) || '');
          if (typeof fn === 'function') el.addEventListener('click', fn);
          continue;
        }
        el.setAttribute(name, val.indexOf('{{') > -1 ? interp(val, scope) : val);
      }
      render(n, scope, el);
      out.appendChild(el);
    }
  }

  window.DCLogic = function DCLogic() {};
  window.DCLogic.prototype.setState = function (patch) {
    var next = typeof patch === 'function' ? patch(this.state) : patch;
    for (var key in next) this.state[key] = next[key];
    this.paint();
  };
  window.DCLogic.prototype.paint = function () {
    var vals = this.renderVals();
    var frag = document.createDocumentFragment();
    render(this._tpl, vals, frag);
    this._root.textContent = '';
    this._root.appendChild(frag);
  };
  window.DCLogic.prototype.mount = function (root) {
    this._root = root;
    this._tpl = document.createElement('div');
    this._tpl.innerHTML = root.innerHTML;
    this.paint();
  };
})();
"""

BOOT = """<script>
document.addEventListener('DOMContentLoaded', function () {
  new Component().mount(document.getElementById('page'));
});
</script>"""


def head_block() -> str:
    faq_ld = (
        '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}'
    )
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
<script type="application/ld+json" id="faq-ld">{faq_ld}</script>'''


def main() -> int:
    html = io.open(SRC, encoding="utf-8").read()

    html = strip_editor_runtime(html)

    for a, b in DASH_FIXES:
        html = html.replace(a, b)
    html = html.replace("–", "-")          # en dash -> hyphen

    left = html.count("—")
    if left:
        ctx = [html[max(0, m.start() - 60):m.start() + 60]
               for m in re.finditer("—", html)]
        print("REFUSING TO BUILD: %d em dash(es) left, each needs its own rewrite:" % left)
        for c in ctx:
            print("   ...", c.replace("\n", " "))
        return 1

    html = convert_image_slots(html)

    # page's own <style>
    styles = re.findall(r'<style>(.*?)</style>', html, flags=re.S)
    page_css = "\n".join(styles)
    page_css += """
.img-slot-note{display:none}
.img-slot.is-empty{outline:1px dashed #B5DEF5}
.img-slot.is-empty .img-slot-note{display:block;padding:14px 18px;font:400 14px 'Source Sans 3',sans-serif;color:#5A79AD;text-align:center}
"""

    body = re.search(r'<body[^>]*>(.*?)</body>', html, flags=re.S).group(1)
    body = re.sub(r'<style>.*?</style>', '', body, flags=re.S)
    logic = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', body, flags=re.S)
    component = logic.group(1).strip() if logic else ""
    body = re.sub(r'<script type="text/x-dc".*?</script>', '', body, flags=re.S)
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
             'family=Questrial&family=Source+Sans+3:wght@300;400;600;700&display=swap">')

    out = f"""<!doctype html>
<html lang="en">
<head>
{head_block()}
{fonts}
<style>
{page_css.strip()}
</style>
</head>
<body>
<div id="page">
{body.strip()}
</div>
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
