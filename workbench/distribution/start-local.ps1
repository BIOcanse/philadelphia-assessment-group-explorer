param(
    [ValidateSet('start','status','stop')][string]$Action='start',
    [ValidateRange(1024,65535)][int]$Port=8767,
    [switch]$OpenBrowser
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
try {
    $packageRoot=Split-Path -Parent $PSScriptRoot
    $pythonExe=Join-Path $packageRoot 'runtime\python.exe'
    $serverScript=Join-Path $packageRoot 'workbench\server.py'
    $outputRoot=Join-Path $packageRoot 'outputs\group_workbench'
    $url="http://127.0.0.1:${Port}/"
    $health=$null
    try { $health=Invoke-RestMethod -Uri ($url+'api/health') -TimeoutSec 2 } catch { $health=$null }
    if ($null -ne $health) {
        if ($health.app -ne 'housing-group-workbench' -or $health.workspace -ne $packageRoot) {
            throw "Port ${Port} is used by another application or copy. Choose a different -Port."
        }
        $owner=Get-CimInstance Win32_Process -Filter "ProcessId = $($health.pid)"
        if ($null -eq $owner -or $owner.ExecutablePath -ne $pythonExe -or -not $owner.CommandLine.Contains($serverScript)) {
            throw 'The responding process does not belong to this portable package.'
        }
    }
    if ($Action -eq 'status') {
        if ($null -eq $health) { Write-Output 'Group Explorer is not running.' } else { $health | ConvertTo-Json }
        exit 0
    }
    if ($Action -eq 'stop') {
        if ($null -ne $health) { Stop-Process -Id $health.pid; Write-Output 'Group Explorer stopped.' }
        exit 0
    }
    if ($null -eq $health) {
        if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Extract the entire portable ZIP before starting.' }
        $tcp=New-Object System.Net.Sockets.TcpClient
        try {
            $connected=$tcp.ConnectAsync('127.0.0.1',$Port).Wait(300)
            if ($connected -and $tcp.Connected) { throw "Port ${Port} is occupied. Choose a different -Port." }
        } catch [System.AggregateException] { } finally { $tcp.Dispose() }
        $process=Start-Process -FilePath $pythonExe -ArgumentList @('-B',('"'+$serverScript+'"'),'--port',[string]$Port) -WorkingDirectory $packageRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $outputRoot 'server.stdout.log') -RedirectStandardError (Join-Path $outputRoot 'server.stderr.log')
        $deadline=[DateTime]::UtcNow.AddSeconds(45)
        while ([DateTime]::UtcNow -lt $deadline) {
            Start-Sleep -Milliseconds 400
            $process.Refresh()
            if ($process.HasExited) { throw ('Startup failed. '+[IO.File]::ReadAllText((Join-Path $outputRoot 'server.stderr.log'))) }
            try { $health=Invoke-RestMethod -Uri ($url+'api/health') -TimeoutSec 1 } catch { continue }
            if ($health.app -eq 'housing-group-workbench' -and $health.workspace -eq $packageRoot -and $health.pid -eq $process.Id) { break }
            $health=$null
        }
        if ($null -eq $health) {
            $process.Refresh()
            if (-not $process.HasExited) { $process.Kill() }
            throw 'Startup exceeded 45 seconds. See outputs/group_workbench/server.stderr.log.'
        }
    }
    Write-Output "Group Explorer is ready: $url"
    if ($OpenBrowser) { Start-Process -FilePath $url }
} catch { Write-Error $_; exit 1 }
