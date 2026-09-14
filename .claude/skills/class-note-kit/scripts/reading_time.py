#!/usr/bin/env python3
"""class-note-kit — 발표대본의 낭독 시간을 실측한다.

    python reading_time.py <대본.md> [--wpm 330]

대본 머리말에 적을 숫자를 뽑아 준다. 어림하지 말고 이걸 쓸 것.

세는 규칙
  - `## 0:00 — …` 구간 제목 아래의 본문만 센다
  - `# 예상 질문 대비` 이후는 낭독하지 않으므로 제외
  - 인용(>), 목록 표시, 굵게(**), 쉼표 표시(/), 공백은 글자 수에서 뺀다
  - `[줄일 때 뺄 곳]` 이 있는 문단은 따로 세어, 뺐을 때의 시간도 같이 낸다
"""

import re
import sys
from pathlib import Path

# Windows 콘솔 기본 인코딩(cp949)에서 —, ⚠ 같은 글자가 깨지지 않게
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

CPM_DEFAULT = 330  # 보통 속도, 분당 글자 수
CUT_MARK = "[줄일 때 뺄 곳]"


def mmss(seconds: float) -> str:
    s = round(seconds)
    return f"{s // 60}분 {s % 60:02d}초"


def count(text: str) -> int:
    """낭독 표기를 걷어내고 실제 발음되는 글자만 센다."""
    text = re.sub(r"`[^`]*`", "", text)          # 인라인 코드
    text = re.sub(r"[\s`*_/\[\]>#|-]", "", text)  # 표기·공백
    return len(text)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2

    path = Path(args[0])
    if not path.is_file():
        print(f"파일이 없습니다: {path}", file=sys.stderr)
        return 1

    cpm = CPM_DEFAULT
    if "--wpm" in sys.argv:
        cpm = int(sys.argv[sys.argv.index("--wpm") + 1])

    raw = path.read_text(encoding="utf-8")

    # 낭독 구간만 — 첫 타임스탬프 제목(## 0:00 …)부터,
    # 타임스탬프가 아닌 제목(## 분량 확인 / ## 예상 질문 대비 / ## 발표 전 점검 …)이 나오기 전까지.
    # 제목 이름을 외워 두지 않는다. "시각 제목이 아니면 낭독 구간이 끝난 것"으로 본다.
    time_head = re.compile(r"^#{1,3}\s*\d+:\d{2}")
    other_head = re.compile(r"^#{1,3}\s+\S")

    spoken, started = [], False
    for ln in raw.splitlines():
        if time_head.match(ln):
            started = True
            continue              # 구간 제목 자체는 읽지 않는다
        if started and other_head.match(ln):
            break                 # 낭독 구간 끝
        if started:
            spoken.append(ln)

    if not started:
        print("낭독 구간(## 0:00 — …)을 찾지 못했습니다.", file=sys.stderr)
        return 1

    body = "\n".join(spoken)
    lines = [ln for ln in spoken if ln.strip() and not ln.startswith((">", "---"))]
    total = count("\n".join(lines))

    # [줄일 때 뺄 곳]은 그 줄만이 아니라 **문단 전체**를 뺀다
    cut_paras = [
        p for p in re.split(r"\n\s*\n", body)
        if CUT_MARK in p
    ]
    cut = count("\n".join(cut_paras))

    def secs(chars: int) -> float:
        return chars / cpm * 60

    print(f"파일       : {path.name}")
    print(f"기준 속도  : {cpm}자/분")
    print()
    print(f"전체       : {total:,}자  →  {mmss(secs(total))}")
    if cut:
        print(f"뺄 곳      : {cut:,}자  →  {mmss(secs(cut))}")
        print(f"축약 시    : {total - cut:,}자  →  {mmss(secs(total - cut))}")
    else:
        print(f"뺄 곳      : 없음  ({CUT_MARK} 표시가 없습니다)")
    print()

    # 머리말에 그대로 붙여넣을 문장
    line = (f"> **분량 실측** — 낭독 기준 **{mmss(secs(total))}**"
            f"(보통 속도 {cpm}자/분, {total:,}자).")
    if cut:
        line += (f" **3분에 맞추려면** `{CUT_MARK}` 문단을 통째로 빼세요 → "
                 f"**{mmss(secs(total - cut))}**({total - cut:,}자).")
    print("머리말에 붙여넣기:")
    print(line)

    if secs(total - cut) > 200:  # 3분 20초 초과
        print()
        print("⚠️  축약해도 3분을 넘습니다. 문단을 하나 더 덜어내세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
