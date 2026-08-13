# -*- coding: utf-8 -*-
"""E6 공유 확정 게이트 — 발행된 아티팩트가 실제로 전체(링크) 공유인지 익명으로 판정한다.

사용법:
  python tools/check_publish.py [YYYY-MM-DD | 아티팩트URL]
    날짜 생략 시 오늘. 날짜를 주면 output/artifact-url-<날짜>.txt 에서 URL을 읽는다.

판정:
  익명(무인증) GET 이 200 이면 공유됨 → 통과 (종료코드 0)
  404 / 로그인 리다이렉트면 비공개 → 실패 (종료코드 1)

근거: 2026-08-11 실측 — 새 아티팩트는 비공개가 기본값이라 발행자 화면에선 멀쩡해도
링크를 받은 독자에겐 404 다. 2026-08-13 편집장 지시 — "항상 전체공유로해야함.
왜 이 게이트는 안만들었어?" 발행의 완결 조건은 로컬 산출물이 아니라 익명 개통이다.
"""
import io
import os
import re
import sys
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import urllib.request
import urllib.error

USAGE = "사용법: python tools/check_publish.py [YYYY-MM-DD | 아티팩트URL]"
UA = "Mozilla/5.0 (compatible; cheil-briefing-kit check_publish; anonymous-probe)"


def resolve_url(arg, kit_root):
    if arg and arg.startswith("http"):
        return arg, None
    target = arg or date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", target):
        print(USAGE)
        sys.exit(2)
    url_file = os.path.join(kit_root, "output", f"artifact-url-{target}.txt")
    if not os.path.exists(url_file):
        print(f"실패: {os.path.relpath(url_file, kit_root)} 이 없다 — "
              f"발행 절차가 URL 기록을 빠뜨렸거나 아직 발행 전이다")
        sys.exit(1)
    url = io.open(url_file, encoding="utf-8").read().strip().splitlines()[0].strip()
    if not url.startswith("http"):
        print(f"실패: URL 파일 첫 줄이 URL 이 아니다: {url[:80]}")
        sys.exit(1)
    return url, url_file


def main():
    kit_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    url, url_file = resolve_url(arg, kit_root)
    m = re.search(r"artifact/([0-9a-f-]{36})", url)
    if not m:
        print(f"실패: URL 에서 아티팩트 ID 를 못 찾았다: {url[:80]}")
        sys.exit(1)
    probe = f"https://claude.ai/api/public/artifact/{m.group(1)}"
    print(f"판정 대상: {url}")

    # 페이지 HTML 은 공유 여부와 무관하게 동일한 SPA 셸(200)이라 판별력이 없다
    # (2026-08-13 실측: 비공개/공유 모두 14186B 동일 셸). 익명으로 공개 API 를
    # 찔러 판정한다 — 비공개면 403(forbidden), 공유면 404/200 (실측 3회 일관).
    req = urllib.request.Request(probe, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        print(f"실패: 네트워크 오류로 판정 불가 — {e}")
        sys.exit(1)

    if code == 403:
        print("실패: 익명 조회 403 — 아티팩트가 비공개다. Share → General access 를 "
              "Anyone with the link 로 전환하라 (새 아티팩트는 비공개가 기본값 — 08.11 함정). "
              "409(unscannable)로 전환이 거절되면 오디오가 audio/mp4(AAC)인지 보라 — "
              "스캐너가 AAC data URI 를 못 다룬다. MP3(audio/mpeg)로 재이식·재발행이 처방이다 (2026-08-13 규명)")
        sys.exit(1)
    print(f"통과: 익명 조회 {code} (403 아님) — 링크 공유로 판정. "
          "간접 판별이니 독자 제보로 최종 확인하라")
    return 0


if __name__ == "__main__":
    sys.exit(main())
