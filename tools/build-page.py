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
# The FAQ tab shares a two-column layout, and its image slot, with About Us.
# The client wants no image on FAQs. Gating the slot on the About tab leaves the
# FAQ list alone in an auto-fit grid, so it takes the full width on its own.
_FAQ_IMG_OLD = ('<div style="position:relative;height:400px;border-radius:10px;'
                'overflow:hidden"><image-slot id="{{ resSlot }}" shape="rect" '
                'placeholder="{{ resAlt }}"></image-slot></div>')
_FAQ_IMG_NEW = ('<sc-if value="{{ res0 }}" hint-placeholder-val="{{ true }}">'
                + _FAQ_IMG_OLD + '</sc-if>')

# The design condensed the hero to two sentences and lost the menu size, the
# price range and the coverage. The client wants the fuller opening back: it is
# the only place above the fold that answers what it costs and where they go.
_HERO_OLD = (
    "IV therapy in Phoenix is a licensed registered nurse bringing a sterile infusion to "
    "your home, office or hotel room, and The Drip IV Infusion reaches most Phoenix "
    "addresses within 60 minutes of a confirmed booking. Arizona law requires a valid "
    "prescriber's order before any elective infusion, and it's arranged as part of your "
    "intake."
)
_HERO_NEW = (
    "IV therapy in Phoenix is a licensed registered nurse bringing a sterile infusion to "
    "your home, office or hotel room, and The Drip IV Infusion reaches most Phoenix "
    "addresses within 60 minutes of a confirmed booking. Eight drips make up the menu, "
    "priced from $195 to $495, and a nurse places every line. Mobile visits run 7:00AM "
    "to 9:00PM, seven days a week, across Central Phoenix, Arcadia, Biltmore, Desert "
    "Ridge and Ahwatukee. Arizona law requires a valid order from a prescriber before "
    "any elective infusion, and that order is arranged as part of your intake."
)

# The client's reference page writes Why Choose as a two-sentence prose block,
# not a list: "Choose [brand] for [place] [service] to benefit from A, B, C and
# a D approach designed to E. Our team emphasises F, G, H and I, ensuring
# [audience] receive [benefit] whenever [condition]." Same shape here, with the
# noun phrases swapped for facts this business can stand behind. The tab groups
# below it keep all thirty USPs.
# CPI's heading is "Why Choose [brand] For [place] [service]?". Match it. The
# brand sits in a coloured span, so the trailing question mark moves out of it.
_WHY_HEAD_OLD = "Why Do Phoenix Residents Choose "
_WHY_HEAD_NEW = "Why Choose "
_WHY_TAIL_OLD = "The Drip IV Infusion?</span>"
_WHY_TAIL_NEW = "The Drip IV Infusion</span> for Phoenix IV Therapy?"
_WHY_INTRO_OLD = ("Thirty points separate this practice from the Phoenix field, covering "
                  "response, clinical staffing, oversight, coverage, pricing and the "
                  "visit itself.")
_WHY_INTRO_NEW = (
    "Choose The Drip IV Infusion for Phoenix IV therapy to benefit from registered "
    "nurse administration, 60-minute metro coverage, published menu pricing, and a "
    "seven-day mobile service approach designed to deliver a supervised infusion "
    "wherever you already are. Our team emphasises prescriber-ordered treatment, "
    "single-use sterile technique, full-session nurse presence, and post-care "
    "verification, ensuring homes, offices and hotel rooms across the Valley receive "
    "clinically supervised hydration whenever it is needed."
)

# Same story as the hero: the design cut three approved paragraphs down to two
# shorter ones and lost the city list, the licence and insurance wording, and
# the whole response-time paragraph. Restored verbatim from the approved copy.
_TRUST_P1_OLD = ("The Drip IV Infusion has treated Maricopa County patients since Fall 2022. "
                 "The mobile service covers Phoenix and seven neighbouring cities, with an "
                 "office at 4531 N 16th St, Suite 102 (85016) and three more in Gilbert.")
_TRUST_P1_NEW = ("The Drip IV Infusion has treated Maricopa County patients since Fall 2022, "
                 "when two registered nurses founded the practice. The mobile service covers "
                 "Phoenix and seven neighbouring cities: Gilbert, Queen Creek, Mesa, "
                 "Chandler, San Tan Valley, Scottsdale and Tempe. A Phoenix office at 4531 N "
                 "16th St, Suite 102, in the 85016 ZIP, handles in-office appointments, and "
                 "three further offices operate in Gilbert.")

_TRUST_P2_OLD = ("A licensed registered nurse administers every infusion under MD-supervised "
                 "protocols. Nurses carry hospital-grade supplies, so the drip that runs in a "
                 "Biltmore living room matches the drip that runs in the Gilbert office.")
_TRUST_P2_NEW = ("A licensed registered nurse administers every infusion. The company states "
                 "that 100% of the clinicians who place lines are licensed RNs, that the "
                 "business is fully licensed and insured, and that treatments follow "
                 "MD-supervised protocols. Nurses carry hospital-grade supplies to the "
                 "address you give, so the drip that runs in a Biltmore living room matches "
                 "the drip that runs in the Gilbert office.</p>"
                 '<p style="font-size:18px;line-height:1.6;color:#2b3140;text-wrap:pretty">'
                 "Response time is the metric the practice publishes: 60 minutes from "
                 "confirmed booking to a nurse at the door, within the Phoenix service area. "
                 "Mobile hours run 7:00AM to 9:00PM every day of the week, which covers "
                 "early-morning trailhead recovery and late-evening calls after a downtown "
                 "event.")

_CTA_FIXES = [('Book a Phoenix nurse visit', 'Book a Nurse Visit'), ('Book a Phoenix Nurse Visit', 'Book a Nurse Visit'), ('BOOK A PHOENIX NURSE VISIT', 'Book a Nurse Visit'), ('Book a Phoenix IV appointment', 'Book a Nurse Visit'), ('Book a Phoenix IV Appointment', 'Book a Nurse Visit'), ('Reserve a slot online', 'Book a Nurse Visit'), ('Reserve Online', 'Book a Nurse Visit'), ('reserve a slot online', 'Book a Nurse Visit')]

CONTENT_FIXES = _CTA_FIXES + [
    (_OLD_NOTICE, _NEW_NOTICE),
    (_FAQ_IMG_OLD, _FAQ_IMG_NEW),
    (_HERO_OLD, _HERO_NEW),
    (_TRUST_P1_OLD, _TRUST_P1_NEW),
    (_TRUST_P2_OLD, _TRUST_P2_NEW),
    (_WHY_INTRO_OLD, _WHY_INTRO_NEW),
    (_WHY_HEAD_OLD, _WHY_HEAD_NEW),
    (_WHY_TAIL_OLD, _WHY_TAIL_NEW),
]

# ---- 5e. trailing "read more" link lines ----------------------------------
# The client wants the see-also sentences gone: they send a reader away from a
# money page at the exact moment the section has finished making its case, and
# every one of them pointed at href="#" anyway. Whole paragraphs go where the
# paragraph exists only to link. Where a link sits inside a real sentence, the
# link goes and the sentence stays.
_A = r'<a href="#"[^>]*>(.*?)</a>'

_DROP_PARAGRAPHS = [
    ('<p style="font-size:15px;color:#3a4150">Read more on <a href="#" '
     'style="text-decoration:underline">sterile IV safety</a> and <a href="#" '
     'style="text-decoration:underline">whether IV drips are safe</a>.</p>'),
    ('<p style="font-size:16px;line-height:1.6;color:#3a4150">Further local reading: '
     '<a href="#" style="text-decoration:underline">how Arizona dry heat causes '
     'dehydration</a> and <a href="#" style="text-decoration:underline">reasons to get '
     'IV therapy in Phoenix</a>.</p>'),
    ('<p style="font-size:15px;color:#3a4150">Related: <a href="#" '
     'style="text-decoration:underline">prescription requirements</a>, <a href="#" '
     'style="text-decoration:underline">who can administer IV therapy</a>, <a href="#" '
     'style="text-decoration:underline">IV therapy regulations</a>.</p>'),
]

_TRIM_SENTENCES = [
    # cost: keep the first and last sentences, drop the see-also in the middle
    ('which is why the menu is priced directly. See <a href="#" '
     'style="text-decoration:underline">what an IV costs at urgent care</a> and '
     '<a href="#" style="text-decoration:underline">does insurance cover IV vitamin '
     'therapy</a>. The full menu includes',
     'which is why the menu is priced directly. The full menu includes'),
    # service area: the coverage sentence stands on its own
    ('Queen Creek and San Tan Valley — see <a href="#" '
     'style="text-decoration:underline">service areas</a>.',
     'Queen Creek and San Tan Valley.'),
    # about: keep the phone and email, drop the about-page pointer
    ('hello@thedripivinfusion.com</a>, and read the founders\' story on the '
     '<a href="#" style="color:#5A79AD">about page</a>.',
     'hello@thedripivinfusion.com</a>.'),
]


# ---- 5h. Common Reasons: merge the safety text up, drop the image ---------
# Same split as the Benefits section had. The safety paragraph sat below the
# tab panel, stranded after the box, and the image slot beside the list was
# empty because there is no Phoenix monsoon or trailhead photography. The
# safety text moves into the opening paragraph, where it is read rather than
# scrolled past, and the empty slot goes so the reasons take the full width.
_REASONS_INTRO_OLD = (
    "Phoenix recorded 100F earlier in 2026 than at any point in its history — an "
    "eight-day triple-digit run from 18 to 25 March, three consecutive days at 105F. "
    "March 2026 finished as the hottest March on record."
)
_REASONS_INTRO_NEW = (
    "Phoenix recorded 100F earlier in 2026 than at any point in its history, during an "
    "eight-day triple-digit run from 18 to 25 March with three consecutive days at "
    "105F, and March finished as the hottest on record. Maricopa County confirmed 81 "
    "heat-related deaths by late September, against 35 at the same point in 2025. An IV "
    "drip is a wellness service and is not treatment for heat exhaustion or heat "
    "stroke: confusion, a temperature above 103F, fainting, hot dry skin or a seizure "
    "are emergencies that need 911 or an emergency department."
)


# The header was a two-column grid: heading left, intro right. It is the only
# section on the page laid out that way, and with the safety text folded in the
# intro is now long enough that the two columns fall out of balance. Stack them
# so the section reads heading, then content, then the panel, full width.
_REASONS_GRID_TPL = ('<div style="display:grid;grid-template-columns:'
                     'repeat(auto-fit,minmax(min(100%,420px),1fr));gap:40px;'
                     'align-items:end">')
_REASONS_GRID_SNAP = ('<div data-dc-tpl="430" style="display: grid; '
                      'grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), '
                      '1fr)); gap: 40px; align-items: end;">')
_REASONS_STACK = ('<div style="display:flex;flex-direction:column;gap:16px;'
                  'max-width:900px">')


# The Why Choose header and its tab row were centred, the only section on the
# page that is. Left-align both so it sits flush with the heading above and the
# cost heading below it.
_WHY_ALIGN = [
    ("display:flex;flex-direction:column;gap:14px;align-items:center;"
     "text-align:center;max-width:760px;margin:0 auto",
     "display:flex;flex-direction:column;gap:14px;max-width:900px"),
    ("display: flex; flex-direction: column; gap: 14px; align-items: center; "
     "text-align: center; max-width: 760px; margin: 0px auto;",
     "display: flex; flex-direction: column; gap: 14px; max-width: 900px;"),
    ("border-bottom:1px solid #d9dfe8;flex-wrap:wrap;justify-content:center",
     "border-bottom:1px solid #d9dfe8;flex-wrap:wrap"),
    ("border-bottom: 1px solid rgb(217, 223, 232); flex-wrap: wrap; "
     "justify-content: center;",
     "border-bottom: 1px solid rgb(217, 223, 232); flex-wrap: wrap;"),
]


def why_choose_align(html: str) -> str:
    for a, b in _WHY_ALIGN:
        html = html.replace(a, b)
    return html


def founder_headshots(html: str) -> str:
    """Square off the two founder slots and give them room.

    Rewrites the whole tag instead of using a backreference. An earlier version
    used one, the escape was mangled on the way into this file, and the
    replacement silently deleted the elements it was meant to edit.
    """
    def rewrite(m):
        tag = m.group(0)
        tag = tag.replace('shape="circle"', 'shape="rect"')
        tag = tag.replace("width:84px;height:84px",
                          "width:116px;height:116px;border-radius:12px")
        tag = tag.replace("width: 84px; height: 84px",
                          "width: 116px; height: 116px; border-radius: 12px")
        return tag

    for slot in ("team-brandon", "team-corbin"):
        html = re.sub(r'<image-slot[^>]*id="' + slot + r'"[^>]*>', rewrite, html)
    return html


def fix_reasons(html: str) -> str:
    html = html.replace(_REASONS_GRID_TPL, _REASONS_STACK)
    html = html.replace(_REASONS_GRID_SNAP, _REASONS_STACK)
    html = html.replace(_REASONS_INTRO_OLD, _REASONS_INTRO_NEW)
    # the empty image beside the reason list
    html = re.sub(
        r'<div[^>]*>\s*<image-slot[^>]*id="(?:\{\{ reasonSlot \}\}|reason-[a-z]+)"'
        r'[^>]*>\s*</image-slot>\s*</div>', "", html, flags=re.S)
    # the safety paragraph that used to sit under the panel
    html = re.sub(r'<p[^>]*>\s*Safety matters more in Phoenix(?:(?!</p>).)*?</p>',
                  "", html, flags=re.S)
    return html


def strip_readmore(html: str) -> str:
    """Remove see-also lines from both sources.

    Matched on paragraph TEXT, not on the inline styles, because the template
    writes them as `color:#3a4150` and the rendered snapshot as `rgb(58,65,80)`.
    """
    # whole paragraphs that exist only to link out
    html = re.sub(
        r'<p[^>]*>\s*(?:Read more on|Further local reading:|Related:)\s'
        r'(?:(?!</p>).)*?</p>', "", html, flags=re.S)

    # a link inside a real sentence: drop the link, keep the sentence
    html = re.sub(
        r'\.\s*See\s*<a [^>]*href="#"(?:(?!</a>).)*?</a>\s*and\s*<a [^>]*href="#"'
        r'(?:(?!</a>).)*?</a>\.\s*The full menu',
        ". The full menu", html, flags=re.S)
    html = re.sub(
        r'Queen Creek and San Tan Valley[^<]*<a [^>]*href="#"(?:(?!</a>).)*?</a>\.',
        "Queen Creek and San Tan Valley.", html, flags=re.S)
    html = re.sub(
        r',?\s*and read the founders(?:&#39;|’|\')? story on the\s*'
        r'<a [^>]*href="#"(?:(?!</a>).)*?</a>\.',
        ".", html, flags=re.S)
    return html

# ---- 5c. the map, and the resources block --------------------------------
# The design leaves a dashed "Embedded Google map" box. The Phoenix office is a
# real address with a real listing, so the box becomes the actual embed. No API
# key: the classic maps query embed is enough for a location pin.
# The query embed was a fixed 420px iframe in a grid cell that stretches to the
# height of the copy column, so the bottom third of the card was white. It fills
# the cell now, and the src is the client's OWN embed for the Phoenix listing,
# lifted from their home page, rather than an address query.
_MAP_SRC = (
    "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3326.916662148377"
    "!2d-112.04698499999999!3d33.5035453!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1"
    "!3m3!1m2!1s0x613525030dbc573d%3A0x1875bd7bd973935e!2sThe%20Drip%20IV%20Infusion"
    "!5e0!3m2!1sen!2s!4v1775075168815!5m2!1sen!2s"
)
_MAP_EMBED = (
    '<div style="background:#fff;border-radius:10px;overflow:hidden;display:flex;'
    'min-height:520px;box-shadow:0 1px 3px rgba(21,48,96,0.08)">'
    '<iframe title="Map to The Drip IV Infusion, 4531 N 16th St Suite 102, Phoenix, AZ 85016" '
    'src="' + _MAP_SRC + '" '
    'style="border:0;display:block;width:100%;height:100%;min-height:520px;flex:1 1 auto" '
    'loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div>'
)
_MAP_RENDERED = ('<div data-dc-tpl="547" style="background: rgb(255, 255, 255); '
                 'border-radius: 10px; min-height: 420px; border: 1px dashed '
                 'rgb(185, 196, 214); display: flex; align-items: center; '
                 'justify-content: center; color: rgb(90, 121, 173); '
                 'font-size: 15px;">Embedded Google map</div>')
_MAP_TEMPLATE = ('<div style="background:#fff;border-radius:10px;min-height:420px;'
                 'border:1px dashed #b9c4d6;display:flex;align-items:center;'
                 'justify-content:center;color:#5A79AD;font-size:15px">'
                 'Embedded Google map</div>')

# The client asked for the resources block to carry information rather than a
# list of blog links. The cards keep the design's grid, stop being <a> elements,
# and gain a body paragraph.
_CARD_OLD = ('<a href="#" style="scroll-snap-align:start;display:flex;'
             'flex-direction:column;border-radius:12px;overflow:hidden;'
             'background:#F4F8FC;text-decoration:none;'
             'box-shadow:0 1px 3px rgba(21,48,96,0.06)">')
_CARD_NEW = ('<div style="scroll-snap-align:start;display:flex;'
             'flex-direction:column;border-radius:12px;overflow:hidden;'
             'background:#F4F8FC;box-shadow:0 1px 3px rgba(21,48,96,0.06)">')
_TITLE_OLD = ('<div style="font-family:Questrial,sans-serif;font-size:20px;'
              'line-height:1.3;color:#153060">{{ bl.title }}</div>')
_TITLE_NEW = (_TITLE_OLD + '<p style="font-size:15px;line-height:1.6;'
              'color:#3a4150;margin:0">{{ bl.body }}</p>')

INFO_CARDS = [
    ("HYDRATION", "How much water Phoenix actually needs",
     "In triple-digit heat the eight-glasses rule stops being useful. Losses rise with "
     "exertion and time outdoors, and thirst lags behind the deficit. Urine colour, "
     "headache and fatigue tell you more than a glass count."),
    ("WARNING SIGNS", "When fluids stop being enough",
     "Dizziness on standing, a dry mouth that water does not fix, dark urine and a "
     "headache that persists past two glasses are the point at which most people call. "
     "Confusion, a temperature above 103F or fainting mean 911, not a drip."),
    ("BEFORE YOUR VISIT", "The hour before the nurse arrives",
     "Eat something, drink a glass of water, and wear short sleeves or a loose top. Have "
     "your medication list, allergies and any prior infusion reactions ready for intake."),
    ("AFTER YOUR VISIT", "The rest of the day",
     "Keep the dressing on for a few hours and drink normally. Mild tenderness at the "
     "site is usual. Call us if you see swelling, increasing pain, or redness spreading "
     "from the site."),
    ("PHOENIX CALENDAR", "When the Valley runs driest",
     "March now opens the triple-digit season. Monsoon runs 15 June to 30 September and "
     "brings dust and pollen alongside the humidity. Winter travel out of Sky Harbor "
     "drives the immune bookings."),
    ("COST", "What you will pay",
     "Drips run $195 to $495, with add-on ingredients at a flat $30. Elective wellness "
     "infusions are generally not reimbursed by insurance, so expect to pay the menu "
     "price directly."),
]


def _info_js() -> str:
    rows = []
    for tag, title, body in INFO_CARDS:
        rows.append("['%s', '%s', '%s']"
                    % (tag, title.replace("'", "\\'"), body.replace("'", "\\'")))
    return ("  blogs: [" + ", ".join(rows) +
            "].map(([tag, title, body], i) => ({ tag, title, body, slot: 'blog-' + i })),")


def resources_to_info(html: str) -> str:
    """Swap the blog-link cards for informational ones."""
    html = re.sub(r"  blogs: \[.*?\}\)\),", _info_js(), html, count=1, flags=re.S)
    html = html.replace(_CARD_OLD, _CARD_NEW)
    html = html.replace("</a>\n            </sc-for>", "</div>\n            </sc-for>")
    html = html.replace(_TITLE_OLD, _TITLE_NEW)
    # These are information cards now, not article teasers. The image slot only
    # rendered an empty box echoing the title, so it goes.
    html = html.replace(
        '<div style="position:relative;height:200px">'
        '<image-slot id="{{ bl.slot }}" shape="rect" placeholder="{{ bl.title }}">'
        '</image-slot></div>', '')
    html = html.replace("Explore Our Phoenix Guides", "Phoenix Hydration Reference")
    html = html.replace("'Phoenix and Arizona Guides'", "'Phoenix Hydration Reference'")
    return html





# ---- 5d. the Benefits section ---------------------------------------------
# Written to the client's reference page: a question heading, a counted list
# intro, short declarative items, and a problem/consequence/solution close.
# The benefits themselves stay CATEGORY-LEVEL on purpose. Nothing here is a
# claim about this business, so nothing here needs a business fact to stand it
# up. The brand appears once, in the last line, where the section hands off to
# the booking CTA that follows it.
# Each item opens on a positive predicate (Optimized, Reduced, Controlled) so
# the benefit is the first word read, and each body is a single sentence.
_BENEFIT_ITEMS = [
    ("Optimized absorption",
     "Fluids and nutrients enter the bloodstream directly, so none of the dose is lost "
     "to digestion."),
    ("Accelerated rehydration",
     "A litre by line goes in at a known rate, instead of waiting on a stomach that "
     "empties slowly when you are already short of fluid."),
    ("Reliable delivery during nausea",
     "A line still works when vomiting or stomach upset has made oral fluids "
     "impractical."),
    ("Controlled dosing",
     "The bag, the additions and the volume are fixed by the prescriber's order, so "
     "repeat sessions deliver the same thing."),
    ("Supervised administration",
     "Vitals are taken before and after, and a clinician watches the site for the whole "
     "infusion."),
    ("Predictable session length",
     "Most sessions run 45 to 60 minutes from line placement to removal."),
    ("Reduced travel",
     "A mobile visit removes the drive, the waiting room and the exposure to other "
     "unwell patients."),
]

# The limits used to sit in a separate block below the list, which split the
# section in two. Folded into the opening paragraph instead, where it also
# previews the benefits the list then expands.
_BENEFIT_INTRO = (
    "IV therapy puts fluid and nutrients straight into the bloodstream, which produces "
    "optimized absorption, accelerated rehydration, controlled dosing and supervised "
    "delivery. It does not treat infection, replace a prescribed medication or "
    "substitute for emergency care, and anyone pregnant or managing a kidney, heart or "
    "blood pressure condition is screened by the prescriber first. Those benefits "
    "belong to the method rather than to any one provider: at The Drip IV Infusion a "
    "licensed registered nurse runs every Phoenix session under a valid prescriber's "
    "order, usually within 60 minutes of a confirmed booking. 7 benefits of IV therapy "
    "are listed below."
)


def _benefits_html() -> str:
    cards = []
    for i, (title, body) in enumerate(_BENEFIT_ITEMS, 1):
        cards.append(
            '<div style="background:#fff;border-radius:10px;padding:22px 24px;display:flex;'
            'gap:16px;align-items:flex-start">'
            '<div style="flex:none;width:34px;height:34px;border-radius:50%%;background:#B5DEF5;'
            'color:#153060;display:flex;align-items:center;justify-content:center;'
            'font-family:Questrial,sans-serif;font-size:15px">%02d</div>'
            '<div style="display:flex;flex-direction:column;gap:6px">'
            '<h3 style="margin:0;font-family:Questrial,sans-serif;font-weight:400;'
            'font-size:20px;color:#153060">%s</h3>'
            '<p style="margin:0;font-size:16px;line-height:1.6;color:#3a4150">%s</p>'
            '</div></div>' % (i, title, body)
        )
    head = (
        '<section id="benefits" data-screen-label="12b Benefits" '
        'style="padding:88px 24px;background:#F6F6F6">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:28px">'
        '<div style="display:flex;flex-direction:column;gap:12px;max-width:900px">'
        '<h2 style="margin:0;font-family:Questrial,sans-serif;font-weight:400;'
        'font-size:clamp(28px,3.2vw,40px);color:#153060">'
        'What Are the Benefits of IV Therapy?</h2>'
        '<p style="margin:0;font-size:18px;line-height:1.65;color:#2b3140">'
        + _BENEFIT_INTRO + '</p></div>'
    )
    grid = ('<div style="display:grid;grid-template-columns:'
            'repeat(auto-fit,minmax(min(100%,340px),1fr));gap:20px">'
            + "".join(cards) + '</div>')
    return head + grid + '</div></section>'


_CTA_ANCHOR_TPL = '<section data-screen-label="13 Reserve CTA"'
_CTA_ANCHOR_SNAP = '<section data-dc-tpl="453" data-screen-label="13 Reserve CTA"'


def insert_benefits(html: str) -> str:
    """Place the Benefits section immediately before the Reserve CTA."""
    block = _benefits_html()
    if "id=\"benefits\"" in html:
        return html
    for anchor in (_CTA_ANCHOR_SNAP, _CTA_ANCHOR_TPL):
        if anchor in html:
            return html.replace(anchor, block + anchor, 1)
    return html




# ---- 5f. the Safety section's board heading -------------------------------
# It was a <p> styled to look like a heading, so the section had no heading of
# its own and the three tab panels each opened at H2. Make it a real H2 that
# covers all three tabs, and demote the panels to H3 underneath it.
_BOARD_OLD_TPL = ('<p style="font-family:Questrial,sans-serif;'
                  'font-size:clamp(28px,3.2vw,38px);line-height:1.2">Every line at a '
                  'Phoenix address is placed by a licensed RN, <span '
                  'style="color:#5A79AD">under a valid prescriber\'s order.</span></p>')
_BOARD_NEW_TPL = ('<h2 style="font-family:Questrial,sans-serif;font-weight:400;'
                  'font-size:clamp(28px,3.2vw,38px);line-height:1.2;margin:0">IV Therapy '
                  'Safety <span style="color:#5A79AD">and Arizona Requirements</span></h2>')

_BOARD_OLD_SNAP = ('<p data-dc-tpl="327" style="font-family: Questrial, sans-serif; '
                   'font-size: clamp(28px, 3.2vw, 38px); line-height: 1.2;">Every line at '
                   'a Phoenix address is placed by a licensed RN, <span data-dc-tpl="328" '
                   'style="color: rgb(90, 121, 173);">under a valid prescriber\'s order.'
                   '</span></p>')
_BOARD_NEW_SNAP = ('<h2 data-dc-tpl="327" style="font-family: Questrial, sans-serif; '
                   'font-weight: 400; font-size: clamp(28px, 3.2vw, 38px); '
                   'line-height: 1.2; margin: 0;">IV Therapy Safety <span '
                   'data-dc-tpl="328" style="color: rgb(90, 121, 173);">and Arizona '
                   'Requirements</span></h2>')

_PANEL_DEMOTE = [
    "Our Clinical Credentials and Safety Standards",
    "Do You Need a Prescription for IV Therapy in Arizona?",
]


def board_heading(html: str) -> str:
    html = html.replace(_BOARD_OLD_TPL, _BOARD_NEW_TPL)
    html = html.replace(_BOARD_OLD_SNAP, _BOARD_NEW_SNAP)
    # the two tab panels now sit under the board heading, so H2 -> H3
    for title in _PANEL_DEMOTE:
        html = re.sub(r"<h2([^>]*)>(\s*" + re.escape(title) + r"\s*)</h2>",
                      r"<h3\1>\2</h3>", html)
    return html


# ---- 5g. one image per process step ---------------------------------------
# The stepper had a single static slot, so all eight steps showed the same
# photo. The slot id now follows the active step, and each step gets the shot
# that actually depicts it. Steps with no honest match stay empty rather than
# borrowing a picture of something else.
_STEP_IMG_OLD = ('<div style="position:relative;height:300px;border-radius:10px;'
                 'overflow:hidden"><image-slot id="process-visual" shape="rect" '
                 'placeholder="Nurse checking vitals before a Phoenix home infusion">'
                 '</image-slot></div>')
_STEP_IMG_NEW = ('<div style="position:relative;height:300px;border-radius:10px;'
                 'overflow:hidden"><image-slot id="{{ stepSlot }}" shape="rect" '
                 'placeholder="{{ stepAlt }}"></image-slot></div>')

_STEP_SLOTS = ("['step-book','step-intake','step-arrive','step-vitals',"
               "'step-select','step-infusion','step-postcare','step-followup'][s.step]")
_STEP_ALTS = ("['Booking a Phoenix mobile IV visit by phone',"
              "'Health intake before an infusion',"
              "'Nurse arriving at a Phoenix address with the IV kit',"
              "'Nurse checking vitals before a Phoenix infusion',"
              "'Nurse selecting the drip and add-ons',"
              "'Infusion running while the client works',"
              "'Post-care check before the nurse leaves',"
              "'Follow-up after a Phoenix infusion'][s.step]")


def step_images(html: str) -> str:
    html = html.replace(_STEP_IMG_OLD, _STEP_IMG_NEW)
    html = html.replace("...stepVals,",
                        "...stepVals, stepSlot: " + _STEP_SLOTS +
                        ", stepAlt: " + _STEP_ALTS + ",", 1)
    return html




# ---- 5i. the drip menu slider ---------------------------------------------
# The client's own /menu page, as a horizontal slider straight after the
# reviews. Name, price, what it is for, the full ingredient list and the
# client's own description, verbatim. All eight bag renders exist on the site;
# the media REST API only returned three of them, the same pagination gap that
# hid the founder headshots, so these came from the menu page markup.
_MENU_ITEMS = [
    ("The Classic Myers", "$195", "rehydration and replenishment", "myers",
     "Vitamin C, B12, B-Complex, Zinc, Glutathione, Magnesium, Fluids*",
     "Rapid recovery from dehydration is just around the corner with this staple IV "
     "cocktail. The Classic Myers swoops in to save the day when you're not feeling "
     "your best, or simply searching for that extra replenishment."),
    ("RE:VIVE", "$300", "stomach and headache relief", "revive",
     "Vitamin C, B12, B-Complex, Zinc, Glutathione, Magnesium, Pepcid, Zofran, "
     "Toradol, Fluids*",
     "RE:VIVE combines everything from The Classic Myers with additional stomach and "
     "headache relief for a truly transformative end-result."),
    ("The Kitchen Sink", "$495", "ultimate sickness recovery", "kitchen",
     "Vitamin C, B12, B-Complex, Zinc, Glutathione, Magnesium, Taurine, L-Carnitine, "
     "Pepcid, Zofran, Toradol, Benadryl, Fluids*",
     "For those that have gone the extra mile or are really not doing well and need "
     "the ultimate recovery, The Kitchen Sink will get you back up and running most "
     "quickly. This IV Cocktail has the highest dosage of the most impactful blend."),
    ("The Mama Bear", "$250", "morning sickness relief", "mama",
     "Vitamin C, B12, Glutathione, Magnesium, Zofran, Pepcid, Pyridoxine (B6), Fluids*",
     "For expecting mothers out there carrying the next generation, all the while "
     "dealing with fatigue and morning sickness, we are here to help. The Mama Bear "
     "provides rapid relief and relaxation."),
    ("The Total Prevention", "$325", "maximum immune support", "total",
     "Vitamin C, B12, B-Complex, Zinc, Glutathione, Magnesium, Fluids*",
     "Friends and family around you coming down with something? The Total Prevention "
     "provides a max dose of vitamins to keep you on your feet so you can keep at it. "
     "Recommended also by frequent flyers who need to stay healthy amidst a lifestyle "
     "of travel."),
    ("The Defender", "$375", "cold, flu and virus", "defender",
     "Vitamin C, Zinc, Glutathione, NAC and Fluids* in the infusion cocktail, plus a "
     "Vitamin D and NAD+ injection.",
     "Whether it's the first time or you've lost count, The Defender is here for you "
     "when you've been exposed to, or come down with, a cold, flu or any other "
     "seasonal virus. It aims to lessen symptoms and reduce your downtime."),
    ("The GOAT", "$375", "peak performance", "goat",
     "Vitamin C, B12, Zinc, Taurine, NAC, Pyridoxine (B6) and Fluids* in the infusion "
     "cocktail, plus an NAD+ injection.",
     "Sometimes you need all the help you can get to prepare for your next event. The "
     "GOAT is tailored for the athletes and performers out there doing big things with "
     "their bodies, before or after the big event."),
    ("The Skinny", "$350", "weight loss support", "skinny",
     "B12, B-Complex, Glutathione, L-Carnitine, Amino Blend, Fluids*",
     "As you continue to pursue a healthy and active lifestyle, The Skinny is an extra "
     "tool to help support your weight loss journey. It complements the weight-loss "
     "injections offered by The Drip, and is recommended weekly or bi-weekly."),
]

# Reference-page shape: what we provide, in which city, to address what; then
# who we are to the reader, what we do about it, and for whom.
_MENU_OVERVIEW = (
    "We provide eight IV drip formulations in Phoenix to address dehydration, hangover "
    "and stomach upset, seasonal illness, morning sickness, immune support, athletic "
    "recovery and weight-loss support. As a nurse-owned IV provider Phoenix residents "
    "trust, The Drip IV Infusion matches the bag to your intake, confirms it against "
    "the prescriber's order, and delivers it at your home, office or hotel for adults "
    "across the Valley, from expecting mothers and frequent flyers to athletes, shift "
    "workers and anyone recovering from a long week. Prices run $195 to $495, with "
    "add-on ingredients at a flat $30. Fluids* are included in every cocktail."
)


# Add-on ingredients, verbatim from the client's own /menu page. These are the
# client's published product claims, so they ship in their own wording under
# the claim-precedence rule. Several read as treatment claims rather than
# wellness ones, which is flagged in the run notes for their sign-off.
_ADDONS = [
    ("N-Acetyl Cysteine (NAC)",
     "Is used to treat many conditions, which may include flu, dry eye, cough and "
     "other lung conditions."),
    ("Vitamin C", "Boosts immune function and fights off illnesses."),
    ("Lipo-C / Lipo-plus",
     "Lipo-C injections have shown to target fatty deposits of the stomach, hips, "
     "inner thighs, buttocks and neck area. The mix of ingredients works to boost the "
     "body's metabolic function, therefore burning fat in concentrated areas."),
    ("Vitamin B12",
     "For morning sickness relief. Increases energy levels, boosts immune function, "
     "helps improve mood and depression, improves sleep patterns, and keeps the body's "
     "nerve and blood cells healthy."),
    ("B-Complex Vitamins",
     "Improves liver function and memory. Protects the body's immune system and aids "
     "in the breakdown of fats and carbohydrates into energy. It can have positive "
     "effects on hair, skin and nails."),
    ("Toradol",
     "Toradol is a nonsteroidal anti-inflammatory medication (NSAID). It works to "
     "reduce the hormones that cause inflammation and pain."),
    ("Glutathione",
     "Master antioxidant that aids in the detoxification process in the body and helps "
     "the body create energy."),
    ("Zofran",
     "A medication that is able to block the actions of chemicals in the body that can "
     "trigger nausea and vomiting."),
    ("Zinc",
     "Boosts immune function and fights off illnesses, aids in wound healing, provides "
     "added skin hydration, and increases the sense of taste and smell."),
    ("Pepcid",
     "A histamine-2 blocker medication that decreases the amount of stomach acids "
     "produced."),
    ("Magnesium",
     "Helps relax smooth muscles and can help with anxiety, stress, insomnia, "
     "inflammation and constipation."),
    ("Benadryl",
     "An antihistamine medication that reduces the effect of the natural chemical "
     "histamine in the body."),
    ("Taurine",
     "Promotes healthy metabolism, balances electrolytes, aids in lowering mild "
     "hypertension, reduces inflammation and anxiety."),
    ("Amino Blend",
     "Prevents breakdown of muscle. Aids in conversion of fatty acids into energy. "
     "Used for fat metabolism and energy, performance recovery time, and muscle "
     "building."),
    ("Pyridoxine (B6)",
     "Important for brain development, helps keep the nervous system and immune system "
     "healthy. A vital piece in assisting with morning sickness."),
    ("L-Carnitine", "Helps the body turn fat into energy."),
]

_MENU_URL = "https://thedripivinfusion.com/menu"

_DROP_SVG = (
    '<svg width="34" height="34" viewBox="0 0 24 24" fill="#13646D" aria-hidden="true">'
    '<path d="M12 2.5c3.6 4.4 6.5 8 6.5 11.3a6.5 6.5 0 0 1-13 0C5.5 10.5 8.4 6.9 12 2.5z"'
    '></path></svg>'
)


def _addons_html() -> str:
    cards = []
    for name, body in _ADDONS:
        cards.append(
            '<div style="scroll-snap-align:start;flex:0 0 250px;background:#fff;'
            'border:1px solid #e3e7ee;border-radius:12px;padding:22px;display:flex;'
            'flex-direction:column;gap:10px">'
            + _DROP_SVG +
            '<h4 style="margin:0;font-family:Questrial,sans-serif;font-weight:400;'
            'font-size:17px;color:#153060">' + name + '</h4>'
            '<div style="font-size:14px;font-weight:600;color:#5A79AD">'
            '$30 Add-On to IV Infusion</div>'
            '<p style="margin:0;font-size:14px;line-height:1.55;color:#3a4150">'
            + body + '</p></div>'
        )
    return (
        '<div style="display:flex;flex-direction:column;gap:22px;margin-top:8px">'
        '<div style="display:flex;flex-direction:column;gap:8px;max-width:900px">'
        '<h3 style="margin:0;font-family:Questrial,sans-serif;font-weight:400;'
        'font-size:clamp(24px,2.6vw,32px);color:#153060">Add-Ons and Ingredients</h3>'
        '<p style="margin:0;font-size:17px;line-height:1.6;color:#2b3140">'
        'Sixteen add-on ingredients attach to any cocktail on the menu at a flat $30 '
        'each, so a bag can be adjusted to what your intake and the prescriber\'s order '
        'call for on the day.</p></div>'
        '<div style="display:flex;gap:16px;overflow-x:auto;padding-bottom:14px;'
        'scroll-snap-type:x mandatory;scrollbar-width:thin;'
        'scrollbar-color:#5A79AD #F6F6F6">' + "".join(cards) + '</div></div>'
    )


def _menu_footer_html() -> str:
    return (
        '<div style="display:flex;flex-direction:column;gap:14px;align-items:flex-start;'
        'margin-top:8px">'
        '<a href="' + _MENU_URL + '" style="display:inline-block;background:#153060;'
        'color:#fff;text-decoration:none;padding:16px 34px;border-radius:10px;'
        'font:600 15px \'Source Sans 3\',sans-serif;letter-spacing:1px;'
        'text-transform:uppercase">View the Full Menu</a>'
        '</div>'
    )


def _menu_html() -> str:
    cards = []
    for name, price, purpose, key, ingr, desc in _MENU_ITEMS:
        cards.append(
            '<div style="scroll-snap-align:start;flex:0 0 300px;background:#fff;'
            'border:1px solid #e3e7ee;border-radius:12px;overflow:hidden;display:flex;'
            'flex-direction:column">'
            '<div style="height:190px;background:#F6F6F6;display:flex;align-items:center;'
            'justify-content:center;padding:14px">'
            '<image-slot id="menu-' + key + '" shape="rect" style="width:auto;height:100%;'
            'max-width:100%" placeholder="' + name + ' IV bag"></image-slot></div>'
            '<div style="padding:20px 22px 24px;display:flex;flex-direction:column;gap:8px">'
            '<h3 style="margin:0;font-family:Questrial,sans-serif;font-weight:400;'
            'font-size:21px;color:#153060">' + name + '</h3>'
            '<div style="font-family:Questrial,sans-serif;font-size:22px;color:#13646D">'
            + price + '</div>'
            '<div style="font-size:14px;font-weight:600;color:#5A79AD">For '
            + purpose + '</div>'
            '<p style="margin:0;font-size:13px;line-height:1.55;color:#5a6070">'
            + ingr + '</p>'
            '<p style="margin:0;font-size:15px;line-height:1.6;color:#3a4150">'
            + desc + '</p>'
            '</div></div>'
        )
    return (
        '<section id="drip-menu" data-screen-label="02b Drip Menu" '
        'style="padding:88px 24px">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;'
        'gap:28px">'
        '<div style="display:flex;flex-direction:column;gap:12px;max-width:900px">'
        '<h2 style="margin:0;font-family:Questrial,sans-serif;font-weight:400;'
        'font-size:clamp(28px,3.2vw,40px);color:#153060">'
        'Our IV Drip Menu in <span style="color:#5A79AD">Phoenix</span></h2>'
        '<p style="margin:0;font-size:18px;line-height:1.65;color:#2b3140">'
        + _MENU_OVERVIEW + '</p></div>'
        '<div style="display:flex;gap:20px;overflow-x:auto;padding-bottom:14px;'
        'scroll-snap-type:x mandatory;scrollbar-width:thin;'
        'scrollbar-color:#5A79AD #F6F6F6">' + "".join(cards) + '</div>'
        + _addons_html() + _menu_footer_html() + '</div></section>'
    )


# Sits after the Trusted block rather than before it, so the reader meets who
# runs the service before they meet the price list.
_MENU_ANCHOR_TPL = '<section id="menu" data-screen-label="04 Drip Menu"'
_MENU_ANCHOR_SNAP = '<section data-dc-tpl="145" id="menu" data-screen-label="04 Drip Menu"'


def rewrite_uses_intro(html: str) -> str:
    return html.replace(_USES_OLD, _USES_NEW)


def insert_menu(html: str) -> str:
    """Place the menu slider between the reviews and the Trusted section."""
    if 'id="drip-menu"' in html:
        return html
    block = _menu_html()
    for anchor in (_MENU_ANCHOR_SNAP, _MENU_ANCHOR_TPL):
        if anchor in html:
            return html.replace(anchor, block + anchor, 1)
    return html


# ---- 5j. the IV uses intro, in the reference format ------------------------
_USES_OLD = ("Eight named drips and a set of $30 add-on ingredients make up the Phoenix "
             "menu. Choose a goal to see the matching treatments.")
_USES_NEW = (
    "We provide IV therapy in Phoenix for the symptoms people most often call about, "
    "including dehydration, hangovers, migraine, fatigue, cold and flu, pregnancy "
    "nausea, arthritis pain, anxiety and weight-loss support. As a nurse-owned provider "
    "Phoenix residents trust, The Drip IV Infusion reviews your symptoms at intake, "
    "matches them to a formulation the prescriber has ordered, and sends a registered "
    "nurse to your address for adults across the Valley, whether you are recovering at "
    "home, working through it at the office or travelling through Sky Harbor. Our IV "
    "therapy uses in Phoenix cover the treatments below."
)


# ---- 5k. the gallery slider ------------------------------------------------
# Was a five-cell CSS grid with the slot ids baked into the markup, so adding a
# sixth photo meant editing the layout. It is a list now: append a line here and
# a card appears in the slider. Map the new slot in SLOT_IMAGES and it fills.
_GALLERY = [
    ("gal-1", "Nurse setting up a sterile field on a Central Phoenix kitchen counter"),
    ("gal-2", "Hydration line running in an Arcadia living-room chair"),
    ("gal-3", "In-office suite at 4531 N 16th St, Phoenix"),
    ("gal-4", "RE:VIVE drip in a hotel near Sky Harbor"),
    ("gal-5", "GOAT recovery drip after a Camelback hike"),
]


def _gallery_slider() -> str:
    cards = []
    for slot, alt in _GALLERY:
        cards.append(
            '<div style="scroll-snap-align:start;flex:0 0 330px;height:250px;'
            'position:relative;border-radius:10px;overflow:hidden">'
            '<image-slot id="' + slot + '" shape="rect" placeholder="' + alt + '">'
            '</image-slot></div>'
        )
    return ('<div style="display:flex;gap:16px;overflow-x:auto;padding-bottom:14px;'
            'scroll-snap-type:x mandatory;scrollbar-width:thin;'
            'scrollbar-color:#5A79AD #F6F6F6">' + "".join(cards) + '</div>')


_GAL_GRID_TPL_OPEN = ('<div style="display:grid;grid-template-columns:'
                      'repeat(auto-fit,minmax(min(100%,260px),1fr));'
                      'grid-auto-rows:230px;gap:16px">')


def gallery_slider(html: str) -> str:
    """Swap the gallery grid, in either source, for the slider."""
    pat = (r'<div[^>]*(?:grid-auto-rows:\s*230px|grid-auto-rows: 230px)[^>]*>'
           r'(?:(?!</section>).)*?</div>\s*(?=</div>)')
    return re.sub(pat, _gallery_slider(), html, count=1, flags=re.S)


# ---- 5l. the four corrections from the 25 Sep review -----------------------
# Each runs over BOTH sources, so the patterns are written against the text
# rather than the inline styles: the template writes `color:#3a4150` and the
# rendered snapshot the same rule as `rgb(58, 65, 80)`.

# (a) The closing band carried one button and a dashed "Scheduler embed" box.
#     There is no scheduler to embed, so the box goes and the band takes the
#     same two-button pair as every other CTA on the page. The primary points at
#     the client's real booking form, which lives at #book-now on their home
#     page; the on-page #book anchor IS this section.
_BOOK_PRIMARY = (
    '<a href="https://thedripivinfusion.com/#book-now" style="background:#fff;'
    'color:#13646D;padding:16px 28px;border-radius:10px;font-size:14px;'
    'font-weight:700;letter-spacing:1px;text-transform:uppercase;'
    'text-decoration:none">Book a Nurse Visit</a>'
)
_BOOK_SECONDARY = (
    '<a href="tel:6023413511" style="background:#153060;color:#fff;padding:16px 28px;'
    'border-radius:10px;font-size:14px;font-weight:700;letter-spacing:1px;'
    'text-transform:uppercase;text-decoration:none">Call (602) 341-3511</a>'
)
_BOOK_SECTION = (
    '<section id="book" data-screen-label="05 Book CTA" '
    'style="background:#13646D;color:#fff;padding:64px 24px">'
    '<div style="max-width:1200px;margin:0 auto;display:flex;flex-wrap:wrap;gap:32px;'
    'align-items:center;justify-content:space-between">'
    '<div style="display:flex;flex-direction:column;gap:14px;flex:1 1 520px;max-width:720px">'
    '<h2 style="font-family:Questrial,sans-serif;font-weight:400;'
    'font-size:clamp(30px,3.6vw,42px);line-height:1.15">'
    'Book Your Phoenix IV Drip Today</h2>'
    '<p style="font-size:18px;line-height:1.6;color:#e6f3f4">Call or text '
    '(602) 341-3511, or book online. A nurse reaches most Phoenix addresses within '
    '60 minutes, any day between 7:00AM and 9:00PM.</p></div>'
    '<div style="display:flex;gap:12px;flex-wrap:wrap;flex:0 0 auto">'
    + _BOOK_PRIMARY + _BOOK_SECONDARY + '</div></div></section>'
)


def book_cta(html: str) -> str:
    return re.sub(r'<section[^>]*id="book"[^>]*>.*?</section>',
                  _BOOK_SECTION.replace('\\', '\\\\'), html, count=1, flags=re.S)


# (b) The gallery heading carried a second paragraph restating what the
#     photographs show. The photographs show it.
def drop_gallery_intro(html: str) -> str:
    return re.sub(r'<p[^>]*>\s*The infusion as it actually runs in Phoenix'
                  r'(?:(?!</p>).)*?</p>', "", html, count=1, flags=re.S)


# (c) Jenna, Karena and Kris have no headshot anywhere on the client site, so
#     the three avatar slots rendered as initials in grey discs. Rather than
#     invent faces, the card names them. The credential is already carried by
#     the body copy directly below it.
_NURSE_CHIPS = (
    '<div style="display:flex;flex-wrap:wrap;gap:8px">'
    + "".join(
        '<span style="background:rgba(181,222,245,0.14);border:1px solid #5A79AD;'
        'border-radius:999px;padding:7px 15px;font-size:14px;font-weight:600;'
        'color:#B5DEF5">' + n + ', RN</span>'
        for n in ("Jenna", "Karena", "Kris")
    ) + '</div>'
)


def nurse_chips(html: str) -> str:
    return re.sub(
        r'<div[^>]*>\s*(?:<image-slot[^>]*id="team-(?:jenna|karena|kris)"[^>]*>\s*'
        r'</image-slot>\s*){3}</div>',
        _NURSE_CHIPS, html, count=1, flags=re.S)


# (d) The service area opened with a paragraph, a ZIP chip row, a neighbourhood
#     chip row and a second paragraph. The client wants no ZIP codes and one
#     paragraph, so the neighbourhoods move into the prose, where they read as
#     places rather than as tags.
_AREA_PARA = (
    '<p style="font-size:17px;line-height:1.6;color:#2b3140">Coverage runs across '
    'central and north-central Phoenix and out to the eastern suburbs, with a '
    '60-minute response target inside the city. Nurses cover Central Phoenix, '
    'Arcadia, Biltmore, Desert Ridge and Ahwatukee, and run regularly to hotels '
    'near Sky Harbor, homes below Camelback Mountain and Piestewa Peak, rentals '
    'around the Phoenix Convention Center and Footprint Center, and the South '
    'Mountain side of the city. The same dispatch covers Gilbert, Tempe, '
    'Scottsdale, Mesa, Chandler, Queen Creek and San Tan Valley.</p>'
)


def service_area(html: str) -> str:
    return re.sub(
        r'<p[^>]*>\s*Coverage runs across central.*?'
        r'Queen Creek and San Tan Valley[^<]*</p>',
        _AREA_PARA, html, count=1, flags=re.S)


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
    "bag-kitchen": (f"{U}/2024/11/thedripivinfusion-ivbag-kitchen-retina.webp",
                    "The Kitchen Sink IV bag"),
    "bag-mama":    (f"{U}/2024/11/thedripivinfusion-ivbag-mama-retina.webp",
                    "The Mama Bear IV bag"),
    "bag-total":   (f"{U}/2024/11/thedripivinfusion-ivbag-total-retina.webp",
                    "The Total Prevention IV bag"),
    "bag-goat":    (f"{U}/2024/11/thedripivinfusion-ivbag-goat-retina.webp",
                    "The GOAT IV bag"),
    "bag-skinny":  (f"{U}/2024/11/thedripivinfusion-ivbag-skinny-retina.webp",
                    "The Skinny IV bag"),
    "athlete-iv":  (f"{U}/2024/11/thedrip-strictvision-2-retina.webp",
                    "Drip IV Infusion nurse placing a recovery IV for an athlete at a Phoenix gym"),
    "athlete-gym": (f"{U}/2024/11/thedrip-strictvision-1-retina.webp",
                    "Drip IV Infusion nurse with an athlete at Strict Vision Athletics in Phoenix"),
    "injection":   (f"{U}/2024/11/thedripivinfusion-needle-retina.webp",
                    "Gloved nurse holding a prepared intramuscular injection"),
    # Individual headshots, from the about page. The first media-library sweep
    # missed them because the REST pagination returned an incomplete first page.
    "brandon":     (f"{U}/2024/11/thedripivinfusion-brandon-retina.webp",
                    "Brandon Lang, MSN, RN, Co-founder and Chief Executive Officer"),
    "corbin":      (f"{U}/2024/11/thedripivinfusion-corbin-retina.webp",
                    "Corbin King, MBA, RN, Co-founder and Chief Operating Officer"),
    # final-img was the same team portrait as the process and resources slots.
    # The client's April upload is the in-office suite itself, which is what the
    # design slot asked for, so the closing CTA gets its own picture.
    "headache":    (f"{U}/2024/11/IV-Therapy-for-Dehydration-1.jpg",
                    "Woman sitting on a sofa holding her head during a headache"),
    "in-office":   (f"{U}/2026/04/Drip-New-Image-1.jpeg",
                    "Client resting under a blanket in the infusion chair at The Drip "
                    "IV Infusion on N 16th St in Phoenix"),
}
# slot id -> photo key. Slots absent from this map stay empty by design.
SLOT_IMAGES = {
    "hero-nurse": "cannulation",
    "trust-a": "workplace",
    "trust-b": "vein-check",
    "drip-myers": "bag-myers",
    "drip-hangover": "bag-revive",
    "drip-immune": "bag-total",
    "drip-mama": "bag-mama",
    "drip-food": "bag-kitchen",
    "drip-skinny": "bag-skinny",
    "drip-hydration": "in-office",
    "drip-migraine": "headache",
    "drip-glutathione": "vial-check",
    "gal-1": "cannulation",
    "gal-2": "at-home",
    "gal-3": "vein-check",
    "gal-4": "workplace",
    "gal-5": "athlete-gym",
    "team-brandon": "brandon",
    "team-corbin": "corbin",
    "drip-athletic": "athlete-iv",
    "drip-energy": "injection",
    "drip-nad": "injection",
    "res-team": "team",
    # the eight menu bag renders
    "menu-myers": "bag-myers",
    "menu-revive": "bag-revive",
    "menu-kitchen": "bag-kitchen",
    "menu-mama": "bag-mama",
    "menu-total": "bag-total",
    "menu-defender": "bag-defender",
    "menu-goat": "bag-goat",
    "menu-skinny": "bag-skinny",
    # One distinct photo per process step, no repeats across the eight. Book,
    # intake and follow-up have no literal match in the library, so they take
    # the people involved rather than the action, and the alt text says what
    # the photograph actually shows rather than restating the step.
    "step-book": "team",
    "step-intake": "vein-check",
    "step-arrive": "at-home",
    "step-vitals": "cannulation",
    "step-select": "vial-check",
    "step-infusion": "workplace",
    "step-postcare": "athlete-iv",
    "step-followup": "founders",
    "safety-kit": "vial-check",
    "process-visual": "vein-check",
    "reserve-img": "at-home",
    "final-img": "in-office",
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
        // A single letter or a lone first name is an avatar label, so it
        // becomes a real initial avatar. Anything with a space was describing
        // a photograph nobody has, so the figure leaves the layout.
        var label = (img.getAttribute('alt') || '').trim();
        if (label && label.indexOf(' ') === -1 && label.length <= 12) {
          fig.classList.add('is-initial');
          fig.setAttribute('data-initial', label.charAt(0).toUpperCase());
        } else {
          fig.classList.add('is-blank');
        }
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
    html = html.replace(_MAP_RENDERED, _MAP_EMBED).replace(_MAP_TEMPLATE, _MAP_EMBED)
    html = resources_to_info(html)
    html = insert_benefits(html)
    html = insert_menu(html)
    html = gallery_slider(html)
    html = rewrite_uses_intro(html)
    html = why_choose_align(html)
    html = founder_headshots(html)
    html = fix_reasons(html)
    html = strip_readmore(html)
    html = board_heading(html)
    html = step_images(html)
    html = book_cta(html)
    html = drop_gallery_intro(html)
    html = nurse_chips(html)
    html = service_area(html)
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
.img-slot.is-initial{background:#153060;border:0}
.img-slot.is-initial::after{content:attr(data-initial);font:400 1.05rem Questrial,sans-serif;color:#B5DEF5;line-height:1}
.img-slot.is-initial .img-slot-note{display:none}
.img-slot.is-blank{display:none!important}
.img-slot[data-slot="final-img"] img{object-position:center 72%}
.img-slot[data-slot="drip-hydration"] img{object-position:center 12%}
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
