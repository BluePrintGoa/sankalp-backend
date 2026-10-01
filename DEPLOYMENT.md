# Deployment Preparation

This is a deployment checklist, not a production certification. The current local filesystem file store must be moved to durable private storage before running multiple API replicas; the app currently writes under `UPLOAD_DIR` on a single filesystem.

## 1. Provision services

- Provision a managed PostgreSQL database with TLS, automated backups, and restricted network access.
- Provision a private persistent volume for a single API instance, or implement an object-storage adapter before scaling to multiple instances.
- Deploy the API behind an HTTPS reverse proxy. Keep the database and file volume private.
- Deploy the SvelteKit frontend on the same site as the API (for example `app.example.com` and `api.example.com`) so SameSite=Lax cookies work.

## 2. Configure secrets and environment

Set secrets in the hosting provider's secret manager, not in source control:

```dotenv
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@DB_HOST:5432/DB_NAME
SECRET_KEY=<random value with at least 32 characters>
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["https://app.example.com"]
COOKIE_SECURE=true
COOKIE_DOMAIN=.example.com
ALLOW_DOCTOR_REGISTRATION=false
AUTO_CREATE_TABLES=false
MAX_FILE_STORAGE_MB=100
UPLOAD_DIR=/var/lib/sankalp/uploads
```

Use a host-only cookie (omit `COOKIE_DOMAIN`) when the frontend and API share one hostname. `COOKIE_DOMAIN` should be the narrowest shared parent domain when they use sibling subdomains. Never set `COOKIE_SECURE=false` in production. Keep doctor self-registration disabled; provision clinician accounts through a verified administrative workflow.

Set `PUBLIC_API_BASE_URL=https://api.example.com` in the frontend build environment. Set the API CORS origin to the exact frontend origin, not a wildcard. If the frontend and API are cross-site rather than same-site, use a same-origin reverse proxy or redesign cookie policy and CSRF protection before deployment; SameSite=Lax cookies are not sent for cross-site fetches.

## 3. Build and migrate

In the API release job, install dependencies and run migrations before replacing the live API process:

```sh
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
```

Keep `AUTO_CREATE_TABLES=false` in production so application startup does not create or alter schema outside the migration job. Do not run `python -m scripts.seed` against production; it inserts demo patient records and development credentials.

Build the frontend with the production `PUBLIC_API_BASE_URL`:

```sh
pnpm install --frozen-lockfile
pnpm check
pnpm build
```

The frontend currently uses `adapter-auto`; choose and install the adapter supported by the selected hosting platform before release. A local production build can succeed while adapter-auto reports that no production environment was detected.

## 4. Verify release

- Confirm `/health` succeeds and `/docs` is not publicly exposed if your organization treats the API schema as sensitive.
- Confirm HTTPS, CORS, and cookie attributes (`Secure`, `HttpOnly` for access/refresh, `SameSite=Lax`) in browser developer tools.
- Test doctor and patient login, refresh rotation, logout, patient cross-account denial, file quota, download, delete, and QR privacy using non-production fixtures.
- Generate client types from `/openapi.json` and review schema changes before release.
- Verify database and uploaded-file backups can be restored; configure monitoring for failed login bursts, 401/403 rates, quota failures, and storage capacity.

## Before handling real patient data

Add request rate limits at the edge for login and registration, clinician identity verification and account provisioning, audit logging for medical-record reads and changes, malware/content scanning for uploads, key rotation and secret-management procedures, and a documented incident/retention process. Confirm applicable health-data, privacy, and hosting obligations with qualified security and compliance reviewers. This development backend alone does not provide those controls or establish regulatory compliance.
