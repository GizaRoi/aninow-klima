# Model comparison API

Implemented on `feat/klima-model`. This stateless API exposes the existing historical
rules model to HTTP clients. It is separate from the proposed authenticated,
persisted application API in [API-Contract.md](API-Contract.md). It does not provide
accounts, saved farms, yield predictions, finances, or the frontend's sample scores.

## Run locally

From the checkout root:

```sh
python -m venv .venv
# Windows: .venv\Scripts\python.exe -m pip install -r model/requirements-dev.txt
# macOS/Linux: .venv/bin/python -m pip install -r model/requirements-dev.txt
```

Using that environment's Python, run from `model/`:

```sh
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --workers 1
python -m unittest discover .
```

Interactive API documentation is at `/docs`; the machine-readable contract is at
`/openapi.json`. The core CLI and local HTML form still use only the standard
library; the HTTP API needs the packages in `requirements.txt`. API tests also need
`requirements-dev.txt`.

## Deploy on Render

Create a **Web Service** connected to `GizaRoi/aninow-klima` with:

| Setting | Value |
|---|---|
| Branch | `feat/klima-model` |
| Runtime | Python 3 |
| Root directory | `model` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn api:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health check | `/health` |
| Instance | Free for a demo; choose paid compute if idle wake-up delays are unacceptable |
| `PYTHON_VERSION` | `3.12.10` (the version used for local verification) |
| `CORS_ORIGINS` | Exact frontend origins, comma-separated, without paths or trailing slashes |

The current frontend is `https://aninow-klima.vercel.app` and its model service is
`https://aninow-klima.onrender.com`. The API defaults and Blueprint allow the exact
frontend origin plus localhost ports 3000 and 4173. `CORS_ORIGINS` replaces that
list when set; for example `https://aninow-klima.vercel.app,http://localhost:3000`.
Do not use a wildcard for all Vercel preview domains. Add an exact preview origin
when needed. CORS controls browser access; it is not authentication.

`render.yaml` provides the same settings for creating a Render Blueprint. Changing
that file does not update a service created manually: edit that service's settings.
The local `.python-version` selects the 3.12 series; `PYTHON_VERSION` takes precedence
on Render. No credentials or NASA downloads are needed at request time. All input
datasets are committed under `model/`.

After deploying, visit `/health`, `/docs`, and `/api/v1/catalog`, then submit the
example below. Free Render services can sleep when idle; a request may first wait
for the service to wake. A cold start is separate from the model calculation time.

References: [Render FastAPI deployment](https://render.com/docs/deploy-fastapi),
[Python version selection](https://render.com/docs/python-version), and
[free service behavior](https://render.com/docs/free).

## Endpoints and contract

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Fast process health, without running the model |
| GET | `/api/v1/catalog` | Supported place IDs, crops, field enums and season groups |
| POST | `/api/v1/compare` | Run the existing model and return its complete JSON result |

This comparison endpoint is public and stateless, for a demonstration. It accepts
no account IDs, farm names, uploaded files or arbitrary coordinates and stores no
submissions or results. Place IDs are the exact catalogue strings. It is not the
private `/v1/predict` service or `/api/v1/analyses` persistence workflow in the
proposed application contract.

Example request:

```json
{
  "place": "Science City of Muñoz, Nueva Ecija",
  "main_crop": "rice",
  "harvest": "2026-11-15",
  "next_planting": "2027-05-31",
  "drainage": "well_drained",
  "water": "rain",
  "priority": "balanced",
  "soil_ph": null,
  "soil_texture": null,
  "turnaround_days": 0,
  "pass_mark": 0.6
}
```

Required fields are `place`, `harvest`, `next_planting` and `drainage`. Other fields
use the example defaults. Soil values must be measured overrides, or null to let
the model use its documented SARAI sample lookup. Do not infer a numeric pH or a
texture class from the prototype's soil label without a reviewed mapping.

Dates must be ISO calendar dates, next planting must follow harvest, and the window
must fit within one annual cycle. February 29 is rejected because the model replays
month/day pairs over non-leap historical years. Soil pH is bounded to 3–10, pass
mark to 0–1, and land preparation to an integer from 0–90 days, matching the local
form. Unknown fields, unsupported places/crops, and nonfinite numbers are rejected.
Clients cannot choose output paths, model versions, thresholds other than the
explicit pass mark, or arbitrary subprocess arguments.

Responses have:

- `contract_version`: `klima-comparison.v1`.
- `mode`: `rules_model`, distinguishing these results from frontend fixtures.
- `model_version`: a SHA-256 fingerprint of the engine and committed model datasets.
- `request_id`: the same ID as the `X-Request-ID` response header.
- `inputs`: the validated request, including defaults.
- `ranking`: the existing model order for the selected water scenario and priority.
- `warnings`: limitations of the historical rules model and selected inputs.
- `results`: the CLI's full, unchanged JSON, including methods, sources, soil
  provenance, exclusions, both water scenarios, season counts and planting dates.

Display `results.fields[inputs.water]`. For crop history, select
`crop.counts.balanced[season].short`, where season is `all`, `normal`, `dry`, or
`el_nino`. Counts include `pass` and `of`; intervals remain historical intervals,
not forecasts. Rankings are the model's all-season order and do not change when a
client displays a different season group. The irrigation scenario assumes water
is sufficient; it does not measure a farmer's available irrigation supply.

All responses have `Cache-Control: no-store`. Validation failures return 422,
busy/unavailable model responses return 503, and model timeouts return 504. Errors
use `{ "error": { "code": "...", "message": "...", "field_errors": {} }, "request_id": "..." }`.
A busy response includes `Retry-After: 5`. Keep field inputs on screen when a
request fails and give the user an explicit retry control.

## Frontend integration

The frontend is on `feat/planting-planner` and `prod`; this API does not change its
sample adapter or deploy it. First fetch the catalogue, then send JSON:

```ts
const response = await fetch(`${apiBaseUrl}/api/v1/compare`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(inputs),
  signal: AbortSignal.timeout(180_000),
});
const body = await response.json();
if (!response.ok) throw new Error(body.error?.message ?? 'Comparison failed');
if (body.contract_version !== 'klima-comparison.v1' || body.mode !== 'rules_model') {
  throw new Error('Unsupported model response');
}
```

Use the deployed Render base URL, configure its `CORS_ORIGINS` to include the
frontend's exact origin, and handle a waking Render service returning non-JSON or
a delayed response. Never fall back silently from real results to sample results.

The current frontend uses different field names: `pond` no/yes/unsure maps to
`drainage` well_drained/poorly_drained/unknown; `water` rain/irrig maps to
rain/irrigation; `next` maps to `next_planting`; blank `ph` becomes null. Priorities
even/water/soil/time map to balanced/saving_water/healthier_soil/finishing_early.
These are explicit enum translations, not inferred soil or agronomic evidence.
The four-crop sample output must be replaced with the catalogue/model's crop set,
actual season denominators, exclusions and missing values before enabling live
results in the UI. Label historical results and remove sample-only claims.

## Isolation and limits

The model uses module-level configuration, so each request runs its unmodified CLI
in an isolated subprocess. Arguments are a list and never passed through a shell.
Each request gets a temporary output directory that is removed even on timeout;
there is no shared `results.json`. The API fingerprint records the engine and
dataset contents; request-specific settings travel in `inputs` and model metadata.

One calculation is allowed at a time per process; use one Uvicorn worker on free
compute. Additional calculations fail promptly with 503 instead of accumulating
processes. Health and catalogue requests remain available during calculations.
The subprocess timeout is 120 seconds. This is not a distributed rate limit,
authentication system, job queue, or persistent history store. Add those when
moving to an authenticated production application.
