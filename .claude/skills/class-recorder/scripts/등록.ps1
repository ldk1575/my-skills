# class-recorder — 감시기를 로그인 시 자동 실행하도록 등록한다.
#
#   powershell -ExecutionPolicy Bypass -File 등록.ps1
#   powershell -ExecutionPolicy Bypass -File 등록.ps1 -제거
#
# 관리자 권한은 필요 없다 (현재 사용자 작업으로 등록).

param([switch]$제거)

$작업이름 = "class-recorder 감시기"
$여기     = Split-Path -Parent $MyInvocation.MyCommand.Path
$감시기   = Join-Path $여기 "감시기.py"

if ($제거) {
    if (Get-ScheduledTask -TaskName $작업이름 -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $작업이름 -Confirm:$false
        Write-Host "제거했습니다: $작업이름"
    } else {
        Write-Host "등록된 작업이 없습니다."
    }
    exit 0
}

if (-not (Test-Path $감시기)) {
    Write-Error "감시기.py를 찾을 수 없습니다: $감시기"; exit 1
}

# 콘솔 창이 뜨지 않게 pythonw 를 쓴다 (없으면 python)
$py = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Error "Python을 찾을 수 없습니다."; exit 1 }

$동작 = New-ScheduledTaskAction -Execute $py `
          -Argument "`"$감시기`"" -WorkingDirectory $여기

# 로그인 시 시작 + 매일 09:25에도 한 번 (로그인 상태로 밤을 넘긴 경우 대비)
$트리거 = @(
    (New-ScheduledTaskTrigger -AtLogOn),
    (New-ScheduledTaskTrigger -Daily -At 9:25am)
)

# 배터리로 돌아가도 멈추지 않게, 실패하면 다시 띄우게
$설정 = New-ScheduledTaskSettingsSet `
          -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
          -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
          -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
          -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $작업이름 -Action $동작 -Trigger $트리거 `
    -Settings $설정 -Description "Zep 창을 감지해 OBS 녹화를 켜고 끈다" -Force | Out-Null

Write-Host "등록했습니다: $작업이름"
Write-Host "  실행    : $py `"$감시기`""
Write-Host "  트리거  : 로그인 시 · 매일 09:25"
Write-Host ""
Write-Host "지금 바로 켜 보려면:"
Write-Host "  Start-ScheduledTask -TaskName `"$작업이름`""
Write-Host "상태 보기:"
Write-Host "  Get-ScheduledTask -TaskName `"$작업이름`" | Get-ScheduledTaskInfo"
