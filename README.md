# Sankalp Medical Records API

FastAPI backend for the Phase 1 SvelteKit patient-record workspace. The API keeps the frontend's stable IDs and camelCase JSON fields while using UUID primary keys internally.

## Run locally

Requires Python 3.10 or newer.

```powershell
cd sankalp-backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For plain `http://localhost:5173` development, set `COOKIE_SECURE=false` in `.env`. Keep it `true` behind HTTPS. Replace `SECRET_KEY` with a random value of at least 32 characters before deployment. Doctor self-registration is disabled by default; only enable `ALLOW_DOCTOR_REGISTRATION=true` in a controlled development environment.

```powershell
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

The API is at `http://localhost:8000`, interactive docs at `/docs` and `/redoc`, and the generated schema at `/openapi.json`. Export a checked-in schema for code generation with:

```powershell
python -m scripts.export_openapi
```

The application creates missing tables on startup by default for local development. Set `AUTO_CREATE_TABLES=false` in production and use Alembic migrations for deployment and schema changes. See [DEPLOYMENT.md](DEPLOYMENT.md) for the release checklist and production safeguards.

## Seed accounts

The idempotent seed script creates Dr. Maya Patel (`DR-0081`), four mock patients, and five appointments for October 1, 2026.

- Doctor: `maya.patel@northstar.health` / `doctor123`
- Patients: each seeded patient's fixture email / `patient123`

Seed records contain demo data only. Do not use real patient information in development.

## Authentication and browser requests

`POST /auth/login` sets an access token (15 minutes), rotating refresh token (7 days), and readable CSRF cookie. Tokens are HttpOnly, SameSite=Lax cookies; CSRF is sent back in the `X-CSRF-Token` header for cookie-authenticated POST/PATCH/DELETE requests. `POST /auth/refresh` rotates both JWT cookies; logout revokes the active refresh token and clears cookies. API clients can alternatively send a bearer access token.

Patient accounts can view only their own patient record and files. Doctor-only operations are enforced by API dependencies. Uploaded files are stored under `uploads/{patient_id}/` and each patient has a configurable `MAX_FILE_STORAGE_MB` limit (100 MB by default).

## Tests

```powershell
pytest
```

## Main endpoints

- `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`
- `GET /patients`, `GET/PATCH /patients/{id}`, `GET /patients/{id}/qr`
- `GET/PATCH /doctors/me`
- `GET /appointments/daily`, `GET /appointments/mine`, `PATCH /appointments/{id}`
- `GET/POST /patients/{id}/files`, `DELETE /patients/{id}/files/{file_id}`, `GET /patients/{id}/files/{file_id}/download`
