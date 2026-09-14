#!/usr/bin/env python3
"""PDF에 실제로 임베드된 글꼴을 확인한다 — 글꼴이 먹었다는 유일한 증거.

    python check_fonts.py <파일.pdf> [<파일2.pdf> ...]

KoPub 계열과 코드용 Consolas 외의 글꼴이 끼어 있으면 그 PDF 어딘가에
**KoPub에 없는 글자**가 있어 다른 서체로 폴백했다는 뜻이다.
서체가 섞여 인쇄되므로 그 글자를 찾아 바꿔야 한다.

자주 걸리는 글자 (KoPub에 없음):
    ᵀ U+1D40   윗첨자 T      →  ^T
    − U+2212   수학 빼기      →  - (보통 하이픈)
    ≈ U+2248   근사           →  "약"
    ∞ U+221E   무한대         →  "무한대"
    ▸ U+25B8   삼각 불릿      →  · 또는 목록
    ⚠ U+26A0   경고           →  ※
    ☐ U+2610   빈 네모        →  CSS로 그린다
    💡 🎯 …    이모지         →  글자로 바꾼다

폴백이 잡히면 `find_bad_glyphs.py` 대신 아래 한 줄로 원본 HTML의 후보를 뽑는다:

    python -c "import collections;s=open('X.html',encoding='utf-8').read();\
c=collections.Counter(ch for ch in s if ord(ch)>0x7f and not (0xAC00<=ord(ch)<=0xD7A3));\
print(' | '.join('U+%04X x%d'%(ord(ch),n) for ch,n in c.most_common()))"
"""
import re
import sys

# 통과시킬 글꼴 — 본문 KoPub 세 벌, 코드블록 한글용 KoPub돋움, 코드 Consolas
OK = re.compile(r"(KoPubWorld|Consolas|D2Coding)", re.I)


def fonts_in(path):
    """PDF 원본에서 서브셋 글꼴 이름(ABCDEF+Name)을 뽑는다."""
    data = open(path, "rb").read()
    names = sorted(set(
        m.decode("latin-1")
        for m in re.findall(rb"[A-Z]{6}\+[A-Za-z0-9\-]+", data)
    ))
    return [n.split("+", 1)[1] for n in names]


def main(paths):
    bad_total = 0
    for path in paths:
        try:
            names = fonts_in(path)
        except OSError as e:
            print(f"[읽기 실패] {path} — {e}")
            bad_total += 1
            continue

        if not names:
            print(f"[글꼴 없음] {path} — PDF가 비었거나 압축 방식이 다릅니다")
            bad_total += 1
            continue

        bad = [n for n in names if not OK.search(n)]
        mark = "OK  " if not bad else "폴백"
        print(f"[{mark}] {path}")
        for n in names:
            flag = "   <-- 폴백" if n in bad else ""
            print(f"        {n}{flag}")
        if bad:
            print("        → KoPub에 없는 글자가 있습니다. 위 목록의 글자를 찾아 바꾸고 다시 뽑으세요.")
            bad_total += 1

    return 1 if bad_total else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
