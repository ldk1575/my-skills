# class-recorder - 녹화 조종 명령을 PowerShell 프로필에 등록한다.
# 등록하면 어느 폴더에서든 한 단어로 쓸 수 있다.
#
#   powershell -ExecutionPolicy Bypass -File 명령등록.ps1
#   powershell -ExecutionPolicy Bypass -File 명령등록.ps1 -Remove
#
# 주의: 이 파일은 반드시 UTF-8 BOM 으로 저장한다.

param([switch]$Remove)

try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Here '녹화.py'
$Begin  = '# >>> class-recorder >>>'
$End    = '# <<< class-recorder <<<'

if (-not (Test-Path $Script)) {
    Write-Error "녹화.py를 찾을 수 없습니다: $Script"
    exit 1
}

# 프로필 파일이 없으면 만든다
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}
$Body = Get-Content $PROFILE -Raw -Encoding UTF8
if ($null -eq $Body) { $Body = '' }

# 이전에 넣은 블록이 있으면 걷어낸다 (중복 등록 방지)
$Pattern = [regex]::Escape($Begin) + '[\s\S]*?' + [regex]::Escape($End) + '\r?\n?'
$Body = [regex]::Replace($Body, $Pattern, '')

if ($Remove) {
    Set-Content -Path $PROFILE -Value $Body -Encoding UTF8
    Write-Host "제거했습니다: $PROFILE"
    Write-Host '새 PowerShell 창을 열면 반영됩니다.'
    exit 0
}

$Block = @"
$Begin
`$Global:녹화스크립트 = '$Script'
function 녹화상태 { python `$Global:녹화스크립트 상태 }
function 정지     { python `$Global:녹화스크립트 정지 }
function 재개     { python `$Global:녹화스크립트 재개 }
function 토글     { python `$Global:녹화스크립트 토글 }
function 쉬기     { python `$Global:녹화스크립트 쉬기 }
function 녹화시작 { python `$Global:녹화스크립트 시작 }
function 녹화중지 { python `$Global:녹화스크립트 중지 }
function 감시대기 { python `$Global:녹화스크립트 대기 }
function 감시해제 { python `$Global:녹화스크립트 해제 }
$End
"@

Set-Content -Path $PROFILE -Value ($Body.TrimEnd() + "`r`n`r`n" + $Block) -Encoding UTF8

# 정말 들어갔는지 확인하고 나서 말한다
$확인 = Select-String -Path $PROFILE -Pattern ([regex]::Escape($Begin)) -Quiet
if (-not $확인) {
    Write-Host '프로필에 쓰지 못했습니다.' -ForegroundColor Red
    exit 1
}

Write-Host "등록됐습니다: $PROFILE"
Write-Host ''
Write-Host '새 PowerShell 창을 열고 아래를 쓰세요 (어느 폴더에서든):'
Write-Host '  녹화상태   지금 상태'
Write-Host '  정지       일시정지  ← 쉬는 시간엔 이것'
Write-Host '  재개       다시 시작'
Write-Host '  토글       정지 <-> 재개'
Write-Host '  쉬기       교시 끝 - 파일 저장하고 잠시 멈춤'
Write-Host '  녹화시작   다음 교시 - 새 파일로 시작'
Write-Host '  녹화중지'
Write-Host '  감시대기 / 감시해제   자동 판단 끄기·켜기'
Write-Host ''
Write-Host '지금 창에서 바로 쓰려면:'
Write-Host "  . `$PROFILE"
