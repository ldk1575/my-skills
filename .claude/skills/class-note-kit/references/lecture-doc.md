# 정리본 조판 규칙

`AI에이전트2기교육_YYYYMMDD_<주제>.html` → PDF. A4 세로, 20~40쪽 규모.

## 문서 뼈대

```
표지 (page-break-after)
목차 (page-break-after)
SECTION 01 …
SECTION 02 …
…
마지막 섹션 = 회고 · 출처 · 핵심 정리
```

`<head>`에 `assets/print.css`의 내용을 **인라인 `<style>`로 넣는다.** 외부 파일 링크는 PDF 변환 시 누락될 수 있다.

## 표지에 들어갈 것

- `eyebrow` — 과정명 · 회차 성격 (예: `AI 에이전트 2기 · 노드 정리`)
- `h1` + `small` — 주제와 한 줄 부제
- `lede` — 이 회차가 무엇을 다루는지 3~4문장
- `meta` — **학습 목표** · **산출물** · **정리일**
- `note-front` — **이 자료에 대하여**: 원문 대비 무엇을 뺐고(사진), 무엇을 다시 그렸는지(도해 목록), 정보는 어디로 옮겼는지. 도구 이름·가격이 나오면 *"기준 시점과 빠르게 바뀜"* 을 함께 밝힌다

## 섹션 표제

```html
<h2><span class="num">SECTION 01</span>제목 — 부제</h2>
<p class="kicker">한 줄 도입 (기울임)</p>
```

`h2`는 `page-break-before:always` — 섹션마다 새 쪽에서 시작한다.

## 콜아웃 4종 — 성격에 맞게 골라 쓴다

| 클래스 | 쓰임 | 색 |
|---|---|---|
| `box` | 개념 정리, 예시 | 파랑 |
| `box story` | 역사·일화·사례 | 호박 |
| `box warn` | 주의·함정·실패 사례 | 적 |
| `box tip` | 실전 요령, 프롬프트 예시 | 초록 |
| `box deep` | 곁가지 심화 (작은 글씨) | 회색 |

각 콜아웃 첫 줄은 `<span class="label">라벨</span>`.

섹션의 결론 한 문장은 `keyline`으로 뽑는다. 남발하지 말고 **섹션당 최대 하나.**

## 표

```html
<table>
  <caption>표 2-1. 표 제목</caption>
  <thead><tr><th style="width:20%">…</th><th>…</th></tr></thead>
  <tbody>…</tbody>
</table>
```

캡션 번호는 `표 <섹션번호>-<일련번호>`. 첫 열에 폭을 지정해 무너지지 않게 한다.

## 도해 (SVG)

```html
<figure>
<svg viewBox="0 0 620 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="설명">
  …
</svg>
<figcaption>그림이 말하려는 것 한 줄</figcaption>
</figure>
```

- `viewBox` 폭은 **620** 고정 (본문 폭에 맞음). 높이만 내용에 맞춰 조절
- 색은 CSS 변수가 아니라 **리터럴 값**으로 (`#1f4e79`, `#eaf1f8`, `#8a5a00`, `#1f5f45`) — SVG 안에서는 변수가 안 먹는 경우가 있다
- 글꼴은 `font-family="Malgun Gothic,sans-serif"`, 코드성 텍스트는 `Consolas,monospace`
- 화살표는 `<defs><marker>` 로 정의해 재사용
- **그림 하나에 개념 하나.** 흐름도·구조도·비교도 정도면 충분하고, 장식용 그림은 넣지 않는다

## 출처 표기

본문 안에서는 문장 끝에:

```html
<span class="src">(출처: 기관, "문서 제목", 연도)</span>
```

마지막 섹션에 전체 목록:

```html
<ul class="body refs">
  <li><strong>주제</strong> — 출처명, "제목."<br><span class="u">https://…</span></li>
</ul>
```

## 마지막 섹션

1. 회고 질문 3~4개 (자기 노트에 답할 것)
2. **핵심 정리 표** — `오늘 배운 것 / 한 문장 정리 / 내가 할 수 있는 행동` 3열
3. 출처 목록

## 자주 나는 문제

| 증상 | 원인 / 해결 |
|---|---|
| PDF에 배경색이 안 나옴 | `-webkit-print-color-adjust:exact` 누락 |
| 표가 쪽 사이에서 잘림 | `table { page-break-inside:avoid }` |
| 제목만 쪽 끝에 남음 | `h3,h4 { page-break-after:avoid }` |
| 한글이 어색하게 끊김 | `p { word-break:keep-all }` |
| SVG가 안 보임 | `xmlns` 속성 누락 |
