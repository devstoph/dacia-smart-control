# Dacia Smart Control

A self-hosted web app to monitor and control a **Dacia Spring** (MY25/MY26),
built on top of [renault-api](https://github.com/hacf-fr/renault-api), the
library behind the MyRenault app integration.

It serves:

- **A browser dashboard** that is also a **PWA** — installable on your Android
  home screen ("Add to Home screen") with no app-store or APK build required.
- **A documented REST API** (OpenAPI schema at `/openapi.json`, interactive
  docs at `/docs`) designed so **AI assistants** can control the vehicle too.

## Supported actions (Dacia Spring / XBG2VE)

| Action | Endpoint |
| --- | --- |
| Battery / cockpit / HVAC / location status | `GET /api/status` |
| Vehicle details | `GET /api/vehicle` |
| Start charging | `POST /api/charge/start` |
| Charge schedule | `GET /api/charge/schedule` |
| Start pre-conditioning (15–25 °C) | `POST /api/hvac/start` |
| Stop pre-conditioning | `POST /api/hvac/stop` |
| Horn / lights (find the car) | `POST /api/horn`, `POST /api/lights` |
| Refresh GPS position | `POST /api/location/refresh` |

Note: the Spring does not expose a remote "stop charging" endpoint in the
Renault/Dacia API, so only *start* is available.

## Setup

Run from the repository root (the app imports `renault_api` from `src/`):

```console
pip install -e ".[cli]" -r app/requirements.txt
```

First run — provide your MyRenault/Dacia account credentials via environment
variables (used once, then a login token is cached in
`~/.dacia-smart-control/credential.json` and the password is no longer
needed):

```console
export DSC_EMAIL="you@example.com"
export DSC_PASSWORD="your-password"
export DSC_LOCALE="de_DE"     # or fr_FR, it_IT, ... matching your account country
python -m uvicorn dacia_smart_control.main:get_app --factory --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and click "Install app" / "Add to Home screen" in
your browser menu. Optional settings:

| Variable | Purpose |
| --- | --- |
| `DSC_ACCOUNT_ID` | Pin a specific Kamereon account (auto-detected otherwise) |
| `DSC_VIN` | Pin a specific VIN (auto-detected if you have one vehicle) |
| `DSC_APP_TOKEN` | Require `X-App-Token` header on all `/api/*` calls |
| `DSC_CREDENTIAL_FILE` | Where the login token is cached |

## Security

- Bind to `127.0.0.1` and keep it that way unless you know what you are doing;
  anyone who can reach the API can control your car (horn, HVAC, charging).
- Set `DSC_APP_TOKEN` to a long random string and enter it once in the UI; all
  API calls (browser and AI assistants) must then include the
  `X-App-Token: <token>` header.
- If your account requires 2FA, first login may raise a pending-2FA error;
  run the `renault-api` CLI once to complete the 2FA handshake and cache the
  login token, then start the app without `DSC_PASSWORD`.

## AI assistant usage

Point your AI assistant at the OpenAPI schema (`GET /openapi.json`) or the
human-readable docs (`GET /docs`). All control endpoints are plain JSON REST
calls, for example:

```console
curl -X POST http://127.0.0.1:8000/api/hvac/start \
  -H "X-App-Token: $DSC_APP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"temperature": 21}'
```

## Tests

```console
pip install -r app/requirements-test.txt
PYTHONPATH=src:app pytest app/tests
```
