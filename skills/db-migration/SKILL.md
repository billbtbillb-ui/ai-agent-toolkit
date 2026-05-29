---
name: db-migration
description: Database migration assistant -- compares database schemas (PostgreSQL, MySQL, SQLite), detects drift, generates safe migration scripts with rollback, and validates against breaking changes.
version: 1.0.0
author: AI Agent Toolkit
license: MIT
tags: [database, migration, schema, postgresql, mysql, sqlite, alembic, flyway]
platforms: [linux, macos]
metadata:
  hermes:
    category: devops
    pricing: paid
---

# DB Migration -- Schema Comparison & Migration Script Generator

Compares database schemas across environments (dev/staging/prod), ORM models vs live database, or git history. Generates safe, reversible migration scripts with validation for breaking changes. Supports PostgreSQL, MySQL/MariaDB, and SQLite.

## Triggers

- User says "migrate database", "schema diff", "generate migration"
- User mentions "database drift", "schema out of sync"
- User wants to compare dev vs prod schema
- User has ORM models that need database migration

## Steps

### 1. Connect to Databases

```bash
# Compare two live databases
python3 scripts/migrate.py --source postgresql://user:pass@dev-db/mydb \
                           --target postgresql://user:pass@prod-db/mydb

# Compare ORM models (SQLAlchemy) vs live database
python3 scripts/migrate.py --orm ./models/ --target postgresql://localhost/mydb

# Compare schema files (SQL export)
python3 scripts/migrate.py --source-file schema_v1.sql --target-file schema_v2.sql
```

### 2. Schema Analysis

The tool extracts from each source:
- **Tables**: name, columns (type, nullable, default, constraints)
- **Indexes**: unique, composite, partial, expression-based
- **Foreign keys**: references, ON DELETE/UPDATE cascade rules
- **Check constraints**: validation rules
- **Sequences**: current value, increment, min/max
- **Views**: materialized vs regular, definition SQL
- **Functions/Triggers**: language, body, volatility
- **Extensions**: PostGIS, pgcrypto, etc.

### 3. Diff Detection

Identifies all differences, categorized by risk:

| Risk | Changes |
|------|---------|
| **Safe** | ADD COLUMN (nullable), CREATE INDEX, ADD EXTENSION |
| **Caution** | ADD COLUMN (NOT NULL with default), ADD FOREIGN KEY |
| **Dangerous** | DROP COLUMN, RENAME COLUMN, CHANGE TYPE, DROP TABLE |
| **Breaking** | REMOVE NOT NULL, DROP CONSTRAINT (with data risk) |

### 4. Migration Script Generation

Generates both UP and DOWN (rollback) scripts:

```sql
-- Migration: 20260518_add_user_preferences.sql
-- UP --
BEGIN;

-- Safe: add nullable column with default
ALTER TABLE users
    ADD COLUMN preferences JSONB DEFAULT '{}'::jsonb;

-- Caution: add foreign key
ALTER TABLE orders
    ADD COLUMN promo_code_id INTEGER
    REFERENCES promo_codes(id)
    ON DELETE SET NULL;

-- Create index for new queries
CREATE INDEX idx_users_preferences_gin
    ON users USING GIN (preferences);

COMMIT;

-- DOWN --
BEGIN;
DROP INDEX IF EXISTS idx_users_preferences_gin;
ALTER TABLE orders DROP COLUMN IF EXISTS promo_code_id;
ALTER TABLE users DROP COLUMN IF EXISTS preferences;
COMMIT;
```

### 5. Validation & Safety Checks

Before applying:
- **Breaking change detection**: warns about DROP COLUMN, type changes
- **Data loss estimation**: estimates rows affected by destructive changes
- **Lock duration estimate**: warns about long ACCESS EXCLUSIVE locks
- **Downtime estimation**: categorizes migrations by required downtime
- **Idempotency check**: ensures migration can be safely re-run
- **Transaction safety**: flags operations that can't run in transactions (CREATE INDEX CONCURRENTLY, VACUUM)

### 6. Apply Migration

```bash
# Preview migration (dry run)
python3 scripts/migrate.py --apply --dry-run

# Apply with automatic backup
python3 scripts/migrate.py --apply --backup

# Apply with confirmation prompt for dangerous changes
python3 scripts/migrate.py --apply --interactive

# Rollback last migration
python3 scripts/migrate.py --rollback
```

## Configuration

```yaml
# .db-migration.yaml
environments:
  development:
    url: postgresql://localhost:5432/myapp_dev
  staging:
    url: postgresql://staging-db:5432/myapp_staging
  production:
    url: ${DATABASE_URL}
    ssl: require

# ORM model paths
orm:
  - ./models/user.py
  - ./models/order.py

# Migration output
migrations_dir: ./migrations/

# Safety checks
safety:
  require_backup: true
  require_review_for: [Dangerous, Breaking]
  max_lock_duration_seconds: 30
```

## Pitfalls

- **Always backup before applying in production** -- the tool auto-backups with `--backup` flag.
- **RENAME COLUMN in PostgreSQL** renames only; any dependent views/functions break silently. Use CASCADE detection.
- **MySQL ALTER TABLE copies entire table** for some operations (old versions). Check MySQL version and disk space.
- **DEFAULT values on large tables** (PostgreSQL 10 and earlier) rewrite the entire table. Use batched updates instead.
- **Foreign key locks**: adding a FK with ON DELETE CASCADE may lock the referenced table. Check lock levels.
- **Don't mix DDL and DML in migrations** -- separate schema changes from data migrations.
- **Sequence gaps after rollback** -- rolling back doesn't reclaim sequence values. Document this.

## Verification

1. `--dry-run` output shows exact SQL that will execute
2. `--validate` checks for syntax errors and constraint violations
3. Rollback scripts are tested (when possible with `--test-rollback`)
4. Migration runs in a transaction (or explicitly documents why not)
5. Breaking changes are flagged with estimated impact

## Scripts

- `scripts/migrate.py` -- Main orchestrator: connect, diff, generate, apply
- `scripts/schema_extractor.py` -- Extract schema from live databases
- `scripts/diff_engine.py` -- Compare and categorize schema differences
- `scripts/sql_generator.py` -- Generate dialect-specific migration SQL
