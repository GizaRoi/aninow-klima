`comparison.json` is a trimmed public response captured from the deployed Render
service on 2026-11-15 using the default Muñoz request. It retains the values the
frontend consumes; per-year arrays and unrelated evidence are omitted.
`catalog.json` reproduces the live catalogue using the service branch's committed
place/crop CSV rows and API enums. These files are test inputs, never application
fallbacks. Use `KLIMA_LIVE_TEST=1 npx playwright test live-model` for an actual
browser-to-Render comparison.
