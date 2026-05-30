---
name: dev-workflow
description: >
  Use this skill for ANY development workflow task across the three-vhost Apache/CGI stack
  (food.net, dungeoneer.com, thoughtrights.com). Triggers include: setting up a new repo,
  running or writing unit tests, previewing a CGI locally, deploying to EC2, running
  end-to-end tests, debugging a failed deploy, or any question about the build/test/deploy
  pipeline. Also trigger when the user mentions a feature repo, a subdomain (e.g. qr.food.net),
  a .api file, pytest, rsync, Apache vhost config, RDS, API keys, secrets, .env files,
  or asks "how do I test/deploy/run/secure this."
  Always consult this skill before writing any deploy script, test harness, or local preview
  setup — the environment specifics matter.
---

# Dev Workflow Skill

Covers the full lifecycle for a multi-repo, Apache/CGI Python stack:
**Build → Unit Test → Local Preview → Deploy → E2E Test**

## Stack at a Glance

| Layer | Local (MacBook) | Production (EC2 Ubuntu) |
|---|---|---|
| Web server | Apache via Homebrew + mod_cgi | Apache2 + mod_cgi |
| CGI scripts | `.api` files, Python 3 | `.api` files, Python 3 |
| Database | Local MySQL (per-vhost DBs) | AWS RDS MySQL (per-vhost DBs) |
| Deployment | Git pull on EC2 | Git pull on EC2 |
| Repos | Feature-scoped, multiple per vhost | Same repos, pulled to vhost docroot |

## Virtual Hosts

| Vhost | Purpose | Example subdomain |
|---|---|---|
| `food.net` | Food commerce features | `qr.food.net` |
| `dungeoneer.com` | Gaming tools, RPG docs | `tools.dungeoneer.com` |
| `thoughtrights.com` | Professional / misc | — |

Each vhost has its own MySQL database locally and on RDS. Database names follow the pattern in `references/databases.md`.

---

## 1. New Repo Setup

When a user starts a new feature repo, follow this checklist. Read `references/repo-template.md` for the standard file layout.

```bash
# On MacBook
mkdir my-feature && cd my-feature
git init
# Create standard structure (see references/repo-template.md)
git remote add origin git@github.com:USERNAME/my-feature.git
git push -u origin main
```

**Apache vhost fragment** (add to the relevant vhost config on both local and EC2):
```apache
Alias /feature-path /var/www/vhost/feature-path
<Directory /var/www/vhost/feature-path>
    Options +ExecCGI
    AddHandler cgi-script .api
    AllowOverride All
    Require all granted
</Directory>
```

For subdomains (e.g. `qr.food.net`), see `references/vhost-configs.md`.

---

## 2. Local Preview (MacBook → Apache)

Goal: mirror EC2 as closely as possible using Homebrew Apache with mod_cgi.

> **Full setup guide**: `references/local-apache-setup.md`

### Quick start (repo already set up)

```bash
# Ensure Apache is running
brew services start httpd

# Symlink repo into local docroot (adjust path per vhost)
ln -s ~/projects/my-feature /usr/local/var/www/food.net/my-feature

# Tail Apache logs
tail -f /usr/local/var/log/httpd/error_log
```

### CGI environment parity

Local `.api` files must be executable and have the correct shebang:
```python
#!/usr/bin/env python3
```

```bash
chmod +x path/to/endpoint.api
```

Set `DATABASE_URL` and other env vars in `/usr/local/etc/httpd/extra/httpd-vhosts.conf` using `SetEnv`, matching what EC2 uses via its Apache config. See `references/env-vars.md` for the canonical list per vhost.

---

## 3. Unit Tests

**Stack**: `pytest` + `pytest-cov`. Database tests use a local MySQL test database — never the real RDS.

> **Full guide**: `references/unit-testing.md`

### Conventions

- Test files live in `tests/` at repo root, named `test_*.py`
- Each `.api` file should have a corresponding `tests/test_<name>.py`
- Database-touching tests use the fixture in `references/unit-testing.md` which spins up schema from `schema.sql` and tears it down after

### Running tests

```bash
# From repo root
pip install -r requirements-dev.txt
pytest                        # all tests
pytest tests/test_myfile.py   # single file
pytest --cov=. --cov-report=term-missing  # with coverage
```

### Local MySQL test DB setup

```bash
mysql -u root -e "CREATE DATABASE IF NOT EXISTS test_foodnet;"
# Run schema
mysql -u root test_foodnet < schema.sql
```

Database names follow the convention `test_<vhost_db_name>`. See `references/databases.md`.

---

## 4. Deployment (MacBook → EC2)

Deployment is **always Git-based**: push to GitHub, then pull on EC2. No direct rsync.

> **Full deploy guide**: `references/deploy.md`

### Standard deploy flow

```bash
# 1. On MacBook — push your changes
git add -A && git commit -m "your message"
git push origin main

# 2. SSH to EC2
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP>

# 3. On EC2 — pull into the feature's docroot
cd /var/www/<vhost-docroot>/<feature-path>
git pull origin main

# 4. Fix permissions if needed
sudo chown -R www-data:www-data .
sudo chmod -R 755 .
find . -name "*.api" -exec chmod +x {} \;

# 5. Test immediately
curl -I https://<vhost>/<feature-path>/health.api
```

### Deploy script

For repos with a `deploy.sh` at root, Claude will generate one using the template in `references/deploy.md`. The script wraps the steps above and accepts a `--vhost` flag.

### Apache reload (only needed for config changes)

```bash
sudo systemctl reload apache2
```

---

## 5. End-to-End Tests

E2E tests run against the **live EC2 URLs** after deployment. They use `pytest` + `requests` (no browser automation unless explicitly needed).

> **Full guide**: `references/e2e-testing.md`

### Conventions

- E2E tests live in `tests/e2e/`, named `e2e_*.py`
- They test HTTP responses: status codes, JSON shape, key field values
- They must be safe to run against production (read-only or use isolated test records with a `_e2etest` suffix / teardown)
- Base URLs are set via env var: `E2E_BASE_URL=https://food.net/my-feature`

### Running E2E tests

```bash
E2E_BASE_URL=https://food.net/my-feature pytest tests/e2e/
```

### Minimal E2E test example

```python
import os, requests

BASE = os.environ["E2E_BASE_URL"]

def test_health():
    r = requests.get(f"{BASE}/health.api")
    assert r.status_code == 200

def test_main_endpoint_returns_json():
    r = requests.get(f"{BASE}/data.api?q=test")
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
```

---

## Reference Files

Read these on demand — only when the relevant section above is being executed:

| File | When to read |
|---|---|
| `references/local-apache-setup.md` | First-time local Apache/CGI setup |
| `references/repo-template.md` | Creating a new feature repo |
| `references/vhost-configs.md` | Subdomain or new vhost Apache config |
| `references/databases.md` | DB names, schema conventions, RDS connection strings |
| `references/env-vars.md` | Canonical env vars, API key storage, secrets.conf pattern |
| `references/readme-example.md` | Complete README template — use when creating any new repo |
| `references/unit-testing.md` | pytest fixtures, DB test patterns |
| `references/deploy.md` | Full deploy script template, EC2 paths, troubleshooting |
| `references/e2e-testing.md` | E2E patterns, teardown, auth handling |

---

## Decision Tree

```
User asks about...
├── new feature / repo setup       → Section 1 + references/repo-template.md + references/readme-example.md
├── running it locally / preview   → Section 2 + references/local-apache-setup.md
├── writing or running tests       → Section 3 + references/unit-testing.md
├── pushing to EC2 / deploying     → Section 4 + references/deploy.md
├── testing after deploy / e2e     → Section 5 + references/e2e-testing.md
├── DB schema / connections        → references/databases.md
├── env vars / secrets / API keys  → references/env-vars.md
└── README for a repo              → references/readme-example.md
```
