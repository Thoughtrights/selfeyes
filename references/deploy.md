# Deployment

## Principles

- **Always deploy via Git**: push to GitHub, then `git pull` on EC2. No rsync.
- **One deploy script per repo** (`deploy.sh` at repo root)
- Deployment does not restart Apache unless config changed
- Schema changes are applied manually after deploy (see below)

## EC2 docroot paths

| Vhost | Apache docroot |
|---|---|
| food.net | `/var/www/food.net/` |
| dungeoneer.com | `/var/www/dungeoneer.com/` |
| thoughtrights.com | `/var/www/thoughtrights.com/` |

Feature repos are cloned into subdirectories:
```
/var/www/food.net/
└── qr/           ← clone of qr-feature repo
└── menu/         ← clone of menu-feature repo
```

Subdomains (e.g. `qr.food.net`) have their own docroot:
```
/var/www/qr.food.net/   ← clone of qr-feature repo
```

## deploy.sh template

```bash
#!/bin/bash
# deploy.sh — run locally on MacBook to deploy this repo to EC2
# Usage: ./deploy.sh [--vhost food.net|dungeoneer.com|thoughtrights.com]

set -e

EC2_USER="ubuntu"
EC2_IP="thoughtrights"           
SSH_KEY="~/.ssh/thoughtrights-2014-07-18.pem"
VHOST="thoughtrights.com"                 # default; override with --vhost
DEPLOY_PATH="my-feature"         # path under vhost docroot

# Parse args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --vhost) VHOST="$2"; shift ;;
    esac
    shift
done

REMOTE_DIR="/var/www/$VHOST/$DEPLOY_PATH"

echo "==> Pushing to GitHub..."
git push origin main

echo "==> Pulling on EC2: $REMOTE_DIR"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" "
    cd $REMOTE_DIR &&
    git pull origin main &&
    sudo chown -R www-data:www-data . &&
    sudo chmod -R 755 . &&
    find . -name '*.api' -exec chmod +x {} \;
    echo 'Deploy complete.'
"

echo "==> Smoke test..."
curl -sf "https://$VHOST/$DEPLOY_PATH/health.api" && echo " OK" || echo " FAILED"
```

Make executable: `chmod +x deploy.sh`

## First-time EC2 repo setup (run once per repo)

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP>
cd /var/www/food.net/
git clone git@github.com:USERNAME/my-feature.git my-feature
sudo chown -R www-data:www-data my-feature
find my-feature -name "*.api" -exec chmod +x {} \;
```

GitHub SSH key must be configured on the EC2 instance (`~/.ssh/id_ed25519` added to GitHub).

## Applying schema changes on EC2

After a deploy that includes schema changes, run manually:

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP>
mysql -h <RDS_HOST> -u <RDS_USER> -p<RDS_PASS> foodnet < /var/www/food.net/my-feature/schema.sql
```

## Apache config changes

Only needed when adding a new vhost, subdomain, or `Alias`. After editing:

```bash
sudo apache2ctl configtest   # verify syntax
sudo systemctl reload apache2
```

## Troubleshooting

| Symptom | Check |
|---|---|
| 500 on `.api` | `sudo tail /var/log/apache2/error.log` |
| 403 Forbidden | File permissions: `chmod +x *.api`, `chown www-data` |
| 404 | Apache `Alias` config, confirm repo path matches |
| DB connection error | EC2 env vars in vhost config, RDS security group |
| Old code still running | Did `git pull` actually update? `git log --oneline -3` |
