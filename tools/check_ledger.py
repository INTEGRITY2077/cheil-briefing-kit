# -*- coding: utf-8 -*-
"""원장 정합 게이트 (D7) — 배포본 시드 원장의 자기모순을 정적으로 판정.

사용: python tools/check_ledger.py [킷루트] [--profile 이름]
      (킷루트 생략 시 이 스크립트의 상위 디렉토리. 프로파일 선택은 tools/profile_lib.py —
       --profile > config.yaml `profile:` > profiles/ 유일 파일 순. 2026-08-15 수리:
       종전에는 `profiles/cheil.yaml` 이 코드에 박혀 있어, 다른 프로파일을 얹은 설치본에
       cheil.yaml 이 남아 있으면 엉뚱한 프로파일로 판정했다 — 규율 ② 위반, 검수 문제 7)

규칙 (2026-08-12 이슈 #7에서 나온 것):
  JSONL 정본(output/ledger — gitignore 대상)에만 쓰고 okf/ 미러를 빠뜨리면,
  배포본에는 실체 없는 손가락(F-###)만 남는다. 새 설치본은 그걸 조회할 방법이
  없고, 대체된 수치를 유효한 최신값으로 방송한다. 셋 다 정적으로 판정 가능하다.

  ① 매달린 참조 — okf/**·profiles/** 텍스트의 F-###(-x) 참조는 전부
     okf/facts/f-###.md 로 실존해야 한다 (매달린 참조 0건)
  ② 상태 정합 — status: deprecated 인 개념이 index.md 「사실 — 유효」에
     남아 있으면 실패. 「사실 — 대체됨」에 등재돼 있어야 한다
  ③ 인덱스 신선도 — index.md 의 generated.at 이 facts 최신 파일의
     generated.at 보다, 그리고 log.md 최신 항목 날짜보다 오래되면 실패
     (routine 7절 재생성 누락 검출)

큰축 축적 봉인 (2026-08-14 이슈 #27 — 태깅 누락·점수판 오기·3중 장부 표류가
전부 무탐이던 실측에서. okf/axes.md 가 없으면 두 판정은 생략·고지한다):
  ④ 큰축 등재 완결 — status: stable 인 사실 전수가 okf/axes.md 의 계보 표
     또는 무소속 판정 원장에 등재돼 있어야 한다 (axes.md 증분 원칙 「여기 없고
     계보에도 없는 유효 사실이 생기면 그것이 미검토다」의 기계화)
  ⑤ 점수판 3중 장부 대조 — 축별 계보 표의 방향(지지/반증/조건형성/중립) 행 수를
     재계산해 ⓐ axes.md **점수판** 줄 ⓑ profiles macro_axes.status
     ⓒ okf/index.md 큰축 요약 셋 모두와 대조한다. 최신 관측 F-ID 는 계보 실존만
     본다. 수동 집계가 어긋난 채 발행되는 것을 막는다 — 집계의 정본은 계보 표다

증류·재귀납 봉인 (2026-08-15 이슈 #35 — 실측: 원장 67건의 방향 태그가 반증 0,
세 축 점수판도 전부 반증 0. 반증 재료(챗GPT CPM $60→$25·OpenAI 목표 대비 10%
페이스·빅6 점유율 44.6%→29.6%)가 지면에 실려 있는데도 계상되지 않았다 — 축이
옳아서가 아니라 아무도 반증을 찾지 않았기 때문이다):
  ⑥ⓐ 증류 명제 — 축마다 axes.md 에 「**현재 판정(증류)**」 슬롯이 있고, 그 줄의
     근거 좌표(F-###)가 전부 실존하고 **status: deprecated 가 아니어야** 한다.
     문장의 내용(옳은가·신선한가)은 보지 않는다(황금률)
  ⑥ⓑ 재귀납 기록 — profiles macro_axes[].reinduct_when 의 「반증 >= N」 조건이
     계보 재계산으로 충족됐는데 그 축의 「### 재귀납 기록」 표에 날짜 행이 없거나,
     **가장 최근 기록이 가장 최근 반증 등재일보다 이르면** 실패.
     재귀납의 내용(유지/분할/합병/신설)은 사람·패널 몫이라 보지 않는다
  ⑥ⓒ 반증 탐색 이력 — 축마다 「### 반증 탐색 이력」의 최신 **탐색** 날짜가 log.md 최신
     발행일보다 이르면 **경고**(차단 아님). 「안 찾은 날」과 「찾았는데 없는 날」을
     가르는 기록이라, 없으면 반증 0 이 관측 결과인지 미탐색인지 알 수 없다

2026-08-15 ⑥ 수리 (검수 문제 4·5·13·19-1·19-2) — 넷 다 「형식만 본다」가 규율로는
옳고 효과로는 공허해지던 지점이다:
  · ⓒ 자기 참조 순환 — 채널 도입 당일 세 축에 들어간 첫 행이 「미탐색 — 다음 실행부터
    상설」이었는데 ⓒ 는 날짜 행의 **존재만** 봤다. 「아무것도 탐색하지 않았다」는 자백이
    「탐색 기록이 있다」 판정을 만들었다. 이제 결과 칸이 프로파일
    `refute_sweep.log_result_vocab.non_search` 어휘로 시작하는 행은 탐색으로 세지 않는다
    (어휘는 정본, 도구는 읽어서 판정만 — 규율 ②).
  · MM-DD 연도 붕괴 — `max(dates) < log_latest[5:]` 는 문자열 비교라, 작년 12월 기록이
    올해 8월 미탐색을 덮었다(실측: 08-15 행을 12-30 으로 바꾸자 경고 없이 EXIT=0).
    이제 표기 정본은 `YYYY-MM-DD` 이고, MM-DD 는 기준일 ±(과거 무제한/미래 31일)
    창 안에서 연도를 추정한 뒤 경고를 남긴다.
  · ⓑ 최초 1회용 — 첫 반증 때 한 줄 넣으면 이후 반증이 쌓여도 그 축은 영구 통과였다.
    이제 최신 재귀납 기록이 최신 반증 등재일 이후여야 한다.
  · ⓐ 무경고 즉시 차단 — 다른 프로파일 설치본은 axes.md 에 슬롯을 손으로 넣기 전까지
    발행이 막혔다(저자가 선례로 든 ⑤ⓑ 는 못 읽으면 경고 후 강등이었다). 이제 **전 축에
    슬롯이 하나도 없으면** 미도입 킷으로 보고 경고 후 강등하고, 일부 축에만 있으면
    나머지를 차단한다(도입한 킷에는 전수를 요구한다).

전부 정적 검사라 네트워크 없이 돌릴 수 있다. 실패 시 종료코드 1.
"""
import io, os, re, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profile_lib import resolve_profile  # noqa: E402 — 프로파일 선택의 단일 정본 해석기

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

USAGE = "사용법: python tools/check_ledger.py [킷루트]"

REF_RE = re.compile(r"\b[Ff]-\d{3}(?:-[xX])?\b")  # f-100 이후 세 자리 전체 커버 (첫 자리 0 고정이면 f-1## 매달림을 놓친다)
GEN_AT_RE = re.compile(r"^generated:\s*\{[^}]*\bat:\s*([0-9T:\-]+)Z?\s*[},]", re.M)
STATUS_RE = re.compile(r"^status:\s*(\S+)", re.M)
LOG_DATE_RE = re.compile(r"^##\s*(\d{4}-\d{2}-\d{2})", re.M)
# ⑥ 증류·재귀납 봉인 (이슈 #35)
DISTILL_RE = re.compile(r"^\*\*현재 판정\(증류\)\*\*\s*(.+?)(?=\n\n|\n###|\Z)", re.M | re.S)
# 원장 표의 날짜 칸. 표기 정본은 YYYY-MM-DD 이고, 옛 MM-DD 표기도 읽되 연도를 추정한다
# (2026-08-15 — 검수 문제 5: MM-DD 문자열 비교는 해가 바뀌는 순간 조용히 죽는다).
ROW_DATE_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2}|\d{2}-\d{2})\s*\|", re.M)
# 표 한 행을 칸으로 가른다 (⑥ⓒ 가 「결과」 칸을 읽는다)
ROW_CELLS_RE = re.compile(r"^\|(.+)\|\s*$", re.M)
REFUTE_COND_RE = re.compile(r"^\s*반증\s*(>=|>)\s*(\d+)\s*$")   # reinduct_when 중 기계가 읽는 유일한 조건
# ⑥ⓒ 결과 칸 어휘의 폴백 — 정본은 프로파일 refute_sweep.log_result_vocab.non_search 다.
# 못 읽으면 이 값으로 강등하고 경고한다 (⑤ⓑ 선례: 조용히 통과시키지 않는다).
NON_SEARCH_FALLBACK = ["미탐색", "미실행", "건너뜀"]
# 미래 허용 폭 — MM-DD 의 연도를 추정할 때, 기준일보다 이만큼까지는 미래를 허용한다.
# 기록 표에는 기준일(log.md 최신 발행일)보다 며칠 뒤인 오늘 행이 정상적으로 들어온다.
FUTURE_SLACK = timedelta(days=31)


def norm_date(s, ref):
    """표 날짜 문자열을 YYYY-MM-DD 로 정규화한다. (값, 연도추정여부) 를 돌려준다.

    MM-DD 는 기준일 `ref`(YYYY-MM-DD) 주변에서 연도를 고른다 — 후보 연도 중
    `ref + FUTURE_SLACK` 이하이면서 ref 에 가장 가까운 것. 그래서 8월 기준일에서
    12-30 은 **작년** 12-30 이 되고, 「작년 12월 기록이 올해 8월 미탐색을 덮는」
    연도 붕괴가 생기지 않는다 (2026-08-15 실측 수리, 검수 문제 5).
    """
    if len(s) == 10:
        return s, False
    try:
        y0 = int(ref[:4])
        rd = date.fromisoformat(ref)
    except ValueError:
        return s, True
    best = None
    for y in (y0 - 1, y0, y0 + 1):
        try:
            cand = date(y, int(s[:2]), int(s[3:5]))
        except ValueError:
            continue
        if cand > rd + FUTURE_SLACK:
            continue
        if best is None or abs((cand - rd).days) < abs((best - rd).days):
            best = cand
    return ((best or date(y0, 1, 1)).isoformat(), True)


def read(path):
    """BOM 이 섞인 파일도 있으므로 utf-8-sig 로 읽는다."""
    return io.open(path, encoding="utf-8-sig").read()


def subsection(sec_text, title):
    """축 절(`## MA#`) 안의 `### <제목>` 소절 본문. 없으면 None (⑥ 전용)."""
    for part in re.split(r"^### +", sec_text, flags=re.M)[1:]:
        if part.startswith(title):
            return part
    return None


def iter_text_files(*roots):
    for root in roots:
        if not os.path.isdir(root):
            continue
        for d, _, files in os.walk(root):
            for f in files:
                if f.lower().endswith((".md", ".yaml", ".yml", ".txt")):
                    yield os.path.join(d, f)


def parse_args(argv):
    kit, profile = None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--profile":
            if i + 1 >= len(argv):
                sys.exit(USAGE)
            profile, i = argv[i + 1], i + 2
        elif a.startswith("--profile="):
            profile, i = a.split("=", 1)[1], i + 1
        elif a.startswith("-"):
            sys.exit(USAGE)
        else:
            kit, i = a, i + 1
    if kit is None:
        kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return kit, profile


def main():
    kit, profile_name = parse_args(sys.argv[1:])
    okf = os.path.join(kit, "okf")
    facts_dir = os.path.join(okf, "facts")
    index_path = os.path.join(okf, "index.md")
    log_path = os.path.join(okf, "log.md")
    for p in (okf, facts_dir, index_path, log_path):
        if not os.path.exists(p):
            sys.exit(f"{USAGE}\n실패: {p} 가 없다 — 킷루트가 맞는지 확인")

    errors = []

    # ① 매달린 참조 — okf/**·profiles/** 의 F-### 참조 전수 대조
    refs = {}  # id(소문자) -> 첫 발견 위치
    for path in iter_text_files(okf, os.path.join(kit, "profiles")):
        text = read(path)
        for n, line in enumerate(text.splitlines(), 1):
            for m in REF_RE.finditer(line):
                rid = m.group(0).lower()
                refs.setdefault(rid, f"{os.path.relpath(path, kit)}:{n}")
    for rid in sorted(refs):
        if not os.path.exists(os.path.join(facts_dir, rid + ".md")):
            errors.append(f"[매달린 참조] {rid.upper()} — {refs[rid]} 에서 참조되는데 okf/facts/{rid}.md 가 없다")

    # 사실 파일 전수 파싱 (②·③ 공용)
    fact_status, fact_gen = {}, {}
    for f in sorted(os.listdir(facts_dir)):
        if not f.endswith(".md"):
            continue
        text = read(os.path.join(facts_dir, f))
        rid = f[:-3]
        m = STATUS_RE.search(text)
        fact_status[rid] = m.group(1) if m else None
        if fact_status[rid] is None:
            errors.append(f"[형식] okf/facts/{f} 에 status 프론트매터가 없다")
        g = GEN_AT_RE.search(text)
        if g:
            fact_gen[rid] = g.group(1)

    # ② 상태 정합 — deprecated 가 index 「유효」에 남아 있으면 실패
    index_text = read(index_path)
    m_valid = re.search(r"^# 사실 — 유효\n(.*?)(?=^# )", index_text, re.M | re.S)
    m_dep = re.search(r"^# 사실 — 대체됨\n(.*)", index_text, re.M | re.S)
    if not m_valid or not m_dep:
        errors.append("[인덱스] index.md 에 「사실 — 유효」/「사실 — 대체됨」 절이 없다")
    else:
        valid_ids = set(re.findall(r"facts/(f-\d{3}(?:-x)?)\.md", m_valid.group(1)))
        dep_ids = set(re.findall(r"facts/(f-\d{3}(?:-x)?)\.md", m_dep.group(1)))
        for rid, st in sorted(fact_status.items()):
            if st == "deprecated":
                if rid in valid_ids:
                    errors.append(f"[상태 충돌] {rid} 는 status: deprecated 인데 index 「사실 — 유효」에 남아 있다")
                if rid not in dep_ids:
                    errors.append(f"[상태 충돌] {rid} 는 status: deprecated 인데 index 「사실 — 대체됨」에 없다")
            elif st == "stable" and rid in dep_ids:
                errors.append(f"[상태 충돌] {rid} 는 status: stable 인데 index 「사실 — 대체됨」에 있다")

    # ③ 인덱스 신선도 — generated.at 이 facts 최신·log 최신보다 오래되면 실패
    g = GEN_AT_RE.search(index_text)
    if not g:
        errors.append("[신선도] index.md 에서 generated.at 을 읽지 못했다")
    else:
        idx_at = g.group(1)  # ISO8601(Z 제외) — 사전순 비교가 시간순 비교와 같다
        if fact_gen:
            newest_id = max(fact_gen, key=fact_gen.get)
            if idx_at < fact_gen[newest_id]:
                errors.append(
                    f"[신선도] index generated.at({idx_at}Z) 이 facts 최신({newest_id}: {fact_gen[newest_id]}Z)보다 오래됐다 — 7절 재생성 누락"
                )
        log_dates = LOG_DATE_RE.findall(read(log_path))
        if log_dates and idx_at[:10] < max(log_dates):
            errors.append(
                f"[신선도] index generated.at({idx_at[:10]}) 이 log.md 최신 항목({max(log_dates)})보다 오래됐다 — 7절 재생성 누락"
            )

    # ④⑤ 큰축 축적 봉인 (이슈 #27) — axes.md 가 있으면 등재 완결·점수판 정합을 본다
    axes_path = os.path.join(okf, "axes.md")
    # 프로파일은 정본 해석기로 고른다 (2026-08-15 — 검수 문제 7. 종전 `cheil.yaml` 리터럴)
    profile_path, profile_why = resolve_profile(kit, profile_name)
    if profile_path is None:
        print(f"경고: 판정 대상 프로파일을 특정하지 못했다 — {profile_why} "
              "(⑤ⓑ·⑥ⓑ profiles 대조를 생략한다)")
        profile_path = ""
    else:
        print(f"고지: 프로파일 정본 — {profile_why}")
    if not os.path.exists(axes_path):
        print("고지: okf/axes.md 없음 — 큰축 미도입 킷으로 보고 ④⑤ 생략")
    else:
        axes_text = read(axes_path)
        listed = {m.lower() for m in re.findall(r"facts/(f-\d{3}(?:-[xX])?)\.md", axes_text)}
        missing_axes = [rid for rid, st in sorted(fact_status.items())
                        if st == "stable" and rid not in listed]
        for rid in missing_axes:
            errors.append(f"[큰축 미검토] {rid} — 계보에도 무소속 원장에도 없다 "
                          "(④ 수집 등재 시 태깅 증분 의무 — 등재와 함께 계보 또는 무소속 표에 기입한다, 이슈 #27)")

        # ⑤ 축별 재계산 — 계보 표가 집계의 정본이다
        DIRS = ("지지", "반증", "조건형성", "중립")
        recount, latest_ok, sec_by_ma = {}, {}, {}
        sections = re.split(r"^## +", axes_text, flags=re.M)
        for sec in sections:
            m = re.match(r"(MA\d+)\b", sec)
            if not m:
                continue
            ma = m.group(1)
            sec_by_ma[ma] = sec  # ⑥ 이 같은 절을 다시 읽는다 (이슈 #35)
            rows = re.findall(r"^\|\s*\[(F-\d{3})\]\(facts/f-\d{3}\.md\)\s*\|[^|]*\|\s*(지지|반증|조건형성|중립)\s*\|",
                              sec, re.M)
            recount[ma] = {d: sum(1 for _, v in rows if v == d) for d in DIRS}
            sb = re.search(r"\*\*점수판\*\*\s*지지 (\d+) · 반증 (\d+) · 조건형성 (\d+) · 중립 (\d+) · 최신 관측 (F-\d{3})", sec)
            if not sb:
                errors.append(f"[점수판] {ma} — axes.md 에서 점수판 줄을 읽지 못했다 (⑤ 형식)")
                continue
            stated = dict(zip(DIRS, map(int, sb.groups()[:4])))
            for d in DIRS:
                if stated[d] != recount[ma][d]:
                    errors.append(f"[점수판 표류] {ma} {d} — axes.md 점수판 {stated[d]} ≠ 계보 재계산 {recount[ma][d]} "
                                  "(⑤ 집계의 정본은 계보 표다, 이슈 #27)")
            latest = sb.group(5)
            latest_ok[ma] = latest
            if latest not in {r for r, _ in rows}:
                errors.append(f"[점수판] {ma} 최신 관측 {latest} 이 계보 표에 없다 (⑤)")

        # ⓑ profiles macro_axes.status 대조
        try:
            import yaml
            prof = yaml.safe_load(read(profile_path)) if os.path.exists(profile_path) else {}
            for a in (prof or {}).get("macro_axes") or []:
                ma = str(a.get("id"))
                st = a.get("status") or {}
                if ma not in recount:
                    errors.append(f"[3중 장부] profiles macro_axes {ma} 가 axes.md 에 절이 없다 (⑤)")
                    continue
                for d in DIRS:
                    pv = st.get(d)
                    if pv is not None and int(pv) != recount[ma][d]:
                        errors.append(f"[3중 장부] profiles {ma} {d} {pv} ≠ 계보 재계산 {recount[ma][d]} (⑤ 수동 동기화 표류)")
                lv = str(st.get("최신관측") or "")
                if lv and latest_ok.get(ma) and lv != latest_ok[ma]:
                    errors.append(f"[3중 장부] profiles {ma} 최신관측 {lv} ≠ axes.md {latest_ok[ma]} (⑤)")
        except Exception as ex:
            print(f"경고: profiles macro_axes 대조 생략 ({ex})")

        # ⓒ index.md 큰축 요약 대조
        for m in re.finditer(r"^- (MA\d+) — \[[^\]]*\]\(axes\.md\) \(지지 (\d+) · 반증 (\d+) · 조건형성 (\d+) · 중립 (\d+)\)",
                             index_text, re.M):
            ma = m.group(1)
            if ma not in recount:
                continue
            stated = dict(zip(DIRS, map(int, m.groups()[1:])))
            for d in DIRS:
                if stated[d] != recount[ma][d]:
                    errors.append(f"[3중 장부] index.md {ma} {d} {stated[d]} ≠ 계보 재계산 {recount[ma][d]} (⑤)")

        # ⑥ 증류·재귀납 봉인 (이슈 #35) — 기계는 형식만 본다
        # ⑥ⓑ 임계는 profiles 의 reinduct_when 이 정본이다 (정본-판정 분리 — 도구는
        # 값을 읽어 판정만 한다). 못 읽으면 ⑤ⓑ 선례대로 경고 후 강등한다.
        refute_need, non_search = {}, None
        try:
            import yaml
            prof6 = yaml.safe_load(read(profile_path)) if os.path.exists(profile_path) else {}
            for a in (prof6 or {}).get("macro_axes") or []:
                for cond in a.get("reinduct_when") or []:
                    mc = REFUTE_COND_RE.match(str(cond))
                    if mc:  # 「반증 > N」 은 N+1 건부터 충족
                        refute_need[str(a.get("id"))] = int(mc.group(2)) + (1 if mc.group(1) == ">" else 0)
            # ⑥ⓒ 결과 칸 어휘의 정본 (2026-08-15 — 검수 문제 4). 도구는 값을 읽어 판정만 한다
            vocab = (((prof6 or {}).get("refute_sweep") or {}).get("log_result_vocab") or {})
            if vocab.get("non_search"):
                non_search = [str(v).strip() for v in vocab["non_search"]]
        except Exception as ex:
            print(f"경고: profiles reinduct_when 을 읽지 못했다 — ⑥ⓑ 재귀납 기록 판정 생략 ({ex})")
        if non_search is None:
            non_search = list(NON_SEARCH_FALLBACK)
            print("경고: profiles refute_sweep.log_result_vocab.non_search 를 읽지 못했다 — "
                  f"⑥ⓒ 는 폴백 어휘 {non_search} 로 판정한다 (정본은 프로파일이다)")

        log_latest = max(LOG_DATE_RE.findall(read(log_path)) or ["0000-00-00"])
        # ⓐ 강등 판정 (검수 문제 19-1) — 전 축에 슬롯이 **하나도** 없으면 미도입 킷이다.
        # 일부 축에만 있으면 도입한 킷이므로 나머지를 차단한다.
        distilled_any = any(DISTILL_RE.search(sec_by_ma[ma]) for ma in sec_by_ma)
        if sec_by_ma and not distilled_any:
            print("경고: 어느 축에도 「**현재 판정(증류)**」 슬롯이 없다 — 증류 미도입 킷으로 보고 "
                  "⑥ⓐ 를 생략한다 (⑥ⓐ 이슈 #35 · 강등 선례 ⑤ⓑ. 도입하려면 axes.md 각 축에 "
                  "슬롯 한 줄을 넣는다)")
        year_warned = False
        for ma in sorted(sec_by_ma):
            sec = sec_by_ma[ma]
            # ⓐ 증류 명제 — 슬롯 실존 + 근거 좌표 실존·유효 (문장의 내용은 사람·패널 몫)
            dm = DISTILL_RE.search(sec)
            if not dm:
                if distilled_any:
                    errors.append(f"[증류 명제] {ma} — axes.md 에 「**현재 판정(증류)**」 슬롯이 없다 "
                                  "(⑥ⓐ — 지면의 추적 줄이 읽는 칸이다, 이슈 #35)")
            else:
                # 좌표는 링크 형태([F-045](facts/f-045.md))라 표시·경로에서 두 번 잡힌다 — 소문자로 중복 제거
                coords = sorted({c.lower() for c in REF_RE.findall(dm.group(1))})
                if not coords:
                    errors.append(f"[증류 명제] {ma} — 증류 문장에 근거 좌표(F-###)가 없다 (⑥ⓐ)")
                lineage_ids = {r.lower() for r in re.findall(r"\[(F-\d{3})\]\(facts/", sec)}
                for c in coords:
                    if not os.path.exists(os.path.join(facts_dir, c + ".md")):
                        errors.append(f"[증류 명제] {ma} — 근거 좌표 {c.upper()} 의 사실 파일이 없다 (⑥ⓐ)")
                    elif fact_status.get(c) == "deprecated":
                        # 검수 문제 19-2 — 좌표 실존만 보면 **대체된 사실**을 근거로 단
                        # 증류문이 영구히 통과한다. 대체 여부는 status 한 줄로 판정 가능하다
                        # (증류문의 신선도·옳음은 여전히 사람·패널 몫이다 — 황금률).
                        errors.append(f"[증류 명제] {ma} — 근거 좌표 {c.upper()} 는 status: deprecated 다 "
                                      "(⑥ⓐ — 대체된 사실 위에 선 증류문은 갱신 대상이다)")
                    elif c not in lineage_ids:
                        print(f"경고: {ma} 증류 근거 좌표 {c.upper()} 가 이 축 계보 표에 없다 "
                              "(⑥ⓐ — 교차 축 인용일 수 있어 차단하지 않는다. 계보 등재 여부를 확인하라)")
            # ⓑ 재귀납 기록 — 반증 조건 충족인데 기록이 없거나 **최신 반증보다 이르면** 차단
            need = refute_need.get(ma)
            got = recount.get(ma, {}).get("반증", 0)
            if need is not None and got >= need:
                rec = subsection(sec, "재귀납 기록")
                rec_dates = [norm_date(d, log_latest)[0] for d in (ROW_DATE_RE.findall(rec) if rec else [])]
                if not rec_dates:
                    errors.append(f"[재귀납 누락] {ma} — 반증 {got}건으로 reinduct_when(반증 >= {need}) 이 "
                                  "충족됐는데 「### 재귀납 기록」에 날짜 행이 없다 (⑥ⓑ — 반증이 나온 축은 "
                                  "다렌즈 재독·유지/분할/합병/신설 판정·편집장 승인까지가 한 동작이다, "
                                  "절차 정본 routine-SKILL 2b 절)")
                else:
                    # 최신 반증 등재일과 대조한다 (2026-08-15 — 검수 문제 13). 종전에는
                    # 날짜 행의 **존재만** 봐서, 첫 반증 때 한 줄 넣으면 두 번째·세 번째
                    # 반증이 쌓여도 그 축이 영구히 통과했다 — 「반증이 나온 축은 재독까지가
                    # 한 동작」이라는 취지가 최초 1건에만 걸렸다.
                    ref_rows = re.findall(
                        r"^\|\s*\[F-\d{3}\]\(facts/f-\d{3}\.md\)\s*\|\s*([\d\-]+)\s*\|\s*반증\s*\|",
                        sec, re.M)
                    ref_dates = [norm_date(d, log_latest)[0] for d in ref_rows]
                    if ref_dates and max(rec_dates) < max(ref_dates):
                        errors.append(f"[재귀납 누락] {ma} — 최신 반증 등재일({max(ref_dates)})이 최신 "
                                      f"재귀납 기록({max(rec_dates)})보다 뒤다 (⑥ⓑ — 반증 {got}건. "
                                      "첫 반증에 한 줄 적은 것으로 이후 반증까지 면제되지 않는다. "
                                      "새 반증에 대한 재독·판정·승인·기록을 남겨라)")
            # ⓒ 반증 탐색 이력 — 최근 발행일 이후의 **탐색** 기록이 없으면 경고(차단 아님)
            hist = subsection(sec, "반증 탐색 이력")
            searched = []
            for row in (ROW_CELLS_RE.findall(hist) if hist else []):
                cells = [c.strip() for c in row.split("|")]
                if not cells or not re.match(r"^(\d{4}-\d{2}-\d{2}|\d{2}-\d{2})$", cells[0]):
                    continue
                result = cells[-1] if len(cells) >= 3 else ""
                if any(result.startswith(v) for v in non_search):
                    # 「미탐색」 자백 행은 탐색 기록으로 세지 않는다 (검수 문제 4) — 행 자체는
                    # 남긴다. 「안 찾은 날」의 기록도 기록이고, 다만 통과의 근거는 못 된다.
                    continue
                iso, guessed = norm_date(cells[0], log_latest)
                if guessed and not year_warned:
                    print("경고: 「반증 탐색 이력」 날짜가 연도 없는 MM-DD 표기다 — 연도를 "
                          f"기준일({log_latest}) 주변에서 추정했다. 표기 정본은 YYYY-MM-DD 다 "
                          "(⑥ⓒ, 검수 문제 5 — MM-DD 문자열 비교는 해가 바뀌면 조용히 죽는다)")
                    year_warned = True
                searched.append(iso)
            if not searched or max(searched) < log_latest:
                print(f"경고: {ma} 반증 탐색 이력에 최근 발행일({log_latest}) 이후의 **탐색** 기록이 없다 "
                      f"(최신 탐색: {max(searched) if searched else '없음'}) — 반증 0 이 관측 결과인지 "
                      "미탐색인지 가릴 수 없다 (⑥ⓒ 이슈 #35 — 찾지 못한 날도 한 줄 남긴다. "
                      f"결과 칸이 {non_search} 로 시작하는 행은 탐색으로 세지 않는다)")

    for e in errors:
        print("실패:", e)
    if errors:
        sys.exit(1)
    dep_n = sum(1 for s in fact_status.values() if s == "deprecated")
    print(f"통과: 참조 {len(refs)}건 전부 실존, 사실 {len(fact_status)}건(대체 {dep_n}) 상태 정합, 인덱스 신선"
          + (", 큰축 등재 완결·점수판 3중 장부 정합·증류 좌표 실존·재귀납 기록 정합"
             if os.path.exists(axes_path) else ""))


if __name__ == "__main__":
    main()
