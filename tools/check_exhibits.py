# -*- coding: utf-8 -*-
"""전시물 게이트 (F1·F2·F4) — 발행 전 자동 점검.

사용: python tools/check_exhibits.py output/web/YYYY-MM-DD.html

합(合) v2 마크업 계약 기반 정적 검사. 계약의 단일 정본은
templates/exhibit-contract.yaml — 이 스크립트는 그 값을 읽어 판정만 한다.
게이트의 정직성(F5)에 따라 **존재·계약만** 판정한다 — 판형 일치·
하이라이트의 질은 eval/ 수동 스팟체크.

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

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

USAGE = "사용법: python tools/check_exhibits.py <웹판.html>"

# 계약 단일 정본 — 값(화이트리스트·상한·필수 요소)은 전부 여기서 읽는다
CONTRACT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "exhibit-contract.yaml")

CHEIL_PAT = re.compile(r"제일기획")


def load_contract():
    """templates/exhibit-contract.yaml 을 읽는다. 없으면 게이트 판정 불가 — 실패."""
    if not os.path.exists(CONTRACT_PATH):
        print("실패: 계약 파일 없음 — templates/exhibit-contract.yaml 이 단일 정본이다. 정본 없이는 게이트 판정 불가")
        sys.exit(1)
    import yaml
    c = yaml.safe_load(io.open(CONTRACT_PATH, encoding="utf-8")) or {}
    for key in ("edition", "exhibit", "reexhibit", "text_limits"):
        if key not in c:
            print(f"실패: 계약 파일에 {key} 절이 없다 — templates/exhibit-contract.yaml 확인")
            sys.exit(1)
    return c


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


def domain_ok(url, whitelist):
    m = re.match(r"https?://([^/:?#]+)", url)
    if not m:
        return False
    host = m.group(1).lower()
    return any(host == d or host.endswith("." + d) for d in whitelist)


def prior_exhibit_counts(html_path, pub_date, doc, item, re_class, window_days):
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
        if not d or not (pub_date - timedelta(days=window_days) <= d < pub_date):
            continue
        try:
            h = io.open(os.path.join(folder, fn), encoding="utf-8").read()
        except OSError:
            continue
        for attrs, _body in find_blocks(h, "figure", "exhibit"):
            if get_attr(attrs, "data-doc") == doc and get_attr(attrs, "data-item") == item:
                shown += 1
                if has_class(attrs, re_class):
                    reshown += 1
    return shown, reshown


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    path = sys.argv[1]
    contract = load_contract()
    ex_c, re_c, tl_c = contract["exhibit"], contract["reexhibit"], contract["text_limits"]
    h = io.open(path, encoding="utf-8").read()
    pub_date = parse_pub_date(path)
    errors, warns = [], []

    # ── 판(edition) 판정 ───────────────────────────────────────────
    # 아티팩트 웹판은 body 없는 프래그먼트로 저장된다(발행 시 래핑) —
    # 판 선언은 body 또는 최상위 래퍼 등 아무 요소의 data-edition 속성으로 인정한다.
    ed_attr = contract["edition"]["attr"]
    ed_values = contract["edition"]["values"]
    ed_m = re.search(ed_attr + r'\s*=\s*"(' + "|".join(ed_values) + r')"', h)
    edition = ed_m.group(1) if ed_m else ""
    if not edition:
        print(f'실패: {ed_attr}="{"|".join(ed_values)}" 선언이 없다 — 판 선언 없이는 게이트 판정 불가')
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
        intro_max = tl_c["intro_sentences_warn"]
        if n_intro > intro_max:
            warns.append(f"[{name}] 절 도입 문장 {n_intro}개 > {intro_max} (F2 권고: 도입은 {intro_max}문장까지)")

    # ── F2: 뉴스 항목 ─────────────────────────────────────────────
    for li_attrs, li_body in find_blocks(h, "li", "news"):
        outside = re.sub(r"<details\b.*?</details>", " ", li_body, flags=re.S)  # details 밖만 계상
        label = strip_tags(outside).strip()[:25] or "(빈 항목)"
        n_s = len(re.findall(r'<span\b[^>]*class="[^"]*\bs\b[^"]*"', outside))
        if n_s > tl_c["news_s_max"]:
            errors.append(f"[뉴스: {label}…] .s 요소 {n_s}개 > {tl_c['news_s_max']} (F2 계약: 사실1+의미/한계1)")
        n_sent = count_sentences(strip_tags(outside))
        if n_sent > tl_c["news_sentences_warn"]:
            warns.append(f"[뉴스: {label}…] details 밖 문장 {n_sent}개 > {tl_c['news_sentences_warn']} (F2 권고: 초과 맥락은 <details>로)")

    # ── F4: 전시물 계약 ───────────────────────────────────────────
    exhibits = find_blocks(h, "figure", "exhibit")
    for attrs, body in exhibits:
        name = exhibit_name(attrs)
        # 필수 data 속성 (정본: required_data_attrs)
        for a in ex_c["required_data_attrs"]:
            if not get_attr(attrs, a):
                errors.append(f"[{name}] {a} 가 비었다 (F4: 출처 각주 계약)")
        # 필수 자식 요소 (정본: required_children)
        for child in ex_c["required_children"]:
            if not find_blocks(body, child["tag"], child["class"]):
                errors.append(f"[{name}] .{child['class']} 없음 (F4: {child.get('why', '필수 자식 요소')})")
        # .ex-head 정형 문구 (권고)
        heads = find_blocks(body, "p", "ex-head")
        phrase = ex_c["ex_head_phrase"]
        if heads and phrase not in strip_tags(heads[0][1]):
            warns.append(f"[{name}] .ex-head 가 '…{phrase}: ___' 정형을 안 따른다 (권고)")
        # 하이라이트 상한 (정본: ex_hl)
        hl_min, hl_max = ex_c["ex_hl"]["min"], ex_c["ex_hl"]["max"]
        n_hl = len(re.findall(r'class="[^"]*\bex-hl\b[^"]*"', body))
        if n_hl < hl_min:
            errors.append(f"[{name}] .ex-hl {n_hl}개 < {hl_min} — 하이라이트 없는 재현은 전시물이 아니다 (F4)")
        elif n_hl > hl_max:
            errors.append(f"[{name}] .ex-hl {n_hl}개 > {hl_max} (독자反3: 전시물당 셀 {hl_max}개 상한)")
        # 원문 파일 실존 (제작反1: 재현은 저장된 원문의 변환)
        src_file = get_attr(attrs, ex_c["src_file_attr"])
        if not src_file:
            errors.append(f"[{name}] {ex_c['src_file_attr']} 없음 — 원문 파일 없는 전시물은 F4 불통과")
        elif not resolve_src_file(src_file, path):
            errors.append(f"[{name}] 원문 파일 실존 안 함: {src_file} — sources/YYYY-MM-DD/ 에 저장했나")
        # 도메인 화이트리스트 (제작反3, 정본: src_domain_whitelist)
        url = get_attr(attrs, "data-src-url")
        if url and not domain_ok(url, ex_c["src_domain_whitelist"]):
            errors.append(f"[{name}] src-url 도메인이 화이트리스트 밖: {url} — 기사·유료 리포트는 전시 불가, 링크+2문장만")
        # 재전시 강제 (편집反3) — 과거 호에 같은 전시물이 실렸으면 재전시로 표기해야 한다
        re_class, badge_class = re_c["class"], re_c["badge_class"]
        is_re = has_class(attrs, re_class)
        shown, reshown = prior_exhibit_counts(path, pub_date, get_attr(attrs, "data-doc"), get_attr(attrs, "data-item"),
                                              re_class, re_c["window_days"])
        if shown and not is_re:
            errors.append(f"[{name}] 지난 7일 호에 이미 전시된 문서인데 {re_class} 표기가 없다 (A3 위반 소지)")
        if is_re:
            if not find_blocks(body, "p", badge_class):
                errors.append(f"[{name}] 재전시인데 .{badge_class}('○월○일 공시 재전시 — 오늘 신규 아님') 없음")
            # 주간 상한 (제작反5, 정본: weekly_max) — 오늘 것 포함
            if reshown + 1 > re_c["weekly_max"]:
                errors.append(f"[{name}] 동일 전시물 재전시 주 {reshown + 1}회 > {re_c['weekly_max']} (제작反5 상한)")

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
