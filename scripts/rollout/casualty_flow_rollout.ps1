<#
.SYNOPSIS
  Roll the casualty verification flow out to the REAL War News database, step by step.

.DESCRIPTION
  Run from the repository root on the machine that hosts the real Docker stack
  (docker-compose.yml, project "war-news"). Every step asks before it changes anything,
  and the script stops at the first failure. See Docs/recon/casualty_flow_rollout_runbook.md.

  Steps: 0 preflight, 1 backup, 2 stop writers, 3 build, 4 migrate, 5 data scripts,
  6 start + post-checks, 7 feature-flag instructions, 8 rollback instructions.

  -DryRunOnly: preflight, build, and the four data scripts in dry-run mode (no --apply).
  No database write, no service stopped, no migration. Use it first and check the numbers.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\rollout\casualty_flow_rollout.ps1 -DryRunOnly
  powershell -ExecutionPolicy Bypass -File scripts\rollout\casualty_flow_rollout.ps1
#>
[CmdletBinding()]
param(
    [switch]$DryRunOnly,
    [string]$Since = "2026-08-17",
    [string]$ExpectedDb = "war_news_dev",
    [string]$RollbackRevision = "",
    [int]$MinFreeGb = 5
)

# "Continue": in Windows PowerShell 5.1, "Stop" turns any native stderr line (docker progress
# output) into a terminating error. Every native call is checked through $LASTEXITCODE instead.
$ErrorActionPreference = "Continue"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = Join-Path "backups" "casualty_rollout_$Stamp"
$script:CurrentStep = "start"
$script:StoppedServices = @()
$script:BackupFile = $null
$script:Applied = $false

# Services that must keep running (or are restarted explicitly) during the rollout.
$KeepRunning = @("db", "redis")
$AppServices = @("backend", "frontend")

# Files owned by the casualty-flow work (Docs/recon/casualty_flow_manifest.md).
$ManifestPaths = @(
    "app/news/services/incident_details/casualty_count_fill.py",
    "app/news/services/incident_details/casualty_status.py",
    "app/news/services/incident_details/casualty_merge_guard.py",
    "app/news/services/casualty_flag_evaluator.py",
    "app/news/services/verification_flag_service.py",
    "app/news/repositories/incident_verification_flag_repository.py",
    "app/news/repositories/incident_repository.py",
    "app/news/services/materialization/incident_materialization_service.py",
    "app/news/services/extraction/tier2_detail_fill_service.py",
    "app/news/services/reconciliation/bulletin_reconciliation_service.py",
    "app/news/dtos/incident_dto.py",
    "app/api/verification_flags_router.py",
    "app/api/incidents_router.py",
    "app/api/router.py",
    "app/core/config.py",
    "alembic/migration/20260928_",
    "scripts/fixes/casualty_",
    "scripts/recon/casualty_flow_invariants.py",
    "frontend/src/features/casualtyChecks/",
    "frontend/src/features/news/",
    "frontend/src/app/routes.tsx",
    "frontend/src/app/AppShell.tsx",
    "tests/test_casualty_",
    "tests/test_verification_flags_api.py",
    "tests/test_incident_visible_verification_flags.py"
)
$AppPaths = @("app", "alembic", "scripts/fixes", "requirements.txt", "frontend/src", "frontend/package.json", "frontend/package-lock.json")

function Write-Step([string]$Name) {
    $script:CurrentStep = $Name
    Write-Host ""
    Write-Host ("=" * 78) -ForegroundColor DarkCyan
    Write-Host "STEP $Name" -ForegroundColor Cyan
    Write-Host ("=" * 78) -ForegroundColor DarkCyan
}
function Write-Info([string]$Text) { Write-Host "  $Text" }
function Write-Warn([string]$Text) { Write-Host "  WARNING: $Text" -ForegroundColor Yellow }
function Hide-Secrets([string]$Text) {
    if (-not $Text) { return $Text }
    $masked = $Text -replace '(://[^:/@\s]+:)[^@\s]+@', '$1***@'
    return ($masked -replace '(?i)(password|secret|api_key|token)(\s*[=:]\s*)\S+', '$1$2***')
}
function Stop-Rollout([string]$Reason) { throw $Reason }

function Confirm-Continue([string]$Question) {
    $answer = Read-Host "  $Question [y/N]"
    if ($answer -notin @("y", "Y", "yes", "YES")) { Stop-Rollout "stopped by operator at: $Question" }
}
function Confirm-Yes([string]$Question) {
    $answer = Read-Host "  $Question Type YES to continue"
    if ($answer -cne "YES") { Stop-Rollout "stopped by operator at: $Question" }
}

function Invoke-Native {
    param([string]$Label, [scriptblock]$Command, [switch]$Quiet)
    $output = & $Command 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    if (-not $Quiet) { $output | ForEach-Object { Write-Host ("    " + (Hide-Secrets $_)) } }
    if ($code -ne 0) {
        if ($Quiet) { $output | Select-Object -Last 20 | ForEach-Object { Write-Host ("    " + (Hide-Secrets $_)) } }
        Stop-Rollout "$Label failed (exit $code)"
    }
    return $output
}

function Read-DotEnv {
    $values = @{}
    if (-not (Test-Path ".env")) { return $values }
    foreach ($line in Get-Content ".env") {
        if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
        $key, $value = $line -split '=', 2
        $values[$key.Trim()] = $value.Trim().Trim('"').Trim("'")
    }
    return $values
}

function Invoke-Sql([string]$Sql) {
    $out = $Sql | docker compose exec -T db psql -U $script:DbUser -d $script:DbName -At -v ON_ERROR_STOP=1 -f - 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { $out | ForEach-Object { Write-Host "    $_" }; Stop-Rollout "SQL failed: $Sql" }
    return $out
}

function Get-Fingerprint {
    # Changes whenever a casualty field, a flag or an audit row changes.
    return (Invoke-Sql @"
SELECT (SELECT count(*) FROM incident_updates) || '|' ||
       (SELECT md5(coalesce(string_agg(id::text || coalesce(deaths::text,'') || '/' || coalesce(injuries::text,'') || '/' ||
               coalesce(total_deaths::text,'') || '/' || coalesce(total_injuries::text,'') || '/' || coalesce(casualty_status,'') || '/' ||
               coalesce(casualty_deaths_status,'') || '/' || coalesce(casualty_injuries_status,''), ',' ORDER BY id), '')) FROM incidents) || '|' ||
       (SELECT md5(coalesce(string_agg(id::text || status || coalesce(updated_at::text,''), ',' ORDER BY id), '')) FROM incident_verification_flags);
"@) -join ""
}

function Show-Counts([string]$Label) {
    Write-Info "$Label"
    Invoke-Sql "SELECT '    flags ' || reason_code || ' ' || status || ': ' || count(*) FROM incident_verification_flags GROUP BY reason_code, status ORDER BY reason_code, status;" | ForEach-Object { Write-Host $_ }
    $nv = Invoke-Sql @"
SELECT count(*) FROM incidents i WHERE NOT i.is_deleted AND (
  (i.verification_status = 'needs_verification' AND i.duplicate_flag)
  OR EXISTS (SELECT 1 FROM incident_verification_flags f WHERE f.incident_id = i.id AND f.status = 'open'
             AND f.flag_type = 'casualty_check' AND (f.visible_after IS NULL OR f.visible_after <= now())));
"@
    Write-Info "  incidents visibly needs-verification: $nv"
}

function Invoke-DataScript([string]$Module, [string[]]$ScriptArgs, [switch]$Apply, [string]$Tag) {
    $name = "casualty_rollout_${Tag}_$Stamp"
    $runArgs = @("compose", "run", "--no-deps", "--name", $name, "-e", "CASUALTY_FLAG_GRACE_MINUTES=0", "backend", "python", "-m", "scripts.fixes.$Module") + $ScriptArgs
    if ($Apply) { $runArgs += "--apply" }
    $output = & docker @runArgs 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $target = Join-Path $BackupDir $Tag
    New-Item -ItemType Directory -Force -Path $target -ErrorAction Stop | Out-Null
    & docker cp "${name}:/app/scripts/fixes/out/." $target 2>&1 | Out-Null
    & docker rm -f $name 2>&1 | Out-Null
    $output | Set-Content -Encoding utf8 (Join-Path $target "output.txt")
    $summary = $output | Where-Object { $_ -match '^(planned|processed|apply:|flag_changes|csv:|skipped|per_day|peak|count_missing_with|would|opened|summary|total|by_)' -or $_ -match 'csv=' }
    if (-not $summary) { $summary = $output | Select-Object -Last 12 }
    $summary | ForEach-Object { Write-Host ("    " + (Hide-Secrets $_)) }
    Write-Info "full output and CSV files: $target"
    if ($code -ne 0) { $output | Select-Object -Last 20 | ForEach-Object { Write-Host "    $_" }; Stop-Rollout "$Module failed (exit $code)" }
}

function Show-Rollback {
    $target = $RollbackRevision
    if (-not $target) { $target = $script:DbRevisionBefore }
    if (-not $target) { $target = "<revision before the rollout>" }
    $dump = $script:BackupFile
    if (-not $dump) { $dump = "backups\casualty_rollout_<timestamp>\$($script:DbName)_before.dump" }
    Write-Host @"

ROLLBACK OPTIONS (run from the repository root; nothing below runs automatically)

A. Full restore from the backup (undoes schema AND data; loses every write made after the backup,
   including news ingested after the backup if the workers were running):

   docker compose stop $(($script:WriterServices + $AppServices) -join ' ')
   docker compose cp "$dump" db:/tmp/restore.dump
   docker compose exec -T db psql -U $($script:DbUser) -d postgres -c "DROP DATABASE $($script:DbName) WITH (FORCE)"
   docker compose exec -T db psql -U $($script:DbUser) -d postgres -c "CREATE DATABASE $($script:DbName)"
   docker compose exec -T db pg_restore -U $($script:DbUser) -d $($script:DbName) --no-owner --exit-on-error /tmp/restore.dump
   git checkout <previous commit>  ;  docker compose build  ;  docker compose up -d

B. Schema-only rollback to $target (the revision before this rollout unless -RollbackRevision
   is given; keeps news written since). Going back to 20260928_0071 only drops the 0072 index.
   Going back before 20260928_0070 drops incident_verification_flags (every flag, resolution and
   dismissal is lost). Count changes made by the cleanup scripts STAY in incidents either way:

   docker compose stop $(($script:WriterServices + $AppServices) -join ' ')
   docker compose run --rm --no-deps backend alembic downgrade $target
   git checkout <previous commit>  ;  docker compose build  ;  docker compose up -d

   Note: this also downgrades migrations that are not part of the casualty work
   (20260924_0063..0067 pipeline columns, 20260928_0068 merge). Code older than those needs that.
"@ -ForegroundColor Yellow
}

try {
    # ---------------------------------------------------------------- STEP 0
    Write-Step "0  Preflight (read only)"
    foreach ($required in @("docker-compose.yml", "alembic.ini", ".env", "app", "alembic\migration")) {
        if (-not (Test-Path $required)) { Stop-Rollout "run from the repository root ($required not found)" }
    }
    if (Test-Path "docker-compose.casualty-test.yml") { Write-Info "scratch compose file present; this script only uses docker-compose.yml" }

    $envValues = Read-DotEnv
    $script:DbName = $envValues["POSTGRES_DB"]
    $script:DbUser = $envValues["POSTGRES_USER"]
    if (-not $script:DbName -or -not $script:DbUser) { Stop-Rollout "POSTGRES_DB / POSTGRES_USER missing in .env" }
    Write-Info ("DATABASE_URL (masked): " + (Hide-Secrets $envValues["DATABASE_URL"]))
    Write-Info "POSTGRES_DB=$($script:DbName)  POSTGRES_USER=$($script:DbUser)  POSTGRES_PASSWORD=***"
    if ($script:DbName -ne $ExpectedDb) { Stop-Rollout "POSTGRES_DB is '$($script:DbName)', expected '$ExpectedDb' (pass -ExpectedDb if that is intended)" }
    if ($script:DbName -eq "war_news_casualty_test") { Stop-Rollout "this is the scratch database; use reset_scratch.ps1 there" }

    $branch = (Invoke-Native "git branch" { git rev-parse --abbrev-ref HEAD } -Quiet) -join ""
    $commit = (Invoke-Native "git log" { git log -1 --format="%h %s" } -Quiet) -join ""
    Write-Info "branch: $branch   commit: $commit"

    $status = Invoke-Native "git status" { git status --porcelain } -Quiet | Where-Object { $_ }
    $ours = @(); $others = @()
    foreach ($line in $status) {
        $path = $line.Substring(3) -replace '^.* -> ', '' -replace '"', ''
        if ($ManifestPaths | Where-Object { $path.StartsWith($_) }) { $ours += $line } else { $others += $line }
    }
    if ($ours.Count -gt 0) {
        Write-Warn "uncommitted files from the casualty-flow manifest:"
        $ours | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
        Stop-Rollout "commit the casualty-flow files first (images are built from the working tree)"
    }
    if ($others.Count -gt 0) {
        Write-Warn "other uncommitted or untracked files (not part of the casualty flow):"
        $others | Select-Object -First 40 | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
        Confirm-Yes "These will be ignored for the rollout checks."
    }

    $dbId = (Invoke-Native "docker compose ps" { docker compose ps -q db } -Quiet) -join ""
    if (-not $dbId) { Stop-Rollout "the real db container is not running (docker compose ps -q db is empty)" }
    Write-Info "real stack containers:"
    Invoke-Native "docker compose ps" { docker compose ps --format "table {{.Service}}\t{{.Name}}\t{{.Status}}" } | Out-Null

    $script:WriterServices = @(Invoke-Native "docker compose config" { docker compose config --services } -Quiet |
        Where-Object { $_ -and ($KeepRunning -notcontains $_) -and ($AppServices -notcontains $_) })
    Write-Info ("writer services (stopped in step 2): " + ($script:WriterServices -join ", "))

    $drive = (Get-Item . -ErrorAction Stop).PSDrive
    $dbSize = (Invoke-Sql "SELECT pg_size_pretty(pg_database_size(current_database())) || ' (' || pg_database_size(current_database()) || ' bytes)';") -join ""
    if ($null -eq $drive.Free) {
        Write-Warn "free space on $($drive.Name): unknown (network drive); database size: $dbSize"
        Confirm-Continue "Check free space by hand (need about 2x the database size). Enough space?"
    } else {
        $freeGb = [math]::Round($drive.Free / 1GB, 1)
        Write-Info "free space on $($drive.Name): ${freeGb} GB; database size: $dbSize"
        if ($freeGb -lt $MinFreeGb) { Stop-Rollout "less than $MinFreeGb GB free for the backup" }
    }
    Invoke-Native "docker system df" { docker system df } | Out-Null

    $current = (Invoke-Sql "SELECT current_database();") -join ""
    if ($current -ne $ExpectedDb) { Stop-Rollout "current_database() is '$current', expected '$ExpectedDb'" }
    Write-Info "current_database(): $current"
    Write-Info ("incidents: " + ((Invoke-Sql "SELECT count(*) FROM incidents;") -join "") + "   raw_messages: " + ((Invoke-Sql "SELECT count(*) FROM raw_messages;") -join ""))
    $dbRevision = (Invoke-Sql "SELECT version_num FROM alembic_version;") -join ","
    $script:DbRevisionBefore = $dbRevision
    Write-Info "database revision: $dbRevision"

    $migrationFiles = Get-ChildItem "alembic\migration\*.py" | ForEach-Object { Get-Content -Raw $_.FullName }
    $revisions = @(); $downs = @(); $parents = @{}
    foreach ($text in $migrationFiles) {
        if ($text -notmatch '(?m)^revision\s*(?::[^=\r\n]*)?=\s*["'']([^"'']+)["'']') { continue }
        $rev = $Matches[1]; $revisions += $rev
        $block = [regex]::Match($text, '(?ms)^down_revision\s*(?::[^=\r\n]*)?=\s*(.+?)^\S').Groups[1].Value
        $parents[$rev] = @([regex]::Matches($block, '["'']([^"'']+)["'']') | ForEach-Object { $_.Groups[1].Value })
        $downs += $parents[$rev]
    }
    $heads = @($revisions | Where-Object { $downs -notcontains $_ })
    Write-Info ("alembic heads from code: " + ($heads -join ", "))
    if ($heads.Count -ne 1) { Stop-Rollout "code has $($heads.Count) alembic heads; expected exactly one" }
    $script:CodeHead = $heads[0]

    # What "alembic upgrade head" will apply from the database's own revision.
    function Get-Ancestors([string]$Start) {
        $seen = @{}; $queue = New-Object System.Collections.Queue; $queue.Enqueue($Start)
        while ($queue.Count -gt 0) {
            $rev = $queue.Dequeue()
            if ($seen.ContainsKey($rev)) { continue }
            $seen[$rev] = $true
            foreach ($parent in @($parents[$rev])) { if ($parent) { $queue.Enqueue($parent) } }
        }
        return $seen
    }
    foreach ($rev in ($dbRevision -split ',')) {
        if (-not $parents.ContainsKey($rev)) { Stop-Rollout "database revision '$rev' is not in this code's migrations (database newer than the code?)" }
    }
    $applied = @{}
    foreach ($rev in ($dbRevision -split ',')) { (Get-Ancestors $rev).Keys | ForEach-Object { $applied[$_] = $true } }
    $script:Pending = @((Get-Ancestors $script:CodeHead).Keys | Where-Object { -not $applied.ContainsKey($_) } | Sort-Object)
    Write-Info "database revision: $dbRevision   code head: $($script:CodeHead)"
    if ($script:Pending.Count -eq 0) {
        Write-Info "database is already at the code head; step 4 will be skipped"
    } else {
        Write-Info ("upgrade head will apply $($script:Pending.Count) revision(s): " + ($script:Pending -join ", "))
    }

    # Casualty flag objects that may already exist on a partly migrated database.
    $flagTable = (Invoke-Sql "SELECT to_regclass('public.incident_verification_flags') IS NOT NULL;") -join ""
    if ($flagTable -eq "t") {
        Write-Info ("incident_verification_flags exists; rows by status: " + ((Invoke-Sql "SELECT coalesce(string_agg(status || '=' || n, ', '), 'none') FROM (SELECT status, count(*) n FROM incident_verification_flags GROUP BY status) s;") -join ""))
        Write-Info ("indexes: " + ((Invoke-Sql "SELECT string_agg(indexname, ', ' ORDER BY indexname) FROM pg_indexes WHERE tablename = 'incident_verification_flags';") -join ""))
        $newIndex = (Invoke-Sql "SELECT count(*) FROM pg_indexes WHERE indexname = 'ix_incident_verification_flags_incident_status_visible_after';") -join ""
        if ($script:Pending -contains "20260928_0072" -and $newIndex -ne "0") {
            Stop-Rollout "index ix_incident_verification_flags_incident_status_visible_after already exists but 20260928_0072 is pending; check how it was created before upgrading"
        }
        Write-Info "existing flags are kept: the flags backfill updates or reuses open flags and never reopens resolved/dismissed ones"
    } else {
        Write-Info "incident_verification_flags does not exist yet (created by 20260928_0070)"
    }

    # ---------------------------------------------------------------- STEP 3 (build) in dry-run mode
    if ($DryRunOnly) {
        Write-Step "3  Build images from the committed code (dry-run mode: running services are not recreated)"
        Confirm-Continue "Build the images now?"
        Invoke-Native "docker compose build" { docker compose build } -Quiet | Out-Null
        Write-Info "images built; running containers keep their old image until step 6 of a real run"

        Write-Step "5  Data scripts, dry-run only (no --apply)"
        $hasColumns = (Invoke-Sql "SELECT count(*) FROM information_schema.columns WHERE table_name = 'incident_verification_flags' AND column_name = 'visible_after';") -join ""
        if ($hasColumns -ne "1") {
            Write-Warn "the casualty tables are not migrated yet on this database; dry-runs need step 4 first. Skipped."
        } else {
            New-Item -ItemType Directory -Force -Path $BackupDir -ErrorAction Stop | Out-Null
            Invoke-DataScript "casualty_cleanup" @() -Tag "dry_1_cleanup"
            Invoke-DataScript "casualty_merge_leak_cleanup" @() -Tag "dry_2_merge_leak"
            Invoke-DataScript "casualty_status_backfill" @() -Tag "dry_3_status"
            Invoke-DataScript "casualty_flags_backfill" @("--since", $Since) -Tag "dry_4_flags"
            Write-Info "Each dry-run reads the current data; later scripts do not see the earlier scripts' changes yet."
        }
        Show-Counts "current counts (unchanged):"
        Write-Host "`nDry run finished. No database write, no service stopped, no migration." -ForegroundColor Green
        exit 0
    }

    Confirm-Continue "Preflight passed. Continue to the backup?"

    # ---------------------------------------------------------------- STEP 1
    Write-Step "1  Backup (pg_dump, custom format)"
    New-Item -ItemType Directory -Force -Path $BackupDir -ErrorAction Stop | Out-Null
    $dumpName = "$($script:DbName)_before.dump"
    Invoke-Native "pg_dump" { docker compose exec -T db pg_dump -U $script:DbUser -d $script:DbName -Fc -f "/tmp/$dumpName" } | Out-Null
    Invoke-Native "docker cp" { docker compose cp "db:/tmp/$dumpName" (Join-Path $BackupDir $dumpName) } -Quiet | Out-Null
    $script:BackupFile = (Resolve-Path (Join-Path $BackupDir $dumpName) -ErrorAction Stop).Path
    $size = (Get-Item $script:BackupFile).Length
    if ($size -lt 1MB) { Stop-Rollout "backup $($script:BackupFile) is empty or too small ($size bytes)" }
    $toc = Invoke-Native "pg_restore --list" { docker compose exec -T db pg_restore --list "/tmp/$dumpName" } -Quiet
    $tableData = @($toc | Where-Object { $_ -match 'TABLE DATA' }).Count
    if ($tableData -lt 10) { Stop-Rollout "pg_restore --list shows only $tableData table-data entries" }
    Invoke-Native "cleanup" { docker compose exec -T db rm -f "/tmp/$dumpName" } -Quiet | Out-Null
    Write-Info ("backup: $($script:BackupFile)  size: {0:N1} MB  table-data entries: $tableData" -f ($size / 1MB))
    Write-Info "suggestion: add 'backups/' to .gitignore (this script does not edit it)"
    Confirm-Continue "Backup verified. Stop the writer services?"

    # ---------------------------------------------------------------- STEP 2
    Write-Step "2  Stop writers"
    $toStop = @($script:WriterServices + $AppServices)
    Invoke-Native "docker compose stop" { docker compose stop @toStop } | Out-Null
    $script:StoppedServices = $toStop
    Write-Info ("stopped: " + ($toStop -join ", ") + "   (db and redis keep running)")
    $clients = Invoke-Sql "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid();"
    Write-Info "other connections to the database now: $($clients -join '')"

    # ---------------------------------------------------------------- STEP 3
    Write-Step "3  Build images from the committed code"
    $dirtyApp = Invoke-Native "git status" { git status --porcelain -- @AppPaths } -Quiet | Where-Object { $_ }
    if ($dirtyApp) {
        Write-Warn "the working tree differs from the commit for application paths; the image will contain these changes:"
        $dirtyApp | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
        Confirm-Yes "Build anyway?"
    }
    Invoke-Native "docker compose build" { docker compose build } -Quiet | Out-Null
    Write-Info "images built from $commit"
    $imageHeads = @(Invoke-Native "alembic heads" { docker compose run --rm --no-deps backend alembic heads } -Quiet | Where-Object { $_ -match '\(head\)' })
    Write-Info ("alembic heads in the new image: " + ($imageHeads -join ", "))
    if ($imageHeads.Count -ne 1 -or $imageHeads[0] -notmatch [regex]::Escape($script:CodeHead)) { Stop-Rollout "the new image does not have exactly one head '$($script:CodeHead)'" }

    # ---------------------------------------------------------------- STEP 4
    Write-Step "4  Migrate (alembic upgrade head)"
    if ($script:Pending.Count -eq 0) {
        Write-Info "SKIPPED: database is already at the code head $($script:CodeHead); nothing to migrate."
    } else {
    Write-Info ("revisions to apply from ${dbRevision}: " + ($script:Pending -join ", "))
    $before = (Invoke-Native "alembic current" { docker compose run --rm --no-deps backend alembic current } -Quiet | Where-Object { $_ -match '^\w' -and $_ -notmatch '^INFO' }) -join ", "
    Write-Info "current: $before"
    Write-Info "pending revisions:"
    Invoke-Native "alembic history" { docker compose run --rm --no-deps backend alembic history -r "$($dbRevision):head" } | Out-Null
    if ($script:Pending | Where-Object { $_ -lt "20260928_0069" }) {
        Write-Info "Some pending revisions are not casualty-flow migrations (for example 20260923_0063 cara_d/cara_i,"
        Write-Info "20260924_0063..0067 pipeline columns, 20260928_0068 merge). See the runbook table."
    }
    Confirm-Continue "Apply these migrations?"
    Invoke-Native "alembic upgrade" { docker compose run --rm --no-deps backend alembic upgrade head } | Out-Null
    $after = (Invoke-Sql "SELECT version_num FROM alembic_version;") -join ","
    if ($after -ne $script:CodeHead) { Stop-Rollout "database is at '$after' after upgrade, expected '$($script:CodeHead)'" }
    Write-Info "database revision now: $after"
    }

    # ---------------------------------------------------------------- STEP 5
    Write-Step "5  Data scripts (dry-run, apply, then a second apply that must change nothing)"
    Write-Warn "the first --apply is the point of no return: after it, only a restore from the backup undoes the data changes."
    Show-Counts "before:"
    $scripts = @(
        @{ Module = "casualty_cleanup"; Args = @(); Tag = "1_cleanup" },
        @{ Module = "casualty_merge_leak_cleanup"; Args = @(); Tag = "2_merge_leak" },
        @{ Module = "casualty_status_backfill"; Args = @(); Tag = "3_status" },
        @{ Module = "casualty_flags_backfill"; Args = @("--since", $Since); Tag = "4_flags" }
    )
    foreach ($item in $scripts) {
        Write-Host "`n  --- $($item.Module) $($item.Args -join ' ')" -ForegroundColor Cyan
        Invoke-DataScript $item.Module $item.Args -Tag "$($item.Tag)_dryrun"
        Confirm-Continue "Apply $($item.Module)?"
        Invoke-DataScript $item.Module $item.Args -Apply -Tag "$($item.Tag)_apply"
        $script:Applied = $true
        $print = Get-Fingerprint
        Write-Info "second --apply (must change nothing):"
        Invoke-DataScript $item.Module $item.Args -Apply -Tag "$($item.Tag)_apply_again"
        if ((Get-Fingerprint) -ne $print) { Stop-Rollout "$($item.Module) changed data on its second run (not idempotent)" }
        Write-Info "second run: 0 changes (casualty fields, flags and audit rows identical)"
    }
    Show-Counts "after:"

    # ---------------------------------------------------------------- STEP 6
    Write-Step "6  Start services and post-checks"
    Confirm-Continue "Start all services again?"
    Invoke-Native "docker compose up" { docker compose up -d } | Out-Null
    $script:StoppedServices = @()
    $port = $envValues["BACKEND_HOST_PORT"]; if (-not $port) { $port = "8000" }
    $healthy = $false
    foreach ($i in 1..60) {
        try { if ((Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://localhost:$port/health").StatusCode -eq 200) { $healthy = $true; break } } catch { }
        Start-Sleep -Seconds 3
    }
    if (-not $healthy) { Stop-Rollout "backend did not become healthy on http://localhost:$port/health" }
    Write-Info "backend healthy on http://localhost:$port"
    $listCheck = @'
from app.core.database import SessionLocal
from app.news.dtos.incident_dto import IncidentListParams
from app.news.repositories.incident_repository import IncidentRepository
with SessionLocal() as db:
    repo = IncidentRepository(db)
    for label, params in (("all", IncidentListParams(limit=150)), ("needs_verification", IncidentListParams(limit=150, verification_status="needs_verification"))):
        r = repo.list_all(params)
        print(f"list {label}: total={r.total} page_rows={len(r.items)} needs_card={r.needs_verification_count} casualties_card={r.casualties_count} outside_range={r.needs_verification_outside_range_count}")
'@
    $listOut = $listCheck | docker compose exec -T -w /app backend python - 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { $listOut | Select-Object -Last 15 | ForEach-Object { Write-Host "    $_" }; Stop-Rollout "incidents list query failed" }
    $listOut | Where-Object { $_ -like "list *" } | ForEach-Object { Write-Info $_ }
    Show-Counts "final:"
    Invoke-Native "docker compose ps" { docker compose ps --format "table {{.Service}}\t{{.Status}}" } | Out-Null

    # ---------------------------------------------------------------- STEP 7
    Write-Step "7  Feature flags (manual)"
    Write-Host @"
  Flags created by the backfill are already visible on the Incidents page. The settings below
  only control NEW flags created by the live pipeline. Check the step 5 numbers first, then:

    1. Edit .env and add (or change):
         CASUALTY_FLAGS_ENABLED=true
         CASUALTY_FLAG_GRACE_MINUTES=120
    2. docker compose up -d --force-recreate backend $($script:WriterServices -join ' ')
    3. docker compose exec backend python -c "from app.core.config import settings; print(settings.casualty_flags_enabled, settings.casualty_flag_grace_minutes)"
       should print: True 120
"@

    Write-Step "8  Rollback (for reference)"
    Show-Rollback
    Write-Host "`nRollout finished. Backup: $($script:BackupFile)  Logs and CSVs: $BackupDir" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "FAILED at step $($script:CurrentStep): $($_.Exception.Message)" -ForegroundColor Red
    if ($script:StoppedServices.Count -gt 0) {
        Write-Host "Stopped services are still stopped: $($script:StoppedServices -join ', ')" -ForegroundColor Yellow
        Write-Host "  bring them back: docker compose up -d" -ForegroundColor Yellow
    }
    if ($script:Applied) { Write-Host "At least one --apply ran; data was changed. See rollback option A." -ForegroundColor Yellow }
    if ($script:BackupFile) { Write-Host "Backup: $($script:BackupFile)" -ForegroundColor Yellow }
    if ($script:DbName) { Show-Rollback }
    exit 1
}
