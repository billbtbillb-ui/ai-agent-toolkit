# DB Migration Skill

> Premium AI Agent Skill -- Safe database schema migration with automatic diff, rollback, and validation

## Overview

Database migrations don't have to be risky. The DB Migration skill compares schemas across environments, detects every difference, and generates safe, reversible migration scripts with built-in validation for breaking changes, lock duration estimates, and data loss warnings.

## Key Features

- Schema comparison -- dev vs staging vs prod, ORM vs live DB
- Auto-diff -- detect tables, columns, indexes, FKs, constraints, views
- Safe migrations -- up/down scripts with transaction safety checks
- Risk scoring -- categorizes changes as Safe/Caution/Dangerous/Breaking
- Lock estimation -- warns about long ACCESS EXCLUSIVE locks
- Multi-database -- PostgreSQL, MySQL/MariaDB, SQLite
- ORM integration -- SQLAlchemy, Django ORM, Prisma

## Quick Start

```bash
# Install
hermes skills install freshtemp-labs/ai-agent-toolkit/db-migration

# Compare schemas
hermes skill run db-migration --source dev-db --target prod-db

# Generate and apply migration
hermes skill run db-migration --apply --backup
```

## Supported Databases

| Database | Version Support | Dialect Features |
|----------|----------------|------------------|
| PostgreSQL | 12, 13, 14, 15, 16 | Full (extensions, BRIN, GIN, PARTITION BY) |
| MySQL/MariaDB | 8.0+ / 10.6+ | Full (except CHECK, partial indexes) |
| SQLite | 3.35+ | Limited (no ALTER COLUMN TYPE, no DROP COLUMN on old versions) |

## Pricing

$9.99 -- One-time purchase, includes all updates.

[Get License](https://ai-agent-toolkit.dev/buy/db-migration)

## License

MIT License -- see [LICENSE](../../LICENSE)
