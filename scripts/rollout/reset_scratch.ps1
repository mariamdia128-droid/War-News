<#
.SYNOPSIS
  Put the SCRATCH casualty-test database back to its saved starting state.

.DESCRIPTION
  Scratch only. Works on the compose project in docker-compose.casualty-test.yml
  (database war_news_casualty_test, host port 5435). It refuses to run if the
  target database has any other name, so it can never touch war_news_dev.

  Default: drop and recreate war_news_casualty_test, restore the saved dump,
  restart the scratch backend and reset the test admin password.
  -RerunScripts: instead of restoring, apply migrations and re-run the four
  casualty data scripts. This does NOT undo resolutions or dismissals made by hand.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\rollout\reset_scratch.ps1
#>
[CmdletBinding()]
param(
    [string]$Dump = "backups\scratch\war_news_casualty_test_baseline.dump",
    [switch]$RerunScripts,
    [string]$Since = "2026-08-17"
)

$ErrorActionPreference = "Stop"
$ScratchDb = "war_news_casualty_test"
$ComposeFile = "docker-compose.casualty-test.yml"

function Fail([string]$Message) { Write-Host "STOP: $Message" -ForegroundColor Red; exit 1 }
function Step([string]$Message) { Write-Host "`n== $Message" -ForegroundColor Cyan }
function Invoke-Checked([scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { Fail "command failed (exit $LASTEXITCODE)" }
}

if (-not (Test-Path $ComposeFile)) { Fail "run this from the repository root ($ComposeFile not found)." }
$composeText = Get-Content -Raw $ComposeFile
if ($composeText -notmatch "POSTGRES_DB:\s*$ScratchDb") { Fail "$ComposeFile does not point at $ScratchDb." }
if ($composeText -notmatch "(?m)^name:\s*war_news_casualty_test\s*$") { Fail "$ComposeFile is not the scratch project." }

$dc = @("compose", "-f", $ComposeFile)
$dbContainer = (& docker @dc ps -q db).Trim()
if (-not $dbContainer) { Fail "the scratch db container is not running. Start it: docker compose -f $ComposeFile up -d db" }

function Get-ScratchDbName {
    $name = (& docker exec $dbContainer psql -U postgres -d $ScratchDb -Atc "select current_database()")
    if ($LASTEXITCODE -ne 0) { return $null }
    return "$name".Trim()
}

Step "Safety check"
$current = Get-ScratchDbName
if ($current -and $current -ne $ScratchDb) { Fail "target database is '$current', not '$ScratchDb'." }
Write-Host "Target database: $ScratchDb (container $dbContainer)"

if ($RerunScripts) {
    if ($current -ne $ScratchDb) { Fail "database $ScratchDb does not exist; use the dump restore instead." }
    Step "Migrations and data scripts (scratch)"
    Invoke-Checked { docker @dc run --rm backend alembic upgrade head }
    foreach ($script in @("casualty_cleanup", "casualty_merge_leak_cleanup", "casualty_status_backfill")) {
        Invoke-Checked { docker @dc run --rm backend python -m "scripts.fixes.$script" --apply }
    }
    Invoke-Checked { docker @dc run --rm backend python -m scripts.fixes.casualty_flags_backfill --since $Since --apply }
    Write-Host "Done. Manual resolutions and dismissals were kept." -ForegroundColor Green
    exit 0
}

if (-not (Test-Path $Dump)) { Fail "dump not found: $Dump" }
if ((Get-Item $Dump).Length -lt 1MB) { Fail "dump $Dump looks empty." }

Step "Stop scratch backend (drops its connections)"
Invoke-Checked { docker @dc stop backend }

Step "Recreate $ScratchDb and restore $Dump"
Invoke-Checked { docker cp $Dump "${dbContainer}:/tmp/scratch_reset.dump" }
Invoke-Checked { docker exec $dbContainer psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $ScratchDb WITH (FORCE)" }
Invoke-Checked { docker exec $dbContainer psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $ScratchDb" }
Invoke-Checked { docker exec $dbContainer pg_restore -U postgres -d $ScratchDb --no-owner --exit-on-error /tmp/scratch_reset.dump }
docker exec $dbContainer rm -f /tmp/scratch_reset.dump | Out-Null
if ((Get-ScratchDbName) -ne $ScratchDb) { Fail "restore did not produce $ScratchDb." }

Step "Start scratch backend"
Invoke-Checked { docker @dc up -d backend }
$healthy = $false
foreach ($i in 1..40) {
    try { if ((Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://localhost:8002/health").StatusCode -eq 200) { $healthy = $true; break } } catch { }
    Start-Sleep -Seconds 3
}
if (-not $healthy) { Fail "scratch backend did not become healthy on http://localhost:8002/health" }

Step "Reset test admin (scratch only)"
$py = @'
from sqlalchemy import text
from app.core.database import SessionLocal
from app.accounts.services.auth_service import password_context
with SessionLocal() as db:
    assert db.execute(text("select current_database()")).scalar() == "war_news_casualty_test"
    db.execute(text("insert into users (username, password_hash, full_name, role_id) values ('casualty_test_admin', :h, 'Casualty Test Admin (scratch only)', 1) on conflict (username) do update set password_hash=excluded.password_hash, failed_login_attempts=0, locked_until=null"), {"h": password_context.hash("CasualtyTest!2026")})
    db.commit()
print("admin ok")
'@
Invoke-Checked { $py | docker @dc exec -T -w /app backend python - }

$summary = docker exec $dbContainer psql -U postgres -d $ScratchDb -Atc "select reason_code||' '||status||' '||count(*) from incident_verification_flags group by reason_code, status order by 1"
Write-Host "Flags now:"; $summary | ForEach-Object { Write-Host "  $_" }
Write-Host "`nScratch reset done. Frontend http://localhost:5175  Backend http://localhost:8002" -ForegroundColor Green
