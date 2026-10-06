param([string]$InstallRoot = (Join-Path $env:USERPROFILE 'Apps/BandicussWeather'))
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath $InstallRoot).Path
$taskPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
$taskRunner = Join-Path $taskRoot 'support/run_windows.py'
& $taskPython -B $taskRunner --check
if ($LASTEXITCODE -ne 0) { throw 'Installation check failed; shortcuts were not created.' }
$taskTerminal = (Get-Command wt.exe -ErrorAction Stop).Source
$taskDesktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Bandicuss Weather.lnk'
foreach ($taskLink in @($taskDesktop)) {
    if (Test-Path -LiteralPath $taskLink) { throw "Existing shortcut preserved: $taskLink" }
}
$taskShell = New-Object -ComObject WScript.Shell
foreach ($taskLink in @($taskDesktop)) {
    $taskShortcut = $taskShell.CreateShortcut($taskLink)
    $taskShortcut.TargetPath = $taskTerminal
    $taskShortcut.Arguments = '-w new --size 120,36 new-tab --title "Bandicuss Weather" -d "' + $taskRoot + '" powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $taskRoot 'Launch-Bandicuss.ps1') + '"'
    $taskShortcut.WorkingDirectory = $taskRoot
    $taskShortcut.Description = 'Bandicuss Weather - Windows terminal dashboard'
    $taskShortcut.Save()
    Write-Output $taskLink
}
