# Vhost & Subdomain Configs

## EC2: adding a feature path to an existing vhost

Edit `/etc/apache2/sites-available/food.net.conf`:

```apache
<VirtualHost *:80>
    ServerName food.net
    ServerAlias www.food.net
    DocumentRoot /var/www/food.net

    <Directory /var/www/food.net>
        Options +ExecCGI -Indexes
        AddHandler cgi-script .api
        AllowOverride All
        Require all granted
    </Directory>

    # Config vars (non-secret) — safe to put in vhost conf
    SetEnv DB_HOST <RDS_ENDPOINT>
    SetEnv DB_NAME foodnet
    SetEnv DB_USER <user>
    SetEnv ENV production
    SetEnv SITE_URL https://food.net

    # Secrets (DB_PASS, API keys) live in /etc/apache2/conf-available/secrets.conf
    # NOT here. See references/env-vars.md.

    ErrorLog ${APACHE_LOG_DIR}/food.net-error.log
    CustomLog ${APACHE_LOG_DIR}/food.net-access.log combined
</VirtualHost>
```

```bash
sudo apache2ctl configtest
sudo systemctl reload apache2
```

## EC2: new subdomain vhost

For `qr.food.net`, create `/etc/apache2/sites-available/qr.food.net.conf`:

```apache
<VirtualHost *:80>
    ServerName qr.food.net
    DocumentRoot /var/www/qr.food.net

    <Directory /var/www/qr.food.net>
        Options +ExecCGI -Indexes
        AddHandler cgi-script .api
        AllowOverride All
        Require all granted
    </Directory>

    SetEnv DB_HOST <RDS_ENDPOINT>
    SetEnv DB_NAME foodnet
    SetEnv DB_USER <user>
    SetEnv ENV production
    SetEnv SITE_URL https://qr.food.net
    # Secrets in /etc/apache2/conf-available/secrets.conf — not here.

    ErrorLog ${APACHE_LOG_DIR}/qr.food.net-error.log
    CustomLog ${APACHE_LOG_DIR}/qr.food.net-access.log combined
</VirtualHost>
```

```bash
sudo a2ensite qr.food.net.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

Also add the subdomain DNS A record pointing to the EC2 IP.

## HTTPS / SSL (Certbot)

```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d qr.food.net
# Certbot will modify the vhost config automatically
sudo systemctl reload apache2
```

## Local (MacBook): subdomain preview

Add to `/etc/hosts`:
```
127.0.0.1   qr.food.net.local
```

Add to `/usr/local/etc/httpd/extra/httpd-vhosts.conf`:
```apache
<VirtualHost *:8080>
    ServerName qr.food.net.local
    DocumentRoot /usr/local/var/www/qr.food.net
    <Directory /usr/local/var/www/qr.food.net>
        Options +ExecCGI -Indexes
        AddHandler cgi-script .api
        AllowOverride All
        Require all granted
    </Directory>
    SetEnv DB_HOST 127.0.0.1
    SetEnv DB_NAME foodnet
    SetEnv DB_USER root
    SetEnv ENV local
    SetEnv SITE_URL http://qr.food.net.local:8080
    # Secrets — add API keys for this feature, e.g.:
    # SetEnv DB_PASS ""
    # SetEnv STRIPE_KEY "sk_test_..."
</VirtualHost>
```

```bash
mkdir -p /usr/local/var/www/qr.food.net
ln -s ~/projects/qr-feature /usr/local/var/www/qr.food.net
brew services restart httpd
```

## Vhost summary

| Domain | EC2 config file | EC2 docroot | Local hostname |
|---|---|---|---|
| food.net | `food.net.conf` | `/var/www/food.net` | `food.net.local:8080` |
| dungeoneer.com | `dungeoneer.com.conf` | `/var/www/dungeoneer.com` | `dungeoneer.com.local:8080` |
| thoughtrights.com | `thoughtrights.com.conf` | `/var/www/thoughtrights.com` | `thoughtrights.com.local:8080` |
| qr.food.net | `qr.food.net.conf` | `/var/www/qr.food.net` | `qr.food.net.local:8080` |
