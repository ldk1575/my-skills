#!/usr/bin/env bash
# class-note-kit — HTML을 A4 PDF로 뽑는다 (헤드리스 Chrome)
#
#   bash html2pdf.sh <입력.html> [출력.pdf]
#
# 출력 경로를 생략하면 입력과 같은 이름의 .pdf.
# 쪽 여백·용지는 HTML 안의 @page 규칙을 그대로 따른다.

set -u

IN="${1:-}"
if [ -z "$IN" ]; then
  echo "사용법: bash html2pdf.sh <입력.html> [출력.pdf]" >&2
  exit 2
fi
if [ ! -f "$IN" ]; then
  echo "입력 파일이 없습니다: $IN" >&2
  exit 1
fi
OUT="${2:-${IN%.html}.pdf}"

# 출력 경로를 **절대경로로 고정한다.**
# Chrome 은 Windows 실행 파일이라 상대경로를 자기 작업 폴더 기준으로 푼다.
# 그대로 두면 엉뚱한 자리에 쓰거나, 에러 페이지를 PDF 로 저장해 놓고 성공처럼 보인다.
OUTDIR="$(cd "$(dirname "$OUT")" && pwd)"
OUT="$OUTDIR/$(basename "$OUT")"

# --- Chrome 찾기 ---------------------------------------------------------
CHROME=""
for c in \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "$(command -v google-chrome 2>/dev/null)" \
  "$(command -v chromium 2>/dev/null)"
do
  [ -n "$c" ] && [ -x "$c" ] && CHROME="$c" && break
done

if [ -z "$CHROME" ]; then
  echo "Chrome(또는 Edge)을 찾지 못했습니다. CHROME 변수를 직접 지정하세요." >&2
  exit 1
fi

# --- 경로를 Windows 형태로 바꾼다 -----------------------------------------
# Chrome 은 Windows 실행 파일이라 **셸의 경로가 아니라 Windows 경로**를 받아야 한다.
# `/c/...` 를 `C:/...` 로 바꾸는 것만으로는 부족하다 —
# **Git Bash 는 Windows TEMP 를 `/tmp` 로 매핑**하기 때문에
# 스크래치패드에 둔 HTML 의 pwd 가 `/tmp/claude/...` 로 나온다.
# 그걸 그대로 넘기면 Chrome 이 파일을 못 찾고 **오류 페이지를 1쪽짜리 PDF 로 인쇄한다.**
# (증상: 36KB 안팎, 1쪽, 본문 대신 Malgun Gothic + Segoe UI 만 임베드 — 2026-09-15에 겪었다.)
# `pwd -W` 가 Git Bash 에서 진짜 Windows 경로를 준다. 이것을 먼저 쓴다.
winpath() {  # $1 = 셸 경로 → Windows 경로(C:/...)
  local p="$1" d b w
  d="$(dirname "$p")"; b="$(basename "$p")"
  if w="$(cd "$d" 2>/dev/null && pwd -W 2>/dev/null)" && [ -n "$w" ]; then
    printf '%s/%s' "${w%/}" "$b"; return
  fi
  # pwd -W 가 없는 환경(WSL 등)용 대비책
  [ -d "$d" ] && p="$(cd "$d" && pwd)/$b"
  case "$p" in
    /[a-zA-Z]/*) printf '%s:%s' "$(echo "${p:1:1}" | tr 'a-z' 'A-Z')" "${p:2}" ;;
    *)           printf '%s' "$p" ;;
  esac
}

ABS="$(winpath "$IN")"
URL="file:///${ABS}"
WOUT="$(winpath "$OUT")"

# 뷰어가 기존 PDF를 열어 두면 덮어쓰기가 막힌다.
# 그래서 **임시 파일로 뽑은 뒤 옮긴다.** 이러면 열려 있어도 대개 성공하고,
# 실패하더라도 옛 파일을 새 것으로 착각하지 않는다.
TMP="${OUT%.pdf}.__tmp.pdf"
rm -f "$TMP"
WTMP="$(winpath "$TMP")"

# 실행마다 별도 프로파일을 준다.
# 안 그러면 앞서 띄운 헤드리스 Chrome 이 아직 살아 있을 때
# 두 번째 호출이 그 인스턴스에 붙어 조용히 아무것도 하지 않고 끝난다.
# (한 번 렌더에 1분 안팎이 걸리므로 이 겹침은 흔하게 일어난다.)
PROFILE="${TMPDIR:-/tmp}/cnk-profile-$$"
rm -rf "$PROFILE"
mkdir -p "$PROFILE"
trap 'rm -rf "$PROFILE"' EXIT

# 렌더 예산. 25초로는 사진 여러 장 + KoPub 6종을 다 못 불러와
# **본문이 통째로 빠진 1쪽짜리 PDF**가 나온다 (2026-09-15에 실제로 그랬다).
# 그때 PDF 에 Malgun Gothic 만 박혀 있으면 이 증상이다. 필요하면 CNK_TIME_BUDGET 으로 올린다.
"$CHROME" --headless --disable-gpu --no-sandbox \
  --user-data-dir="$PROFILE" \
  --no-pdf-header-footer \
  --virtual-time-budget="${CNK_TIME_BUDGET:-120000}" \
  --print-to-pdf="$WTMP" \
  "$URL" 2>&1 | grep -iE "bytes written|failed" | grep -vi "gcm" || true

# --- 결과 확인 (0바이트면 실패) -------------------------------------------
if [ ! -s "$TMP" ]; then
  echo "PDF 생성 실패: $OUT" >&2
  rm -f "$TMP"
  exit 1
fi

if ! mv -f "$TMP" "$OUT" 2>/dev/null; then
  echo "PDF를 제자리에 옮기지 못했습니다 - 뷰어에서 열려 있는지 확인하세요: $OUT" >&2
  echo "새로 뽑은 파일은 여기 있습니다: $TMP" >&2
  exit 1
fi

SIZE=$(wc -c < "$OUT" | tr -d ' ')

# 쪽수는 Windows 경로로 넘긴다.
# Git Bash 의 /d/... 를 그대로 주면 Windows 파이썬이 열지 못해 "?" 가 나온다.
PYOUT="$(winpath "$OUT")"

PAGES=$(python -c "
import re,sys
d=open(sys.argv[1],'rb').read()
print(len(re.findall(rb'/Type\s*/Page[^s]', d)))
" "$PYOUT" 2>/dev/null || echo "?")

echo "완료: $OUT  (${SIZE} bytes, ${PAGES}쪽)"
