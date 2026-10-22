# OpenRouter model picker: design (draft, agree before coding)

## Current state (from the live index.html)
- Already OpenRouter BYOK: key stored in localStorage, verified via GET /api/v1/models.
- Model is hard-coded: `const OR_MODEL = 'z-ai/glm-5.2'`, used by `claude()` (chat/completions).
- PDFs are sent whole as OpenRouter `file` content parts (base64 data URL), not page images.
- Change needed: replace OR_MODEL with getModel() (localStorage, default glm-5.2).

## UI (matches existing minimal style)
- New collapsible "Model" panel directly under the API key panel, reusing .apikey-panel.
- Questions as pill toggles; pages/month as a small .mi input.
- Up to 3 radio-style recommendations: model id (mono), one-line reason, est. monthly cost.
- "Tested on CRFs" tag only for models actually benchmarked.
- Privacy note (sbar sb-ok) when identifiable data = yes.
- Mockup: docs/model-panel-mockup.png

## Goal
Let BYOK users pick a suitable OpenRouter model without browsing the full catalogue.

## Setup form (4 questions)
1. Forms are: handwritten / typed / mixed
2. Data contains identifiable participant information? yes / no
3. Priority: accuracy / balanced / cost
4. Approx. pages per month (number)

## Rules
- Hard filter: model must accept file/PDF or image input (check the models list's input modalities).
  Note: for non-vision models OpenRouter may fall back to text-only PDF parsing, which fails on handwriting.
- If identifiable data = yes: restrict requests to providers that do not retain
  or train on prompts (confirm the exact OpenRouter request setting from their docs).
- Show the "Tested on handwritten CRFs" shortlist first (2-3 benchmarked models).
- Everything else behind "Advanced: any vision model", with an accuracy warning.
- Output: 1-3 recommendations, each with estimated monthly cost and a one-line reason.

## Extraction robustness
- Not all models return clean JSON: validate every response against the form's
  field schema; retry once, then flag the page for manual entry.

## Interfaces
- provider.extract(pageImage, formSchema, options) -> { fields, raw, usage }
- modelPicker.recommend(answers, catalogue, shortlist) -> [{ id, reason, estMonthlyCost }]
  (pure function: catalogue passed in, so it is testable without network)

## Open questions
- Which 2-3 models go on the tested shortlist? Needs a small benchmark on real CRFs.
- Fifth question on form language (e.g. French)?
