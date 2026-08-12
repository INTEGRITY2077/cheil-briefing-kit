# -*- coding: utf-8 -*-
"""전시물 게이트 (F1·F2·F4) — 발행 전 자동 점검.

사용: python tools/check_exhibits.py output/web/YYYY-MM-DD.html

합(合) v2 마크업 계약 기반 정적 검사. 게이트의 정직성(F5)에 따라
**존재·계약만** 판정한다 — 판형 일치·하이라이트의 질은 eval/ 수동 스팟체크.

  F1  절(section.sec)마다 figure.exhibit >=1.
      data-edition="digest"면 면제하되 section.sec 존재 시 즉시 실패.
      제일기획 절이 비면 "강등 전 재전시 시도 필수" 안내와 함께 실패.
  F2  li.news 의 .s 요소 <=2 (details 밖 기준) — 요소 수 초과는 실패.
      항목 문장 수 >2, 절 도입 문장 수 >3 은 경고 (질적 권고).
      문장은 종결부호(한글+마침표, !, ?) 기준으로 보수적으로 센다 —
      소수점(1.5)·라틴 약어(p. vs.)는 한글이 앞에 없으므로 자연히 제외.
  F4  exhibit마다: data-doc/item/unit/doc-date/src-url 비어있지 않음,
      .ex-head · .ex-note · figcaption.ex-src 존재, .ex-hl 1~3개,
      data-src-file 원문 파일 실존, src-url 도메인 화이트리스트,
      doc-date < 발행일이면 .reexhibit + .ex-badge 강제,
      동일 data-doc|item 재전시 주 2회 이하 (같은 폴더 지난 호 스캔).

판정 구분: 마크업 계약 위반 = 실패(종료코드 1), 질적 권고 = 경고(통과).
"""
import io, os, re, sys
from datetime import date, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게

USAGE = "사용법: python tools/check_exhibits.py <웹판.html>"

# 소스 화이트리스트 (제작反3): DART · 회사 공식 IR/보도자료/뉴스룸 · 정부 통계.
# 기사·유료 리포트 도메인은 절대 추가하지 않는다 — 링크+2문장만 가능.
WHITELIST = (
    "dart.fss.or.kr",          # 전자공시
    "cheil.com", "cheil.co.kr",            # 제일기획 공식
    "samsung.com", "news.samsung.com",      # 삼성전자 뉴스룸/IR
    "innocean.com", "innocean.co.kr",       # 이노션 공식
    "hsad.co.kr",                            # HSAD 공식
    "kostat.go.kr", "kosis.kr", "index.go.kr",  # 정부 통계
)

CHEIL_PAT = re.compile(r"제일기획")


def strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html)


def count_sentences(text):
    """종결부호 기준 보수적 문장 수.

    한글 음절 바로 뒤의 마침표(다./이다./습니다. 등)와 한글 뒤 ! ? 만 센다.
    숫자 소수점(927.5), 라틴 약어(p.3, vs.), URL 의 점은 앞이 한글이
    아니므로 자연히 제외 — 오탐(과대 계상)보다 미탐을 택한다.
    """
    text = re.sub(r"https?://\S+", " ", text)
    return len(re.findall(r"[가-힣][.!?]", text))


def get_attr(attrs, name):
    m = re.search(name + r'\s*=\s*"([^"]*)"', attrs)
    return m.group(1).strip() if m else ""


def has_class(attrs, cls):
    return re.search(r'class\s*=\s*"[^"]*\b' + cls + r'\b[^"]*"', attrs) is not None


def find_blocks(html, tag, cls):
    """<tag class="…cls…">…</tag> 블록을 (attrs, body) 로 돌려준다.

    중첩 없는 전제(계약 마크업이 그렇다) — 정규식으로 충분하다.
    """
    out = []
    pat = re.compile(r"<" + tag + r"\b([^>]*)>(.*?)</" + tag + r">", re.S)
    for m in pat.finditer(html):
        if has_class(m.group(1), cls):
            out.append((m.group(1), m.group(2)))
    return out


def exhibit_name(attrs):
    doc = get_attr(attrs, "data-doc") or "(data-doc 없음)"
    item = get_attr(attrs, "data-item")
    return doc + ("|" + item if item else "")


def parse_pub_date(path):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", os.path.basename(path))
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def resolve_src_file(src, html_path):
    """data-src-file 경로를 kit 루트/HTML 위치 양쪽 기준으로 찾아본다."""
    if not src:
        return None
    html_dir = os.path.dirname(os.path.abspath(html_path))
    candidates = [
        os.path.join(html_dir, src),                       # HTML 옆
        os.path.join(html_dir, "..", "..", src),           # kit 루트 (output/web/ 기준)
        src,                                                # 실행 위치 기준
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def domain_ok(url):
    m = re.match(r"https?://([^/:?#]+)", url)
    if not m:
        return False
    host = m.group(1).lower()
    return any(host == d or host.endswith("." + d) for d in WHITELIST)


def prior_exhibit_counts(html_path, pub_date, doc, item):
    """같은 폴더의 지난 7일 호에서 동일 doc|item 의 (전시 횟수, 재전시 횟수)를 센다.

    재전시 여부는 문서 날짜가 아니라 **과거 호에 같은 전시물이 실렸는가**로 판정한다 —
    과거 날짜 문서라도 이 호가 첫 전시면 재전시가 아니다.
    """
    if not pub_date:
        return 0, 0
    folder = os.path.dirname(os.path.abspath(html_path))
    shown = reshown = 0
    for fn in os.listdir(folder):
        if not fn.endswith(".html") or fn == os.path.basename(html_path):
            continue
        d = parse_pub_date(fn)
        if not d or not (pub_date - timedelta(days=6) <= d < pub_date):
            continue
        try:
            h = io.open(os.path.join(folder, fn), encoding="utf-8").read()
        except OSError:
            continue
        for attrs, _body in find_blocks(h, "figure", "exhibit"):
            if get_attr(attrs, "data-doc") == doc and get_attr(attrs, "data-item") == item:
                shown += 1
                if has_class(attrs, "reexhibit"):
                    reshown += 1
    return shown, reshown


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    path = sys.argv[1]
    h = io.open(path, encoding="utf-8").read()
    pub_date = parse_pub_date(path)
    errors, warns = [], []

    # ── 판(edition) 판정 ───────────────────────────────────────────
    # 아티팩트 웹판은 body 없는 프래그먼트로 저장된다(발행 시 래핑) —
    # 판 선언은 body 또는 최상위 래퍼 등 아무 요소의 data-edition 속성으로 인정한다.
    ed_m = re.search(r'data-edition\s*=\s*"(full|digest)"', h)
    edition = ed_m.group(1) if ed_m else ""
    if not edition:
        print('실패: data-edition="full|digest" 선언이 없다 — 판 선언 없이는 게이트 판정 불가')
        sys.exit(1)

    sections = find_blocks(h, "section", "sec")
    if edition == "digest":
        if sections:
            print(f"실패: digest 판인데 section.sec 이 {len(sections)}개 있다 — 단신판은 절 구성을 갖지 않는다")
            sys.exit(1)
        print("digest 판 — 전시 게이트 면제, 통과")
        return

    # ── F1: 절마다 전시물 >=1 ─────────────────────────────────────
    if not sections:
        errors.append("full 판인데 section.sec 이 하나도 없다 — 절은 이 태그로만 구성한다")
    for i, (s_attrs, s_body) in enumerate(sections, 1):
        head_m = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", s_body, re.S)
        name = strip_tags(head_m.group(1)).strip()[:30] if head_m else f"절#{i}"
        exhibits_in = find_blocks(s_body, "figure", "exhibit")
        if not exhibits_in:
            hint = " — 제일기획 절은 접지 말고 강등 전 재전시(reexhibit) 시도 필수" if CHEIL_PAT.search(name) else ""
            errors.append(f"[{name}] figure.exhibit 이 0개 (F1: 절당 전시물 >=1){hint}")

        # ── F2: 절 도입 문장 수 (첫 전시물/목록 이전 구간의 <p>) ──
        cut = len(s_body)
        for pat in (r"<figure\b", r"<ul\b", r"<ol\b", r"<table\b"):
            m = re.search(pat, s_body)
            if m:
                cut = min(cut, m.start())
        intro = s_body[:cut]
        n_intro = sum(count_sentences(strip_tags(p)) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", intro, re.S))
        if n_intro > 3:
            warns.append(f"[{name}] 절 도입 문장 {n_intro}개 > 3 (F2 권고: 도입은 3문장까지)")

    # ── F2: 뉴스 항목 ─────────────────────────────────────────────
    for li_attrs, li_body in find_blocks(h, "li", "news"):
        outside = re.sub(r"<details\b.*?</details>", " ", li_body, flags=re.S)  # details 밖만 계상
        label = strip_tags(outside).strip()[:25] or "(빈 항목)"
        n_s = len(re.findall(r'<span\b[^>]*class="[^"]*\bs\b[^"]*"', outside))
        if n_s > 2:
            errors.append(f"[뉴스: {label}…] .s 요소 {n_s}개 > 2 (F2 계약: 사실1+의미/한계1)")
        n_sent = count_sentences(strip_tags(outside))
        if n_sent > 2:
            warns.append(f"[뉴스: {label}…] details 밖 문장 {n_sent}개 > 2 (F2 권고: 초과 맥락은 <details>로)")

    # ── F4: 전시물 계약 ───────────────────────────────────────────
    exhibits = find_blocks(h, "figure", "exhibit")
    for attrs, body in exhibits:
        name = exhibit_name(attrs)
        # 필수 data 속성 5종
        for a in ("data-doc", "data-item", "data-unit", "data-doc-date", "data-src-url"):
            if not get_attr(attrs, a):
                errors.append(f"[{name}] {a} 가 비었다 (F4: 출처 각주 계약)")
        # 필수 자식 요소
        heads = find_blocks(body, "p", "ex-head")
        if not heads:
            errors.append(f"[{name}] .ex-head 없음 (F4: '이 표에서 볼 것은 하나' 헤드라인 1줄)")
        elif "볼 것은 하나" not in strip_tags(heads[0][1]):
            warns.append(f"[{name}] .ex-head 가 '…볼 것은 하나: ___' 정형을 안 따른다 (권고)")
        if not find_blocks(body, "p", "ex-note"):
            errors.append(f"[{name}] .ex-note 없음 (F4: 사실+한계 동일문장 주석 필수)")
        if not find_blocks(body, "figcaption", "ex-src"):
            errors.append(f"[{name}] figcaption.ex-src 없음 (F4: 문서명·항목명·단위·URL 각주)")
        # 하이라이트 1~3
        n_hl = len(re.findall(r'class="[^"]*\bex-hl\b[^"]*"', body))
        if n_hl == 0:
            errors.append(f"[{name}] .ex-hl 0개 — 하이라이트 없는 재현은 전시물이 아니다 (F4)")
        elif n_hl > 3:
            errors.append(f"[{name}] .ex-hl {n_hl}개 > 3 (독자反3: 전시물당 셀 3개 상한)")
        # 원문 파일 실존 (제작反1: 재현은 저장된 원문의 변환)
        src_file = get_attr(attrs, "data-src-file")
        if not src_file:
            errors.append(f"[{name}] data-src-file 없음 — 원문 파일 없는 전시물은 F4 불통과")
        elif not resolve_src_file(src_file, path):
            errors.append(f"[{name}] 원문 파일 실존 안 함: {src_file} — sources/YYYY-MM-DD/ 에 저장했나")
        # 도메인 화이트리스트 (제작反3)
        url = get_attr(attrs, "data-src-url")
        if url and not domain_ok(url):
            errors.append(f"[{name}] src-url 도메인이 화이트리스트 밖: {url} — 기사·유료 리포트는 전시 불가, 링크+2문장만")
        # 재전시 강제 (편집反3) — 과거 호에 같은 전시물이 실렸으면 재전시로 표기해야 한다
        is_re = has_class(attrs, "reexhibit")
        shown, reshown = prior_exhibit_counts(path, pub_date, get_attr(attrs, "data-doc"), get_attr(attrs, "data-item"))
        if shown and not is_re:
            errors.append(f"[{name}] 지난 7일 호에 이미 전시된 문서인데 reexhibit 표기가 없다 (A3 위반 소지)")
        if is_re:
            if not find_blocks(body, "p", "ex-badge"):
                errors.append(f"[{name}] 재전시인데 .ex-badge('○월○일 공시 재전시 — 오늘 신규 아님') 없음")
            # 주 2회 상한 (제작反5) — 오늘 것 포함
            if reshown + 1 > 2:
                errors.append(f"[{name}] 동일 전시물 재전시 주 {reshown + 1}회 > 2 (제작反5 상한)")

    # ── 결과 ──────────────────────────────────────────────────────
    for w in warns:
        print("경고:", w)
    for e in errors:
        print("실패:", e)
    print(f"— 절 {len(sections)}개 · 전시물 {len(exhibits)}개 · 실패 {len(errors)} · 경고 {len(warns)}")
    if errors:
        sys.exit(1)
    print("통과: 전시물 계약(F1·F2·F4) 충족 — 질(판형 일치·하이라이트)은 eval/ 스팟체크로 (F5)")

if __name__ == "__main__":
    main()
