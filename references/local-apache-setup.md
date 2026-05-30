# Local Apache Setup (MacBook)

Goal: run Apache + mod_cgi on macOS via Homebrew, matching EC2 as closely as possible.

## One-time install

```bash
brew install httpd
brew services start httpd
```

Apache config lives at: `/usr/local/etc/httpd/httpd.conf`

## Enable mod_cgi

In `httpd.conf`, uncomment:
```apache
LoadModule cgi_module lib/httpd/modules/mod_cgi.so
```

## Enable vhost includes

In `httpd.conf`, uncomment:
```apache
Include /usr/local/etc/httpd/extra/httpd-vhosts.conf
```

## /etc/hosts entries

Add local vhost names so your browser resolves them:
```
127.0.0.1   food.net.local
127.0.0.1   dungeoneer.com.local
127.0.0.1   thoughtrights.com.local
# Subdomain examples:
127.0.0.1   qr.food.net.local
```

Use the `.local` suffix to avoid conflicting with real DNS.

## httpd-vhosts.conf template

```apache
<VirtualHost *:8080>
    ServerName food.net.local
    DocumentRoot /usr/local/var/www/food.net
    ErrorLog /usr/local/var/log/httpd/food.net-error.log
    CustomLog /usr/local/var/log/httpd/food.net-access.log combined

    # CGI support
    <Directory /usr/local/var/www/food.net>
        Options +ExecCGI -Indexes
        AddHandler cgi-script .api
        AllowOverride All
        Require all granted
    </Directory>

    # Config vars (non-secret)
    SetEnv DB_HOST 127.0.0.1
    SetEnv DB_PORT 3306
    SetEnv DB_NAME foodnet
    SetEnv DB_USER root
    SetEnv ENV local
    SetEnv SITE_URL http://food.net.local:8080

    # Secrets — add any API keys or passwords this vhost needs, e.g.:
    # SetEnv DB_PASS ""
    # SetEnv STRIPE_KEY "sk_test_..."
    # SetEnv SENDGRID_KEY "SG.test_..."
    # On EC2 these live in /etc/apache2/conf-available/secrets.conf instead.
    # See references/env-vars.md for the full pattern.
</VirtualHost>
```

Repeat blocks for `dungeoneer.com.local` and `thoughtrights.com.local`, adjusting `DB_NAME` and `SITE_URL`.

Note: Homebrew Apache runs on port **8080** by default (not 80) to avoid needing sudo.

## Local docroot structure

```
/usr/local/var/www/
├── food.net/
│   └── my-feature/       ← symlink or clone of feature repo
├── dungeoneer.com/
└── thoughtrights.com/
```

Create docroots:
```bash
mkdir -p /usr/local/var/www/food.net
mkdir -p /usr/local/var/www/dungeoneer.com
mkdir -p /usr/local/var/www/thoughtrights.com
```

## Symlinking a feature repo

```bash
ln -s ~/projects/my-feature /usr/local/var/www/food.net/my-feature
```

## Restart & logs

```bash
brew services restart httpd
tail -f /usr/local/var/log/httpd/error_log
tail -f /usr/local/var/log/httpd/food.net-error.log
```

## Verifying CGI works

```bash
curl http://food.net.local:8080/my-feature/health.api
```

If you get a 500, check:
1. File is executable: `chmod +x health.api`
2. Shebang line is correct: `#!/usr/bin/env python3`
3. Script prints `Content-Type` header before any output:
   ```python
   print("Content-Type: application/json\n")
   ```
4. Apache error log for the actual Python traceback
