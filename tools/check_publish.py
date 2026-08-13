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

USAGE = "사용법: python tools/check_publish.py [YYYY-MM-DD | 아티팩트URL]"
KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)


def resolve(arg):
    """(아티팩트 URL, 로컬 웹판 경로 또는 None) 반환."""
    if arg and arg.startswith("http"):
        return arg, None
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
    return url, (html if os.path.exists(html) else None)


def frame_meta(uid):
    return fetch_anon(f"https://claude.ai/api/frame/{uid}?via=user_open",
                      FRAME_API_HEADERS)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    url, html_p = resolve(arg)
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
