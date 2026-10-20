"""학습템플릿 md → study.css 를 물린 HTML (PDF 를 뽑기 위한 중간 파일 — 스크래치패드에 둔다).

    python build_study.py <학습템플릿.md> <출력.html> [--warn 4,6]

--warn 에 준 번호의 콜아웃은 주의 색(warn)으로 칠한다.
md 의 섹션 이름은 references/study-template.md 의 고정 순서를 따른다.
'오늘의 실습 의미'(2026-10-20 추가)는 없으면 건너뛴다 — 옛 회차 md 도 그대로 뽑힌다.
"""
import re, sys, pathlib, markdown

MD, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
WARN = set()
if '--warn' in sys.argv:
    WARN = {int(x) for x in sys.argv[sys.argv.index('--warn') + 1].split(',') if x}
CSS = (pathlib.Path(__file__).resolve().parent.parent / 'assets' / 'study.css').read_text(encoding='utf-8')

md = lambda s: markdown.markdown(s, extensions=['extra', 'sane_lists'])
inline = lambda s: md(s)[3:-4]  # <p>…</p> 벗기기
src = MD.read_text(encoding='utf-8')
title = re.search(r'^# (.*)$', src, re.M).group(1)
lede = re.search(r'^> (.*)$', src, re.M)
secs = dict(re.findall(r'^## (.+?)\n(.*?)(?=^## |\Z)', src, re.M | re.S))

def ol_body(s): return md(s).replace('<ol>', '<ol class="body">').replace('<ul>', '<ul class="body">', 1)

# 학습 내용 — 콜아웃 + 오늘의 한 줄
parts = re.split(r'^\*\*\[콜아웃 (\d+)\]\*\*\s*$', secs['오늘의 학습 내용'], flags=re.M)
cos, tail = [], ''
for i in range(1, len(parts), 2):
    n, chunk = int(parts[i]), parts[i + 1]
    if '**오늘의 한 줄**' in chunk:
        chunk, tail = chunk.split('**오늘의 한 줄**')
    t = re.search(r'^\d+\. .*$', chunk, re.M).group(0)
    bullets = chunk[chunk.index(t) + len(t):]
    cos.append(f'<div class="co{" warn" if n in WARN else ""}"><span class="t">{t}</span>{md(bullets.strip())}</div>')
one = ('<div class="oneline"><span class="t">오늘의 한 줄</span>'
       + ''.join(f'<p>{inline(l)}</p>' for l in tail.strip().splitlines() if l.strip()) + '</div>') if tail.strip() else ''

# 실습 의미 — 실습마다 초록 콜아웃, 끝의 잇는 문장은 oneline
meaning = ''
if '오늘의 실습 의미' in secs:
    ps = re.split(r'^\*\*\[실습\] (.+?)\*\*\s*$', secs['오늘의 실습 의미'], flags=re.M)
    items, rest = [], ''
    for i in range(1, len(ps), 2):
        lines = ps[i + 1].strip().splitlines()
        k = next((j for j, l in enumerate(lines) if l.strip() and not l.startswith('- ')), len(lines))
        bl, after = '\n'.join(lines[:k]), '\n'.join(lines[k:])  # 불릿 뒤의 문단 = 앞 회차와 잇는 문장
        items.append(f'<div class="co mine"><span class="t">{ps[i]}</span>{md(bl.strip())}</div>')
        rest = after.strip() or rest
    link = f'<div class="oneline"><span class="t">앞 회차와 잇기</span><p>{inline(rest)}</p></div>' if rest else ''
    meaning = f'<h2>오늘의 실습 의미</h2>{"".join(items)}{link}'

# 질문
qs = []
for q, a in re.findall(r'^\*\*Q(\d+\. .*?)\*\*\s*\n(.*?)(?=^---|^\*\*Q\d|\Z)', secs['오늘의 질문사항'], re.M | re.S):
    a = re.sub(r'^\*\*(?!결론)([^*\n]+)\*\*\s*$', r'#### \1', a.strip(), flags=re.M)
    qs.append(f'<p class="q">{q}</p><div class="a">{md(a)}</div>')

rf = ''.join(f'<div class="rf"><span class="t">{k}</span><p>{inline(v)}</p></div>'
             for k, v in re.findall(r'^- \*\*(.+?)\*\* — (.*)$', secs['오늘의 회고'], re.M))
role = ''.join(f'<div>{inline(r)}</div>' for r in re.findall(r'^- (.*)$', secs['오늘의 역할'], re.M))

body = f'''<div class="head"><div class="eyebrow">AI 에이전트 2기 · 학습템플릿</div>
<h1>{title.replace("학습템플릿 · ", "")}</h1><div class="sub">{inline(lede.group(1)) if lede else ""}</div></div>
<h2>오늘의 역할</h2><div class="role">{role}</div>
<h2>오늘의 주제</h2>{ol_body(secs["오늘의 주제"])}
<h2>오늘의 목표</h2>{ol_body(secs["오늘의 목표"])}
<h2>오늘의 학습 내용</h2>{"".join(cos)}{one}
{meaning}
<h2>오늘의 질문사항</h2>{"".join(qs)}
<h2>오늘의 회고</h2>{rf}'''
OUT.write_text(f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{MD.stem}</title>'
               f'<style>{CSS}</style></head><body>{body}</body></html>', encoding='utf-8')
print('callouts', len(cos), 'meaning', meaning.count('co mine'), 'questions', len(qs), 'retro', rf.count('class="rf"'))
