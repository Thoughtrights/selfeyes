# QR Code Generator

Generates and manages QR codes for menu items and promotions.

- **Vhost**: food.net
- **URL**: `https://qr.food.net` (subdomain) / `http://qr.food.net.local:8080` (local)
- **Database**: `foodnet` (tables prefixed `qr_`)

---

## Environment Variables

This repo requires the following environment variables. They are **never stored in git**.

| Variable | Description | Example |
|---|---|---|
| `DB_HOST` | MySQL host | `127.0.0.1` (local) or RDS endpoint |
| `DB_PORT` | MySQL port | `3306` |
| `DB_NAME` | Database name | `foodnet` |
| `DB_USER` | Database user | `root` (local) |
| `DB_PASS` | Database password | *(empty locally)* |
| `ENV` | Environment name | `local` or `production` |
| `SITE_URL` | Base URL for this vhost | `https://qr.food.net` |
| `QR_API_KEY` | Third-party QR service key | `qr_live_abc123...` |
| `SENDGRID_KEY` | Email delivery key | `SG.abc123...` |

### Where secrets live (NOT in this repo)

**Production (EC2)** — `/etc/apache2/conf-available/secrets.conf`:
```apache
SetEnv QR_API_KEY "qr_live_abc123..."
SetEnv SENDGRID_KEY "SG.abc123..."
```
This file is owned by root, not in any repo, and loaded by Apache at startup via `a2enconf secrets`.

**Local (MacBook)** — `/usr/local/etc/httpd/extra/httpd-vhosts.conf`:
```apache
<VirtualHost *:8080>
    ServerName qr.food.net.local
    ...
    SetEnv QR_API_KEY "qr_test_xyz..."
    SetEnv SENDGRID_KEY "SG.test..."
</VirtualHost>
```

**Unit tests** — `.env` file at repo root (gitignored). Copy `.env.example` and fill in real values:
```bash
cp .env.example .env
# edit .env with your local test keys
```

See `references/env-vars.md` in the skill docs for the full pattern.

---

## Local Setup

### Prerequisites
- Homebrew Apache configured (see `references/local-apache-setup.md`)
- Local MySQL running: `brew services start mysql`
- Python 3 with pip

### Steps

```bash
# 1. Clone into local docroot
ln -s ~/projects/qr-feature /usr/local/var/www/qr.food.net

# 2. Create and seed local database
mysql -u root foodnet < schema.sql

# 3. Add secrets to httpd-vhosts.conf (see Environment Variables above)
#    Then restart Apache:
brew services restart httpd

# 4. Make CGI files executable
find . -name "*.api" -exec chmod +x {} \;

# 5. Install dev dependencies
pip install -r requirements-dev.txt

# 6. Verify
curl http://qr.food.net.local:8080/health.api
```

---

## Running Tests

### Unit tests

```bash
# Copy and fill in .env before first run
cp .env.example .env

pytest
pytest --cov=. --cov-report=term-missing
```

### End-to-end tests (against production, run after deploy)

```bash
E2E_BASE_URL=https://qr.food.net pytest tests/e2e/ -v
```

---

## Deploying

```bash
# Push to GitHub, then deploy to EC2:
./deploy.sh --vhost food.net
```

The deploy script pushes the latest commit, pulls it on EC2, fixes permissions, and runs a health check. See `references/deploy.md` for details.

If this deploy includes **schema changes**, apply them on EC2 after deploying:
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP>
mysql -h <RDS_HOST> -u <RDS_USER> -p foodnet < /var/www/qr.food.net/schema.sql
```

---

## Project Structure

```
qr-feature/
├── README.md
├── health.api              # smoke test endpoint
├── generate.api            # POST: generate a QR code
├── list.api                # GET: list saved QR codes
├── requirements.txt
├── requirements-dev.txt
├── schema.sql
├── deploy.sh
├── .env.example            # ← committed; copy to .env locally
├── .gitignore              # ← .env is listed here
├── lib/
│   ├── db.py
│   └── qr_service.py
└── tests/
    ├── conftest.py
    ├── test_generate.py
    ├── test_list.py
    └── e2e/
        ├── e2e_health.py
        └── e2e_generate.py
```
