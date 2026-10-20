"""학습템플릿 md → 노션 붙여넣기용 md. 내용은 글자 하나까지 같게, 자르기만 한다.

    python build_notion.py <학습템플릿.md> <출력.md> <YYYY-MM-DD> <주제>

끝에 각 ===== 블록의 모든 줄이 학습템플릿 안에 그대로 있는지 대조해 출력한다
(굵게·공백만 정규화). mismatch 가 비어 있지 않으면 고쳐서 다시 뽑는다.
"""
import re, sys, pathlib

MD, OUT, DATE, TOPIC = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3], sys.argv[4]
src = MD.read_text(encoding='utf-8')
secs = dict(re.findall(r'^## (.+?)\n(.*?)(?=^## |\Z)', src, re.M | re.S))
blk = lambda s: '=====\n' + s.strip() + '\n====='

parts = re.split(r'^\*\*\[콜아웃 (\d+)\]\*\*\s*$', secs['오늘의 학습 내용'], flags=re.M)
cos, tail = [], ''
for i in range(1, len(parts), 2):
    chunk = parts[i + 1]
    if '**오늘의 한 줄**' in chunk:
        chunk, tail = chunk.split('**오늘의 한 줄**')
    cos.append(chunk.strip())
if tail.strip():
    cos.append('오늘의 한 줄\n' + tail.strip())
qa = [q.strip() for q in re.split(r'^---\s*$', secs['오늘의 질문사항'], flags=re.M) if q.strip()]

n = len(cos)
out = [f'노션 붙여넣기용 · {DATE} {TOPIC}', '',
       '▶ 안내문 (복사하지 않는 줄)',
       f'▶ 콜아웃 {n}개가 필요합니다. 하나 만들고 Ctrl+D 로 {n-1}번 복제하면 빠릅니다.',
       '▶ ===== 로 감싼 구역만 복사하세요.', '', '',
       '▶▶ ① 템플릿 「오늘의 역할」 아래 빈 블록에 붙여넣기', blk(secs['오늘의 역할']), '', '',
       '▶▶ ② 템플릿 「오늘의 주제」 아래 빈 블록에 붙여넣기', blk(secs['오늘의 주제']), '', '',
       '▶▶ ③ 템플릿 「오늘의 목표」 아래 빈 블록에 붙여넣기', blk(secs['오늘의 목표']), '', '',
       '▶▶ ④ 템플릿 「오늘의 학습 내용」 — 먼저 /토글 로 토글을 만들고 이름을 「오늘의 학습 내용」으로 넣은 뒤,',
       f'▶▶    그 안에 콜아웃 {n}개를 만들어 아래 블록을 하나씩 붙여넣기 (첫 줄이 콜아웃 제목이 됩니다)', '']
for i, c in enumerate(cos, 1):
    out += [f'▶▶ 콜아웃 {i}', blk(c), '']
step = 5
if '오늘의 실습 의미' in secs:
    out += ['', f'▶▶ ⑤ 「오늘의 실습 의미」 — 템플릿에 칸이 없으면 「오늘의 학습 내용」 토글 아래에 제목(H2)을 직접 만들고 그 아래에 붙여넣기',
            blk(secs['오늘의 실습 의미']), '']
    step = 6
mark = '①②③④⑤⑥⑦⑧'
out += ['', f'▶▶ {mark[step-1]} 템플릿 「오늘의 질문사항」 아래에 Q1, Q2 를 각각 붙여넣기']
for i, q in enumerate(qa, 1):
    out += [f'▶▶ Q{i}', blk(q), '']
out += ['', f'▶▶ {mark[step]} 템플릿 「오늘의 회고」 아래 빈 블록에 붙여넣기', blk(secs['오늘의 회고']),
        '', '', '▶ 다 채운 뒤 이 페이지를 노션 템플릿으로 저장해 두세요.', '']
OUT.write_text('\n'.join(out), encoding='utf-8')

norm = lambda s: re.sub(r'\s+', ' ', s.replace('**', '')).strip()
whole = norm(src)
blocks = re.findall(r'=====\n(.*?)\n=====', '\n'.join(out), re.S)
bad = [b[:40] for b in blocks if not all(norm(l) in whole for l in b.splitlines() if l.strip())]
print('blocks', len(blocks), 'mismatch', bad)
