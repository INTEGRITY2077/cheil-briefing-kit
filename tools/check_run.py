# -*- coding: utf-8 -*-
"""실행 실체 게이트 — '실행됐다는 기록'과 '오늘자 산출물 실존'을 대조한다.

사용(USAGE):
  python tools/check_run.py [--date YYYY-MM-DD] [킷루트]
    --date  판정 기준 날짜 (생략 시 오늘, 로컬 시각).
            다음날 점검은 --date 어제날짜 로 돌린다.
    킷루트  생략 시 이 스크립트의 상위 디렉토리.

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
            "artifacts":[...],"gates":["check_tables:0",...],"reason":실패 사유}
            gates 는 산출을 낸 실행의 의무 필드다 — 실제로 실행한 기계 게이트
            목록+종료코드. 없거나 비면 이 스크립트가 발행을 실패로 판정한다

정적 검사라 네트워크 없이 돌릴 수 있다. 실패 시 종료코드 1.
"""
import io, json, os, re, sys
from datetime import date

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게

USAGE = "사용법: python tools/check_run.py [--date YYYY-MM-DD] [킷루트]"

FAIL_RESULTS = {"실패", "중단"}
QUIET_RESULTS = {"quiet_day"}


def parse_args(argv):
    target, kit_root = None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--date":
            if i + 1 >= len(argv):
                sys.exit(USAGE)
            target = argv[i + 1]
            i += 2
        elif a.startswith("--date="):
            target = a.split("=", 1)[1]
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
    return target, kit_root


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
    names = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
    return names or None


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


def main():
    target, kit_root = parse_args(sys.argv[1:])
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
        print(f"통과: 오늘자 산출물이 실존하고 게이트 기록이 로스터 전수와 일치한다 "
              f"({n}행 gates={o['gates']})")
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
