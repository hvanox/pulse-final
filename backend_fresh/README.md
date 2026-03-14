# backend_fresh

Fresh backend implementation for Pulse with:
- onboarding questions loaded from SQLite
- JWT auth + bcrypt password hashing
- health check and ML preparation endpoints
- CI-ready Docker and GitHub Actions workflow

## Run locally

```bash
pip install -r backend_fresh/requirements.txt
uvicorn backend_fresh.main:app --reload
```

## Environment variables

- `DB_PATH` (default: `pulse_fresh.db`)
- `JWT_SECRET` (required in production)
- `JWT_EXPIRES_MIN` (default: `180`)
- `START_BALANCE` (default: `1000000`)
- `CORS_ORIGINS` (comma-separated origins)
