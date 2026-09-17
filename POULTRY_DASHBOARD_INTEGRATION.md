# Poultry Dashboard integration

This branch ports the supplied Poultry Dashboard into SENSD as the isolated
`poultrydashboard` Django app. It deliberately does not import the ZIP's Django
6 project settings, authentication, Railway configuration, `.env`, or database.

## Security model

- Existing SENSD authentication protects every page and API.
- Every user-owned record has a foreign key to `AUTH_USER_MODEL`.
- Profiles, notes, uploaded rows, chat content, attachment summaries, and
  BluConsole credentials use SENSD's Fernet encrypted fields.
- BluConsole credentials are server-side only and are never returned by an API.
- User/provider-controlled strings rendered by JavaScript are HTML escaped.
- CSRF middleware protects all state-changing endpoints.
- Poultry demo login defaults to enabled only when Django DEBUG is enabled.
- OpenAI and BluConsole are optional; missing provider configuration does not
  prevent SENSD, Maps, uploads, or deterministic AI estimation from loading.

## Local verification

Run from `D:\SENSD_WEB\sensdweb`:

```powershell
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py test
..\.venv\Scripts\python.exe manage.py check
```

Open `/poultry/` after signing in through the existing SENSD login.

## Optional environment variables

```text
BLU_BASE=https://http-receiver.bluconsole.com
POULTRY_DEMO_LOGIN_ENABLED=False
POULTRY_DEMO_LOGIN_USERNAME=
POULTRY_DEMO_LOGIN_PASSWORD=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

Do not commit values. Configure production values in `/etc/sensd.env` on EC2.

## Merge and deployment order

1. Merge and deploy `feature/mapsapp-spatial-analysis` first.
2. Merge `feature/poultry-dashboard-integration` after Maps is on the target.
3. On EC2, install `requirements-aws.txt`, run `manage.py migrate`, run
   `manage.py collectstatic --noinput`, and restart Gunicorn.
4. Validate `/poultry/` without provider credentials first.
5. Add BluConsole and OpenAI configuration only after the base page passes.

The source ZIP is ignored and must not be committed.
