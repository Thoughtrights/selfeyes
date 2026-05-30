# Environment Variables & Secrets

## Two categories of env vars

| Category | Examples | Git? |
|---|---|---|
| **Config** — non-secret, env-specific | `DB_HOST`, `ENV`, `SITE_URL` | `.env.example` only |
| **Secrets** — API keys, passwords | `STRIPE_KEY`, `DB_PASS`, `SENDGRID_KEY` | Never |

Both are passed to CGIs the same way (Apache `SetEnv`), but secrets have stricter storage rules.

---

## Where vars are set — by context

| Context | Where they live |
|---|---|
| EC2 / production (Apache) | `/etc/apache2/conf-available/secrets.conf` + vhost conf |
| MacBook / local (Apache) | `/usr/local/etc/httpd/extra/httpd-vhosts.conf` |
| Unit tests (pytest) | `.env` file at repo root, loaded by python-dotenv |
| Git (committed) | `.env.example` with placeholder values only |

---

## EC2: secrets.conf (API keys & passwords)

Store all secrets in a single file outside any repo or docroot:

```apache
# /etc/apache2/conf-available/secrets.conf
# NOT in git. Permissions: root:root 640.
SetEnv STRIPE_KEY      "sk_live_..."
SetEnv SENDGRID_KEY    "SG...."
SetEnv OPENAI_KEY      "sk-..."
SetEnv DB_PASS         "rds-password-here"
```

Enable once, reload when updated:
```bash
sudo a2enconf secrets
sudo chmod 640 /etc/apache2/conf-available/secrets.conf
sudo chown root:root /etc/apache2/conf-available/secrets.conf
sudo systemctl reload apache2
```

Non-secret, per-vhost config (DB_HOST, ENV, SITE_URL) stays in the vhost `.conf` file.

---

## MacBook: httpd-vhosts.conf (local values)

```apache
# /usr/local/etc/httpd/extra/httpd-vhosts.conf
<VirtualHost *:8080>
    ServerName food.net.local
    DocumentRoot /usr/local/var/www/food.net
    ...
    # Config vars
    SetEnv DB_HOST    127.0.0.1
    SetEnv DB_PORT    3306
    SetEnv DB_NAME    foodnet
    SetEnv DB_USER    root
    SetEnv DB_PASS    ""
    SetEnv ENV        local
    SetEnv SITE_URL   http://food.net.local:8080
    # API keys — use test/sandbox keys locally
    SetEnv STRIPE_KEY    "sk_test_..."
    SetEnv SENDGRID_KEY  "SG.test_..."
    SetEnv OPENAI_KEY    "sk-..."
</VirtualHost>
```

This file is outside all repos and never committed anywhere.

---

## Unit tests: .env file

Tests run outside Apache, so they don't get `SetEnv`. Use python-dotenv:

**.env.example** (committed to git — placeholder values only):
```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=foodnet
DB_USER=root
DB_PASS=
ENV=local
SITE_URL=http://food.net.local:8080
STRIPE_KEY=sk_test_replace_me
SENDGRID_KEY=SG.replace_me
OPENAI_KEY=sk-replace_me
```

**.env** (gitignored — real test/sandbox values):
```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=foodnet
DB_USER=root
DB_PASS=
ENV=local
SITE_URL=http://food.net.local:8080
STRIPE_KEY=sk_test_abc123...
SENDGRID_KEY=SG.abc123...
OPENAI_KEY=sk-real...
```

`conftest.py` already calls `load_dotenv()` — no other setup needed.

---

## .gitignore (every repo)

```
.env
*.env
__pycache__/
*.pyc
*.log
.DS_Store
```

---

## Canonical config vars per vhost

### food.net
```
DB_HOST     RDS endpoint (EC2) or 127.0.0.1 (local)
DB_PORT     3306
DB_NAME     foodnet
DB_USER     <rds username>
DB_PASS     → secrets.conf on EC2 / vhosts.conf locally
ENV         local | production
SITE_URL    https://food.net or http://food.net.local:8080
```

### dungeoneer.com
```
DB_HOST     RDS endpoint or 127.0.0.1
DB_PORT     3306
DB_NAME     dungeoneer
DB_USER     <rds username>
DB_PASS     → secrets.conf on EC2 / vhosts.conf locally
ENV         local | production
SITE_URL    https://dungeoneer.com or http://dungeoneer.com.local:8080
```

### thoughtrights.com
```
DB_HOST     RDS endpoint or 127.0.0.1
DB_PORT     3306
DB_NAME     thoughtrights
DB_USER     <rds username>
DB_PASS     → secrets.conf on EC2 / vhosts.conf locally
ENV         local | production
SITE_URL    https://thoughtrights.com or http://thoughtrights.com.local:8080
```

---

## Reading vars in Python CGI

```python
import os
stripe_key = os.environ.get("STRIPE_KEY")
db_host    = os.environ.get("DB_HOST", "127.0.0.1")
env        = os.environ.get("ENV", "local")
```

Apache passes all `SetEnv` variables into the CGI process environment automatically.
No imports of dotenv, no config files needed in production code.
