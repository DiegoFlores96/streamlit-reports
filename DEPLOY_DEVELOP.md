# Deploy Develop

This guide standardizes deploy for the `develop` environment.

## 1. Prerequisites

- Docker Desktop with `docker compose`
- PowerShell (Windows)
- Repository cloned locally

## 2. Environment file

Create `.env.develop` from the template:

```powershell
Copy-Item .env.develop.example .env.develop
```

Required values to review:

- `JWT_SECRET_KEY` (must be non-empty)
- `PATH_TESTES_ARQUIVOS` (absolute path used by dashboards)
- `DB_FILE` or `DATABASE_URL`
- `HOST_PORT` / `STREAMLIT_SERVER_PORT`

## 3. Deploy command

Use the script:

```powershell
./scripts/deploy-develop.ps1
```

Manual equivalent:

```powershell
docker compose -f docker-compose.develop.yml up --build -d
```

## 4. Verify

- App: `http://localhost:8501` (or `HOST_PORT`)
- Health endpoint: `http://localhost:8501/_stcore/health`

Quick logs:

```powershell
docker compose -f docker-compose.develop.yml logs -f
```

## 5. Stop / restart

Stop:

```powershell
docker compose -f docker-compose.develop.yml down
```

Restart:

```powershell
docker compose -f docker-compose.develop.yml up -d
```

## 6. Branch flow suggestion

- Open PRs to `develop`
- Merge only after tests pass (`.github/workflows/develop-ci.yml`)
- Run deploy command right after merge
- Keep production deploy isolated from this compose file
