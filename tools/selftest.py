# -*- coding: utf-8 -*-
"""킷 자가 회귀 시험 — 게이트의 게이트 (2026-08-14 신설).

사용: python tools/selftest.py

임시 디렉토리에 킷 사본(tools·templates·profiles·okf)을 만들고, 합성 입력
(심사 기록·지면·뼈대·run_log·마스터 SKILL)으로 각 게이트의 통과/차단 계약을
실측한다 — 정상 입력은 exit 0, 우회·위반 입력은 exit 1 이어야 한다.

왜 있는가: 2026-08-14 메커니즘 감사에서 게이트 12종+봉인은 정작 자기 자신을
지키는 시험이 없었다 — 도구를 고치면 그 수리가 무엇을 깨는지 아무도 몰랐다.
그 감사의 회귀 케이스(우회 실측 전건)를 여기 정본화한다. **게이트(check_*.py)·
게이트가 읽는 정본(templates)을 고친 커밋은 이 시험을 먼저 돌린다.**

플랫폼: 표준 라이브러리 + pyyaml(게이트 자체의 의존)만 쓴다. 리눅스에서 실측
확정(2026-08-14) — macOS·Windows 설치 실측 시 이 스크립트 한 방이 도구층 검증이다.
이 스크립트는 발행 게이트가 아니다 (required-gates 로스터 밖 — 개발용 도구).

레포를 건드리지 않는다 — 모든 입력·변형은 임시 사본 안에서만 일어난다.
전 케이스 기대 일치 시 exit 0, 하나라도 어긋나면 exit 1.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 소스 로스터 봉인(#36)의 스냅샷 경로는 **오늘 날짜에만** 판정된다 — 프로파일
# last_checked 는 소스마다 최신 한 값만 보관하는 현재값 스냅샷이기 때문이다
# (2026-08-15 재설계, 검수 문제 1). 그래서 그 경로를 시험하는 케이스는 오늘로 돈다.
TODAY = date.today().isoformat()
EXEMPT_DATE = TODAY          # 산출+검증만 이 겹친 날 — 면제되면 안 되는 날
VERIFY_ONLY = "2026-09-11"   # 생산 기록 없이 검증만 한 날 — 면제 대상
# 다른 픽스처가 쓰는 고정 날짜와 오늘이 겹치면 케이스끼리 원장을 오염시킨다 — 시끄럽게 죽인다.
CF_DATE = "2026-09-14"       # CF 챌린지 합성 케이스의 호 (이슈 #37)
UNDECIDED_DATE = "2026-09-15"  # gates 에 check_publish:2 · reason 형식 미달 (이슈 #37)
CFL_DATE = "2026-09-16"      # check_formats --check-links 합성 케이스의 호 (검수 문제 6)
MANUAL_DATE = "2026-09-17"   # :2 + 「수동 확인 마감」 형식을 갖춘 날 (검수 문제 4·9)
_FIXED = {"2026-08-20", "2026-08-21", "2026-08-22", "2026-08-23", "2026-08-24",
          "2026-08-25", "2026-08-26", "2026-08-30", "2026-08-31", "2026-09-01",
          "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06",
          "2026-09-07", "2026-09-08", VERIFY_ONLY, "2026-09-12", "2026-09-13",
          CF_DATE, UNDECIDED_DATE, CFL_DATE, MANUAL_DATE}
if TODAY in _FIXED:
    raise SystemExit(f"selftest 픽스처 충돌 — 오늘({TODAY})이 고정 픽스처 날짜와 겹친다. "
                     "고정 날짜 집합을 옮겨라")

DIMS = ["R1 이해관계 계량", "R2 함의 실행가능성", "R3 축 교차",
        "R4 새로움", "R5 근거-주장 정합", "R6 카피 인테그리티"]


def score_table(scores, reason="사유 한 줄이다"):
    rows = "\n".join(f"| {d} | {s} | {reason} |" for d, s in zip(DIMS, scores))
    avg = sum(scores) / len(scores)
    return (f"| 차원 | 점수 | 사유 한 줄 |\n|---|---:|---|\n{rows}\n"
            f"| **평균** | {avg:.2f} | |")


COLD_TABLE = """### cold (배경 0 독자 렌즈)

| 차원 | 점수 | 사유 한 줄 |
|---|---:|---|
| R5 근거-주장 정합 | 7 | 사유 한 줄이다 |
| R6 카피 인테그리티 | 8 | 사유 한 줄이다 |
| **평균** | 7.50 | |
"""


def review_record(date, target=None, headings=None, scores=None, stated="7.61",
                  reason="사유 한 줄이다", issues=True, cold=True):
    """review-form 정본 골격의 합성 심사 기록. 인자로 위반을 주입한다."""
    target = target or f"eval/proto-{date}.md"
    headings = headings or ["### reader (독자 렌즈)", "### refuter (반증 렌즈)",
                            "### crosser (교차 렌즈)"]
    scores = scores or [[8, 7, 8, 7, 8, 8], [7, 8, 7, 8, 7, 8], [8, 8, 7, 8, 8, 7]]
    parts = [f"# 정성 심사 — {date} 호", "", "## 머리", "", "| 항목 | 값 |", "|---|---|",
             f"| 호 날짜 | {date} |", f"| 심사 대상 파일 | {target} |",
             "| 루브릭 버전 | insight-rubric.yaml v2 |", "", "## 심사자별 채점", ""]
    for h, s in zip(headings, scores):
        if h:
            parts += [h, ""]
        parts += [score_table(s, reason), ""]
    if cold:
        parts += [COLD_TABLE, ""]
    parts += ["## 종합", "", "| 항목 | 값 |", "|---|---|",
              f"| 3인 평균 | {stated} |", "| 판정 | 통과 |", ""]
    if issues:
        parts += ["## 지적 목록", "", "| # | 렌즈 | 지적 | 처리 (반영 / 기각-사유) |",
                  "|---:|---|---|---|", "| 1 | refuter | 시험 지적 | 반영 |", ""]
    return "\n".join(parts)


PAGE = """<h1>광고 자본은 GPT로 움직이는가 — 답의 한 조각이 우리 손에 있다</h1>
<p class="standfirst">유료 미디어 +17.5%, 구글 62%→57% (F-038). 해야 하는 확인이 있다 (F-042)</p>
<section class="sec" data-macro="MA3" data-axis="채널 편입" data-side-a="F-042, F-041" data-side-b="F-038, F-012">
<h2>챗GPT 채널 편입</h2>
<p class="note">담당 캠페인의 챗GPT 픽셀 설치 여부를 8월 17일 전에 확인하라</p>
</section>"""

SPINE_OK = PAGE + (
    '<div><b data-spine="결론">세계 광고회사의 전환은 보상을 받기 시작했다</b>'
    '<b data-spine="발견">보상은 계량된 전환에 붙었다</b>'
    '<p data-spine="근거">유료 미디어 투자가 크게 늘었다(F-038) — 픽셀 확인 시한이 다가온다(F-042)</p></div>')

SPINE_LIST = PAGE + (
    '<div><b data-spine="결론">부호가 반대다</b>'
    '<b data-spine="발견">값은 전환에 붙는다</b>'
    '<p data-spine="근거">F-038 — 벤치마크 · F-042 — 픽셀</p></div>')

PROTO = """# 오늘의 제일기획 뉴스 — {date}

## 오늘의 화두

### 광고 자본은 GPT로 움직이는가 — 답의 한 조각이 우리 손에 있다

**함의** — 담당 캠페인의 챗GPT 픽셀 설치 여부를 8월 17일 전에 확인하라(F-042).
"""

GATES_FULL = ["check_tables:0", "check_exhibits:0", "check_css_vars:0",
              "check_ledger:0", "check_size:0", "check_insight:0", "check_formats:0",
              "check_theme:0", "check_review:0", "check_publish:0"]

THEME_EVAL = """| 단위 | 요지 | 판정 | 근거 |
|---|---|---|---|
| 화두(h1) | 시험 | 정렬 | 시험 근거 |
| 축 절 | 시험 | 정렬 | 시험 근거 |
"""

THEME_PAGE = """<h1>시험 화두</h1>
<section class="sec" data-macro="{macro}" data-axis="시험 축"><h2>시험</h2></section>
"""

# CF 챌린지 케이스용 합성 스텁 (2026-08-15 신설 — 이슈 #37, 2026-08-15 재설계 — 검수 문제 3).
# **네트워크를 타지 않는다**: 진짜 check_formats 를 그대로 재수출하고 **urlopen 층**만
# 갈아끼운다 — `fetch_anon` 은 정본이 돈다.
#
# 왜 fetch_anon 스텁을 버렸나 (검수 문제 3): 종전 스텁은 `fetch_anon` 을 통째로
# 갈아끼워, 이번 수리의 하중 지점인 `check_formats.fetch_anon` 의 HTTPError 갈래
# (`e.read()` 로 챌린지 본문을, `getattr(e,'headers')` 로 헤더를 회수하는 곳)가 한
# 번도 실행되지 않았다. 실제 CF 회선에서 탐지가 성립하는지는 전적으로 그 갈래에
# 달려 있는데 시험이 없었다. urlopen 에 HTTPError(챌린지 본문·헤더 포함)를 세우면
# 네트워크 없이 그 갈래가 덮인다 — CF 403 은 urllib 에서 예외로 도착하기 때문이다.
#
# @SEQ@ 는 (코드, 본문, 헤더dict) 응답 대본이다. 대본이 다 떨어지면 마지막 항목을
# 계속 돌려준다. 코드 200 은 정상 응답으로, 그 외는 HTTPError 로 세운다.
CF_STUB = '''# -*- coding: utf-8 -*-
"""selftest 합성 스텁 — 정본 check_formats 를 재수출하고 urlopen 만 갈아끼운다."""
import email.message
import io as _io
import sys
import urllib.request
import urllib.error
import urllib.response

from check_formats_real import *  # noqa: F401,F403
from check_formats_real import (FRAME_API_HEADERS, cf_challenge,  # noqa: F401
                                fetch_anon, main)

SEQ = @SEQ@
_n = [0]


def _msg(d):
    m = email.message.Message()
    for k, v in (d or {}).items():
        m[k] = v
    return m


def _urlopen(req, timeout=None, **kw):
    i = min(_n[0], len(SEQ) - 1)
    _n[0] += 1
    code, body, hdrs = SEQ[i]
    url = getattr(req, "full_url", None) or str(req)
    raw = body.encode("utf-8")
    if code == 200:
        return urllib.response.addinfourl(_io.BytesIO(raw), _msg(hdrs), url, 200)
    # 실제 CF 403/503 은 여기로 도착한다 — 정본 fetch_anon 의 HTTPError 갈래를 태운다
    raise urllib.error.HTTPError(url, code, "stub", _msg(hdrs), _io.BytesIO(raw))


urllib.request.urlopen = _urlopen

if __name__ == "__main__":
    main()
'''

# 대본 조각 — 케이스에서 조립한다.
CF_BODY = ("<html><head><title>Just a moment...</title></head>"
           "<body>challenges.cloudflare.com</body></html>")
R_401 = (401, "", {})                                   # 정상 회선의 「없는 uuid」
R_CF_HDR = (403, CF_BODY, {"cf-mitigated": "challenge"})  # 헤더까지 붙은 챌린지
R_CF_BODY = (403, CF_BODY, {})                          # 헤더 없는 챌린지 — 본문 표식만
FMT_TITLE = "시험 호 — 오늘의 제일기획 뉴스 09.16"
FMT_LINK = "https://claude.ai/code/artifact/00000000-0000-4000-8000-000000000002"
# 지면이 CF 를 인용한 200 응답 — 판정 불가로 접히면 안 된다 (검수 문제 1·8)
R_META_OK = (200, '{"mode":"public","ver":"v1"}', {})
R_BODY_CITES_CF = (200, "<h1>x</h1> Just a moment 와 challenges.cloudflare.com "
                        "을 인용한 오늘 호 지면", {})

MASTER_CLEAN = ("# 킷 위치\n/tmp/somewhere/kit\n\n# 본문\n"
                "https://dart.fss.or.kr/api/todayRSS.xml 를 본다.\n")
MASTER_LEAKY = ("# 킷 위치\n/tmp/somewhere/kit\n\n# 본문\n"
                "원장은 /home/author/briefing/okf 에 있다.\n")


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def edit(path, old, new):
    t = io.open(path, encoding="utf-8").read()
    if old not in t:
        raise RuntimeError(f"시험 픽스처 오류 — {os.path.basename(path)} 에 「{old[:30]}」 이 없다")
    w(path, t.replace(old, new))


def bump_score(path, delta):
    """axes.md 첫 「**점수판** 지지 N」 을 N+delta 로 바꾼다 (복원은 -delta).

    시드 수치를 하드코딩하지 않는다 — 종전에는 「지지 12」 를 문자열로 박아 두어,
    **설치본이 실제로 한 번이라도 루틴을 돌리면 selftest 전체가 픽스처 오류로
    죽었다** (2026-08-15 맥 앱 실측, 이슈 #33: 관측 등재로 지지 12→14 가 되자
    이 케이스에서 RuntimeError 로 중단 — 도구층 검증이 영구히 막혔다).
    점수판은 매 실행 갱신되는 값이라 시험은 현재값에서 출발해야 한다.
    """
    t = io.open(path, encoding="utf-8").read()
    m = re.search(r"(\*\*점수판\*\*\s*지지\s*)(\d+)", t)
    if not m:
        raise RuntimeError(f"시험 픽스처 오류 — {os.path.basename(path)} 에 "
                           "「**점수판** 지지 N」 이 없다")
    w(path, t[:m.start()] + m.group(1) + str(int(m.group(2)) + delta) + t[m.end():])


def sec_span(text, ma):
    """axes.md 에서 `## MA# —` 절의 [시작, 끝) 오프셋 — 변형을 한 축 안으로 가둔다."""
    m = re.search(rf"^## {ma} —", text, re.M)
    if not m:
        raise RuntimeError(f"시험 픽스처 오류 — axes.md 에 「## {ma} —」 절이 없다")
    nxt = re.search(r"^## ", text[m.end():], re.M)
    return m.start(), (m.end() + nxt.start()) if nxt else len(text)


def daily_source_ids(prof_path):
    """프로파일에서 **상시(daily) 소스 id 를 읽어** 돌려준다 (정본에서 읽는다).

    종전 케이스는 `miss="trade-press"` 로 소스 id 를 코드에 박았다 — 프로파일에서
    그 소스가 개명·삭제되면 픽스처가 **아무 소스도 빼지 않고 전수 갱신**해서, 차단을
    기대한 케이스가 통과하고 시험은 엉뚱한 이유로 깨진다(2026-08-15 검수 문제 8a).
    어휘 집합도 코드에 박지 않는다 — sweep_gate.daily_cadence 가 정본이다.
    """
    import yaml
    prof = yaml.safe_load(io.open(prof_path, encoding="utf-8-sig").read()) or {}
    vocab = [str(v).strip().lower()
             for v in ((prof.get("sweep_gate") or {}).get("daily_cadence") or ["매일", "daily"])]
    ids = [str(s.get("id")) for s in (prof.get("sources") or [])
           if isinstance(s, dict) and str(s.get("cadence") or "").strip().lower() in vocab]
    if not ids:
        raise RuntimeError("시험 픽스처 오류 — 프로파일에 상시(daily) 소스가 없다")
    return ids


def refute_fixture(paths, ma="MA1", record=False, record_date=None):
    """축 하나에 반증 1건이 등재된 상태를 3중 장부 전부에 합성한다 (이슈 #35 ⑥ⓑ 시험).

    지지 1건을 반증으로 뒤집고 axes.md 점수판·profiles status·index 요약을 같이 옮긴다 —
    ⑤(3중 장부)를 통과시킨 채로 ⑥ⓑ 만 시험하기 위해서다. 시드 수치는 하드코딩하지
    않는다(#33 의 교훈 — 설치본이 한 번이라도 루틴을 돌리면 고정 수치는 픽스처 오류가 된다).
    record=True 면 「### 재귀납 기록」에 날짜 행까지 넣는다(통과 기대),
    False 면 넣지 않는다(차단 기대 — 반증이 났는데 재독·판정 기록이 없는 상태).
    """
    axes_p, prof_p, index_p = paths
    t = io.open(axes_p, encoding="utf-8").read()
    s, e = sec_span(t, ma)
    sec = t[s:e]
    if "| 지지 |" not in sec:
        raise RuntimeError(f"시험 픽스처 오류 — {ma} 계보에 지지 행이 없다")
    sec = sec.replace("| 지지 |", "| 반증 |", 1)
    m = re.search(r"(\*\*점수판\*\* 지지 )(\d+)( · 반증 )(\d+)", sec)
    if not m:
        raise RuntimeError(f"시험 픽스처 오류 — {ma} 점수판 줄을 읽지 못했다")
    sec = (sec[:m.start()] + m.group(1) + str(int(m.group(2)) - 1)
           + m.group(3) + str(int(m.group(4)) + 1) + sec[m.end():])
    if record:
        # 「### 재귀납 기록」 표의 **구분선 바로 뒤에 행을 끼워 넣는다**.
        # 종전에는 자리표시 행 문구(`| (촉발 없음) ...`)에 re.sub 로 매달렸다 — 이
        # 메커니즘이 한 번이라도 실제로 발동해 진짜 기록 행이 들어가면 자리표시 행이
        # 사라져 시험이 RuntimeError 로 죽는다. **시험이 검사하는 사건이 일어나는 순간
        # 시험이 깨지는** 구조라 문구 의존을 끊는다 (2026-08-15 검수 문제 8b).
        # 날짜도 박지 않는다 — 계보의 반증 등재일보다 뒤여야 ⑥ⓑ 를 통과하므로
        # 「오늘」로 넣는다 (검수 문제 8c).
        rec_at = sec.find("### 재귀납 기록")
        if rec_at < 0:
            raise RuntimeError(f"시험 픽스처 오류 — {ma} 에 「### 재귀납 기록」 소절이 없다")
        m2 = re.search(r"^\|[\s\-:|]+\|\s*$", sec[rec_at:], re.M)
        if not m2:
            raise RuntimeError(f"시험 픽스처 오류 — {ma} 재귀납 기록 표의 구분선이 없다")
        cut = rec_at + m2.end()
        row = (f"\n| {record_date or date.today().isoformat()} | 반증 >= 1 (계보 첫 반증) "
               "| 유지 — 전제는 좁혀졌으나 무너지지 않음 | 편집장 승인 |")
        sec = sec[:cut] + row + sec[cut:]
    w(axes_p, t[:s] + sec + t[e:])

    p = io.open(prof_p, encoding="utf-8").read()
    m = re.search(rf"(- id: {ma}\n(?:.*\n)*?\s*status: \{{ 지지: )(\d+)(, 반증: )(\d+)", p)
    if not m:
        raise RuntimeError(f"시험 픽스처 오류 — profiles 에 {ma} status 줄이 없다")
    w(prof_p, p[:m.start()] + m.group(1) + str(int(m.group(2)) - 1)
      + m.group(3) + str(int(m.group(4)) + 1) + p[m.end():])

    x = io.open(index_p, encoding="utf-8").read()
    m = re.search(rf"(- {ma} — \[[^\]]*\]\(axes\.md\) \(지지 )(\d+)( · 반증 )(\d+)", x)
    if not m:
        raise RuntimeError(f"시험 픽스처 오류 — index.md 에 {ma} 요약 줄이 없다")
    w(index_p, x[:m.start()] + m.group(1) + str(int(m.group(2)) - 1)
      + m.group(3) + str(int(m.group(4)) + 1) + x[m.end():])


def sweep_fixture(prof_path, when, miss=None, skip_note=None, cadence_typo=False):
    """상시(daily) 소스 전수의 last_checked 를 when 으로 옮긴다 (이슈 #36 시험).

    miss 에 소스 id 를 주면 그 하나만 옮기지 않는다 — 「1개 누락」 차단 케이스.
    skip_note 를 주면 miss 소스의 last_item 앞에 「건너뜀 <when> — <사유>」 를 끼운다
    — SKIP_RE 경고 강등 경로 시험 (2026-08-15 신설, 검수 문제 9b·18a).
    skip_note 에 miss=None 이면 **전수**에 건너뜀을 적는다 — 예외 경로 상한 시험.

    시드 날짜도 소스 id 도 cadence 어휘도 하드코딩하지 않는다 — 전부 프로파일에서
    읽는다(#33 의 교훈 + 2026-08-15 검수 문제 8a).
    """
    daily = set(daily_source_ids(prof_path))
    t = io.open(prof_path, encoding="utf-8").read()
    head, sep, body = t.partition("\nsources:\n")
    if not sep:
        raise RuntimeError("시험 픽스처 오류 — profiles 에 sources 블록이 없다")
    m = re.search(r"^\S", body, re.M)          # 다음 최상위 키 전까지가 sources 블록이다
    body, tail = (body[:m.start()], body[m.start():]) if m else (body, "")
    out, n, skipped = [], 0, 0
    for p in re.split(r"(?m)^(?=  - id: )", body):
        mid = re.match(r"  - id: (\S+)", p)
        sid = mid.group(1) if mid else None
        # 건너뜀 표기를 받을 소스는 last_checked 를 옮기지 않는다 — 옮기면 「그날 돈
        # 소스」가 되어 예외 경로 자체가 시험되지 않는다.
        gets_skip = bool(skip_note) and sid in daily and (miss is None or sid == miss)
        if sid in daily and sid != miss and not gets_skip:
            p2, k = re.subn(r"(?m)^    last_checked: .*$",
                            f"    last_checked: {when}", p)
            if k:
                p, n = p2, n + 1
        if gets_skip:
            p2, k = re.subn(r'(?m)^    last_item: "',
                            f'    last_item: "건너뜀 {when} — {skip_note} · ', p)
            if not k:   # last_item 이 없는 소스에는 새로 만든다
                p2 = p.rstrip("\n") + f'\n    last_item: "건너뜀 {when} — {skip_note}"\n'
            p, skipped = p2, skipped + 1
        out.append(p)
    if not n and not skipped:
        raise RuntimeError("시험 픽스처 오류 — 상시 소스의 last_checked 를 찾지 못했다")
    if skip_note and not skipped:
        raise RuntimeError("시험 픽스처 오류 — 건너뜀 표기를 넣지 못했다")
    body2 = "".join(out)
    if cadence_typo:
        # 정본(sweep_gate.known_cadence)에 없는 값을 한 소스에 심는다 — 종전 도구는 이런
        # 값을 만나면 그 소스를 **조용히 로스터에서 빼고 초록으로 통과**했다(검수 문제 6).
        first = sorted(daily)[0]
        body2, k = re.subn(rf"(?ms)(^  - id: {re.escape(first)}\n(?:(?!^  - id: ).)*?^    cadence: )\S+",
                           r"\g<1>매일(평일)", body2, count=1)
        if not k:
            raise RuntimeError("시험 픽스처 오류 — cadence 값을 바꾸지 못했다")
    w(prof_path, head + sep + body2 + tail)


def main():
    tmp = tempfile.mkdtemp(prefix="kit-selftest-")
    try:
        for d in ("tools", "templates", "profiles", "okf"):
            shutil.copytree(os.path.join(KIT_ROOT, d), os.path.join(tmp, d))
        j = lambda *p: os.path.join(tmp, *p)

        # ── 픽스처 ────────────────────────────────────────────────
        import json
        # check_review — 정상·우회 6종 (날짜당 기록 하나)
        w(j("eval", "review-2026-08-20.md"), review_record("2026-08-20"))
        w(j("eval", "review-2026-08-21.md"), review_record(
            "2026-08-21", headings=["### 심사", "", ""]))                # 렌즈 무정체
        w(j("eval", "review-2026-08-22.md"), review_record(
            "2026-08-22", scores=[[99, 7, 8, 7, 8, 8], [7, 8, 7, 8, 7, 8],
                                  [8, 8, 7, 8, 8, 7]], stated="12.67"))  # 점수 인플레
        w(j("eval", "review-2026-08-23.md"), review_record(
            "2026-08-23", reason=""))                                    # 사유 공백
        w(j("eval", "review-2026-08-24.md"), review_record(
            "2026-08-24", issues=False))                                 # 지적 표 부재
        w(j("eval", "review-2026-08-25.md"), review_record(
            "2026-08-25", target="output/web/2026-08-25.html"))          # 웹판 대상
        w(j("eval", "review-2026-08-26.md"), review_record("2026-08-26", cold=False))
        for d in ("20", "21", "22", "23", "24", "25", "26"):
            w(j("output", "web", f"2026-08-{d}.html"), "<h1>x</h1>")

        # check_insight — 정상 / 뼈대 배신 / 가짜 좌표
        w(j("output", "web", "2026-08-30.html"), PAGE)
        w(j("output", "web", "2026-09-05.html"), SPINE_OK)
        w(j("output", "web", "2026-09-06.html"), SPINE_LIST)
        w(j("eval", "proto-2026-08-30.md"), PROTO.format(date="2026.08.30"))
        w(j("output", "web", "2026-08-31.html"),
          PAGE.replace("광고 자본은 GPT로 움직이는가 — 답의 한 조각이 우리 손에 있다",
                       "다른 화두가 실렸다"))
        w(j("eval", "proto-2026-08-31.md"), PROTO.format(date="2026.08.31"))
        w(j("output", "web", "2026-09-01.html"), PAGE.replace("(F-038)", "(F-999)"))
        w(j("output", "web", "2026-09-04.html"), PAGE.replace(
            "광고 자본은 GPT로 움직이는가 — 답의 한 조각이 우리 손에 있다",
            "전환의 값은 세계가 먼저 매겼다 — 우리 증거는 오늘이 법정기한인 반기보고서부터다"))  # 34자 — 간명 상한 위반

        # check_run — 로스터 전수 / 한 줄 / 실패코드
        rows = [
            {"event": "end", "started_at": "2026-08-30T07:00:00",
             "ended_at": "2026-08-30T08:00:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL},
            {"event": "end", "started_at": "2026-08-31T07:00:00",
             "ended_at": "2026-08-31T08:00:00", "mode": "생산", "result": "산출",
             "gates": ["check_tables:0"]},
            {"event": "end", "started_at": "2026-09-01T07:00:00",
             "ended_at": "2026-09-01T08:00:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL[:-1] + ["check_publish:1"]},
            # 자정을 넘긴 실행 — 짝은 started_at 으로 맞춘다 (2026-08-15 실측, 이슈 #33).
            # ended_at 으로 날짜를 가르면 이 두 줄이 09-07/09-08 로 갈려,
            # 게이트를 전종 돌린 실행이 「게이트 기록 없는 발행」 으로 오진됐다.
            {"event": "start", "started_at": "2026-09-07T23:50:00",
             "session": "session-cron", "mode": "미정"},
            {"event": "end", "started_at": "2026-09-07T23:50:00",
             "ended_at": "2026-09-08T00:30:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL},
            # 소스 로스터 봉인 (이슈 #36) — 게이트 기록은 흠 없고 스윕 범위만 다른 날.
            # 같은 원장 줄을 여러 케이스가 공유하고, 갈리는 것은 프로파일 픽스처뿐이다.
            # 날짜는 **오늘**이다: 프로파일 last_checked 는 현재값 스냅샷이라 오늘 날짜에만
            # 뜻이 있고, 그 스냅샷 경로를 시험하려면 대상일이 오늘이어야 한다
            # (2026-08-15 재설계 — 검수 문제 1).
            {"event": "end", "started_at": TODAY + "T07:00:00",
             "ended_at": TODAY + "T08:00:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL},
            # 면제 구멍 (검수 문제 2·17) — 생산·발행 뒤에 **검증 세션을 이어 붙인** 날.
            # routine-SKILL 0-a 상 같은 날 두 번째 실행이 정확히 이 기록을 남기므로,
            # 「검증만 항목이 하나라도 있으면 면제」였던 종전 판정은 매일 재현되는 패턴으로
            # 봉인이 사라졌다. 위 산출 줄과 같은 날짜라, 이 줄이 있어도 면제되면 안 된다.
            {"event": "end", "started_at": TODAY + "T15:00:00",
             "ended_at": TODAY + "T15:10:00", "mode": "검증", "result": "검증만"},
            # 진짜 면제 대상 — 그날 원장이 검증 세션 하나뿐인 날. 게이트를 재실행해
            # gates 를 기록했더라도 「그날 지면을 만들었다」가 아니므로 스윕은 묻지 않는다.
            {"event": "end", "started_at": VERIFY_ONLY + "T15:00:00",
             "ended_at": VERIFY_ONLY + "T15:10:00", "mode": "검증", "result": "검증만",
             "gates": GATES_FULL},
            # 원장 sources 필드 (2026-08-15 신설) — 날짜별 스윕 이력이라 **과거 날짜**도
            # 판정된다. 여기서는 로스터 미달이므로 차단이 기대값이다.
            {"event": "end", "started_at": "2026-09-12T07:00:00",
             "ended_at": "2026-09-12T08:00:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL, "sources": ["dart-target"]},
            # 과거 날짜 + sources 필드 없음 — 스냅샷으로 판정하면 안 되는 날(회귀 보호).
            # 정상 발행된 옛 호(2026-08-11·08-12)가 새 게이트에 걸렸던 실측의 회귀 케이스다.
            {"event": "end", "started_at": "2026-09-13T07:00:00",
             "ended_at": "2026-09-13T08:00:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL},
            # 판정 불가 기록 (2026-08-15 신설 — 이슈 #37). CF 회선에서 E6 가 :2 로
            # 끝난 날이다. 로스터 대조는 여전히 차단하되 「기록된 실패(:1)」와는
            # 다른 사유로 갈라야 한다 — 처방이 산출물이 아니라 판정 경로이기 때문이다.
            {"event": "end", "started_at": UNDECIDED_DATE + "T07:00:00",
             "ended_at": UNDECIDED_DATE + "T08:00:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL[:-1] + ["check_publish:2"],
             "reason": "수동 확인 마감 — 소유자가 브라우저로 공유·핀 직접 확인"},
            # 같은 :2 인데 reason 이 **형식을 갖춘** 날 (2026-08-15 신설 — 검수 문제 4·9).
            # 확인 시각 + 어느 게이트를 대신 확인했는지 + 경위. 위 UNDECIDED_DATE 줄은
            # 시각도 게이트 이름도 없어 계속 차단이어야 한다 — 두 줄이 그 경계다.
            {"event": "end", "started_at": MANUAL_DATE + "T07:00:00",
             "ended_at": MANUAL_DATE + "T08:00:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL[:-1] + ["check_publish:2"],
             "reason": ("수동 확인 마감 2026-09-17 09:20 check_publish — 소유자가 사파리 "
                        "시크릿 창에서 공유 링크를 열어 Anyone with the link 와 핀 버전이 "
                        "오늘 호임을 확인했다 (CF 회선이라 기계 재판정 불가)")},
        ]
        w(j("output", "ledger", "run_log.jsonl"),
          "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        w(j("output", "web", "2026-09-07.html"), "<h1>x</h1>")   # 자정 넘김 호
        for d in (TODAY, EXEMPT_DATE, VERIFY_ONLY, "2026-09-12", "2026-09-13"):
            w(j("output", "web", f"{d}.html"), "<h1>x</h1>")     # 소스 로스터 케이스 호

        w(j("output", "web", f"{UNDECIDED_DATE}.html"), "<h1>x</h1>")

        # check_publish — CF 챌린지 케이스의 호와 URL 기록 (이슈 #37).
        # uuid 는 형식만 맞으면 된다 — 스텁이 응답을 대신하므로 실제 조회는 없다.
        w(j("output", "web", f"{CF_DATE}.html"), "<h1>x</h1>")
        w(j("output", f"artifact-url-{CF_DATE}.txt"),
          "https://claude.ai/code/artifact/00000000-0000-4000-8000-000000000001\n")

        # check_formats --check-links 케이스의 호 (2026-08-15 신설 — 검수 문제 6).
        # 판형 바 + 링크 하나 + 당일 URL 기록 — 정적 판정은 통과하고 링크 판정만 갈린다.
        w(j("output", "web", f"{CFL_DATE}.html"),
          f"<title>{FMT_TITLE}</title><h1>x</h1>"
          f'<div class="fmtbar"><span class="fseg on">웹 버전</span>'
          f'<a class="fseg" href="{FMT_LINK}">라디오 버전</a></div>')
        w(j("output", f"artifact-url-{CFL_DATE}.txt"),
          "https://claude.ai/code/artifact/00000000-0000-4000-8000-000000000001\n")
        w(j("output", "web", f"{MANUAL_DATE}.html"), "<h1>x</h1>")

        # check_theme — data-macro 정상 / 오타
        w(j("output", "web", "2026-09-02.html"), THEME_PAGE.format(macro="M2A"))
        w(j("eval", "theme-2026-09-02.md"), THEME_EVAL)
        w(j("output", "web", "2026-09-03.html"), THEME_PAGE.format(macro="MA1"))
        w(j("eval", "theme-2026-09-03.md"), THEME_EVAL)

        # sync_skill — 마스터 합성
        w(j("master-clean.md"), MASTER_CLEAN)
        w(j("master-leaky.md"), MASTER_LEAKY)

        # ── 케이스 ────────────────────────────────────────────────
        # (라벨, 도구, 인자, 기대 exit, 사전 변형 or None, 사후 복원 or None)
        A = j("okf", "axes.md")
        F98 = j("okf", "facts", "f-098.md")

        # 프로파일 경로는 파일명 리터럴로 잡지 않는다 — 도구가 쓰는 것과 같은 해석기로
        # 고른다 (2026-08-15, 검수 문제 7·8 동형). 사본에는 config.yaml 이 없으므로
        # 「profiles/ 유일 파일」 폴백이 걸린다.
        sys.path.insert(0, j("tools"))
        from profile_lib import resolve_profile as _rp
        PROF, _why = _rp(tmp)
        if PROF is None:
            raise RuntimeError(f"시험 픽스처 오류 — 프로파일을 고르지 못했다: {_why}")

        # 반증→재귀납 케이스용 3중 장부 스냅샷 (이슈 #35) — 변형은 세 파일에 걸치므로
        # 되돌림도 세 파일 통째로 한다.
        TRIO = [A, PROF, j("okf", "index.md")]
        SAVED = {}

        def refute_setup(record, record_date=None):
            def setup():
                SAVED.clear()
                SAVED.update({p: io.open(p, encoding="utf-8").read() for p in TRIO})
                refute_fixture(TRIO, record=record, record_date=record_date)
            return setup

        def axes_setup(fn):
            """axes.md 만 변형하는 케이스의 저장/복원 (⑥ⓐ·⑥ⓒ 시험용)."""
            def setup():
                SAVED.clear()
                SAVED[A] = io.open(A, encoding="utf-8").read()
                fn(A)
            return setup

        def drop_distill(path):
            """축 하나의 증류 슬롯만 지운다 — ⑥ⓐ 는 「일부만 없음」을 차단해야 한다."""
            t = io.open(path, encoding="utf-8").read()
            m = re.search(r"^\*\*현재 판정\(증류\)\*\*.*?(?=\n\n)", t, re.M | re.S)
            if not m:
                raise RuntimeError("시험 픽스처 오류 — axes.md 에 증류 슬롯이 없다")
            w(path, t[:m.start()] + t[m.end():])

        def refute_restore():
            for p, t in SAVED.items():
                w(p, t)

        # 소스 로스터 케이스용 프로파일 스냅샷 (이슈 #36) — 픽스처가 last_checked 를
        # 옮기므로 케이스마다 원본으로 되돌린다.
        PROF_SAVED = {}

        # 「빠뜨릴 소스」는 정본에서 읽는다 — 코드에 id 를 박으면 프로파일에서 개명·삭제될 때
        # 픽스처가 아무 소스도 빼지 않고 전수 갱신해, 케이스가 엉뚱한 이유로 통과한다
        # (2026-08-15 검수 문제 8a — 종전 miss="trade-press").
        MISS_ID = sorted(daily_source_ids(PROF))[0]

        def sweep_setup(when, miss=None, skip_note=None, cadence_typo=False):
            def setup():
                PROF_SAVED["t"] = io.open(PROF, encoding="utf-8").read()
                sweep_fixture(PROF, when, miss, skip_note, cadence_typo)
            return setup

        def sweep_restore():
            if "t" in PROF_SAVED:
                w(PROF, PROF_SAVED.pop("t"))

        # CF 챌린지 케이스 (이슈 #37) — 진짜 check_formats 를 옆으로 밀어 두고 스텁을
        # 세운다. 스텁이 정본을 재수출하므로 판정 로직은 그대로 시험되고, 네트워크는
        # 한 번도 타지 않는다. 케이스가 끝나면 원본을 되돌린다.
        CFM = j("tools", "check_formats.py")
        CFM_REAL = j("tools", "check_formats_real.py")

        def cf_setup(seq):
            """seq: [(코드, 본문, 헤더dict), ...] — 대본대로 urlopen 을 세운다."""
            def setup():
                os.rename(CFM, CFM_REAL)
                w(CFM, CF_STUB.replace("@SEQ@", repr(seq)))
            return setup

        def cf_restore():
            if os.path.exists(CFM_REAL):
                os.remove(CFM)
                os.rename(CFM_REAL, CFM)

        cases = [
            ("review 정상 기록(뼈대 대상·config 부재 rubric 폴백)", "check_review.py",
             ["output/web/2026-08-20.html"], 0, None, None),
            ("review 렌즈 무정체 — 단일 제목 표 3개", "check_review.py",
             ["output/web/2026-08-21.html"], 1, None, None),
            ("review 점수 99 인플레", "check_review.py",
             ["output/web/2026-08-22.html"], 1, None, None),
            ("review 사유 전 칸 공백", "check_review.py",
             ["output/web/2026-08-23.html"], 1, None, None),
            ("review 지적 목록 표 부재", "check_review.py",
             ["output/web/2026-08-24.html"], 1, None, None),
            ("review 심사 대상=웹판 (비소급)", "check_review.py",
             ["output/web/2026-08-25.html"], 1, None, None),
            ("review 심사 대상=웹판 (--retro)", "check_review.py",
             ["output/web/2026-08-25.html", "--retro"], 0, None, None),
            ("review cold 표 누락 (panel 4렌즈 전수)", "check_review.py",
             ["output/web/2026-08-26.html"], 1, None, None),
            ("insight 정상 — 좌표 실존·뼈대 일치", "check_insight.py",
             ["output/web/2026-08-30.html"], 0, None, None),
            ("insight 화두 칸 자립 — 사람 문장 + 좌표 병기 (I8b)", "check_insight.py",
             ["output/web/2026-09-05.html"], 0, None, None),
            ("insight 화두 칸 좌표 나열·지시어 단문 (I8b 차단)", "check_insight.py",
             ["output/web/2026-09-06.html"], 1, None, None),
            ("insight 뼈대 배신 — 화두 실종", "check_insight.py",
             ["output/web/2026-08-31.html"], 1, None, None),
            ("insight 가짜 좌표 (F-999)", "check_insight.py",
             ["output/web/2026-09-01.html"], 1, None, None),
            ("insight h1 간명 상한 초과 (공백 제외 34자 > 30)", "check_insight.py",
             ["output/web/2026-09-04.html"], 1, None, None),
            # 산출을 낸 날은 상시 소스 로스터(#36)도 같이 판정되므로, 통과 기대 케이스는
            # 프로파일의 last_checked 를 그날로 옮긴 상태에서 돌린다.
            ("run 로스터 전수 기록", "check_run.py",
             ["--date", "2026-08-30", tmp], 0, sweep_setup("2026-08-30"), sweep_restore),
            ("run 한 줄 기록 — 로스터 미달", "check_run.py",
             ["--date", "2026-08-31", tmp], 1, None, None),
            ("run 실패코드 :1 기록", "check_run.py",
             ["--date", "2026-09-01", tmp], 1, None, None),
            ("run 자정 넘긴 실행 — 시작일에서 짝이 잡힌다", "check_run.py",
             ["--date", "2026-09-07", tmp], 0, sweep_setup("2026-09-07"), sweep_restore),
            ("run 자정 넘긴 실행 — 종료일은 안 돈 날이다", "check_run.py",
             ["--date", "2026-09-08", tmp], 1, None, None),
            # 소스 로스터 봉인 (이슈 #36) — 조용히 좁게 돈 날을 잡는다.
            # 대상일은 오늘이다(스냅샷 경로는 오늘에만 뜻이 있다 — 검수 문제 1).
            ("run 상시 소스 전수 갱신", "check_run.py",
             ["--date", TODAY, tmp], 0, sweep_setup(TODAY), sweep_restore),
            ("run 상시 소스 1개 누락 — 차단", "check_run.py",
             ["--date", TODAY, tmp], 1,
             sweep_setup(TODAY, miss=MISS_ID), sweep_restore),
            # 검수 문제 2·17 — 「생산 후 검증만 세션을 한 번 더 기록」이 IG7 을 무력화했다.
            # 프로파일은 손대지 않는다(= last_checked 방치). 종전 판정은 여기서 exit 0 이었다.
            ("run 산출+검증만 겹친 날 — 면제되지 않는다", "check_run.py",
             ["--date", TODAY, tmp], 1, None, None,
             "!고지: 그날 생산 기록이 없는"),   # 이 고지가 뜨면 면제된 것이다 — 뜨면 안 된다
            ("run 생산 기록 없는 날(검증만) — 면제", "check_run.py",
             ["--date", VERIFY_ONLY, tmp], 0, None, None),
            # SKIP_RE 경고 강등 경로 (검수 문제 9b·18a) — 사유를 적은 건너뜀은 막지 않는다
            ("run 사유 기록 건너뜀 1건 — 경고 강등", "check_run.py",
             ["--date", TODAY, tmp], 0,
             sweep_setup(TODAY, miss=MISS_ID, skip_note="사이트 장애"), sweep_restore),
            # 같은 경로의 상한 (검수 문제 18 후단) — 전수에 사유를 적으면 그날 스윕은 0건이다
            ("run 로스터 전수 건너뜀 — 상한 차단", "check_run.py",
             ["--date", TODAY, tmp], 1,
             sweep_setup(TODAY, skip_note="사이트 장애"), sweep_restore),
            # 정본 밖 cadence 어휘 (검수 문제 6) — 조용히 로스터에서 빠지지 않는다
            ("run 정본 밖 cadence 어휘 — 차단", "check_run.py",
             ["--date", TODAY, tmp], 1,
             sweep_setup(TODAY, cadence_typo=True), sweep_restore),
            # 과거 날짜 회귀 보호 (검수 문제 1) — 스냅샷을 시계열 판정에 쓰지 않는다.
            # 이 케이스가 종전 설계에서 정상 발행된 옛 호를 실패로 뒤집던 자리다.
            ("run 과거 날짜·원장 sources 없음 — 판정 생략(회귀 보호)", "check_run.py",
             ["--date", "2026-09-13", tmp], 0, None, None),
            # 원장 sources 필드로는 과거도 판정된다 (같은 수리의 반대편)
            ("run 과거 날짜·원장 sources 미달 — 차단", "check_run.py",
             ["--date", "2026-09-12", tmp], 1, None, None),
            ("theme data-macro 정상(MA1)", "check_theme.py",
             ["output/web/2026-09-03.html"], 0, None, None),
            ("theme data-macro 오타(M2A)", "check_theme.py",
             ["output/web/2026-09-02.html"], 1, None, None),
            ("ledger 원본 정합", "check_ledger.py", [tmp], 0, None, None),
            ("ledger 미태깅 신규 사실", "check_ledger.py", [tmp], 1,
             lambda: w(F98, io.open(j("okf", "facts", "f-055.md"),
                                    encoding="utf-8").read().replace("f-055", "f-098")),
             lambda: os.remove(F98)),
            ("ledger 점수판 오기", "check_ledger.py", [tmp], 1,
             lambda: bump_score(A, +1),
             lambda: bump_score(A, -1)),
            # ⑥ⓑ 증류 루프 봉인 (이슈 #35) — 반증이 났는데 축을 되보지 않은 발행을 막는다
            ("ledger 반증 첫 발생 + 재귀납 기록 있음", "check_ledger.py", [tmp], 0,
             refute_setup(True), refute_restore),
            ("ledger 반증 첫 발생 · 재귀납 기록 없음 — 차단", "check_ledger.py", [tmp], 1,
             refute_setup(False), refute_restore),
            # ⑥ⓑ 가 최초 1회용이 아님을 고정한다 (검수 문제 13) — 기록이 최신 반증보다
            # 이르면 차단. 종전 판정(날짜 행 존재만)에서는 이 케이스가 통과했다.
            ("ledger 재귀납 기록이 최신 반증보다 이르다 — 차단", "check_ledger.py", [tmp], 1,
             refute_setup(True, record_date="2020-01-01"), refute_restore),
            # ⑥ⓐ — 축 일부에만 증류 슬롯이 없으면 차단 (도입한 킷에는 전수를 요구한다)
            ("ledger 증류 슬롯 1축 부재 — 차단", "check_ledger.py", [tmp], 1,
             axes_setup(drop_distill), refute_restore),
            # ⑥ⓒ — 「미탐색」 자백 행은 탐색 기록으로 세지 않는다 (검수 문제 4).
            # 시드 axes.md 의 첫 행이 정확히 그 자백이므로, 경고가 떠야 한다(차단은 아님).
            ("ledger 미탐색 자백 행은 ⑥ⓒ 를 통과시키지 않는다", "check_ledger.py", [tmp], 0,
             None, None, "반증 탐색 이력에 최근 발행일"),
            # 종료코드 3분법 (2026-08-15 신설 — 이슈 #37). 판정 불가는 0 도 1 도 아니다:
            # 통과로 내면 깨진 것을 내보내고(#21 회귀), 실패로 내면 멀쩡한 호에 E5 처방
            # (MP3 재이식·재발행)을 지시한다 — 실측 오진이 정확히 그것이었다.
            ("publish 대조군이 CF 챌린지 — 대상 조회 전에 판정 불가(2)", "check_publish.py",
             [CF_DATE], 2, cf_setup([R_CF_HDR]), cf_restore,
             "대조군(무작위 uuid) 조회에서"),
            ("publish 대상 조회가 CF 챌린지 — 판정 불가(2)·E5 처방 없음", "check_publish.py",
             [CF_DATE], 2, cf_setup([R_401, R_CF_HDR]), cf_restore,
             "!MP3 재이식"),   # 봇 차단에 E5 처방을 내면 멀쩡한 호를 고치게 된다
            # 헤더 없는 챌린지(본문 표식만·403) — 이 갈래가 실제 CF 회선의 탐지 하중
            # 지점이다. urlopen 층 스텁이라 정본 fetch_anon 의 HTTPError·e.read()
            # 갈래가 실제로 돈다 (2026-08-15 신설 — 검수 문제 3).
            ("publish 헤더 없는 CF 본문(403) — HTTPError 갈래로 판정 불가(2)", "check_publish.py",
             [CF_DATE], 2, cf_setup([R_401, R_CF_BODY]), cf_restore,
             "응답 본문에 「just a moment」"),
            # 200 응답 + cf-mitigated **헤더** — 헤더는 지면이 못 붙이는 표식이라
            # 200 에서도 CF 로 본다 (좁히기의 반대편 경계, 검수 문제 8)
            ("publish 200 + cf-mitigated 헤더 — 판정 불가(2)", "check_publish.py",
             [CF_DATE], 2,
             cf_setup([R_401, (200, '{"mode":"public","ver":"v1"}',
                               {"cf-mitigated": "challenge"})]), cf_restore,
             "응답 헤더 cf-mitigated"),
            # 정상 200 인데 **지면이 CF 문구를 인용**한 호 — 판정 불가로 접히면
            # 멀쩡한 호가 새 호 마감 규칙상 기계로 영영 닫히지 않는다 (검수 문제 1·8).
            # 재현 근거: cf_challenge('<h1>Just a moment, please</h1>', {}) 가 히트를 냈다.
            ("publish 발행본 지면이 CF 문구를 인용해도 200 이면 통과(0)", "check_publish.py",
             [CF_DATE], 0, cf_setup([R_401, R_META_OK, R_BODY_CITES_CF]), cf_restore,
             "통과: 공유 ON"),
            # E7 로스터 게이트도 같은 3분법을 쓴다 (검수 문제 2·6) — CF 회선에서
            # E6 는 2, E7 은 1 로 갈리면 실행자는 E1/E7 문안대로 공유를 다시 켜고
            # 재발행하러 간다. 그것이 이슈 #37 이 「멀쩡한 호를 고치게 한다」고 적은 행동이다.
            ("formats --check-links CF 챌린지 — 판정 불가(2)", "check_formats.py",
             [f"output/web/{CFL_DATE}.html", "--no-deck", "--check-links"], 2,
             cf_setup([R_CF_HDR]), cf_restore, "판정 불가"),
            ("formats --check-links CF 챌린지 — 「공유 OFF 의심」 오진 없음", "check_formats.py",
             [f"output/web/{CFL_DATE}.html", "--no-deck", "--check-links"], 2,
             cf_setup([R_CF_BODY]), cf_restore, "!공유 OFF 의심"),
            # with_headers 이식이 정상 경로를 깨지 않았는가 (회귀 보호)
            ("formats --check-links 정상 개통 — 통과(0)", "check_formats.py",
             [f"output/web/{CFL_DATE}.html", "--no-deck", "--check-links"], 0,
             cf_setup([(200, '{"mode":"public","title":"%s"}' % FMT_TITLE, {}),
                       (200, '{"mode":"public","ver":"v1"}', {}),
                       (200, FMT_TITLE + " " + FMT_LINK, {})]), cf_restore,
             "발행본 대조"),
            # 2 를 「판정 불가」에 내주면서 사용법 오류는 64 로 옮겼다 — 뜻이 겹치면
            # gates 기록에서 「모르겠다」와 「인자 오타」가 구분되지 않는다.
            ("publish 인자 형식 오류 — 사용법(64)", "check_publish.py",
             ["not-a-date"], 64, None, None),
            # 로스터 대조의 반대편 — :2 는 여전히 차단하되 사유가 다르다
            ("run gates 에 check_publish:2 — 판정 불가로 미완결 차단", "check_run.py",
             ["--date", UNDECIDED_DATE, tmp], 1, None, None, "판정 불가(:2)"),
            # 「수동 확인 마감」의 기계 상태 (2026-08-15 신설 — 검수 문제 4·9).
            # 종전에는 :2 를 **언제나** 1 로 막아, 수동 확인으로 닫은 날이 다음날
            # 점검에서 영구히 실패로 남았다 — 그 압력이 :2 대신 :0 을 적게 만든다.
            ("run :2 + 형식 갖춘 수동 확인 마감 — 형식 봉인으로 통과(0)", "check_run.py",
             ["--date", MANUAL_DATE, tmp], 0, None, None, "수동 확인 마감으로 닫은 날"),
            # 반대편 — 같은 :2 인데 시각·게이트명이 없으면 종전대로 차단.
            # 자기 보고 문구 한 줄을 봉인으로 치지 않는다 (검수 문제 9 덧글).
            ("run :2 + 시각 없는 수동 확인 문구 — 차단(형식 미달)", "check_run.py",
             ["--date", UNDECIDED_DATE, tmp], 1, None, None, "확인 시각"),
            # 통과 줄 꼬리 (이슈 #37 ④) — 「통과」 한 줄만 보고 넘어가는 실행자에게
            # D8 이 검증된 임계가 아니라는 사실을 출력으로 올린다
            ("size 통과 줄에 편집 규율 꼬리", "check_size.py",
             ["output/web/2026-08-30.html"], 0, None, None, "D8 은 편집 규율이다"),
            ("sync 유닉스 경로 누출", "sync_skill.py",
             ["--check", j("master-leaky.md")], 1, None, None),
            ("sync 클린 마스터 (--check 무기록)", "sync_skill.py",
             ["--check", j("master-clean.md")], 0, None, None),
        ]

        failed = []
        for case in cases:
            label, tool, args, want, setup, teardown = case[:6]
            # 7번째 칸(선택) — 출력 대조 (2026-08-15 신설, 검수 문제 18: 종전 시험은
            # **종료코드만** 보고 메시지를 보지 않아, 같은 exit 로 이유가 바뀌어도 몰랐다).
            # 「!」 로 시작하면 **없어야 할** 문자열이다 (면제 고지처럼, 뜨는 것 자체가 실패).
            expect = case[6] if len(case) > 6 else None
            if setup:
                setup()
            try:
                r = subprocess.run([sys.executable, j("tools", tool)] + args,
                                   capture_output=True, text=True, cwd=tmp,
                                   encoding="utf-8", errors="replace")
                got = r.returncode
            finally:
                if teardown:
                    teardown()
            ok = got == want
            note = ""
            if ok and expect:
                neg = expect.startswith("!")
                needle = expect[1:] if neg else expect
                hit = needle in (r.stdout or "")
                if hit == neg:
                    ok, note = False, (f" · 출력에 「{needle}」 이 "
                                       + ("있으면 안 되는데 있다" if neg else "없다"))
            print(f"{'OK  ' if ok else 'FAIL'} [{tool[:-3]}] {label} — exit {got} (기대 {want}){note}")
            if not ok:
                failed.append((label, (r.stdout or "").strip().splitlines()[-3:]))

        print(f"— 케이스 {len(cases)} · 불일치 {len(failed)}")
        if failed:
            for label, tail in failed:
                print(f"불일치 상세 [{label}]:")
                for ln in tail:
                    print("   ", ln)
            sys.exit(1)
        print("통과: 게이트 통과/차단 계약 전 케이스 기대 일치 — 게이트를 고쳤다면 이 줄을 근거로 커밋하라")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
