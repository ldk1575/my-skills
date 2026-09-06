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

"$CHROME" --headless --disable-gpu --no-sandbox \
  --no-pdf-header-footer \
  --virtual-time-budget=15000 \
  --print-to-pdf="$WOUT" \
  "$URL" 2>&1 | grep -iE "bytes written|error" | grep -vi "gcm\|registration" || true

# --- 결과 확인 (0바이트면 실패) -------------------------------------------
if [ ! -s "$OUT" ]; then
  echo "PDF 생성 실패: $OUT" >&2
  exit 1
fi

SIZE=$(wc -c < "$OUT" | tr -d ' ')
PAGES=$(python -c "
import re,sys
d=open(r'''$OUT''','rb').read()
print(len(re.findall(rb'/Type\s*/Page[^s]', d)))
" 2>/dev/null || echo "?")

echo "완료: $OUT  (${SIZE} bytes, ${PAGES}쪽)"
