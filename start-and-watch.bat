@echo off
setlocal EnableExtensions

set "REPO_DIR=C:\Users\User\Desktop\lebanon-news-monitor\War-news"
set "BRANCH=main"
set "PROJECT=war_news_main"
set "ENV_FILE=.env.main"
set "LOG_FILE=%REPO_DIR%\watchdog-main.log"

cd /d "%REPO_DIR%"
if errorlevel 1 (
  echo [%date% %time%] ERROR could not cd to %REPO_DIR%>> "%LOG_FILE%"
  exit /b 1
)

rem This discards local changes in this folder by design. It is a dedicated deploy checkout, never used for editing.
git fetch origin %BRANCH% >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] ERROR git fetch failed for %BRANCH%>> "%LOG_FILE%"
  exit /b 1
)

git reset --hard origin/%BRANCH% >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo [%date% %time%] ERROR git reset failed for origin/%BRANCH%>> "%LOG_FILE%"
  exit /b 1
)

set "NEED_UP=0"
for /f %%A in ('docker compose -p %PROJECT% --env-file %ENV_FILE% config --services ^| find /c /v ""') do set "EXPECTED=%%A"
for /f %%A in ('docker compose -p %PROJECT% --env-file %ENV_FILE% ps --status running --services ^| find /c /v ""') do set "RUNNING=%%A"

if "%EXPECTED%"=="" set "EXPECTED=0"
if "%RUNNING%"=="" set "RUNNING=0"
if not "%EXPECTED%"=="%RUNNING%" set "NEED_UP=1"

if "%NEED_UP%"=="1" (
  rem No alembic upgrade runs here. If the DB schema has drifted from the code, the stack will still come up but the backend may error at runtime until someone runs the migration by hand, per existing convention.
  docker compose -p %PROJECT% --env-file %ENV_FILE% up -d --build >> "%LOG_FILE%" 2>&1
  if errorlevel 1 (
    echo [%date% %time%] ERROR compose up failed project=%PROJECT% expected=%EXPECTED% running=%RUNNING%>> "%LOG_FILE%"
    exit /b 1
  )
  echo [%date% %time%] restarted project=%PROJECT% expected=%EXPECTED% running_before=%RUNNING%>> "%LOG_FILE%"
) else (
  echo [%date% %time%] healthy project=%PROJECT% running=%RUNNING%>> "%LOG_FILE%"
)

exit /b 0
