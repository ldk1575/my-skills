# class-recorder - 감시기를 로그인 시 자동 실행하도록 등록한다.
#
#   powershell -ExecutionPolicy Bypass -File 등록.ps1
#   powershell -ExecutionPolicy Bypass -File 등록.ps1 -Remove
#
# 관리자 권한은 필요 없다. 다만 트리거와 작업 모두에 -User 를 지정해야 한다.
# 지정하지 않으면 '모든 사용자' 작업이 되어 액세스가 거부된다.
#
# 주의: 이 파일은 반드시 UTF-8 BOM 으로 저장한다.
#       Windows PowerShell 5.1 은 BOM 이 없으면 cp949 로 읽어 한글이 깨진다.

param([switch]$Remove)

# 콘솔이 cp949 라도 한글이 깨지지 않게
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

$TaskName = 'class-recorder 감시기'
$Here     = Split-Path -Parent $MyInvocation.MyCommand.Path
$Watcher  = Join-Path $Here '감시기.py'
$Me       = "$env:USERDOMAIN\$env:USERNAME"

if ($Remove) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "제거했습니다: $TaskName"
    } else {
        Write-Host '등록된 작업이 없습니다.'
    }
    exit 0
}

if (-not (Test-Path $Watcher)) {
    Write-Error "감시기.py를 찾을 수 없습니다: $Watcher"
    exit 1
}

# 콘솔 창이 뜨지 않게 pythonw 를 쓴다 (없으면 python)
$Py = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $Py) { $Py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $Py) {
    Write-Error 'Python을 찾을 수 없습니다.'
    exit 1
}

$Action = New-ScheduledTaskAction -Execute $Py -Argument "`"$Watcher`"" -WorkingDirectory $Here

# 로그인 시 시작 + 매일 09:25에도 한 번 (로그인 상태로 밤을 넘긴 경우 대비)
$Triggers = @(
    (New-ScheduledTaskTrigger -AtLogOn -User $Me),
    (New-ScheduledTaskTrigger -Daily -At 9:25am)
)

# 배터리로 돌아가도 멈추지 않게, 실패하면 다시 띄우게, 시간 제한 없이
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -MultipleInstances IgnoreNew

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Triggers `
        -Settings $Settings -User $Me `
        -Description 'Zep 창을 감지해 OBS 녹화를 켜고 끈다' `
        -Force -ErrorAction Stop | Out-Null
} catch {
    Write-Host ''
    Write-Host "등록 실패: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host '액세스 거부라면 PowerShell을 관리자로 열어 다시 실행해 보세요.'
    exit 1
}

# 정말 등록됐는지 확인하고 나서 말한다 ("했다"가 아니라 "된 걸 봤다")
$Made = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $Made) {
    Write-Host '등록 명령은 통과했지만 작업이 보이지 않습니다. 작업 스케줄러를 확인하세요.' -ForegroundColor Red
    exit 1
}

Write-Host "등록됐습니다: $TaskName"
Write-Host "  상태   : $($Made.State)"
Write-Host "  실행   : $Py ""$Watcher"""
Write-Host "  사용자 : $Me"
Write-Host '  트리거 : 로그인 시 · 매일 09:25'
Write-Host ''
Write-Host '지금 바로 켜 보려면:'
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host '상태 보기:'
Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
Write-Host '제거하려면:'
Write-Host "  powershell -ExecutionPolicy Bypass -File '$PSCommandPath' -Remove"
