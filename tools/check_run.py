# -*- coding: utf-8 -*-
"""실행 실체 게이트 — '실행됐다는 기록'과 '오늘자 산출물 실존'을 대조한다.

사용(USAGE):
  python tools/check_run.py [--date YYYY-MM-DD] [--profile <이름>] [킷루트]
    --date    판정 기준 날짜 (생략 시 오늘, 로컬 시각).
              다음날 점검은 --date 어제날짜 로 돌린다.
    --profile 소스 로스터의 정본 프로파일 이름 (생략 시 config.yaml 의 `profile:`,
              그것도 없으면 profiles/ 에 파일이 하나뿐일 때 그것 — tools/profile_lib.py).
    킷루트    생략 시 이 스크립트의 상위 디렉토리.

  쓰는 곳 둘 (이슈 #9):
    ① 설치 6절 시험 실행 직후 — scheduled-task 의 lastRunAt 만 보고
       "돌았다"로 넘어가지 않는다. 이 스크립트 종료코드 0 이 통과 기준이다.
    ② 다음날 점검 — 루틴/사람이 전날 실행의 실체를 확인할 때
       `python tools/check_run.py --date <전날>`.

배경 (2026-08-12 이슈 #9): 무인 시험 실행이 산출물·로그·보고 없이 끝났는데
남은 증거가 lastRunAt 타임스탬프 하나뿐이라 "돌았다"로 읽혔다. 이 게이트는
run_log(output/ledger/run_log.jsonl)의 해당 날짜 항목과 산출물 실존을 대조해
네 가지 상태를 가른다:

  통과(0)  산출물 실존 + 게이트 기록 — output/web/<날짜>.html 이 있고,
           종료 줄의 gates 필드에 실행한 기계 게이트 목록이 있다
           (run_log 항목 자체가 없으면 경고를 내되 실체가 있으므로 통과).
           목록은 **로스터 대조**다 (2026-08-14 이슈 #24) — 정본은
           templates/publish-checklist.md 의 ```required-gates``` 블록.
           로스터 게이트가 목록에서 빠졌거나 종료코드가 :0 이 아니면 실패 —
           종전의 「비어 있지 않음」 판정은 한 줄짜리 자기 보고로 뚫렸다(우회 실측).
           로스터 블록을 못 읽으면 경고 후 종전 판정으로 강등한다 (F5)
           같은 날 **소스 로스터**도 대조한다 (2026-08-15 이슈 #36) — 정본은
           `profiles/<profile>.yaml` 의 `sources[].cadence` 와 `sweep_gate` 블록.
           증거는 **두 층**이고 순서가 있다 (2026-08-15 수리, 검수 문제 1):
             1순위 원장 — 그날 종료 줄의 `sources` 필드(그날 실제로 연 소스 id 목록).
                   날짜별로 남는 **이력**이라 과거 날짜도 판정할 수 있다.
             2순위 스냅샷 — 프로파일의 `last_checked`. 이 칸은 소스마다 **최신 한
                   값만** 보관하는 현재값 스냅샷이라 **오늘 날짜에만** 뜻이 있다.
             과거 날짜인데 원장 `sources` 가 없으면 **판정 생략(고지)** — 통과도
                   실패도 아니다. 종전에는 스냅샷을 임의 과거 날짜와 등호 비교해서,
                   정상 발행된 옛 호(2026-08-11·08-12)가 전부 실패로 뒤집혔고
                   위 ②「다음날 점검」은 구조적으로 영원히 실패했다(오늘 스윕이 이미
                   last_checked 를 오늘로 덮으므로).
           `last_item` 에 「건너뜀 YYYY-MM-DD — 사유」 가 있으면 경고로 강등한다.
           면제는 **그날 생산 기록이 없을 때만**이다 (2026-08-15 수리, 검수 문제 2·17).
           **한계**: last_checked·sources 는 스윕의 자기 보고라 이 봉인이 잡는 것은
           「갱신조차 안 한 채 좁게 돈 날」이지 「형식적으로 갱신만 한 날」이 아니다
  통과(0)  quiet_day — run_log 에 result: quiet_day 항목이 있다
  실패(1)  게이트 기록 없는 발행 — 산출물은 있는데 해당 날짜 종료 줄의
           gates 필드가 없거나 비어 있다 (이슈 #18: 게이트를 건너뛴 발행)
  실패(1)  무증거 실행 — run_log 항목은 있는데 산출물이 없고,
           실패로도 기록돼 있지 않다 (돌았다는 기록 vs 실체 불일치)
  실패(1)  기록된 실패 — run_log 가 스스로 실패/중단을 기록했다 (정직하지만 실패)
  실패(1)  기록 없음 — run_log 에 해당 날짜 항목이 없다 (안 돈 날)

run_log.jsonl 한 줄 형식 (루틴 SKILL 「실행 원장」 절이 정본):
  시작 줄  {"event":"start","started_at":ISO8601,"session":...,"mode":"생산|검증|미정"}
  종료 줄  {"event":"end","started_at":시작줄과 동일,"ended_at":ISO8601,
            "mode":"생산|검증|중단","result":"산출|quiet_day|검증만|실패",
            "artifacts":[...],"gates":["check_tables:0",...],
            "sources":["dart-target",...],"reason":실패 사유}
            gates 는 산출을 낸 실행의 의무 필드다 — 실제로 실행한 기계 게이트
            목록+종료코드. 없거나 비면 이 스크립트가 발행을 실패로 판정한다
            sources 는 그날 실제로 연 상시 소스 id 목록이다 (2026-08-15 신설).
            못 돈 소스는 "id:건너뜀 — 사유" 로 적는다. 이 필드가 **날짜별 스윕
            이력**이고, 프로파일 last_checked 는 현재값 스냅샷일 뿐이다 —
            과거 날짜의 스윕을 판정할 수 있는 것은 이 필드뿐이다(검수 문제 1)

정적 검사라 네트워크 없이 돌릴 수 있다. 실패 시 종료코드 1.
"""
import io, json, os, re, sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from profile_lib import resolve_profile  # noqa: E402 — 프로파일 선택의 단일 정본 해석기

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게

USAGE = "사용법: python tools/check_run.py [--date YYYY-MM-DD] [--profile 이름] [킷루트]"

FAIL_RESULTS = {"실패", "중단"}
QUIET_RESULTS = {"quiet_day"}
# 「생산이 아닌 실행」의 result 어휘. 이 집합에만 속한 날이 면제 대상이다
# (2026-08-15 수리 — 종전에는 이 값이 **하나라도 있으면** 그날 전체를 면제했다).
NON_PRODUCE_RESULTS = QUIET_RESULTS | {"검증만"}


def parse_args(argv):
    target, kit_root, profile = None, None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--date", "--profile"):
            if i + 1 >= len(argv):
                sys.exit(USAGE)
            if a == "--date":
                target = argv[i + 1]
            else:
                profile = argv[i + 1]
            i += 2
        elif a.startswith("--date="):
            target = a.split("=", 1)[1]
            i += 1
        elif a.startswith("--profile="):
            profile = a.split("=", 1)[1]
            i += 1
        elif a.startswith("-"):
            sys.exit(USAGE)
        else:
            kit_root = a
            i += 1
    if target is None:
        target = date.today().isoformat()
    if len(target) != 10 or target[4] != "-" or target[7] != "-":
        sys.exit(f"실패: 날짜 형식이 아니다 — {target!r}\n{USAGE}")
    if kit_root is None:
        kit_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return target, kit_root, profile


def load_roster(kit_root):
    """publish-checklist 의 ```required-gates``` 블록에서 필수 게이트 이름을 읽는다.

    (로스터 정본 신설 — 이슈 #24. 못 읽으면 None → 종전 판정으로 강등 + 경고.)
    """
    path = os.path.join(kit_root, "templates", "publish-checklist.md")
    if not os.path.exists(path):
        return None
    m = re.search(r"```required-gates\n(.*?)```", io.open(path, encoding="utf-8").read(), re.S)
    if not m:
        return None
    # `#` 로 시작하는 줄은 주석이다 (2026-08-15 신설 — 검수 문제 3). 로스터가 왜
    # 이 모양인지를 **정본 안에** 적을 자리가 없어서, check_run 이 이 로스터 밖에
    # 있는 이유(순환)를 어디에도 남길 수 없었다. 종전에는 주석 줄이 게이트 이름으로
    # 읽혀 무조건 실패했으므로, 이 건너뛰기는 기능 추가이지 완화가 아니다.
    names = [ln.strip() for ln in m.group(1).splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    return names or None


# 로스터 판정의 결과 종류 — (상태, 값). 상태는 ok / 실패 / 생략.
class SweepRoster(object):
    """프로파일에서 읽어낸 상시 소스 로스터와 그 판정 값들."""

    def __init__(self, daily, gate, source, error=None):
        self.daily = daily        # [(id, last_checked, last_item), ...]
        self.gate = gate          # sweep_gate 블록 (dict)
        self.source = source      # 어느 프로파일에서 읽었는지 (출력용)
        self.error = error        # 차단 사유 (있으면 daily 는 뜻이 없다)


def load_sweep_roster(kit_root, profile=None):
    """프로파일의 sources 중 **상시(daily) cadence** 소스만 골라 돌려준다.

    (소스 로스터 봉인 — 이슈 #36. 수법은 #24 의 required-gates 로스터 대조와 동형이다:
    정본은 프로파일에 두고 도구는 그 값을 읽어 판정만 한다.)

    2026-08-15 수리 (검수 문제 6·7) — 종전 두 가지가 코드에 박혀 있었다:
      · cadence 어휘 `if cad in ("매일","daily")` — 정본에 없는 값이 들어오면 그
        소스가 **조용히 로스터에서 빠지고 게이트는 초록**이었다. 이제 어휘 정본은
        `sweep_gate.daily_cadence` / `known_cadence` 이고, 모르는 값은 **차단**한다.
      · 파일명 `cheil.yaml` — profile_lib 이 config.yaml `profile:` 을 읽어 고른다.
    또 daily 가 0건이면 차단한다 — 그러지 않으면 정본에서 `cadence: 매일` 을 전부
    지우는 **정본 편집만으로 봉인을 끌 수 있었다**. 끄려면 `sweep_gate.enabled: false`
    와 `disabled_reason` 을 명시해야 한다 (조용히가 아니라 시끄럽게).

    못 읽는 경우(pyyaml 부재·프로파일 미특정)만 error=None + daily=None 로 강등한다
    — #24 로스터 강등의 선례.
    """
    path, why = resolve_profile(kit_root, profile)
    if path is None:
        return SweepRoster(None, {}, why)
    try:
        import yaml  # ⑤ⓑ 선례대로 지연 임포트 — pyyaml 이 없어도 나머지 판정은 돈다
        prof = yaml.safe_load(io.open(path, encoding="utf-8-sig").read()) or {}
    except Exception as ex:
        return SweepRoster(None, {}, f"{why} — 읽기 실패 ({ex})")

    gate = prof.get("sweep_gate") or {}
    if not isinstance(gate, dict):
        gate = {}
    if gate.get("enabled") is False:
        reason = str(gate.get("disabled_reason") or "").strip()
        if not reason:
            return SweepRoster(None, gate, why,
                               error="sweep_gate.enabled: false 인데 disabled_reason 이 없다 — "
                                     "봉인을 끄려면 사유를 정본에 적어야 한다 (조용한 해제 금지)")
        return SweepRoster([], gate, why)  # 명시적으로 끈 프로파일: 로스터 비움 + 고지

    daily_vocab = [str(v).strip().lower() for v in (gate.get("daily_cadence") or [])]
    known_vocab = [str(v).strip().lower() for v in (gate.get("known_cadence") or [])]
    if not daily_vocab or not known_vocab:
        # 정본에 어휘 블록이 없는 프로파일 — 판정 생략 + 경고 강등 (구설치본 호환)
        return SweepRoster(None, gate, f"{why} — sweep_gate.daily_cadence/known_cadence 가 없다")

    daily, unknown = [], []
    for s in prof.get("sources") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id"))
        cad = str(s.get("cadence") or "").strip().lower()
        if cad not in known_vocab:
            unknown.append(f"{sid}:{s.get('cadence')!r}")
            continue
        if cad in daily_vocab:
            daily.append((sid, str(s.get("last_checked") or ""),
                          str(s.get("last_item") or "")))
    if unknown:
        return SweepRoster(None, gate, why,
                           error="정본에 없는 cadence 값이 있다 — " + ", ".join(unknown)
                                 + f" (어휘 정본: sweep_gate.known_cadence = {known_vocab}. "
                                   "모르는 값을 조용히 로스터에서 빼면 게이트가 초록으로 약해진다)")
    if not daily:
        return SweepRoster(None, gate, why,
                           error="cadence 가 상시(daily)인 소스가 0건이다 — 로스터가 비면 "
                                 "봉인이 아무것도 잡지 못한다. 상시 소스가 정말 없는 "
                                 "프로파일이면 sweep_gate.enabled: false + disabled_reason "
                                 "으로 명시하라 (정본 편집만으로 조용히 꺼지지 않게)")
    return SweepRoster(daily, gate, why)


# last_item 안의 예외 표기 — 「건너뜀 YYYY-MM-DD — 사유」. 사유는 문장 끝(· 또는 줄끝)까지만
# 읽는다: last_item 은 사유 뒤에 전날 항목을 이어 적는 칸이라 끝까지 삼키면 경고가 지저분해진다.
SKIP_RE = re.compile(r"건너뜀\s*(\d{4}-\d{2}-\d{2})\s*[—\-–]\s*([^·\n]+)")


def ledger_sweep_evidence(entries):
    """그날 종료 줄의 `sources` 필드에서 (연 소스 집합, {id: 건너뜀 사유}) 를 뽑는다.

    날짜별로 남는 **원장 이력**이라 과거 날짜도 판정할 수 있다 (2026-08-15 신설,
    검수 문제 1 — 프로파일 last_checked 는 소스마다 최신 한 값만 보관하는 현재값
    스냅샷이라 시계열 판정에 쓸 수 없다). 항목이 없으면 (None, None).
    """
    seen, skipped, found = set(), {}, False
    for _, o in entries or []:
        src = o.get("sources")
        if not isinstance(src, list):
            continue
        found = True
        for item in src:
            sid, _, note = str(item).partition(":")
            sid = sid.strip()
            if not sid:
                continue
            m = SKIP_RE.search(note)
            if m or note.strip().startswith("건너뜀"):
                skipped[sid] = (m.group(2).strip() if m else note.strip())
            else:
                seen.add(sid)
    return (seen, skipped) if found else (None, None)


def check_sweep(kit_root, target, entries=None, today=None, profile=None):
    """산출을 낸 날 — 상시(daily) 소스 전수가 그날 실제로 돌았는가.

    (이슈 #36. 실측 배경: 좁게 돈 날에도 산출물은 나왔고 게이트는 전부 초록이었다 —
    어떤 소스를 건너뛰었는지 남는 자리가 없었다. 채널 편성이 흔들려도 지면은 멀쩡해 보인다.)

    **증거 두 층, 순서가 있다** (2026-08-15 재설계 — 검수 문제 1):
      1순위 원장 — 그날 종료 줄의 `sources` 필드. 날짜별 이력이라 과거도 판정 가능.
      2순위 스냅샷 — 프로파일 `last_checked`. **오늘 날짜에만** 뜻이 있다.
      과거 날짜 + 원장 증거 없음 → **판정 생략**. 종전 설계는 이 경우에 스냅샷을
      임의 과거 날짜와 등호 비교해서, 정상 발행된 옛 호가 전부 실패로 뒤집혔다
      (2026-08-11·08-12 실측: diff 이전 EXIT=0 → 이후 EXIT=1, 아홉 소스 전수 지목).
      뿌리는 「현재값 스냅샷을 시계열 판정에 썼다」는 설계 결함이었다.

    **한계(반드시 같이 읽는다)**: 두 증거 다 스윕의 **자기 보고**다. 이 봉인이 잡는
    것은 「기록조차 안 한 채 좁게 돈 날」이지 「형식적으로 기록만 한 날」이 아니다.
    소스를 실제로 열었는지는 기계가 볼 수 없다 — 그 판정은 사람·패널 몫이다(황금률).

    돌려주는 값: 0 통과(경고 강등 포함) / 1 차단 / None 판정 생략.
    """
    r = load_sweep_roster(kit_root, profile)
    if r.error:
        print(f"실패: 소스 로스터 정본이 판정 불가다 [{r.source}] — {r.error} "
              "(이슈 #36 · 정본: profiles/<profile>.yaml sweep_gate·sources[].cadence)")
        return 1
    if r.daily is None:
        print(f"경고: 상시 소스 로스터를 읽지 못했다 [{r.source}] — "
              "소스 로스터 대조를 생략한다 (이슈 #36)")
        return None
    if not r.daily:
        print(f"고지: sweep_gate.enabled: false 인 프로파일이다 [{r.source}] — "
              f"소스 로스터 대조를 생략한다 (사유: {r.gate.get('disabled_reason')})")
        return None

    ids = [sid for sid, _, _ in r.daily]
    seen, skipped = ledger_sweep_evidence(entries)
    if seen is not None:
        layer = "원장 sources 필드"
        stale = [s for s in ids if s not in seen and s not in skipped]
        excused = [f"{s}({skipped[s]})" for s in ids if s in skipped]
    else:
        today = today or date.today().isoformat()
        if target != today:
            print(f"고지: {target} 은 오늘({today})이 아니고 그날 원장에 sources 필드가 없다 — "
                  "상시 소스 로스터 대조를 **생략**한다. 프로파일 last_checked 는 소스마다 "
                  "최신 한 값만 보관하는 현재값 스냅샷이라 과거 날짜의 스윕 범위를 증언하지 "
                  "못한다 (2026-08-15 수리, 검수 문제 1 — 종전에는 이 비교로 정상 발행된 옛 "
                  "호가 전부 실패로 뒤집혔다). 과거 날짜를 판정하려면 종료 줄에 "
                  '"sources":[...] 를 남겨야 한다')
            return None
        layer = "프로파일 last_checked 스냅샷"
        stale, excused = [], []
        for sid, last, item in r.daily:
            if last[:10] == target:
                continue
            m = SKIP_RE.search(item)
            if m and m.group(1) == target:
                # F5 정직성 — 장애·휴무를 사유와 함께 적은 소스는 경고로 강등한다.
                # 조용한 건너뛰기만 잡고, 정직하게 기록한 실패는 막지 않는다.
                excused.append(f"{sid}({m.group(2).strip()})")
            else:
                stale.append(f"{sid}:{last or '기록 없음'}")

    for e in excused:
        print(f"경고: 상시 소스를 사유와 함께 건너뛰었다 — {e} (이슈 #36 예외 경로)")
    if excused and len(excused) == len(ids):
        # 상한 (2026-08-15 신설 — 검수 문제 18 후단): 예외 경로에 상한이 없어서
        # 로스터 전수에 「건너뜀 <오늘> — 사유」 를 적으면 경고만 남기고 통과했다.
        # 전수 건너뜀은 「그날 스윕을 하지 않았다」이지 「정직한 부분 실패」가 아니다.
        print("실패: 상시 소스 전수를 건너뛰었다 — 사유를 적었더라도 그날 스윕은 "
              f"0건이다 (이슈 #36 예외 경로 상한. 로스터 {len(ids)}건 전부 건너뜀). "
              "스윕을 못 돌린 날은 지면을 내지 않거나 quiet_day 로 기록한다")
        return 1
    if stale:
        print("실패: 상시 소스 스윕이 로스터에 미달한다 — "
              + ", ".join(stale)
              + f" (이슈 #36 — 증거층: {layer}. 상시 소스는 산출을 낸 날 {target} 에 "
              "돈 기록이 있어야 한다. 기록이 없다는 것은 이번 스윕이 그 소스를 건너뛰었다는 "
              "뜻이다. 못 돈 소스는 「건너뜀 " + target + " — 사유」 를 남기면 경고로 "
              "강등된다. 로스터 정본: profiles/<profile>.yaml sweep_gate·sources[].cadence)")
        return 1
    print(f"  상시 소스 {len(ids)}건 중 {len(ids) - len(excused)}건 {target} 확인"
          + (f" · 사유 기록 강등 {len(excused)}건" if excused else " (전수)")
          + f" [증거: {layer} · 로스터: {r.source}]")
    return 0


def load_entries(run_log, target):
    """run_log.jsonl 에서 target 날짜의 항목만 (줄번호, dict) 로 돌려준다.

    날짜는 **`started_at` 기준**이다 — 루틴 SKILL 0-원장 절이 "같은 `started_at`
    으로 짝을 맞추고" 를 규약으로 정하므로, 짝의 날짜도 같은 필드로 갈라야 시작
    줄과 종료 줄이 한 날짜에 모인다. `ended_at` 은 시작 줄이 없는 기록에서만 쓴다.

    종전에는 `ended_at` 을 우선했다. 그러면 **자정을 넘긴 실행에서 한 실행의 두
    줄이 서로 다른 날짜로 갈라진다** (2026-08-15 맥 앱 실측, 이슈 #33):
    21:36 시작 → 다음날 09:35 종료한 실행에서 시작일 판정은 시작 줄만 보고
    「게이트 기록 없는 발행」(#18 문안), 종료일 판정은 종료 줄만 보고 「산출물
    없음」 을 냈다. 게이트를 전종 돌린 실행을 게이트 미실행으로 지목하는 것은
    #18 이 막으려던 것과 정반대 방향의 오진이라, 짝맞춤 규약 쪽으로 맞춘다.
    """
    if not os.path.exists(run_log):
        return None  # 파일 자체가 없다
    entries = []
    for n, line in enumerate(io.open(run_log, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            print(f"  경고: run_log {n}행이 JSON 이 아니다 — 무시: {line[:80]}")
            continue
        stamp = str(obj.get("started_at") or obj.get("ended_at") or "")
        if stamp.startswith(target):
            entries.append((n, obj))
    return entries


def has_production_record(entries):
    """그날 원장에 **생산 기록**이 있는가 (2026-08-15 신설 — 검수 문제 2·17).

    종전 면제 판정은 `results & (QUIET_RESULTS | {"검증만"})` — 그날 원장에 검증만
    항목이 **하나라도** 있으면 그날 전체를 면제했다. 그런데 routine-SKILL 0-a 는
    「오늘자 산출물이 있으면 검증만 하고 종료」라, 같은 날 두 번째 실행이 정확히
    `result: 검증만` 을 남긴다 — 즉 「아침에 좁게 돌아 발행하고 오후에 한 번 더
    돌리기」라는 **매일 재현되는 흔한 패턴**이 봉인을 지웠다. 실측: 임시 사본에서
    아홉 소스 last_checked 를 전부 2026-07-01 로 낮춰도 --date 2026-08-14 는 EXIT=0.
    (08-14 는 produced+published 뒤에 검증 세션을 이어 붙인 날이다.)

    그래서 면제는 **그날 생산 기록이 없을 때**로 좁힌다. 생산 기록의 표식은
    ⓐ gates 필드가 있는 종료 줄 ⓑ artifacts 필드가 있는 종료 줄
    ⓒ result 가 「생산이 아닌 실행」 어휘(NON_PRODUCE_RESULTS)가 **아닌** 종료 줄
    — 셋 중 하나라도 있으면 그날은 지면을 만든 날이다.
    """
    for _, o in entries or []:
        if o.get("event") != "end":
            continue
        res = str(o.get("result") or "")
        if res in NON_PRODUCE_RESULTS or res in FAIL_RESULTS:
            # result 가 먼저다 — 검증 세션이 게이트를 재실행하며 gates 를 기록할 수 있다.
            # 그것은 「그날 지면을 만들었다」가 아니므로 생산 기록으로 세지 않는다.
            continue
        if res or o.get("gates") or o.get("artifacts"):
            return True
    return False


def main():
    target, kit_root, profile = parse_args(sys.argv[1:])
    run_log = os.path.join(kit_root, "output", "ledger", "run_log.jsonl")
    artifact = os.path.join(kit_root, "output", "web", target + ".html")

    entries = load_entries(run_log, target)
    has_artifact = os.path.exists(artifact)

    print(f"판정 대상: {target}")
    print(f"  산출물  output/web/{target}.html : {'실존' if has_artifact else '없음'}")
    if entries is None:
        print("  원장    output/ledger/run_log.jsonl : 파일 없음")
    else:
        print(f"  원장    해당 날짜 항목 {len(entries)}건")
        for n, obj in entries:
            print(f"    {n}행 event={obj.get('event')} mode={obj.get('mode')}"
                  f" result={obj.get('result')} session={obj.get('session')}")

    # ① 실체가 있으면 게이트 기록까지 대조한다 (이슈 #18 — 게이트 미실행 발행 차단)
    if has_artifact:
        if not entries:
            # 원장 항목 자체가 없으면 종전대로 경고+통과 — 실체가 있고,
            # 존재하지 않는 종료 줄의 gates 를 판정할 수 없다
            print("경고: 산출물은 있는데 run_log 항목이 없다 — "
                  "루틴이 「실행 원장」 절을 건너뛰었거나 다른 경로로 생산됐다")
            # 산출을 낸 날이면 소스 로스터는 본다 (이슈 #36)
            if check_sweep(kit_root, target, entries, profile=profile) == 1:
                return 1
            print("통과: 오늘자 산출물이 실존한다")
            return 0
        gated = [(n, o) for n, o in entries
                 if o.get("event") == "end"
                 and isinstance(o.get("gates"), list) and o.get("gates")]
        if not gated:
            print("실패: 게이트 기록 없는 발행 — 산출물은 있는데 해당 날짜 종료 줄의 "
                  "gates 필드가 없거나 비어 있다. 기계 게이트를 건너뛴 발행이거나 "
                  "기록을 빠뜨린 것이다 (이슈 #18). 발행 전 게이트를 돌리고 종료 줄에 "
                  '"gates":["check_tables:0",...] 형식으로 기록하라')
            return 1
        n, o = gated[-1]
        # 로스터 대조 (이슈 #24) — 필수 게이트 전수가 :0 으로 기록됐는가
        roster = load_roster(kit_root)
        if roster is None:
            print("경고: publish-checklist 의 required-gates 로스터를 읽지 못했다 — "
                  "목록 완전성 대조를 생략하고 「비어 있지 않음」만 판정한다 (이슈 #24)")
        else:
            recorded = {}
            for g in o["gates"]:
                name, _, code = str(g).partition(":")
                recorded[name.strip()] = code.strip()
            missing = [r for r in roster if r not in recorded]
            nonzero = [r for r in roster if recorded.get(r) not in (None, "0")]
            if missing:
                print("실패: 게이트 기록이 로스터에 미달한다 — 빠진 게이트: "
                      + ", ".join(missing)
                      + " (이슈 #24 — 목록 한 줄로 나머지를 건너뛴 발행은 게이트를 돌린 발행이 아니다. "
                      "로스터 정본: templates/publish-checklist.md required-gates)")
                return 1
            if nonzero:
                print("실패: 로스터 게이트의 종료코드가 0 이 아니다 — "
                      + ", ".join(f"{r}:{recorded[r]}" for r in nonzero)
                      + " (실패한 게이트를 기록한 채 발행했다)")
                return 1
        # 소스 로스터 봉인 (이슈 #36) — 상시 소스 전수가 그날 돌았는가.
        # 면제는 **그날 생산 기록이 없을 때**만이다 (2026-08-15 수리 — 검수 문제 2·17).
        # 종전에는 「그날 항목 중 quiet_day·검증만 이 하나라도 있으면」 면제라,
        # 생산·발행 뒤에 검증 세션을 이어 붙인 날(08-14 가 그런 날이다)이 통째로
        # 면제됐다. 여기는 산출물 실존이 이미 확정된 분기라, 생산 기록이 있으면
        # 그날은 지면을 만든 날이고 스윕 범위를 물어야 한다.
        swept = None
        if not has_production_record(entries):
            print("고지: 그날 생산 기록이 없는 원장이다(quiet_day·검증만 뿐) — "
                  "상시 소스 로스터 대조를 면제한다 (이슈 #36)")
        else:
            swept = check_sweep(kit_root, target, entries, profile=profile)
            if swept == 1:
                return 1
        print(f"통과: 오늘자 산출물이 실존하고 게이트 기록이 로스터 전수와 일치한다 "
              f"({n}행 gates={o['gates']})"
              + (" · 상시 소스 로스터 대조 완료" if swept == 0 else ""))
        return 0

    # ② quiet_day 로 기록된 날 — 산출물 없음이 정상이다
    if entries and any(str(o.get("result")) in QUIET_RESULTS for _, o in entries):
        print("통과: quiet_day 로 기록된 날 — 산출물 부재가 기록과 일치한다")
        return 0

    # ③ 산출물 없음 — 원장 기록과 대조해 실패 종류를 가른다
    if not entries:
        print(f"실패: {target} 실행 기록이 없다 — 안 돈 날이다 "
              "(run_log 시작 줄조차 없음. 루틴이 뜨지 않았거나 첫 동작 전에 죽었다)")
        return 1

    honest = [(n, o) for n, o in entries
              if str(o.get("result")) in FAIL_RESULTS or str(o.get("mode")) == "중단"]
    if honest:
        n, o = honest[-1]
        print(f"실패: 실행이 스스로 실패/중단을 기록했다 ({n}행, 사유: "
              f"{o.get('reason') or '기재 없음'}) — 산출물 없음이 기록과 일치하지만 "
              "그날 호는 없다. 보고와 수동 조치가 필요하다")
        return 1

    print("실패: 무증거 실행 — 실행됐다는 기록은 있는데 산출물이 없고 "
          "실패로도 기록돼 있지 않다. '돌았다'로 읽지 마라 (이슈 #9 계열)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
