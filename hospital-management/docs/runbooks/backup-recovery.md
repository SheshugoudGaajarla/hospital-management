# Database Backup and Recovery Runbook

## Scope
- Service: PostgreSQL (`postgres` container)
- Database: `hospital_dev`
- Backup format: gzipped SQL dump (`.sql.gz`)

## Backup Location
- Host path: `backups/postgres/`
- File naming: `<db>_<YYYYMMDDTHHMMSSZ>.sql.gz`

## Automated Backup
- Service: `db-backup` in `infra/docker/docker-compose.yml`
- Default schedule: every `86400` seconds (24h)
- Default retention: `14` days

## Start Stack with Backup Service
```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
```

## Trigger Backup Manually
```bash
./scripts/db-backup.sh
```

## Restore Database
```bash
./scripts/db-restore.sh backups/postgres/<backup-file>.sql.gz
```

## Non-interactive Restore
```bash
./scripts/db-restore.sh backups/postgres/<backup-file>.sql.gz --yes
```

## Verification Checklist
1. Confirm backup file exists in `backups/postgres/`
2. Confirm latest file is recent (expected timestamp)
3. Run app smoke checks after restore:
   - `GET /health`
   - login works
   - basic OP/Billing/Reports pages load

## RPO / RTO Targets (Baseline)
- RPO target: up to 24 hours (daily backup interval)
- RTO target: 30-60 minutes (restore + app validation)

## Notes
- Restore process replaces current DB schema/data.
- Run restore during maintenance window.
