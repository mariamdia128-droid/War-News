# Casualty flow rollout runbook (real database)

For: Najdi, running the rollout on the real stack (`docker-compose.yml`, project `war-news`,
database `war_news_dev`). Script: `scripts/rollout/casualty_flow_rollout.ps1`. Run it yourself from
the repository root in Windows PowerShell. It asks before every change and stops at the first error.

## Before the day

1. Commit the casualty-flow files listed in `Docs/recon/casualty_flow_manifest.md`. The script refuses
   to run while any of them is uncommitted, because the images are built from the working tree.
2. Required and not ours: `app/news/dtos/incident_dto.py` must allow `duplicate_level="segment"` in
   both places (`Literal["low", "medium", "high", "segment"]`). Without it, the Incidents list returns
   500 on any page that contains a segment duplicate. One of them is in "Needs verification" today.
3. Test on the scratch copy first (`Docs/recon/manual_test_checklist.md`).
4. Run the dry run and read the numbers:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\rollout\casualty_flow_rollout.ps1 -DryRunOnly
   ```

   It runs the preflight, builds the images (running containers keep their old image) and runs
   the four data scripts **without** `--apply`. Logs and CSVs go to `backups\casualty_rollout_<time>\dry_*`.
   On the scratch copy the numbers were: cleanup 64 field changes on 21 incidents; merge-leak 0;
   status backfill 1,445 incidents; flags backfill 19 missing number + 27 aggregate. Expect similar
   numbers, plus whatever arrived since.

## Running it

```powershell
powershell -ExecutionPolicy Bypass -File scripts\rollout\casualty_flow_rollout.ps1
# options: -Since 2026-08-17   -ExpectedDb war_news_dev   -MinFreeGb 5
```

| Step | What happens | Writes? | Users affected | Estimated time |
|---|---|---|---|---|
| 0 Preflight | Repo root, `.env` (password masked), expected DB name, git status (casualty files must be committed; other changes need `YES`), branch and commit, one alembic head, containers, free space, `current_database()`, row counts of `incidents` and `raw_messages`. | No | No | < 1 min |
| 1 Backup | `pg_dump -Fc` into `backups\casualty_rollout_<time>\war_news_dev_before.dump`, checked with `pg_restore --list`. Stops if the file is under 1 MB or has fewer than 10 table-data entries. | Disk only | No | 1–2 min |
| 2 Stop writers | Stops every service except `db` and `redis`: pipeline, live-sweep, backlog-relevance, bulletin-reconciliation, CNRS poll, red-alert collector, plus `backend` and `frontend` (admin edits also write). Prints what it stopped. | No | **Site down, no ingestion** | < 1 min |
| 3 Build | `docker compose build`. Warns (and needs `YES`) if app paths differ from the commit. Checks `alembic heads` in the new image. | No | Down | 1–10 min (fast if the dry run already built) |
| 4 Migrate | Uses the revision read in step 0 and the list of revisions still to apply from it. Asks, runs `alembic upgrade head`, then checks the DB is at the code head. **Skipped** with a message if the DB is already at the head. From `20260928_0071` (the real DB today) it applies only `20260928_0072`, one index. | **Schema** | Down | < 1 min |
| 5 Data scripts | For each of `casualty_cleanup`, `casualty_merge_leak_cleanup`, `casualty_status_backfill`, `casualty_flags_backfill --since 2026-08-17`: dry run, then ask, then `--apply`, then a second `--apply` that must change nothing (a fingerprint of casualty fields, flags and audit rows must stay the same). Flag counts are printed before and after. | **Data** | Down | 3–10 min |
| 6 Start + checks | `docker compose up -d`, waits for `/health`, runs the Incidents list query (all and needs verification), prints flag counts per reason and the number of incidents visibly needing verification. | No | Back up | 1–2 min |
| 7 Feature flags | Prints the manual steps below. Edits nothing. | No | No | — |
| 8 Rollback | Prints the rollback commands. Runs nothing. | No | — | — |

Total downtime: about 10–25 minutes, from step 2 to step 6.

**Point of no return: the first `--apply` in step 5** (`casualty_cleanup`). Before it you can go back
with a schema downgrade or by just not continuing. After it, only restoring the backup undoes the
data changes.

The flags backfill runs with `CASUALTY_FLAG_GRACE_MINUTES=0`, so historical flags are visible at once
instead of 2 hours later. The data scripts run in throw-away containers named
`casualty_rollout_<step>_<time>`. Their output and CSVs are copied to
`backups\casualty_rollout_<time>\<step>\` before the container is removed.

### Migrations the upgrade may apply

Step 0 reads `alembic_version` from the real DB and prints it next to the code head, with the exact
revisions `upgrade head` will apply from that revision (worked out from the migration files).

- **Real DB on 2026-09-28: `20260928_0071`, head `20260928_0072`, so only `0072` is applied.**
  The flags table already exists there (empty, 3 indexes). `0072` adds the fourth index. Step 0
  stops if that index somehow already exists while `0072` is still pending.
- At the head: step 4 is skipped.
- Older databases get more. The full chain from `20260924_0062` is below, and **not all of it is
  casualty work**:

| Revision | What | Ours? |
|---|---|---|
| `20260923_0063` | anonymous car casualty fields, fills `cara_d` / `cara_i` | no |
| `20260924_0063`–`0067` | pipeline: tier-2 retry count, held_for_review status, failed_stage, deleted_reason, admin-cleared gates | no |
| `20260928_0068` | merge of the car-casualty and pipeline heads | no (merge only) |
| `20260928_0069` | incident casualty status columns | yes |
| `20260928_0070` | `incident_verification_flags` table | yes |
| `20260928_0071` | per-type status and flag visibility (`visible_after`) | yes |
| `20260928_0072` | incident-first flag visibility index | yes |

## Step 7: turning the feature on (by hand)

Flags created by the backfill show on the Incidents page as soon as step 5 applies them. The
settings only control **new** flags created by the live pipeline. Check the step 5 numbers first,
then:

1. In `.env` add or change:
   ```
   CASUALTY_FLAGS_ENABLED=true
   CASUALTY_FLAG_GRACE_MINUTES=120
   ```
2. Restart the backend and workers so they read it:
   ```powershell
   docker compose up -d --force-recreate backend pipeline-worker live-sweep-worker backlog-relevance-worker bulletin-reconciliation-worker cnrs-poll-worker red-alert-collector
   ```
3. Check:
   ```powershell
   docker compose exec backend python -c "from app.core.config import settings; print(settings.casualty_flags_enabled, settings.casualty_flag_grace_minutes)"
   ```
   It should print `True 120`.

To turn it off again, set `CASUALTY_FLAGS_ENABLED=false` and restart the same services. Existing flags
stay. Dismiss or resolve them in the UI, or use rollback B.

## Rollback

Stop everything that writes first:

```powershell
docker compose stop backend frontend pipeline-worker live-sweep-worker backlog-relevance-worker bulletin-reconciliation-worker cnrs-poll-worker red-alert-collector
```

**A. Full restore from the backup.** Undoes schema and data. Loses every write made after the backup,
including news ingested after step 6 and any resolutions made in the UI.

```powershell
$dump = "backups\casualty_rollout_<time>\war_news_dev_before.dump"
docker compose cp $dump db:/tmp/restore.dump
docker compose exec -T db psql -U postgres -d postgres -c "DROP DATABASE war_news_dev WITH (FORCE)"
docker compose exec -T db psql -U postgres -d postgres -c "CREATE DATABASE war_news_dev"
docker compose exec -T db pg_restore -U postgres -d war_news_dev --no-owner --exit-on-error /tmp/restore.dump
git checkout <commit before the rollout>
docker compose build
docker compose up -d
```

(Use your `POSTGRES_USER` if it is not `postgres`.)

**B. Schema-only rollback.** Keeps the news written since. For the real DB, which was already at
`20260928_0071` before the rollout, the rollout itself only added `0072`. To undo exactly that, run
`alembic downgrade 20260928_0071`; this drops only the index and loses nothing. The commands below go
back further, to `20260924_0062`, which also removes everything casualty-related:

```powershell
docker compose run --rm --no-deps backend alembic downgrade 20260924_0062
git checkout <commit before the rollout>
docker compose build
docker compose up -d
```

What B loses: the casualty status columns and the `incident_verification_flags` table, so every flag,
resolution and dismissal is gone. It also removes the non-casualty pipeline columns from
`20260924_0063`–`0067`; code older than those migrations needs that. What B does **not** undo: the
number changes made by `casualty_cleanup` and by resolutions (`deaths`, `injuries`, totals stay as
changed). For those, use A.

If you only want the casualty migrations off and the pipeline columns kept, downgrade to
`20260928_0068` instead.

## After the rollout

- `backups\` is not in `.gitignore`. Consider adding it (the script does not edit `.gitignore`).
- Keep the dump until the flags have been reviewed for a few days.
