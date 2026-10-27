# 모두의연구소 LMS에서 노드 원문 가져오기

`learn.modulabs.co.kr` 의 노드는 **로그인해야 열리고 화면에서만 읽힌다.**
이 문서는 그 노드를 **사람이 붙여넣지 않고** 브라우저로 직접 읽어 오는 절차다.
2026-09-14에 「2. 트랜스포머 — AI는 어떻게 언어를 배웠나」 8강을 이 절차로 가져왔다.

---

## 0. 먼저 확인할 것 — 링크가 노드 전체가 아니다

사용자가 주는 링크는 대개 **그 노드의 한 강(step)** 이다.

```
https://learn.modulabs.co.kr/camp/<캠프>/courses/<코스>/node-version/<버전>/steps/<스텝>
                                                                              ^^^^^^^ 한 강
```

**스텝 번호를 1씩 올려서 다음 강을 여는 방식은 통하지 않는다.** 번호가 연속이 아니라
`Loading...` 만 뜬 채 멈춘다. **반드시 페이지 오른쪽 커리큘럼 목록의 제목을 클릭한다.**

첫 페이지를 열면 커리큘럼에 **노드 이름과 전체 강 수**가 보인다. 그게 작업 범위다.

---

## 1. 로그인 — 절대 대신 하지 않는다

내장 브라우저(`mcp__Claude_Browser__navigate`)로 링크를 열면 `member.modulabs.co.kr` 로그인
화면이 뜬다(카카오 / 네이버 / 이메일).

**자격증명은 입력하지 않는다.** 화면을 띄워 둔 채 사용자에게 직접 로그인을 요청하고 기다린다.

> Chrome 확장(Claude in Chrome)이 붙어 있으면 사용자의 기존 세션을 그대로 쓸 수 있다.
> 다만 확장이 연결돼 있지 않은 경우가 흔하니 **내장 브라우저 + 사용자 직접 로그인**을 기본으로 둔다.

---

## 2. 강을 하나씩 읽는다

강마다 아래 세 동작을 반복한다.

```
find      → 커리큘럼에서 그 강의 제목을 찾아 ref 를 얻는다
computer  → left_click 으로 그 ref 를 누른다
computer  → wait 5~6초   ← 이걸 빼면 "Loading..." 만 읽힌다
get_page_text
```

`browser_batch` 로 네 동작을 한 번에 묶으면 왕복이 줄어든다.

**wait 를 충분히 준다.** 2초로는 모자란 경우가 있었고, 그때 본문 대신 `Loading...` 만 돌아온다.
본문이 안 왔으면 **wait 만 더 주고 `get_page_text` 를 다시 부른다** — 다시 클릭하지 않는다.

### `get_page_text` 로 얻어지는 것과 안 얻어지는 것

| 얻어진다 | 안 얻어진다 |
|---|---|
| 본문 문단 전체 | 사진 (설명 텍스트만 옴) |
| 표 (탭 구분 텍스트로) | 도식 (안에 적힌 **글자만** 옴) |
| 코드블록과 실행 결과 | 수식 (아래 4절 참고) |
| 출처·링크의 **표시 텍스트** | 링크의 URL |

**도식과 사진은 텍스트로 안 오지만, 포기하지 않는다.** 다음 절에서 DOM 에서 직접 꺼낸다.

---

## 2-1. 도식과 사진은 DOM 에서 직접 꺼낸다 — 다시 그리지 않는다

**노드의 도식은 인라인 SVG다.** 즉 **원본을 그대로 가져올 수 있다.**
직접 다시 그리면 시간도 들고 원문과 어긋난다. **먼저 확인부터 한다.**

강마다 (토글을 펼친 뒤) `javascript_tool` 로 한 번 훑는다:

```js
(() => {
  const main = document.querySelector('main') || document.body;
  return {
    title: document.title,
    // 아이콘(24px)을 거르려고 폭으로 자른다
    svgs: [...main.querySelectorAll('svg')].filter(s => s.clientWidth > 200).map(s => s.outerHTML),
    imgs: [...main.querySelectorAll('img')].filter(i => i.naturalWidth > 120)
             .map(i => ({src: i.currentSrc || i.src, alt: i.alt || ''}))
  };
})()
```

### 도식 — SVG 를 파일로 저장해 두고 그대로 쓴다

`outerHTML` 을 `도식/NN_이름.svg` 로 저장하고, 문서에서는 이렇게 감싼다.

```html
<figure class="nodefig">
  <!-- 저장해 둔 SVG 를 그대로 붙여넣는다 -->
  <figcaption>그림 N · 설명 <span class="src">— 노드 원문의 도식</span></figcaption>
</figure>
```

```css
.nodefig svg{ max-width:100%; height:auto; }
/* 글자만 본문 글꼴로. 도형·색·배치는 원문 그대로 둔다 */
.nodefig svg text, .nodefig svg tspan{ font-family:var(--kr) !important; }
```

**`!important` 가 꼭 필요하다.** 노드 SVG 는 `font-family="Arial, sans-serif"` 같은 속성이나
내부 `<style>` 의 `.lbl { font: 13px sans-serif }` 로 글꼴을 지정해 둔다.
그대로 두면 **그 글꼴이 PDF 에 따로 임베드돼 `check_fonts.py` 가 폴백으로 잡는다.**

### 사진 — 라이선스를 보고, 되면 내려받아 싣는다

노드 사진은 대개 **`upload.wikimedia.org` 의 CC BY-SA** 이고, 본문에 저작자가 적혀 있다.

```bash
curl -sSL -A "Mozilla/5.0" -H "Referer: https://commons.wikimedia.org/" -o "사진/NN_이름.jpg" "<src>"
```

- **`thumb/.../960px-*.jpg` 주소가 403 으로 막히는 경우가 있다.** 그러면 `thumb/` 와 크기 접두어를 뺀 **원본 주소**로 다시 받는다
- **받은 뒤 `file` 로 확인한다.** HTML 이 돌아왔으면 실패다(오류 페이지가 `.jpg` 로 저장된다 — 2KB 안팎이면 의심)
- 원본이 6000px 처럼 크면 **긴 변 1200px 로 줄인다**

```python
from PIL import Image
im = Image.open(p); im.thumbnail((1200, 1200), Image.LANCZOS)
im.convert("RGB").save(p, "JPEG", quality=85, optimize=True)
```

- 캡션에 **원문이 밝힌 저작자와 라이선스를 그대로** 적는다

---

## 2-2. 인터랙티브 그림(iframe) 추출 — 2026-10-27 노드부터

**그림이 인라인 SVG 가 아니라 `<iframe srcdoc>` 로 들어오는 노드가 있다.**
「그림으로 보기」 카드(제목·설명·SVG·범례, 때로 `다음 ▶` 버튼이나 고르기 버튼)가 통째로 iframe 안의 HTML 이다.
2-1 절의 `main.querySelectorAll('svg')` 는 **iframe 안을 못 보므로 이 그림이 통째로 빠진다.**
10/27 「LangGraph로 에이전트 워크플로 설계하기」에서 실제로 13개가 빠졌고, 그날은 사용자 캡처 24장으로 메웠다.

### 강마다 iframe 을 센다

강을 열고(토글을 펼친 뒤) **2-1 절과 함께 반드시** 이것도 부른다. 채팅 위젯(`Channel chat`)은 뺀다.

```js
(() => [...document.querySelectorAll('iframe')].filter(f => f.title !== 'Channel chat').map((f, i) => {
  let prev = null, el = f;                      // 바로 앞 문단 = 그림이 들어갈 자리
  while (el && !prev) { let s = el.previousElementSibling;
    while (s && !(s.innerText || '').trim()) s = s.previousElementSibling; if (s) prev = s; el = el.parentElement; }
  const sd = f.getAttribute('srcdoc');
  return {i: i + 1, title: f.title, src: f.getAttribute('src'), srcdoc: sd ? sd.length : 0,
          prev: (prev && prev.innerText || '').trim().split('\n').pop().slice(0, 120)};
}))()
```

| 종류 | 알아보는 법 | 할 일 |
|---|---|---|
| **`srcdoc` 그림** | `srcdoc` 길이가 0 이 아니다. `title` 이 `D01 그림: …` | 아래 절차로 꺼내 렌더링한다 |
| **유튜브** | `src` 가 `youtube.com/embed/…` | **제목과 링크만** 남긴다 (`title` + `src` 에서 `?` 앞까지) |

**`prev`(바로 앞 문단의 마지막 줄)를 기록해 둔다.** 정리본에서 그림을 꽂을 자리다.
**강별 iframe 수도 적어 둔다** — 통과 기준에서 PDF 의 그림 수와 맞춘다.

### `srcdoc` 원문은 바깥 DOM 에서 바로 읽힌다

`iframe.getAttribute('srcdoc')` 이 **HTML 원문 전체**를 준다. iframe 내부 문서(`contentDocument`)에 들어갈 필요가 없다.
그림 하나가 2만 자 안팎이라 `javascript_tool` 반환값으로 받으면 컨텍스트가 크게 든다. **클립보드로 옮긴다.**

**① 강을 돌며 sessionStorage 에 모은다** — SPA 라 강을 옮겨도 남는다.

```js
window.__cnk = {
  // 커리큘럼 제목을 글자 그대로 찾아 누른다. "3. " 같은 번호로만 찾으면 본문 퀴즈 보기("3. State 전체를…")와 겹친다
  go(t){ [...document.querySelectorAll('div,span,p')]
           .find(e => e.children.length === 0 && e.textContent.trim() === t).click(); },
  grab(n){
    const figs = [...document.querySelectorAll('iframe')].filter(f => f.title !== 'Channel chat').map((f, i) => {
      let prev = null, el = f;
      while (el && !prev) { let s = el.previousElementSibling;
        while (s && !(s.innerText || '').trim()) s = s.previousElementSibling; if (s) prev = s; el = el.parentElement; }
      return {i: i + 1, title: f.title, src: f.getAttribute('src'),
              prev: (prev && prev.innerText || '').trim().split('\n').pop().slice(0, 200),
              srcdoc: f.getAttribute('srcdoc')};            // 원문 전체
    });
    const all = JSON.parse(sessionStorage.getItem('__cnk') || '{}');
    all[n] = {page: document.title, url: location.href, figs};
    sessionStorage.setItem('__cnk', JSON.stringify(all));
    return `${n}: iframes=${figs.length} srcdoc=${figs.filter(f => f.srcdoc).length}`;   // 강별 수를 여기서 기록
  }
};
sessionStorage.removeItem('__cnk');
```

`browser_batch` 로 강마다 `__cnk.go('3. LangGraph의 세 가지 재료: State, Node, Edge')` → `wait 6` → `__cnk.grab(3)` 을 묶는다
(네 강씩 한 배치). 제목은 0절에서 본 커리큘럼 목록 그대로 쓴다.

**② 복사 버튼을 주입하고 `computer left_click` 으로 누른다.** 복사는 사용자 동작이 있어야 되므로
`javascript_tool` 안에서 바로 `execCommand('copy')` 를 부르면 안 되고, 버튼을 **실제로 클릭**해야 한다.

```js
const b = document.createElement('button'); b.id = '__cnk_copy'; b.textContent = 'COPY ALL';
Object.assign(b.style, {position:'fixed', left:'8px', top:'8px', zIndex:2147483647});
b.onclick = () => { const t = document.createElement('textarea'); t.value = sessionStorage.getItem('__cnk');
  document.body.appendChild(t); t.select(); b.textContent = (document.execCommand('copy') ? 'copied ' : 'FAIL ') + t.value.length; t.remove(); };
document.body.appendChild(b);
```

`find "COPY ALL"` → `left_click` → 버튼 글자가 `copied 269575` 처럼 바뀌면 성공. 앱이 사용자에게 "페이지가 클립보드에 썼다"고 알린다.

**③ PowerShell 로 받아 스크래치패드에 저장하고, 클립보드를 비운다.**

```powershell
$t = Get-Clipboard -Raw
[IO.File]::WriteAllText("<스크래치>\srcdoc\node.json", $t, (New-Object Text.UTF8Encoding $false))
$t.Length          # 버튼에 찍힌 수와 같아야 한다
Set-Clipboard -Value " "
```

> 브라우저 패널에서 `localhost` 로 `fetch` 하는 길은 막혀 있다(Failed to fetch) — 그래서 클립보드다.

### 렌더링 — `scripts/render_srcdoc.py`

```bash
python -I scripts/render_srcdoc.py <스크래치>/srcdoc/node.json --out <스크래치>/srcdoc/out
```

헤드리스 Chromium(Playwright)으로 그림마다 `.page` 카드를 찍는다. 유튜브처럼 `srcdoc` 이 없는 항목은
`kind: embed` 로 제목·링크만 `manifest.json` 에 남는다. 입력으로 srcdoc 을 저장한 `.html` 을 여러 개 줘도 된다.

| 카드 종류 (`manifest.json` 의 `kind`) | 나오는 것 | 정리본에 싣는 법 |
|---|---|---|
| `static-svg` — 조작부 없음, 카드 폭 절반 이상의 SVG 가 그림 본체 | 카드 PNG 1장 + **독립 SVG** | **SVG 를 `.nodefig` 로 그대로** (2-1 절 규칙. 글꼴만 `var(--kr)`). 카드의 제목·설명·범례(`text`)는 캡션에 원문 그대로 |
| `static-html` — 조작부 없음, HTML 타일 + 작은 아이콘 | 카드 PNG 1장 | PNG 를 싣는다 (아이콘만 떼면 뜻이 없다) |
| `interactive` — 버튼·탭·슬라이더 | **상태마다 PNG** (`_s01`, `_s02` …) | 한 그림으로 묶어 단계 순서대로 2열 격자. 캡션에 "단계 N장을 순서대로" |

- **독립 SVG** 는 클래스·CSS 변수로 칠한 색을 인라인 style 로 풀고, 다른 svg 의 `<defs>`(화살촉)를 복사해 넣은 것이다.
  **도형·색·배치는 원문 그대로**이고 다시 그린 것이 아니다
- 조작부 처리 — `다음 ▶` 류는 비활성이 될 때까지 넘기고, 고르기 버튼·탭은 하나씩, 슬라이더는 최소·중간·최대. 같은 화면은 한 번만 남긴다
- PNG 는 **긴 변 1200px 이하**, 폭은 `--width 880`(사용자 화면의 iframe 폭에 가깝게)
- 상대경로 `src`/`href` 가 있으면 `<base href="https://learn.modulabs.co.kr/">` 를 넣는다(`--base auto`).
  **로그인이 필요한 자원은 이걸로도 안 열린다** — `manifest.json` 의 `failed_requests`·`broken_images` 를 보고, 남아 있으면 그 그림만 사용자에게 캡처를 부탁한다
- 캡션 출처는 **"노드 원문의 인터랙티브 그림(헤드리스 렌더링)"** 이라고 밝힌다

**2026-10-27 검증** — srcdoc 13개 전부 성공(실패 요청 0, 깨진 이미지 0). PNG 24장 = 그날 사용자 캡처 24장과 수가 같고,
State 스테퍼 5단계·agent/tools 6단계까지 캡처와 내용이 일치했다. 정적 SVG 6개는 단독으로 열어도 화살촉·색이 원본대로 나왔다.

---

## 3. 접힌 블록을 반드시 펼친다 — 여기가 제일 잘 빠진다

노드에는 접혀 있는 토글이 있다. 제목에 이런 이모지가 붙는다.

- `🔬 깊이 보기 · …` — 수식·원리를 파고드는 블록
- `🧪 손으로 돌려보기 · …` — 실습 코드와 실행 결과
- `한 걸음 더, …` — 이모지 없이 붙기도 한다

**접힌 상태에서는 `get_page_text` 에 제목만 나오고 내용은 안 나온다.**
그런데 **출제자가 노리는 대목이 대개 이 안에 있다.** 빠뜨리면 자료의 절반이 날아간다.

```
find "깊이 보기"  → ref 를 전부 받는다 (한 강에 5개까지 나온 적 있다)
computer left_click × N  → 한 배치로 전부 누른다
computer wait 3
get_page_text     → 이제 펼쳐진 내용이 함께 온다
```

`한 걸음 더` 처럼 이모지가 없는 토글은 `깊이 보기` 검색으로 안 잡힌다.
**본문을 한 번 훑어 "제목만 있고 내용이 없는 줄"을 찾아 따로 클릭한다.**

---

## 4. 수식은 이중으로 깨져서 온다

MathJax가 **렌더 결과와 원본을 둘 다** 내보내서 이렇게 온다.

```
𝐿
∝
𝑁
−
𝛼
L∝N
−α
```

`L ∝ N^(-a)` 하나를 이렇게 토해 낸다. 그대로 옮기면 못 읽는다.

**한 줄로 정리해 적고, 기호와 값은 원문 그대로 둔다.** 그리고 원문 보관본 표지에
"수식은 한 줄로 읽을 수 있게 정리했고 기호와 값은 원문 그대로"라고 밝힌다.

정리 예:

| 웹에서 온 것 | 보관본에 적는 것 |
|---|---|
| `softmax(𝑄𝐾𝑇 𝑑𝑘)𝑉` 형태의 뭉갬 | `Attention(Q, K, V) = softmax( Q K^T / sqrt(d_k) ) V` |
| `𝜋𝜃(𝑦∣𝑥)` | `pi_theta(y|x)` |
| `𝛽 KL(𝜋𝜃 ∥ 𝜋ref)` | `beta * KL( pi_theta || pi_ref )` |

윗첨자 `ᵀ`(U+1D40)는 **KoPub에 없다.** `^T` 로 적는다 (→ `lecture-doc.md` 글리프 절).

---

## 5. 다 읽었으면 원문 보관본부터 만든다

학습자료를 만들기 **전에** 원문을 그대로 붙들어 둔다.

`노드원문_YYYYMMDD_<주제>.html` → `.pdf`

- **본문 문장은 한 글자도 고치지 않는다.** 재편집은 정리본이 할 일이다
- **사진은 라이선스를 확인해 되면 그대로** 싣고, 저작자·라이선스를 캡션에 붙인다
- **도식은 원본 SVG 를 그대로** 넣는다 (글꼴만 본문에 맞춤)
- **접힌 블록은 펼쳐서 제자리에** 두고 테두리로 구분한다
- 표지에 **이 네 가지를 어떻게 처리했는지 명시한다**

왜 따로 만드나 — LMS는 로그인해야 열리고 화면에서만 읽힌다.
**오프라인에서 읽고 밑줄을 그으려면 보관본이 있어야 하고**, 나중에 정리본의 인용을
원문과 대조할 때도 이 파일이 기준이 된다.

---

## 6. 흔한 실패

| 증상 | 원인 | 대응 |
|---|---|---|
| 본문 대신 `Loading...` | wait 부족 | wait 만 더 주고 `get_page_text` 재호출 |
| 스텝 번호를 올렸는데 안 열림 | 번호가 연속이 아님 | 커리큘럼 목록에서 제목을 클릭 |
| 「깊이 보기」 내용이 통째로 없음 | 토글을 안 펼침 | 3절 |
| 수식이 글자 죽처럼 나옴 | MathJax 이중 출력 | 4절 |
| 로그인 화면만 반복 | 세션 없음 | 사용자에게 직접 로그인 요청. **대신 하지 않는다** |
| 본문에 도식·사진이 안 보임 | `get_page_text` 는 못 가져온다 | **2-1절** — DOM 에서 직접 꺼낸다 |
| 「그림으로 보기」가 통째로 없음 | 그림이 `<iframe srcdoc>` 안에 있다 | **2-2절** — `srcdoc` 을 꺼내 `render_srcdoc.py` |
| `javascript_tool` 안의 `execCommand('copy')` 가 false | 사용자 동작이 없다 | 버튼을 주입하고 `computer left_click` 으로 누른다 |
| `python -I` 에서 한글 출력이 `UnicodeEncodeError` | `-I` 가 `PYTHONIOENCODING` 을 무시한다 | 스크립트 안에서 `sys.stdout.reconfigure(encoding='utf-8')` |
| 내려받은 사진이 2KB 남짓 | `thumb/` 주소가 403 | 원본 주소로 재시도. `file` 로 확인 |
| PDF 에 Arial 같은 글꼴이 섞임 | SVG 내부 글꼴 지정 | `.nodefig svg text { … !important }` |
