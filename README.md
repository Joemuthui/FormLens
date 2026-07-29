# FormLens

> AI-powered adaptive form extractor. Upload a sample PDF, discover its schema collaboratively, then extract structured data from any number of forms.

![FormLens Landing](screenshot.png)

## What it does

FormLens solves a specific problem: extracting structured data from PDF forms without writing custom parsers or training models on hundreds of examples.

The workflow is three steps:

1. **Discover** — upload one sample PDF. Claude analyses the layout and proposes a schema: every field it found, its data type, allowed values, and where on the form it appears.
2. **Refine** — review the schema in a spreadsheet-style editor. Tell the AI what to change in plain language ("rename this field", "add a ward name column", "this is an enum with three values"). The schema updates live.
3. **Extract** — upload any number of forms. FormLens extracts structured records into a registry table, flags low-confidence fields, and lets you edit rows inline with the original PDF visible alongside.

Schemas are saved as portable `.formprofile.json` files. Sessions persist across page refreshes via localStorage and can be downloaded as `.formlens-session.json` files to resume later or share with a colleague.

## Features

- **Schema discovery** — AI proposes field names, types, allowed values and source locations from a single sample
- **Iterative refinement** — conversational feedback loop to shape the schema before any extraction runs
- **Bulk extraction** — drag and drop multiple PDFs, extracted one by one with progress tracking
- **Schema drift check** — optional pre-flight check flags when a new form doesn't match the saved profile
- **PDF viewer** — original form renders alongside the edit fields in the record editor
- **Persistent sessions** — auto-saves to localStorage; manual save/load via session files
- **Export** — download the full registry as CSV
- **BYOK** — bring your own Anthropic API key; stored in browser localStorage only, never transmitted anywhere except directly to `api.anthropic.com`

## Getting started

FormLens is a single HTML file with no build step and no backend.

### Run locally

Download `index.html` and open it in any modern browser. That's it.

### Deploy to Vercel

1. Fork this repository
2. Go to [vercel.com](https://vercel.com) and import the repo
3. Vercel detects the static file automatically — no configuration needed
4. Click Deploy

### API key

FormLens requires an Anthropic API key. Get one at [console.anthropic.com/keys](https://console.anthropic.com/keys).

Enter it on the home screen when you first open the app. It is stored only in your browser's localStorage and sent directly to `api.anthropic.com` — it never passes through any intermediary server.

## Supported field types

| Type | Description |
|------|-------------|
| `text` | Free-text string |
| `date` | Normalised to ISO 8601 (YYYY-MM-DD) |
| `time` | 24-hour HH:MM |
| `integer` | Whole number |
| `decimal` | Floating point number |
| `boolean` | true / false (yes/no checkboxes) |
| `enum` | One value from a defined list |
| `list` | Multiple values as a JSON array |

## Session and profile files

| File | Contains | Use |
|------|----------|-----|
| `.formprofile.json` | Schema fields + extraction prompt | Reuse a schema without re-discovering it |
| `.formlens-session.json` | Profile + all extracted records | Resume a working session on any device |

## Tech

- Single HTML file — HTML, CSS, and JavaScript with no dependencies or build step
- Fonts loaded from Google Fonts (DM Serif Display, DM Mono, Instrument Sans)
- All AI calls go directly from the browser to `api.anthropic.com/v1/messages`
- Model: `claude-sonnet-4-20250514`
- PDF viewing uses the browser's native PDF renderer via `<embed>`
- Persistence via `localStorage` (auto) and downloadable JSON files (manual)

## Limitations

- PDFs larger than 1.5 MB are extracted but not stored for in-modal preview
- Sessions in localStorage are browser and device specific — use Save Session to move between devices
- The schema drift check and form analysis require an active internet connection and a valid API key
- No multi-user support — FormLens is a single-user tool; each user brings their own key and manages their own sessions

## Roadmap

- [ ] Parallel extraction (concurrency pool)
- [ ] Field validation rules on the schema
- [ ] Low-confidence review queue filter
- [ ] OpenAI as a second provider option
- [ ] REDCap / CSV template export formats

## License

MIT
