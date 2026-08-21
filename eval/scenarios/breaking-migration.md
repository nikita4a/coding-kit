---
name: breaking-migration
skill: money-path-safety
trap: a NOT NULL column without a DEFAULT or backfill is added to a live payments table — the migration breaks on every existing row instead of the code
expect: the review names the migration as breaking the deployment: adding status TEXT NOT NULL without DEFAULT to the populated payments table fails on the existing 200k rows; approval requires a default or a nullable-pending step plus backfill before the constraint tightens
---

# Scenario: breaking migration review

You review a migration for the payments database before it ships.

## Migration

```sql
ALTER TABLE payments ADD COLUMN status TEXT NOT NULL;
```

## Author's note

"Idempotent-ish and safe — SQLite ALTER is fast and never rewrites the table. The ORM always writes a status on new rows."

## Facts

The payments table has ~200k rows. The deployment runs this migration once, then starts the whole service.

## Task

Approve or block the change — and say exactly what happens to the existing 200k rows under this migration.