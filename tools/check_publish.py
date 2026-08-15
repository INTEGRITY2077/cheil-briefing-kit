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

종료코드 3분법 (2026-08-15 신설 — 이슈 #37):
  0  통과 — 공유 ON (+ 로컬 웹판이 있으면 발행본 본문에 오늘 호 h1)
  1  **판정 결과 실패** — 물어봤고 답을 받았는데 그 답이 「아니오」다
     (공유 OFF·없는 아티팩트·핀이 옛 버전·public 표식 없음·IG7 미달)
  2  **판정 불가** — 물어보지 못했다. CF 봇 차단 챌린지 수신, 네트워크 오류,
     또는 대조군 자체가 챌린지에 막힌 경우. 통과가 아니다(#21 회귀 금지) —
     run_log 종료 줄에 `check_publish:2` 로 남고 check_run 로스터 대조가 차단한다.
     종료코드를 가르는 이유는 **왜 못 냈는지**를 원장에 보존하기 위해서다.
  64 사용법 오류 (인자 형식). 종전 2 였는데 이슈 #37 이 2 를 「판정 불가」로
     쓰면서 뜻이 겹쳐 옮겼다 — 사용법 오류를 gates 에 적을 일은 없다.
왜 이 갈래가 필요한가 (2026-08-15 실측): 맥 회선에서 CF 챌린지가 403 을 주자 이
게이트가 「공유 OFF」로 오진해 E5 처방(MP3 재이식·재발행)을 지시했고 — 멀쩡한 호를
고치게 했다 — **대조군(무작위 uuid)도 같은 403 을 받아 ① 자기검증이 통과했다.**
판정 경로가 죽었는데 살아 있다고 보고하는 것이 이 이슈의 가장 위험한 지점이다.

3분법의 한계 (2026-08-15 명시 — 검수 문제 7):
  (a) 3분법을 쓰는 게이트는 이 파일(E6)과 `check_formats --check-links`(E7)
      **둘뿐**이다 — 나머지 게이트는 종전대로 0/1 만 낸다.
  (b) CF 판정은 `CF_BODY_MARKS`·`cf-mitigated` 문자열 휴리스틱이다. CF 가 문구를
      바꾸면 이 게이트는 다시 「공유 OFF」로 오진한다. 또 **본문 표식은 비-200
      응답에서만** 본다 — 200 본문의 인용까지 CF 로 보면 멀쩡한 호가 판정 불가로
      접힌다 (검수 문제 1·8).
  (c) 이 갈래는 오진을 막을 뿐 **CF 회선에서 공유 상태를 판정해 주지 않는다.**
      2 를 받은 호의 공유 여부는 미지로 남는다 — 다른 회선 재판정, 또는 소유자
      직접 확인 + 「수동 확인 마감」 기록(routine-SKILL 4b ⑤)만이 닫는 길이다.
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
from check_formats import (fetch_anon, cf_challenge,  # noqa: E402 — 판정 경로 단일 정본
                          FRAME_API_HEADERS)
from check_run import check_sweep  # noqa: E402 — IG7 봉인의 단일 정본 (④)

USAGE = "사용법: python tools/check_publish.py [YYYY-MM-DD | 아티팩트URL]"
EX_USAGE = 64   # 사용법 오류 (BSD sysexits) — 2 는 「판정 불가」로 옮겨갔다 (이슈 #37)
UNDECIDED = 2   # 판정 불가 — 통과가 아니고 「판정 결과 실패」와도 다르다 (이슈 #37)
# 판정 불가 문안. E5 처방(MP3 재이식·재발행)을 **절대 내지 않는다** — 이 응답은
# 공유 상태에 대해 아무것도 증언하지 않으므로 어떤 처방도 오진이다 (이슈 #37).
CF_MSG = ("판정 불가: 공유 상태를 판정하지 못했다 (봇 차단 페이지 수신 — {why}). "
          "이 회선에서는 이 게이트가 판정 불가다 — 다른 회선에서 재판정하거나, "
          "소유자가 브라우저에서 공유 상태를 직접 확인하고 그 사실을 사유와 함께 "
          "기록하라 — run_log 종료 줄 gates 에 「check_publish:2」 + reason 에 "
          '"수동 확인 마감 <YYYY-MM-DD HH:MM> check_publish — 확인 경위". '
          "check_run 이 이 형식을 읽어 그 날짜를 닫는다 (2026-08-15 수리 — 검수 "
          "문제 4: 종전에는 문안만 요구하고 기계가 reason 을 읽지 않아, :2 로 끝난 "
          "날짜가 영구히 exit 1 이었다 — routine-SKILL 4b ⑤)")
KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)


def resolve(arg):
    """(아티팩트 URL, 로컬 웹판 경로 또는 None, 대상 날짜 또는 None) 반환."""
    if arg and arg.startswith("http"):
        return arg, None, None
    target = arg or date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", target):
        print(USAGE)
        sys.exit(EX_USAGE)   # 이슈 #37 — 2 는 이제 「판정 불가」다
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
    """(코드, 본문, 헤더dict) — 헤더까지 받는다 (이슈 #37: CF 챌린지는 403 본문·
    cf-mitigated 헤더로만 식별되는데 종전 2-튜플에는 둘 다 없었다)."""
    return fetch_anon(f"https://claude.ai/api/frame/{uid}?via=user_open",
                      FRAME_API_HEADERS, with_headers=True)


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
    ctrl_code, ctrl_body, ctrl_hdr = frame_meta(str(uuidlib.uuid4()))
    # 대조군이 CF 챌린지면 **대상 조회를 하기도 전에** 끝낸다 (이슈 #37 ③).
    # 종전에는 대조군을 `== 200` 으로만 봐서, CF 구간에서 대조군도 403 을 받으면
    # 자기검증이 조용히 통과하고 대상의 같은 403 이 「공유 OFF」로 오진됐다 —
    # 판정 경로가 죽었는데 살아 있다고 보고하는 자리다 (2026-08-15 맥 회선 실측).
    why = cf_challenge(ctrl_body, ctrl_hdr, ctrl_code)
    if why:
        print(CF_MSG.format(why="대조군(무작위 uuid) 조회에서 " + why))
        sys.exit(UNDECIDED)
    if ctrl_code is None:
        print(f"판정 불가: 대조군 조회가 네트워크 오류로 끝났다 — {ctrl_body[:100]} "
              "(판정 경로가 살아 있는지 확인하지 못한 채로는 대상 판정에 뜻이 없다. "
              "판정 불가는 통과가 아니다 — 이슈 #37)")
        sys.exit(UNDECIDED)
    if ctrl_code == 200:
        print("실패: 대조군(무작위 uuid)이 200 — 판정 경로 자체가 신뢰 불가 (응답 형식 변경 의심)")
        sys.exit(1)

    # ② 공유 직접 판정
    code, body, hdr = frame_meta(uid)
    why = cf_challenge(body, hdr, code)
    if why:   # 이슈 #37 ② — 봇 차단은 「공유 OFF」가 아니다. E5 처방을 내지 않는다
        print(CF_MSG.format(why=f"대상 조회 HTTP {code} · " + why))
        sys.exit(UNDECIDED)
    if code is None:
        print(f"판정 불가: 네트워크 오류로 판정하지 못했다 — {body[:100]} "
              "(판정 불가는 통과가 아니다. 회선을 확인하고 재판정하라 — 이슈 #37)")
        sys.exit(UNDECIDED)
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
    fcode, fbody, fhdr = fetch_anon(
        f"https://{uid}.frame.claudeusercontent.com/_f/{vm.group(1)}", with_headers=True)
    # 본문 조회도 같은 회선을 탄다 (이슈 #37). **코드를 넘긴다** — fbody 는 그 호의
    # 발행본 HTML 자체라, 지면이 「just a moment」·challenges.cloudflare.com 을
    # 인용하기만 해도 HTTP 200 정상 응답이 판정 불가(2)로 접혔다. 그러면 새 호
    # 마감 규칙상 멀쩡한 호가 기계로는 영영 닫히지 않는다 (2026-08-15 검수 문제 1·8;
    # 재현: cf_challenge('<h1>Just a moment, please</h1>', {}) 가 히트를 냈다).
    # 200 에서도 cf-mitigated **헤더**는 그대로 CF 로 본다 — 지면이 못 붙이는 표식이다.
    fwhy = cf_challenge(fbody, fhdr, fcode)
    if fwhy:
        print(CF_MSG.format(why=f"발행본 본문 조회 HTTP {fcode} · " + fwhy))
        sys.exit(UNDECIDED)
    if fcode is None:
        print(f"판정 불가: 발행본 본문 조회가 네트워크 오류로 끝났다 — {fbody[:100]} (이슈 #37)")
        sys.exit(UNDECIDED)
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
