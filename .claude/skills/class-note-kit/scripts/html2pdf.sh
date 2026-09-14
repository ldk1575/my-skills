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

# --- 절대경로 file:// URL ------------------------------------------------
ABS="$(cd "$(dirname "$IN")" && pwd)/$(basename "$IN")"
case "$ABS" in
  /c/*|/d/*|/e/*) DRIVE=$(echo "${ABS:1:1}" | tr 'a-z' 'A-Z'); URL="file:///${DRIVE}:${ABS:2}" ;;
  *)              URL="file://${ABS}" ;;
esac

# Chrome은 Windows 경로로 출력을 받는다
case "$OUT" in
  /[a-z]/*) D=$(echo "${OUT:1:1}" | tr 'a-z' 'A-Z'); WOUT="${D}:${OUT:2}" ;;
  *)        WOUT="$OUT" ;;
esac

# 뷰어가 기존 PDF를 열어 두면 덮어쓰기가 막힌다.
# 그래서 **임시 파일로 뽑은 뒤 옮긴다.** 이러면 열려 있어도 대개 성공하고,
# 실패하더라도 옛 파일을 새 것으로 착각하지 않는다.
TMP="${OUT%.pdf}.__tmp.pdf"
rm -f "$TMP"
case "$TMP" in
  /[a-z]/*) D=$(echo "${TMP:1:1}" | tr 'a-z' 'A-Z'); WTMP="${D}:${TMP:2}" ;;
  *)        WTMP="$TMP" ;;
esac

# 실행마다 별도 프로파일을 준다.
# 안 그러면 앞서 띄운 헤드리스 Chrome 이 아직 살아 있을 때
# 두 번째 호출이 그 인스턴스에 붙어 조용히 아무것도 하지 않고 끝난다.
# (한 번 렌더에 1분 안팎이 걸리므로 이 겹침은 흔하게 일어난다.)
PROFILE="${TMPDIR:-/tmp}/cnk-profile-$$"
rm -rf "$PROFILE"
mkdir -p "$PROFILE"
trap 'rm -rf "$PROFILE"' EXIT

"$CHROME" --headless --disable-gpu --no-sandbox \
  --user-data-dir="$PROFILE" \
  --no-pdf-header-footer \
  --virtual-time-budget=25000 \
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
case "$OUT" in
  /[a-z]/*) DD=$(echo "${OUT:1:1}" | tr 'a-z' 'A-Z'); PYOUT="${DD}:${OUT:2}" ;;
  *)        PYOUT="$OUT" ;;
esac

PAGES=$(python -c "
import re,sys
d=open(sys.argv[1],'rb').read()
print(len(re.findall(rb'/Type\s*/Page[^s]', d)))
" "$PYOUT" 2>/dev/null || echo "?")

echo "완료: $OUT  (${SIZE} bytes, ${PAGES}쪽)"
