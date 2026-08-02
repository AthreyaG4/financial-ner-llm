# Financial Entity Extractor — React Project

Vite + React port of the design prototype.

## Setup

```bash
npm install
npm run dev
```

Then open the printed localhost URL.

## Build

```bash
npm run build
npm run preview
```

## Structure

- `src/data.js` — fake document text, entity list, entity type color metadata, span-building helper.
- `src/App.jsx` — full UI: upload/parse/loading/results/error states, collapsible left history sidebar (persisted to `localStorage`), right-side entity legend with click-to-filter, hover tooltips.
- `src/index.css` — fonts (IBM Plex Sans/Mono), keyframes, resets.

## Notes

- This is a simulated flow — no real PDF parsing or entity-extraction model is called. `handleFiles` and `onExtract` use `setTimeout` to fake latency; swap these for real API calls when wiring up a backend.
- The "Preview a scenario" pills on the upload screen let you force the success / parse-error / no-entities / malformed-extraction paths for testing.
- Colors use OKLCH (all modern browsers support this); adjust in `data.js` (`ENTITY_META`) and inline styles in `App.jsx`.
