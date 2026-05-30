# Databases

## Naming Convention

| Vhost | Local DB name | RDS DB name | Test DB name |
|---|---|---|---|
| food.net | `foodnet` | `foodnet` | `test_foodnet` |
| dungeoneer.com | `dungeoneer` | `dungeoneer` | `test_dungeoneer` |
| thoughtrights.com | `thoughtrights` | `thoughtrights` | `test_thoughtrights` |

Feature repos that need their own isolated schema use a table prefix rather than a separate DB:
e.g. `qr_` prefix for the QR code feature within `foodnet`.

## Local MySQL (MacBook)

Assumes MySQL installed via Homebrew:
```bash
brew install mysql
brew services start mysql
```

No root password by default in dev. Create vhost DBs once:
```bash
mysql -u root -e "CREATE DATABASE IF NOT EXISTS foodnet;"
mysql -u root -e "CREATE DATABASE IF NOT EXISTS dungeoneer;"
mysql -u root -e "CREATE DATABASE IF NOT EXISTS thoughtrights;"
```

Test DBs are created/destroyed by pytest fixtures (see references/unit-testing.md).

## EC2 / RDS Connection

RDS credentials are stored as environment variables in Apache's vhost config on EC2
(never in the repo). See references/env-vars.md for the full list.

RDS security group must allow inbound MySQL (3306) from the EC2 instance's private IP only.

## schema.sql conventions

- Always include `IF NOT EXISTS` on `CREATE TABLE`
- Always include a `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` column
- Foreign keys optional but preferred for relational data
- Include a `DROP TABLE IF EXISTS` block commented out at the top for easy reset

```sql
-- Uncomment to reset:
-- DROP TABLE IF EXISTS my_table;

CREATE TABLE IF NOT EXISTS my_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Applying schema

```bash
# Local
mysql -u root foodnet < schema.sql

# EC2 (run after deploy if schema changed)
mysql -h <RDS_HOST> -u <RDS_USER> -p<RDS_PASS> foodnet < schema.sql
```
