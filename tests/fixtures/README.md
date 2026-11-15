`comparison.json` is a trimmed public response captured from the deployed Render
service on 2026-11-15 using the default Muñoz request. It retains the values the
frontend consumes; per-year arrays and unrelated evidence are omitted.
`catalog.json` reproduces the live catalogue using the service branch's committed
place/crop CSV rows and API enums. These files are test inputs, never application
fallbacks. Use `KLIMA_LIVE_TEST=1 npx playwright test live-model` for an actual
browser-to-Render comparison.

`expanded-catalog.json`, `expanded-comparison.json`, and `expanded-fallow.json`
were generated on 2026-11-15 through the actual local API at engine fe13958 with
HTTP changes later committed as 8b0d6eb. They retain the consumed evidence and
omit per-season arrays. The default response includes all 29 crops, schedules,
recommendation verdicts and partial checks. The fallow case submits preparation
14, picking 21, clearing 7 days, and measured pH 3.0 to exercise a real no-suitable
verdict. These fixtures never ship as fallback data. The older responses remain
for contract compatibility tests.
