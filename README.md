# thedripivinfusion

Content and page builds for [thedripivinfusion.com](https://thedripivinfusion.com).

## Layout

| Path | What it holds |
|---|---|
| `brand/` | Brand visual identity kit: palette, type, imagery and CTA rules |
| `content/` | Approved page copy (HTML + DOCX) and the research brief |
| `design/` | Raw Claude Design exports, untouched |
| `site/` | Vercel output directory: built, production-ready pages |
| `tools/` | Build scripts |

## Phoenix location page

Target keyword `iv therapy phoenix`. Replaces the live
`/mobile-iv-therapy-phoenix-az`.

```bash
python tools/build-page.py
```

Reads `design/IV Therapy Phoenix.dc.html` and writes
`site/mobile-iv-therapy-phoenix-az/index.html`. The build strips the Claude Design editor
runtime, swaps `<image-slot>` for real `<img>`, enforces the no-em-dash house
rule (it fails the build rather than mangling a sentence), and adds the SEO head
and JSON-LD.

## Vercel

`vercel.json` serves `site/` as the output directory with no build step, so the
deployed path matches production: `/mobile-iv-therapy-phoenix-az`.

`.vercelignore` keeps `content/`, `design/`, `brand/` and `tools/` out of the
deployment entirely. The client DOCX and XLSX must never be publicly fetchable.

Each built page is self-contained: the render runtime is inlined, so there are
no local file references and the same HTML works on Vercel, pasted into
WordPress, or opened from disk.

Import the repo at vercel.com/new. No framework, no build command, no env vars.

### Before this page goes live

- Fill the `data-slot` image sources in `site/mobile-iv-therapy-phoenix-az/index.html`
- Resolve the `[VERIFY]` items in `content/iv-therapy-phoenix-content.html`:
  medical director name, nurse licence numbers, reviewer star ratings and GBP
  URL, travel/group/HSA-FSA policy, clinical reviewer byline
- Populate `mainEntity` in the `faq-ld` JSON-LD block
- Point the placeholder `href="#"` links at their real URLs
