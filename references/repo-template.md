# Repo Template

Standard layout for a feature repo. Not all files are required — include what's relevant.

## Directory structure

```
my-feature/
├── README.md
├── requirements.txt          # runtime deps (e.g. mysql-connector-python)
├── requirements-dev.txt      # test deps: pytest, pytest-cov, requests
├── schema.sql                # DB schema for this feature (if DB-dependent)
├── deploy.sh                 # deploy script (see references/deploy.md)
├── .env.example              # template of required env vars (no real values)
├── .gitignore
│
├── *.api                     # CGI endpoints at repo root, or in subdirs
│
├── static/                   # CSS, JS, images served directly
│   ├── css/
│   └── js/
│
├── templates/                # HTML templates if using server-side rendering
│
├── lib/                      # Shared Python modules imported by .api files
│   ├── db.py                 # DB connection helper
│   └── auth.py               # Auth/session helpers if needed
│
└── tests/
    ├── conftest.py           # pytest fixtures (DB setup/teardown)
    ├── test_*.py             # unit tests, one per .api file
    └── e2e/
        └── e2e_*.py          # end-to-end tests (run against live EC2 URL)
```

## .gitignore

```
__pycache__/
*.pyc
.env
*.log
.DS_Store
```

## requirements.txt (minimal)

```
mysql-connector-python
```

## requirements-dev.txt

```
pytest
pytest-cov
requests
python-dotenv
```

## lib/db.py — standard DB connection helper

```python
import os
import mysql.connector

def get_connection(db_name=None):
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASS", ""),
        database=db_name or os.environ.get("DB_NAME", ""),
    )
```

## Minimal .api file skeleton

```python
#!/usr/bin/env python3
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("Content-Type: application/json\n")

try:
    result = {"status": "ok"}
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"error": str(e)}))
```

## health.api (include in every repo)

```python
#!/usr/bin/env python3
import json
print("Content-Type: application/json\n")
print(json.dumps({"status": "ok"}))
```

This is the first thing E2E tests hit after a deploy.

## README.md minimum sections

- **Purpose** — one sentence
- **Vhost** — which of food.net / dungeoneer.com / thoughtrights.com
- **URL path** — e.g. `/qr/` or subdomain `qr.food.net`
- **Environment Variables** — table of all vars the repo needs, with a note explaining where secrets live (Apache `SetEnv`, not in repo). See pattern below.
- **DB** — yes/no, which schema
- **Local Setup** — step-by-step including `.env` setup
- **Deploy** — how to run `deploy.sh`
- **Tests** — how to run unit and E2E tests
- **Project Structure** — directory tree

> **See `references/readme-example.md`** for a complete, copy-paste-ready README template.
> Always generate a README following that structure when creating a new repo.

## .env.example

Every repo that uses any env var (DB credentials, API keys, etc.) must include a `.env.example`
committed to git with placeholder values. The real `.env` is gitignored.

```ini
# .env.example — copy to .env and fill in real values
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=foodnet
DB_USER=root
DB_PASS=
ENV=local
SITE_URL=http://food.net.local:8080
# Add any API keys this repo uses:
# STRIPE_KEY=sk_test_replace_me
# SENDGRID_KEY=SG.replace_me
```

For where real secrets are stored (not in `.env` for production), see `references/env-vars.md`.
