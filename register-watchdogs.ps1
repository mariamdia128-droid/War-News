$ErrorActionPreference = "Stop"

$mainBat = "C:\Users\User\Desktop\lebanon-news-monitor\War-news\start-and-watch.bat"
$devBat = "C:\Users\User\Desktop\lebanon-news-monitor\War-news-dev\start-and-watch.bat"
$principalUser = "$env:USERDOMAIN\$env:USERNAME"

# Docker Desktop usually needs an active GUI session. These tasks are registered
# with Interactive logon, so they run only when the user is logged on. If you
# choose "run whether user is logged on or not" in Task Scheduler later, Docker
# Desktop may not be available to the task.
$principal = New-ScheduledTaskPrincipal `
    -UserId $principalUser `
    -LogonType Interactive `
    -RunLevel Highest

$startupTrigger = New-ScheduledTaskTrigger -AtStartup
$repeatTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At "00:00" `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

$mainAction = New-ScheduledTaskAction -Execute $mainBat
$devAction = New-ScheduledTaskAction -Execute $devBat

Register-ScheduledTask `
    -TaskName "War News Main Watchdog" `
    -Action $mainAction `
    -Trigger @($startupTrigger, $repeatTrigger) `
    -Principal $principal `
    -Force

Register-ScheduledTask `
    -TaskName "War News Dev Watchdog" `
    -Action $devAction `
    -Trigger @($startupTrigger, $repeatTrigger) `
    -Principal $principal `
    -Force
