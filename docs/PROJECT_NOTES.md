# FormLens

AI extraction of paper case report forms (CRFs) into structured, analysis-ready data.
First entry by AI, verified by your team.

## Layout

```
index.html              Landing page (site entry): demo video, pricing, pilot request
app.html                The FormLens tool (served at /app)
about.html              Redirect to index.html for old links
src/providers/          One file per AI provider, all behind the same interface
  openrouter.js         OpenRouter BYOK path (current behaviour, extracted from index.html)
  anthropic.js          not needed: FormLens already uses OpenRouter
src/modelPicker.js      Pure logic: vision filter, ranking, cost estimate (tested)
src/modelPanel.js       Model panel UI + saved choice; feeds model/privacy into requests
src/contact.js          Contact settings shared by all pages (WhatsApp, email, form endpoint)
src/footer.js           Builds the same centred footer on every page
src/extract.js          Provider-agnostic extraction + JSON validation against the form schema
tests/                  Unit tests (no network): filtering, ranking, validation
tools/render_demo.py    Re-renders assets/formlens_demo.mp4 (needs Pillow + ffmpeg)
vercel.json             cleanUrls, so app.html is served at /app
assets/                 Demo video and images
docs/                   Design notes
```

No build step: plain HTML + ES modules, deployed to Vercel as static files.

## Status

- [ ] Connect this folder to the GitHub repo and bring in the existing index.html
- [x] OpenRouter design note (docs/openrouter-design.md)
- [x] Model picker + tests (run: node --test tests/modelPicker.test.js)
- [ ] Benchmark 2-3 models on real CRFs, then set tested: true in DEFAULT_SHORTLIST
- [x] Landing page with demo video and tiers
- [ ] Fill in contact details (WhatsApp/email/form endpoint) in src/contact.js
