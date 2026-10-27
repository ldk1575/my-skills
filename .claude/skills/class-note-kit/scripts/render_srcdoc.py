"""LMS 노드의 인터랙티브 그림(<iframe srcdoc>) → PNG / SVG (헤드리스 Chromium, Playwright).

    python render_srcdoc.py <입력.html | 강.json> [...] --out <폴더> [--width 880] [--base auto|always|never]

입력은 둘 중 하나다 (references/modulabs-node.md 의 '인터랙티브 그림' 절).
  · srcdoc 원문을 저장한 .html
  · 브라우저에서 클립보드로 받은 .json — 강 하나 {"page","url","figs":[{"i","title","src","prev","srcdoc"}]}
    또는 노드 전체 {"<강번호>": {"page","url","figs":[…]}, …}. 파일 이름은 <강>-<그림>_p<카드>_s<상태>.png
    유튜브처럼 srcdoc 이 없는 iframe 은 렌더링하지 않고 제목·링크만 manifest 에 남긴다.

그림 하나(iframe)는 '그림책' 카드(.page) 여러 장일 수 있다. 카드마다 —
  · 버튼·탭·슬라이더가 없으면 정적 → 카드 PNG 한 장 + 그림 본체 SVG(카드 폭의 절반 이상)를 독립 파일로
    (클래스·CSS 변수로 칠한 색을 인라인 style 로 풀고, 다른 svg 의 <defs> 화살촉도 복사한다.
     도형·색·배치는 손대지 않는다. 글꼴은 PDF 쪽 .nodefig svg text{font-family:var(--kr)!important} 가 맞춘다)
  · 있으면 상태마다 눌러 PNG — '다음 ▶' 류는 끝까지 넘기고, 고르기 버튼·탭은 하나씩, 슬라이더는 최소·중간·최대.
    같은 화면은 한 번만 남긴다.
PNG 는 긴 변 1200px 이하. 결과 목록은 <폴더>/manifest.json.
"""
import argparse, hashlib, io, json, pathlib, re, sys
from PIL import Image
from playwright.sync_api import sync_playwright

LMS = 'https://learn.modulabs.co.kr/'
NEXT = re.compile(r'다음|next|▶|▷|›|»', re.I)
SKIP = re.compile(r'이전|prev|◀|◁|‹|«|처음|다시|reset|되돌', re.I)
REL = re.compile(r'''(?:src|href)\s*=\s*["'](?!https?:|data:|#|about:|javascript:|mailto:)[^"']+["']''', re.I)

# 계산된 스타일 중 SVG 모양을 정하는 것만 인라인으로 푼다
SVG_STANDALONE = r'''
(svg) => {
  const NS = 'http://www.w3.org/2000/svg';
  const P = ['fill','fill-opacity','fill-rule','stroke','stroke-width','stroke-dasharray','stroke-dashoffset',
             'stroke-linecap','stroke-linejoin','stroke-opacity','opacity','font-family','font-size','font-weight',
             'font-style','letter-spacing','text-anchor','dominant-baseline','marker-start','marker-mid','marker-end'];
  const inline = (from, to) => {
    const a = [from, ...from.querySelectorAll('*')], b = [to, ...to.querySelectorAll('*')];
    a.forEach((el, i) => {
      const cs = getComputedStyle(el);
      let st = P.map(p => p + ':' + cs.getPropertyValue(p).replace(/url\("?[^#"]*#([^")]+)"?\)/g, 'url(#$1)')).join(';');
      if (cs.display === 'none') st += ';display:none';
      if (cs.visibility === 'hidden') st += ';visibility:hidden';
      b[i].setAttribute('style', st); b[i].removeAttribute('class');
    });
  };
  const clone = svg.cloneNode(true);
  inline(svg, clone);
  // 화살촉처럼 다른 svg 의 <defs> 에 있는 것을 끌어온다
  const need = new Set([...clone.outerHTML.matchAll(/url\(#([^)]+)\)|href="#([^"]+)"/g)].map(m => m[1] || m[2]));
  const defs = document.createElementNS(NS, 'defs');
  need.forEach(id => {
    if (clone.querySelector('#' + CSS.escape(id))) return;
    const d = document.getElementById(id); if (!d) return;
    const c = d.cloneNode(true); inline(d, c); defs.appendChild(c);
  });
  if (defs.childNodes.length) clone.insertBefore(defs, clone.firstChild);
  const r = svg.getBoundingClientRect();
  if (!clone.getAttribute('viewBox')) clone.setAttribute('viewBox', `0 0 ${r.width} ${r.height}`);
  clone.setAttribute('xmlns', NS);
  clone.removeAttribute('width'); clone.removeAttribute('height');
  return clone.outerHTML;
}
'''

# 카드 안의 글(제목·설명·범례) — PDF 캡션에 원문 그대로 옮길 때 쓴다
CARD_TEXT = r'''
(el) => {
  const t = s => (el.querySelector(s)?.innerText || '').trim();
  return {eyebrow: t('.eyebrow'), title: t('h1, h2, h3'), say: t('.say'),
          small: [...el.querySelectorAll('.small')].map(x => x.innerText.trim()).filter(Boolean),
          legend: [...el.querySelectorAll('.legend li')].map(x => x.innerText.trim())};
}
'''


def load_inputs(paths):
    """→ [(이름, 제목, 앞문단, srcdoc 또는 None, src)]"""
    out = []
    for p in map(pathlib.Path, paths):
        if p.suffix.lower() == '.json':
            d = json.loads(p.read_text(encoding='utf-8'))
            # 강 하나({"figs":…}) 또는 노드 전체({"1": {"figs":…}, "2": …})
            steps = [(p.stem, d)] if 'figs' in d else [(f'{int(k):02d}', v) for k, v in sorted(d.items(), key=lambda kv: int(kv[0]))]
            for name, st in steps:
                for f in st['figs']:
                    out.append((f'{name}-{f["i"]:02d}', f.get('title', ''), f.get('prev', ''), f.get('srcdoc'), f.get('src')))
        else:
            out.append((p.stem, '', '', p.read_text(encoding='utf-8'), None))
    return out


def with_base(html, mode):
    if mode == 'never' or re.search(r'<base\s', html, re.I):
        return html, False
    if mode == 'auto' and not REL.search(html):
        return html, False
    tag = f'<base href="{LMS}">'
    return (re.sub(r'(<head[^>]*>)', r'\1' + tag, html, count=1, flags=re.I) if re.search(r'<head', html, re.I)
            else tag + html), True


def save_png(raw, path):
    im = Image.open(io.BytesIO(raw))
    im.thumbnail((1200, 1200), Image.LANCZOS)
    im.save(path, optimize=True)
    return list(im.size)


def controls(card):
    """보이고 눌리는 조작부 — (종류, locator)"""
    found = []
    for kind, sel in (('button', 'button, [role=tab], [role=button]'), ('range', 'input[type=range]'), ('select', 'select')):
        loc = card.locator(sel)
        for k in range(loc.count()):
            el = loc.nth(k)
            if el.is_visible():
                found.append((kind, el))
    return found


def label(el):
    return ((el.inner_text() or '') + ' ' + (el.get_attribute('id') or '') + ' ' + (el.get_attribute('aria-label') or '')).strip()


def shoot_states(page, card, stem, out):
    """카드를 상태마다 찍는다. 같은 화면은 건너뛴다."""
    seen, shots = set(), []

    def shot(note):
        page.wait_for_timeout(350)
        raw = card.screenshot(animations='disabled')
        h = hashlib.sha1(raw).hexdigest()
        if h in seen:
            return
        seen.add(h)
        f = out / f'{stem}_s{len(shots) + 1:02d}.png'
        shots.append({'file': f.name, 'size': save_png(raw, f), 'state': note})

    shot('처음 화면')
    ctl = controls(card)
    buttons = [(e, label(e)) for k, e in ctl if k == 'button']
    nexts = [e for e, t in buttons if NEXT.search(t) and not SKIP.search(t)]
    picks = [(e, t) for e, t in buttons if not NEXT.search(t) and not SKIP.search(t)]
    for e in nexts:  # 스테퍼 — 끝(비활성)까지 넘긴다
        for _ in range(40):
            if not e.is_enabled():
                break
            before = len(seen)
            e.click()
            shot(f'「{label(e)}」 누름')
            if len(seen) == before and not e.is_enabled():
                break
    for e, t in picks:  # 고르기 버튼·탭 — 하나씩
        if e.is_enabled():
            e.click()
            shot(f'「{t}」 고름')
    for k, e in ctl:
        if k == 'range':
            lo, hi = float(e.get_attribute('min') or 0), float(e.get_attribute('max') or 100)
            for v in (lo, (lo + hi) / 2, hi):
                e.evaluate("(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true}));"
                           " el.dispatchEvent(new Event('change', {bubbles:true})); }", v)
                shot(f'슬라이더 {v:g}')
        elif k == 'select':
            for v in e.evaluate('el => [...el.options].map(o => o.value)'):
                e.select_option(v)
                shot(f'선택 {v}')
    return shots, len(ctl)


def render(page, html, stem, out, base_mode):
    html, based = with_base(html, base_mode)
    bad = []  # 그림마다 새 page 라 리스너를 떼지 않아도 섞이지 않는다
    page.on('requestfailed', lambda r: bad.append(r.url))
    page.on('response', lambda r: r.status >= 400 and bad.append(f'{r.status} {r.url}'))
    page.set_content(html, wait_until='networkidle')
    page.evaluate('document.fonts.ready')
    page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    broken = page.evaluate("[...document.images].filter(i => i.complete && !i.naturalWidth).map(i => i.getAttribute('src'))")
    cards = page.locator('.page')
    cards = [cards.nth(k) for k in range(cards.count())] or [page.locator('body')]
    res = []
    for ci, card in enumerate(cards, 1):
        cs = f'{stem}_p{ci}'
        shots, nctl = shoot_states(page, card, cs, out)
        svgs = []
        if nctl == 0:  # 정적 — 그림 본체인 SVG 는 원본 그대로 떼어 둔다
            cw = card.bounding_box()['width']
            loc = card.locator('svg')
            for k in range(loc.count()):
                s = loc.nth(k)
                top = s.evaluate("el => !el.parentElement.closest('svg')")
                box = s.bounding_box()
                # 카드 폭의 절반이 안 되는 svg 는 HTML 타일 속 아이콘이다 — 떼면 뜻이 없어 PNG 만 쓴다
                if top and box and box['width'] >= cw * 0.5 and box['height'] > 20:
                    f = out / f'{cs}_{len(svgs) + 1}.svg'
                    f.write_text(s.evaluate(SVG_STANDALONE), encoding='utf-8')
                    svgs.append(f.name)
        kind = 'interactive' if nctl else 'static-svg' if svgs else 'static-html'
        res.append({'card': ci, 'kind': kind, 'controls': nctl,
                    'text': card.evaluate(CARD_TEXT), 'png': shots, 'svg': svgs})
    return {'base': based, 'failed_requests': sorted(set(bad)), 'broken_images': broken, 'cards': res}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--width', type=int, default=880, help='CSS 폭. 사용자가 LMS 에서 보는 iframe 폭에 가깝게')
    ap.add_argument('--scale', type=float, default=2, help='device scale factor — 찍은 뒤 1200px 로 줄인다')
    ap.add_argument('--base', choices=['auto', 'always', 'never'], default='auto',
                    help='auto: 상대경로 src/href 가 있을 때만 <base href=LMS> 를 넣는다')
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    manifest = []
    with sync_playwright() as p:
        br = p.chromium.launch()
        for stem, title, prev, srcdoc, src in load_inputs(a.inputs):
            item = {'name': stem, 'title': title, 'prev': prev}
            if not srcdoc:  # 유튜브 등 — 제목과 링크만
                item.update(kind='embed', src=src)
            else:
                pg = br.new_page(viewport={'width': a.width, 'height': 900}, device_scale_factor=a.scale)
                try:
                    item.update(render(pg, srcdoc, stem, out, a.base))
                except Exception as e:  # 한 그림이 깨져도 나머지는 찍는다
                    item.update(kind='error', error=f'{type(e).__name__}: {e}')
                pg.close()
            manifest.append(item)
            n = sum(len(c['png']) for c in item.get('cards', []))
            v = sum(len(c['svg']) for c in item.get('cards', []))
            print(f"{stem}\t{item.get('kind') or 'srcdoc'}\tcards={len(item.get('cards', []))} png={n} svg={v}"
                  f"\tfail={len(item.get('failed_requests', []))} broken={len(item.get('broken_images', []))}\t{title}")
        br.close()
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
