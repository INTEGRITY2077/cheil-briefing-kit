# -*- coding: utf-8 -*-
"""E6 공유 확정 게이트 — 발행본이 실제로 전체(링크) 공유이고, 독자가 받는
핀 버전이 오늘 호인지 **직접** 판정한다.

사용법:
  python tools/check_publish.py [YYYY-MM-DD | 아티팩트URL]
    날짜 생략 시 오늘. 날짜를 주면 output/artifact-url-<날짜>.txt 에서 URL을 읽고,
    output/web/<날짜>.html 의 h1 으로 발행본 본문까지 대조한다.

판정 (이슈 #21 개정 — 간접 휴리스틱 폐기):
  ① 판정 경로 자기검증 — 무작위 uuid 가 200 을 받으면 판정 자체가 무효 (실패)
  ② `GET /api/frame/<uuid>?via=user_open` (X-Frame-* 헤더) →
     200 + "mode":"public" = 공유 ON / 401 = 공유 OFF **또는 없는 uuid** → 실패
  ③ 응답 ver 로 발행본 본문(`_f/<ver>`)을 받아 오늘 호 h1 이 실려 있는지 —
     핀이 옛 버전·다른 호에 있으면 실패 (게이트 초록 + 독자는 옛 버전, 2026-08-13 실측)
  ④ **IG7 상시 소스 로스터** — 오늘 호를 발행하는 순간, 프로파일의 상시(daily)
     소스 전수가 오늘 돌았는가 (`check_run.check_sweep` 을 그대로 호출한다).

왜 ④ 가 여기 있는가 (2026-08-15 신설 — 검수 문제 3):
  IG7 은 「`check_run.py --date <오늘>` 종료코드 0 이 판정이다」라고 선언하면서도
  `templates/publish-checklist.md` 의 ```required-gates``` 블록에 `check_run` 이 없었다.
  즉 발행 시점에 IG7 을 강제하는 기계 경로가 0개였고, 사람이 잊으면 아무것도 잡지
  않는 항목이었다. 그렇다고 `check_run` 을 로스터에 넣을 수는 없다 — **순환**이다:
  로스터는 run_log 종료 줄의 `gates` 필드에 무엇이 기록돼야 하는지의 정본인데,
  `check_run` 은 바로 그 종료 줄을 판정한다(발행 전에는 아직 없는 줄이다).
  그래서 봉인을 **순환하지 않는 지점**으로 옮겼다: `check_publish` 는 이미 로스터
  안에 있고(E6), 발행 직후에 돌며, run_log 를 읽지 않는다 — 소스 로스터 대조에
  필요한 것은 프로파일 정본과 오늘 날짜뿐이다. 로스터 블록은 손대지 않았으므로
  종전 run_log 기록(check_publish:0)의 판정도 그대로다.
  과거 날짜를 인자로 준 소급 판정에서는 ④ 를 생략한다 — `last_checked` 는 현재값
  스냅샷이라 과거의 스윕 범위를 증언하지 못한다(같은 수리, 검수 문제 1).

구판(404=통과 휴리스틱)은 존재하지 않는 uuid·오타 URL·삭제된 아티팩트도
통과시켰다 — 발행의 완결 조건을 판정하는 게이트가 간접이면 곤란하다 (이슈 #21).
공유 거절(409 unscannable)이면 오디오가 audio/mp4 인지 보라 — MP3 재이식·재발행이
처방이다 (2026-08-13 규명, publish-checklist E5).
"""
import io
import os
import re
import sys
import uuid as uuidlib
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_formats import fetch_anon, FRAME_API_HEADERS  # noqa: E402 — 판정 경로 단일 정본
from check_run import check_sweep  # noqa: E402 — IG7 봉인의 단일 정본 (④)

USAGE = "사용법: python tools/check_publish.py [YYYY-MM-DD | 아티팩트URL]"
KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)


def resolve(arg):
    """(아티팩트 URL, 로컬 웹판 경로 또는 None, 대상 날짜 또는 None) 반환."""
    if arg and arg.startswith("http"):
        return arg, None, None
    target = arg or date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", target):
        print(USAGE)
        sys.exit(2)
    url_file = os.path.join(KIT_ROOT, "output", f"artifact-url-{target}.txt")
    if not os.path.exists(url_file):
        print(f"실패: output/artifact-url-{target}.txt 이 없다 — "
              "발행 절차가 URL 기록을 빠뜨렸거나 아직 발행 전이다")
        sys.exit(1)
    url = io.open(url_file, encoding="utf-8").read().strip().splitlines()[0].strip()
    if not url.startswith("http"):
        print(f"실패: URL 파일 첫 줄이 URL 이 아니다: {url[:80]}")
        sys.exit(1)
    html = os.path.join(KIT_ROOT, "output", "web", f"{target}.html")
    return url, (html if os.path.exists(html) else None), target


def frame_meta(uid):
    return fetch_anon(f"https://claude.ai/api/frame/{uid}?via=user_open",
                      FRAME_API_HEADERS)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    url, html_p, target = resolve(arg)
    m = re.search(r"artifact/([0-9a-f-]{36})", url)
    if not m:
        print(f"실패: URL 에서 아티팩트 ID 를 못 찾았다: {url[:80]}")
        sys.exit(1)
    uid = m.group(1).lower()
    print(f"판정 대상: {url}")

    # ① 판정 경로 자기검증 — 없는 uuid 는 200 이면 안 된다 (이슈 #21: 404=통과
    #    휴리스틱이 없는 uuid 도 통과시켰던 전철)
    ctrl_code, _ = frame_meta(str(uuidlib.uuid4()))
    if ctrl_code == 200:
        print("실패: 대조군(무작위 uuid)이 200 — 판정 경로 자체가 신뢰 불가 (응답 형식 변경 의심)")
        sys.exit(1)

    # ② 공유 직접 판정
    code, body = frame_meta(uid)
    if code is None:
        print(f"실패: 네트워크 오류로 판정 불가 — {body[:100]} (판정 불가는 통과가 아니다)")
        sys.exit(1)
    if code != 200:
        print(f"실패: 익명 메타 조회 HTTP {code} — 공유 OFF 이거나 존재하지 않는 아티팩트다. "
              "Share → General access 를 Anyone with the link 로 전환하라 "
              "(새 아티팩트는 비공개가 기본값 — 08.11 함정). 전환이 409 로 거절되면 "
              "오디오 MIME 이 audio/mp4 인지 보라 — MP3 재이식·재발행이 처방 (E5)")
        sys.exit(1)
    flat = body.replace(" ", "")
    if '"mode":"public"' not in flat and '"kind":"public"' not in flat:
        print(f"실패: 메타 200 이지만 public 표식이 없다 — 응답: {body[:120]}")
        sys.exit(1)
    print("공유 판정: 익명 메타 200 + public — 링크 공유 ON")

    # ④ IG7 상시 소스 로스터 봉인 (2026-08-15 신설 — 검수 문제 3).
    #    발행 시점에 IG7 을 강제하는 기계 경로가 여기다. check_run 을 required-gates
    #    로스터에 넣으면 순환이라(로스터가 정의하는 gates 필드를 check_run 이 판정한다)
    #    이미 로스터 안에 있는 이 게이트에서 같은 판정 함수를 호출한다.
    #    entries=None → 원장 증거 없음 → 오늘 날짜일 때만 스냅샷으로 판정한다.
    if target and check_sweep(KIT_ROOT, target, entries=None) == 1:
        print("실패: IG7 — 오늘 호를 내면서 상시 소스 로스터를 채우지 못했다 "
              "(위 사유 참조). 스윕을 마저 돌려 프로파일 last_checked 를 갱신하거나, "
              "못 돈 소스에 「건너뜀 <오늘> — 사유」 를 남기고 재판정하라")
        sys.exit(1)

    # ③ 발행본 본문 = 오늘 호 대조 (로컬 웹판이 있을 때)
    if not html_p:
        print("안내: 로컬 웹판 없음(URL 직접 지정) — 본문 대조(③)는 생략, 공유 판정만 했다")
        return 0
    vm = re.search(r'"ver"\s*:\s*"([^"]+)"', body)
    if not vm:
        print("실패: 메타에 ver 가 없다 — 발행본 본문을 특정할 수 없다 (응답 형식 변경 의심)")
        sys.exit(1)
    fcode, fbody = fetch_anon(f"https://{uid}.frame.claudeusercontent.com/_f/{vm.group(1)}")
    if fcode != 200:
        print(f"실패: 발행본 본문 조회 HTTP {fcode}")
        sys.exit(1)
    hm = H1.search(io.open(html_p, encoding="utf-8").read())
    if not hm:
        print("실패: 로컬 웹판에 h1 이 없다 — 대조 기준을 세울 수 없다")
        sys.exit(1)
    h1 = re.sub(r"<[^>]+>", "", hm.group(1))
    h1 = re.sub(r"\s+", " ", h1).strip()
    if h1 not in re.sub(r"\s+", " ", fbody):
        print(f"실패: 발행본(핀 버전)에 오늘 호 h1 「{h1}」 이 없다 — 핀이 옛 버전"
              "이거나 다른 호다. 공유 버전을 최신 번호로 옮기고 재판정하라 (이슈 #21)")
        sys.exit(1)
    print(f"통과: 공유 ON + 발행본 본문에 오늘 호 h1 확인 「{h1}」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
