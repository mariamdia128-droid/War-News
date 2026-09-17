$ErrorActionPreference = "Stop"

$mainBat = "C:\Users\User\Desktop\lebanon-news-monitor\War-news\start-and-watch.bat"
$devBat = "C:\Users\User\Desktop\lebanon-news-monitor\War-news-dev\start-and-watch.bat"

# Docker Desktop usually needs an active GUI session. These tasks are registered
# with /IT, so they run only when the user is logged on. If you choose
# "run whether user is logged on or not" in Task Scheduler later, Docker Desktop
# may not be available to the task.
schtasks /Create /TN "War News Main Watchdog" /TR "`"$mainBat`"" /SC MINUTE /MO 5 /ST 00:00 /RL HIGHEST /IT /F
schtasks /Create /TN "War News Dev Watchdog" /TR "`"$devBat`"" /SC MINUTE /MO 5 /ST 00:00 /RL HIGHEST /IT /F

schtasks /Create /TN "War News Main Watchdog Startup" /TR "`"$mainBat`"" /SC ONSTART /RL HIGHEST /IT /F
schtasks /Create /TN "War News Dev Watchdog Startup" /TR "`"$devBat`"" /SC ONSTART /RL HIGHEST /IT /F
