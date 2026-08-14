# -*- coding: utf-8 -*-
"""인사이트·헤드라인 게이트 (IG1) — 발행 전 자동 점검 (issue #15 수리).

사용: python tools/check_insight.py <웹판.html>

판정 규칙의 정본은 templates/insight-guard.yaml · templates/headline-guard.yaml —
이 스크립트는 그 값(축당 양쪽 사실 하한, must_be_in_ledger)을 읽어 판정만 한다.
원장은 okf/facts/*.md (status: deprecated 제외) — 배포본에 실리는 사실 미러이고
그 정합은 check_ledger(D7)가 보증한다. issue #15 가 「정적 판정 가능」이라고
특정한 4개(①~④)에서 출발해 지금은 아홉을 본다 (⑤ issue #18 · ⑥⑦ 2026-08-13 확장 ·
⑧⑨ 2026-08-14 이슈 #25·#30):

  ①      축 개수 >=1   — 축 마크업([data-axis])이 문서에 하나 이상 있는가
  ② I2   양쪽 사실>=2  — 축마다 data-side-a / data-side-b 의 F-ID 가 각각
                         min_facts_per_side(insight-guard axes 절) 이상이고 원장에 실존하는가
  ③ H6   숫자 = 원장   — 헤드라인 자리(masthead h1 = 화두(h1), section h2 = 축 헤드라인)와
                         pull 박스(.pull/.pullq)의 단위 붙은 숫자가 원장 fact 본문에서
                         문자열로 찾아지는가 (headline-guard numbers.in_pull_box.must_be_in_ledger)
  ④ I8   화두 세 칸    — 결론·발견·근거 세 칸([data-spine="결론|발견|근거"])이 지면에
                         실렸는가. 결론·근거는 비면 실패, 발견은 빈 칸 허용(가드 문면)
  ⑤ H9   화두 구체성   — h1 과 그 직후 받는 줄(.answer2/.standfirst)에 구체 신호
                         (단위 붙은 수 / 원장 fact 본문에 등장하는 고유명사)가 **둘 다
                         0이면 실패**. h1 에만 없고 받는 줄에 있으면 통과 — 추상 헤드
                         허용 조건(headline-guard masthead.h1.concreteness, issue #18).
                         비신호어(non_signal)·받는 줄 class 의 정본은 같은 절의
                         static_check — 이 스크립트는 그 값을 읽어 판정만 한다.
                         간명 상한(⑤b — 2026-08-14 편집장 반려): h1 글자수(공백·구두점
                         제외)·대시 절 수가 headline-guard brevity.static_check 상한을
                         넘으면 실패 — 요약문은 카피가 아니다
  ⑥ Q1   함의 유보 종결 — 축 절의 함의 문장(section[data-axis] 의 마지막 p.note —
                         규명·표본 줄은 제외)의 마지막 문장이 유보형 종결
                         ("이후에야"·"에서 드러난다"·"가 재료다"·"쌓여야"류)인 건이
                         함의 전체의 1/2 를 **초과**하면 실패(정확히 절반은 통과 —
                         이슈 #31 문구 통일). 함의 절반을 넘게
                         「나중에 안다」로 끝내는 지면은 오늘 판단할 것을 내놓지
                         않은 것이다 (I11 함의 의무의 정적 근사 — 2026-08-13 확장)
  ⑦ Q2   시한 주장 좌표 — 화두(h1)·스탠드퍼스트(.answer2/.standfirst)에 시한·의무
                         주장 표지("해야 하는"·"시한이 걸린"·"응답 시한")가 있는데
                         그 문단 안에 F-\\d{3} 좌표가 없으면 실패. 독자를 움직이는
                         주장일수록 원장 좌표가 같은 자리에 있어야 한다
                         (H6 이 숫자에 하는 것을 시한 주장에 한다 — 2026-08-13 확장)
  ⑧      발행본 좌표 실존 — 발행본이 참조하는 F-### 전수가 okf/facts/ 에 파일로
                         실존하는가 (매달린 좌표 0건 — 지어낸 좌표는 담보가 아니다.
                         Q2 가 좌표 표기만 보고 실존을 안 봐 (F-999) 가 통과하던
                         이슈 #25 수리). deprecated 좌표 참조는 경고
  ⑨      뼈대 배신 대조 — eval/proto-<날짜>.md(중도금 뼈대)가 있으면 그 화두(###)와
                         함의(**함의** — …) 문장이 지면에 보존됐는지 정규화 문자열로
                         대조한다 (편집 3단 잔금의 유일한 정성 질문 「조판이 뼈대를
                         배신했는가」의 최소 기계화 — 이슈 #30). 뼈대가 없으면 경고
                         (소급·구판 호), 자리표시자([[)면 그 항목 생략

게이트의 정직성 (F5): 판정 대상 마크업이 웹판에 없어 판정 불가한 항목은
「판정 불가 — 마크업 계약 없음」 경고를 내고 통과시킨다 — 못 재는 것을 재는 척하지 않는다.
article-skeleton 에 data-axis · data-spine 마크업 계약이 도입됐으므로(issue #16)
뼈대대로 채운 지면은 ①·②·④ 가 실판정된다 — 계약 이전에 발행된 지면(08.12 이전)만
경고로 남는다. I1·I3~I7·I9·I10,
H1~H5·H7·H8 은 문면상 사람 판정이라 여기서 다루지 않는다 (eval/ 수동 게이트).
H9 도 background_test(배경 0 독자 검사)는 사람 판정이고 ⑤ 는 그 정적 근사만 본다.

H6 숫자 추출 규칙 (오탐 방지 — 절 번호·연도·날짜를 걸러낸다):
  단위(만·억·조·%)가 붙은 수(예: 144만, 927억, 14.2%)와 콤마 포함 4자리 이상 수(예: 1,292)만
  판정한다. 콤마는 양쪽에서 제거해 비교한다. 단위 없는 맨 숫자(연도·절 번호·날짜)는
  겨루는 숫자가 아니므로 판정하지 않는다 — 미탐을 택하고 오탐(발행 차단)을 피한다.
"""
import glob
import io
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

USAGE = "사용법: python tools/check_insight.py <웹판.html>"

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSIGHT_GUARD = os.path.join(KIT_ROOT, "templates", "insight-guard.yaml")
HEADLINE_GUARD = os.path.join(KIT_ROOT, "templates", "headline-guard.yaml")
FACTS_DIR = os.path.join(KIT_ROOT, "okf", "facts")

CANNOT = "판정 불가 — 마크업 계약 없음"

# 화두 세 칸 — 정본은 insight-guard spine.statement.fields (아래 load 에서 확인)
SPINE_CELLS = ["결론", "발견", "근거"]


def load_guards():
    """두 가드에서 판정에 쓰는 값만 읽는다.

    insight-guard.yaml 은 현재 readings 절이 시퀀스+매핑 혼용이라 전체 YAML 파싱이
    실패한다(정본 결함 — 이 도구의 수리 범위 밖). 그 경우 국소 정규식 추출로
    강등하고 경고를 남긴다 — 값을 못 읽으면 게이트 판정 불가로 실패시킨다.
    돌려주는 값: (min_facts_per_side, must_be_in_ledger, concreteness, warns)
    concreteness 는 headline-guard masthead.h1.concreteness.static_check 의
    {receiving: [class...], non_signal: set} — 절이 없으면 None (H9 판정 생략, 경고).
    """
    warns = []
    for p in (INSIGHT_GUARD, HEADLINE_GUARD):
        if not os.path.exists(p):
            print(f"실패: 정본 없음 — {os.path.relpath(p, KIT_ROOT)} 없이는 게이트 판정 불가")
            sys.exit(1)
    import yaml

    ig_text = io.open(INSIGHT_GUARD, encoding="utf-8").read()
    try:
        ig = yaml.safe_load(ig_text)
        min_side = int(ig["axes"]["min_facts_per_side"])
        ids = [f.get("id") for f in ig["spine"]["statement"]["fields"]]
        if ids != SPINE_CELLS:
            warns.append(f"insight-guard 화두 칸이 {ids} 로 바뀌었다 — 이 도구의 SPINE_CELLS 갱신 필요")
    except yaml.YAMLError:
        warns.append("insight-guard.yaml 이 YAML 로 파싱되지 않는다(readings 절 시퀀스+매핑 혼용) — "
                     "min_facts_per_side 를 국소 추출로 강등")
        m = re.search(r"min_facts_per_side:\s*(\d+)", ig_text)
        if not m:
            print("실패: insight-guard.yaml 에서 min_facts_per_side 를 찾지 못했다 — 게이트 판정 불가")
            sys.exit(1)
        min_side = int(m.group(1))

    hg = yaml.safe_load(io.open(HEADLINE_GUARD, encoding="utf-8").read())
    must = bool(hg["numbers"]["in_pull_box"].get("must_be_in_ledger"))
    conc = None
    sc = (hg.get("masthead", {}).get("h1", {}).get("concreteness") or {}).get("static_check")
    if sc and sc.get("receiving_line"):
        conc = {"receiving": [str(c) for c in sc["receiving_line"]],
                "non_signal": {str(w) for w in (sc.get("non_signal") or [])}}
    else:
        warns.append("⑤H9: headline-guard 에 concreteness.static_check 절이 없다 — 화두 구체성 판정 생략")
    brevity = (hg.get("masthead", {}).get("h1", {}).get("brevity") or {}).get("static_check")
    if not brevity:
        warns.append("⑤H9(간명): headline-guard 에 brevity.static_check 절이 없다 — 길이·절 수 상한 판정 생략")
    return min_side, must, conc, brevity, warns


def strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html)


def get_attr(attrs, name):
    m = re.search(name + r'\s*=\s*"([^"]*)"', attrs)
    return m.group(1).strip() if m else ""


def has_class(attrs, cls):
    return re.search(r'class\s*=\s*"[^"]*\b' + cls + r'\b[^"]*"', attrs) is not None


def load_ledger():
    """okf/facts/*.md 를 원장으로 읽는다 (status: deprecated 제외).

    front matter 의 title·description 과 본문(두 번째 --- 이후)만 대조 대상으로 쓴다 —
    sources 의 URL·타임스탬프 숫자가 오탐 매치되는 것을 막는다.
    돌려주는 값: (fact_id 집합(소문자 f-###), 콤마 제거한 대조용 본문 전체)
    """
    ids, corpus = set(), []
    for p in sorted(glob.glob(os.path.join(FACTS_DIR, "*.md"))):
        text = io.open(p, encoding="utf-8").read()
        if re.search(r"^status:\s*deprecated\s*$", text, re.M):
            continue
        ids.add(os.path.splitext(os.path.basename(p))[0].lower())
        parts = text.split("---")
        body = "---".join(parts[2:]) if len(parts) >= 3 else text
        heads = re.findall(r'^(?:title|description):\s*"?(.*?)"?\s*$', text, re.M)
        corpus.append("\n".join(heads) + "\n" + body)
    return ids, "\n".join(corpus).replace(",", "")


def fact_refs(value):
    """'F-003, F-006' 류 문자열에서 F-ID 목록을 뽑는다 (소문자 f-### 로 정규화)."""
    return [m.lower() for m in re.findall(r"[Ff]-\d+", value)]


NUM_UNIT = re.compile(r"\d[\d,]*(?:\.\d+)?(?:만|억|조|%)")
NUM_COMMA = re.compile(r"\d{1,3}(?:,\d{3})+")

# ── ⑥ Q1 · ⑦ Q2 (2026-08-13 확장) ──────────────────────────────
# Q1 유보 종결 표지 — "이후에야"·"에서 드러난다"·"가 재료다"·"쌓여야" 류.
# 활용형을 잡되(드러날다X — 드러난다·드러나기 시작한다, 쌓여야·쌓이기 시작),
# 넓히지 않는다 — 오탐은 발행을 막는다(H6 과 같은 선택은 미탐 쪽).
DEFER_END = re.compile(r"이후에야|에서\s*드러난다|[이가]\s*재료다|쌓여야|쌓이기\s*시작")
# Q2 시한·의무 주장 표지
DEADLINE_CLAIM = re.compile(r"해야 하는|시한이 걸린|응답 시한")
FACT_COORD = re.compile(r"[Ff]-\d{3}")
# 함의가 아닌 p.note — 스켈레톤의 규명·표본 줄 (article-skeleton 축 절 골격)
NOT_IMPLICATION = re.compile(r"^\s*(?:규명\s*\(|표본\s*—)")


def last_sentence(text):
    """함의 문장의 종결부 — 「다.」 경계로 자른 마지막 문장 (8.11 류 숫자 점은 경계가 아니다)."""
    parts = [p.strip() for p in re.split(r"(?<=다)[.!?]\s*", text) if p.strip()]
    return parts[-1] if parts else text.strip()


def headline_numbers(text):
    """판정 대상 숫자 토큰 — 단위 붙은 수 + 콤마 포함 수 (docstring 추출 규칙)."""
    return NUM_UNIT.findall(text) + NUM_COMMA.findall(text)


# ── ⑤ H9 화두 구체성 (issue #18) ────────────────────────────────
# 시간어는 구체 신호가 아니다 — H6 이 연도·날짜를 거르는 것과 같은 취지.
TIME_WORD = re.compile(r"^\d*(?:분기|반기)$|^(?:상반기|하반기|올해|금년|전년|작년|내년)$|^\d+(?:년|월|일)$")
H9_TOKEN = re.compile(r"[가-힣A-Za-z0-9]+")
# 조사 박리 후보 — 긴 것부터. 박리 결과가 2자 미만이면 박리하지 않는다.
PARTICLES = sorted(["에서는", "으로는", "에서", "으로", "이", "가", "은", "는",
                    "을", "를", "의", "에", "와", "과", "도", "만", "로", "요"],
                   key=len, reverse=True)


def concrete_signals(text, ledger_tokens, non_signal):
    """구체 신호 목록 — 단위 붙은 수 + 원장 토큰과 일치하는 고유명사 후보.

    토큰의 원형·조사 박리형 중 하나라도 non_signal(가드 정본)이면 통째로 제외.
    시간어·단위 없는 맨 숫자도 신호가 아니다. 일반명사 오인은 미탐 방향으로만
    남는다(통과를 넓힐 뿐 발행을 막지 않는다) — H6 과 같은 선택.
    """
    sigs = list(headline_numbers(text))
    for tok in H9_TOKEN.findall(text):
        cands = [tok] + [tok[:-len(p)] for p in PARTICLES
                         if tok.endswith(p) and len(tok) - len(p) >= 2]
        if any(c in non_signal for c in cands):
            continue
        for c in cands:
            if len(c) >= 2 and not c.isdigit() and not TIME_WORD.match(c) and c in ledger_tokens:
                sigs.append(c)
                break
    return sigs


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    path = sys.argv[1]
    min_side, must_ledger, conc, brevity, warns = load_guards()
    if not os.path.isdir(FACTS_DIR):
        print("실패: okf/facts/ 가 없다 — 원장 없이는 H6·I2 판정 불가")
        sys.exit(1)
    fact_ids, ledger = load_ledger()
    h = io.open(path, encoding="utf-8").read()
    errors = []

    # ── ① 축 개수 >=1 · ② I2 양쪽 사실 >=min_side ─────────────────
    axes = [(m.group(1), get_attr(m.group(1), "data-axis"))
            for m in re.finditer(r"<(?:section|div|article)\b([^>]*\bdata-axis\s*=[^>]*)>", h)]
    if not axes:
        warns.append(f"①축 개수·②I2: {CANNOT} ([data-axis] 0건 — 계약 도입 전까지 사람 판정, eval/ 기록)")
    else:
        names = [n or "(이름 없음)" for _a, n in axes]
        print(f"①: 축 {len(names)}개 — {', '.join(names)}")
        for attrs, name in axes:
            name = name or "(이름 없음)"
            side_a, side_b = get_attr(attrs, "data-side-a"), get_attr(attrs, "data-side-b")
            if not side_a and not side_b:
                warns.append(f"[축 {name}] I2 판정 불가 — data-side-a/b 마크업 없음 (한쪽 사실만 있으면 축이 아니라 관측이다)")
                continue
            for side, val in (("a", side_a), ("b", side_b)):
                refs = fact_refs(val)
                if len(refs) < min_side:
                    errors.append(f"[축 {name}] side-{side} 사실 {len(refs)}건 < {min_side} (I2: 양쪽 사실 >={min_side})")
                for r in refs:
                    if r not in fact_ids:
                        errors.append(f"[축 {name}] side-{side} 의 {r.upper()} 가 okf/facts/ 에 없다 (매달린 참조)")

    # ── ③ H6 헤드라인·pull 박스 숫자 = 원장 문자열 ────────────────
    if not must_ledger:
        warns.append("③H6: headline-guard must_be_in_ledger 가 꺼져 있다 — 숫자 대조 생략")
    else:
        spots = []  # (자리 이름, 안쪽 HTML)
        m = re.search(r"<h1\b[^>]*>(.*?)</h1>", h, re.S)
        if m:
            spots.append(("화두(h1)", m.group(1)))
        for m in re.finditer(r"<h2\b[^>]*>(.*?)</h2>", h, re.S):
            body = re.sub(r'<span\b[^>]*class="[^"]*\bn\b[^"]*"[^>]*>.*?</span>', " ", m.group(1), flags=re.S)  # 절 번호 제외
            spots.append(("h2", body))
        pulls = re.findall(r'<[a-z]+\b[^>]*class="[^"]*\bpullq?\b[^"]*"[^>]*>(.*?)</', h, re.S)
        for p in pulls:
            spots.append(("pull 박스", p))
        if not pulls:
            warns.append(f"③H6(pull 박스): {CANNOT} (.pull/.pullq 0건 — 헤드라인 자리 h1·h2 만 판정)")
        if not spots:
            warns.append(f"③H6: {CANNOT} (h1·h2·pull 박스 전부 0건)")
        checked = 0
        for where, body in spots:
            text = strip_tags(body)
            for tok in headline_numbers(text):
                checked += 1
                if tok.replace(",", "") not in ledger:
                    errors.append(f"[{where}] 숫자 「{tok}」 이 원장(okf/facts)에서 문자열로 찾아지지 않는다 (H6)")
        print(f"③: 헤드라인 자리 {len(spots)}곳 · 판정한 숫자 {checked}개")

    # ── ④ I8 화두 세 칸이 지면에 실렸는가 ─────────────────────────
    cells = {}
    for m in re.finditer(r"<[a-z]+\b([^>]*\bdata-spine\s*=[^>]*)>(.*?)</", h, re.S):
        cells[get_attr(m.group(1), "data-spine")] = strip_tags(m.group(2)).strip()
    if not cells:
        warns.append(f"④I8: {CANNOT} ([data-spine] 0건 — 세 칸(결론·발견·근거) 지면 판정은 계약 도입 전까지 사람 판정)")
    else:
        for cell in SPINE_CELLS:
            if cell not in cells:
                errors.append(f"화두 칸 [{cell}] 이 지면에 없다 (I8: 세 칸 = {'·'.join(SPINE_CELLS)})")
            elif cell != "발견" and not cells[cell]:
                errors.append(f"화두 칸 [{cell}] 이 비어 있다 (I8 — 발견만 빈 칸 허용)")
        if cells.get("근거"):
            refs = fact_refs(cells["근거"])
            if not refs:
                errors.append("화두 칸 [근거] 에 F-ID 가 없다 (I8: 근거 = fact ID 와 한 줄 설명)")
            for r in refs:
                if r not in fact_ids:
                    errors.append(f"화두 칸 [근거] 의 {r.upper()} 가 okf/facts/ 에 없다 (매달린 참조)")
        # ⑩ I8b 칸 자립성 — 각 칸은 배경지식 없이 단독 완결 (2026-08-14 편집장 반려:
        #    「부호가 반대다/값은 …에 붙는다/F-055 — …」 — 지시 대상이 칸 밖에 있고
        #    근거 칸이 좌표 나열이었다). 기계가 잴 수 있는 최소 판정 둘:
        #    근거 칸은 F-ID 를 걷어낸 뒤에도 한국어 서술 종결(…다)이 남아야 하고,
        #    결론·발견 칸은 공백 제외 12자 미만의 압축 단문이면 지시어 의존 의심으로 실패.
        if cells.get("근거"):
            prose = re.sub(r"[Ff]-\d{3}", "", cells["근거"])
            prose = re.sub(r"[\s·—\-()·,+%$£₹\d.]+", " ", prose).strip()
            if not re.search(r"다(?![가-힣])", prose) or len(prose) < 10:
                errors.append("화두 칸 [근거] 가 좌표 나열이다 — 사람 문장으로 쓰고 F-ID 는 괄호 병기"
                              " (I8b 칸 자립성, 2026-08-14 반려)")
        for cell in ("결론",):
            t = cells.get(cell, "")
            if t and len(re.sub(r"\s", "", t)) < 12:
                errors.append(f"화두 칸 [{cell}] 「{t}」 — 배경지식 없이 읽히지 않는 압축 단문 의심"
                              f" (I8b: 칸은 단독 완결 — 지시어(부호·값 등)의 대상이 칸 안에 있어야 한다)")

    # ── ⑤ H9 화두 구체성 — 추상 헤드는 받는 줄이 즉시 구체로 받는가 ──
    if conc:
        ledger_tokens = set(H9_TOKEN.findall(ledger))
        m = re.search(r"<h1\b[^>]*>(.*?)</h1>", h, re.S)
        if not m:
            warns.append(f"⑤H9: {CANNOT} (h1 0건)")
        else:
            h1_text = strip_tags(m.group(1))
            h1_sigs = concrete_signals(h1_text, ledger_tokens, conc["non_signal"])
            cls = "|".join(conc["receiving"])
            r = re.search(r'<[a-z]+\b[^>]*class="[^"]*\b(?:' + cls + r')\b[^"]*"[^>]*>(.*?)</', h, re.S)
            if h1_sigs:
                print(f"⑤: 화두 구체형 — 신호 {len(h1_sigs)}개 ({', '.join(h1_sigs[:5])})")
            elif r:
                recv_sigs = concrete_signals(strip_tags(r.group(1)), ledger_tokens, conc["non_signal"])
                if recv_sigs:
                    print(f"⑤: 화두 추상형 — 받는 줄(.{'/.'.join(conc['receiving'])})이 즉시 구체로 받음 "
                          f"(신호 {len(recv_sigs)}개: {', '.join(recv_sigs[:5])})")
                else:
                    errors.append("화두(h1)와 받는 줄 둘 다 구체 신호 0 — 압축이 추상화로 갔다 "
                                  "(H9: 단위 붙은 수 / 원장 fact 고유명사, headline-guard concreteness · issue #18)")
            else:
                errors.append(f"화두(h1)에 구체 신호가 0인데 받는 줄(.{'/.'.join(conc['receiving'])})이 없다 — "
                              "추상 헤드는 바로 다음 줄이 즉시 구체로 받을 때만 허용 "
                              "(H9 · issue #18 반려 3건째 「받는 줄도 없음」, 받는 줄은 skeleton 계약 요소)")

    # ── ⑤b H9 간명 상한 — 요약문은 카피가 아니다 (2026-08-14 편집장 반려) ──
    # 정본은 headline-guard masthead.h1.brevity — 공백·구두점 제외 글자수와
    # 대시(—) 절 수만 기계가 본다. 실물/개념어 구분은 R6 사람 판정.
    if brevity:
        m = re.search(r"<h1\b[^>]*>(.*?)</h1>", h, re.S)
        if m:
            raw = re.sub(r"\s+", " ", strip_tags(m.group(1))).strip()
            n_chars = len(re.sub(r"[^0-9A-Za-z가-힣]", "", raw))
            n_clauses = len([p for p in raw.split("—") if p.strip()])
            print(f"⑤b: 화두 간명 — {n_chars}자(공백 제외) · {n_clauses}절")
            if n_chars > int(brevity.get("max_chars", 10**9)):
                errors.append(f"화두(h1) {n_chars}자 > 상한 {brevity['max_chars']}자(공백·구두점 제외) — "
                              "압축이 덜 됐다. 요약문은 카피가 아니다 "
                              "(H9 간명 상한, headline-guard brevity — 2026-08-14 편집장 반려 실측)")
            if n_clauses > int(brevity.get("max_clauses", 10**9)):
                errors.append(f"화두(h1) 절 수 {n_clauses} > 상한 {brevity['max_clauses']} — "
                              "대시로 문장을 잇지 말고 화두 하나를 골라라 (H9 간명 상한)")

    # ── ⑥ Q1 함의 유보 종결 — 절반 넘게 「나중에 안다」로 끝나는가 ──
    # 함의 자리 = 축 절(section[data-axis])의 마지막 p.note (규명·표본 줄 제외).
    # 함의 마크업 계약이 따로 없어 스켈레톤 골격(축 절 끝 p.note)으로 판정한다.
    implications = []
    note_p = re.compile(r'<p\b[^>]*class="(?:[^"]*\s)?note(?:\s[^"]*)?"[^>]*>(.*?)</p>', re.S)
    for m in re.finditer(r"<section\b[^>]*\bdata-axis\s*=[^>]*>(.*?)</section>", h, re.S):
        notes = [strip_tags(t).strip() for t in note_p.findall(m.group(1))]
        notes = [t for t in notes if t and not NOT_IMPLICATION.match(t)]
        if notes:
            implications.append(notes[-1])
    if not axes:
        warns.append(f"⑥Q1: {CANNOT} ([data-axis] 0건 — 함의 자리를 찾을 수 없다)")
    elif not implications:
        warns.append("⑥Q1: 축 절에 함의 p.note 가 0건 — 함의 실존 자체는 I11 사람 판정, 유보 종결 판정 생략")
    else:
        deferred = [imp for imp in implications if DEFER_END.search(last_sentence(imp))]
        print(f"⑥: 함의 {len(implications)}건 · 유보 종결 {len(deferred)}건")
        if len(deferred) * 2 > len(implications):
            for imp in deferred:
                errors.append(f"[함의] 유보 종결 — 「…{last_sentence(imp)[-40:]}」 (Q1)")
            errors.append(f"함의 {len(implications)}건 중 {len(deferred)}건이 유보 종결 — 1/2 초과 "
                          "(Q1: 함의 절반을 넘게 「나중에 안다」로 끝내면 오늘 판단할 것을 내놓지 않은 지면이다)")

    # ── ⑦ Q2 시한·의무 주장에 원장 좌표가 붙어 있는가 ─────────────
    q2_spots = []
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", h, re.S)
    if m:
        q2_spots.append(("화두(h1)", m.group(1)))
    for m in re.finditer(r'<p\b[^>]*class="(?:[^"]*\s)?(?:answer2|standfirst)(?:\s[^"]*)?"[^>]*>(.*?)</p>', h, re.S):
        q2_spots.append(("스탠드퍼스트", m.group(1)))
    if not q2_spots:
        warns.append(f"⑦Q2: {CANNOT} (h1·.answer2/.standfirst 0건)")
    else:
        claimed = 0
        for where, body in q2_spots:
            text = strip_tags(body)
            marks = DEADLINE_CLAIM.findall(text)
            if marks:
                claimed += 1
                if not FACT_COORD.search(body):
                    errors.append(f"[{where}] 시한·의무 주장 표지({'·'.join(sorted(set(marks)))})가 있는데 "
                                  "그 문단에 F-### 좌표가 없다 (Q2: 독자를 움직이는 주장에는 원장 좌표를 같은 자리에)")
        print(f"⑦: 판정 자리 {len(q2_spots)}곳 · 시한 주장 {claimed}곳")

    # ── ⑧ 발행본 좌표 실존 — 매달린 좌표 0건 (이슈 #25) ───────────
    # Q2 는 좌표 표기의 유무만 봤다 — 실존 대조가 없어 지어낸 (F-999) 가 통과했고,
    # check_ledger 는 okf 미러만 보고 발행 HTML 을 안 본다. I2/I8 의 「매달린 참조」
    # 규칙을 발행본 전수로 확장한다. 대조는 파일 실존(상태 불문) — deprecated 는 경고.
    page_refs = sorted({m.lower() for m in re.findall(r"[Ff]-\d{3}(?:-[xX])?", h)})
    dangling, dep_used = [], []
    for rid in page_refs:
        fp = os.path.join(FACTS_DIR, rid + ".md")
        if not os.path.exists(fp):
            dangling.append(rid.upper())
        elif re.search(r"^status:\s*deprecated\s*$", io.open(fp, encoding="utf-8").read(), re.M):
            dep_used.append(rid.upper())
    for rid in dangling:
        errors.append(f"발행본이 참조하는 {rid} 가 okf/facts/ 에 없다 (⑧ 매달린 좌표 — "
                      "지어낸 좌표는 담보가 아니다, 이슈 #25)")
    if dep_used:
        warns.append("⑧: 발행본이 대체된(deprecated) 좌표를 참조한다 — "
                     + ", ".join(dep_used) + " (supersede 후속 반영 여부 확인)")
    print(f"⑧: 발행본 F-좌표 {len(page_refs)}건 · 매달림 {len(dangling)}건")

    # ── ⑨ 뼈대 배신 대조 — 화두·함의 문장의 보존 (이슈 #30) ───────
    # 편집 3단 잔금의 유일한 정성 질문 「조판이 뼈대를 배신했는가」의 최소 기계화.
    # 뼈대(eval/proto-<날짜>.md — 로컬 운영 산출물)가 있으면 화두(###)와 함의 첫
    # 문장이 지면에 남았는지 정규화 문자열(공백·기호 제거)로 대조한다. 좌표
    # 병기 (F-###) 는 조판에서 자리가 바뀔 수 있어 대조 전에 벗긴다.
    base = os.path.splitext(os.path.basename(path))[0]
    proto_path = os.path.join(KIT_ROOT, "eval", f"proto-{base}.md")
    norm = lambda s: re.sub(r"[^0-9A-Za-z가-힣]", "", s)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", base):
        warns.append("⑨: 파일명이 날짜형이 아니라 뼈대(eval/proto-)를 찾을 수 없다 — 배신 대조 생략")
    elif not os.path.exists(proto_path):
        warns.append(f"⑨: 뼈대 없음(eval/proto-{base}.md) — 배신 대조 생략 "
                     "(편집 3단 미준수 또는 소급·구판 호 — 3b 를 거쳤다면 뼈대가 있어야 한다)")
    else:
        ptext = io.open(proto_path, encoding="utf-8").read()
        hnorm = norm(h)
        needles = []
        mh = re.search(r"^###\s+(.+)$", ptext, re.M)
        if mh:
            needles.append(("화두", mh.group(1)))
        for m in re.finditer(r"^\*\*함의\*\*\s*[—-]\s*(.+)$", ptext, re.M):
            needles.append(("함의", re.split(r"(?<=[다라])\.", m.group(1))[0]))
        if not needles:
            warns.append("⑨: 뼈대에서 화두(###)·함의(**함의** —) 표지를 찾지 못했다 — "
                         "templates/proto-skeleton.md 판형 확인")
        n_checked = 0
        for kind, needle in needles:
            if "[[" in needle:
                warns.append(f"⑨: 뼈대 {kind} 가 자리표시자([[)다 — 그 항목 대조 생략")
                continue
            nn = norm(re.sub(r"\([Ff]-\d{3}[^)]*\)", "", needle))
            if not nn:
                continue
            n_checked += 1
            if nn not in hnorm:
                errors.append(f"[{kind}] 뼈대 문장이 지면에 없다 — 「{needle[:50]}」 "
                              "(⑨ 조판이 뼈대를 배신했는가 — 배신 수리는 조판 몫, "
                              "뼈대를 고치려면 ②로 회귀한다. pipeline-three-stage ③·이슈 #30)")
        print(f"⑨: 뼈대 대조 {n_checked}건 (eval/proto-{base}.md)")

    # ── 결과 ──────────────────────────────────────────────────────
    for w in warns:
        print("경고:", w)
    for e in errors:
        print("실패:", e)
    print(f"— 축 {len(axes)}개 · 원장 fact {len(fact_ids)}건 · 실패 {len(errors)} · 경고 {len(warns)}")
    if errors:
        sys.exit(1)
    print("통과: 인사이트·헤드라인 정적 게이트(①·I2·H6·I8·H9·Q1·Q2·좌표실존·뼈대대조) — "
          "판정 불가 항목은 경고에 남겼다 (F5), 나머지 I·H 게이트는 eval/ 사람 판정")


if __name__ == "__main__":
    main()
