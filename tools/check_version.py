# -*- coding: utf-8 -*-
"""킷 버전 게이트 — 이 설치본이 최신 정책 위에서 생산하는지 판정한다.

사용법:
  python tools/check_version.py            # 원격(origin/main)과 대조
  python tools/check_version.py --local    # 네트워크 없이 로컬 버전만 출력

판정:
  로컬 VERSION == 원격 VERSION → 통과 (종료코드 0)
  다르면 → 실패 (종료코드 1) — 생산을 시작하기 전에 `git pull` 하라

근거 (2026-08-13 창설): 워커마다 산출물은 독립이지만 **정책은 전 워커가 같은
버전 위에서** 생산해야 한다. 버전 체계는 CalVer `vYYYY.MM.DD[.N]`, 정본은
루트 `VERSION` 파일 — 상세는 CHANGELOG.md.
"""
import io
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_local():
    p = os.path.join(KIT_ROOT, "VERSION")
    if not os.path.exists(p):
        print("실패: VERSION 파일이 없다 — v2026.08.13 이전의 구판 킷이다. `git pull` 하라")
        sys.exit(1)
    return io.open(p, encoding="utf-8").read().strip()


def git(*args):
    return subprocess.run(["git", "-C", KIT_ROOT] + list(args),
                          capture_output=True, text=True, timeout=60)


def main():
    local = read_local()
    if "--local" in sys.argv[1:]:
        print(f"로컬 킷 버전: {local}")
        return 0

    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        print(f"경고: git 저장소가 아니다(zip 설치본?) — 로컬 {local} 만 확인했다. "
              "원격 대조가 불가능하니 최신성은 보장되지 않는다")
        return 0

    if git("fetch", "--quiet", "origin", "main").returncode != 0:
        print(f"경고: 원격 조회 실패(네트워크/인증) — 로컬 {local} 만 확인했다. "
              "오프라인이면 생산은 진행하되 보고에 이 사실을 남겨라")
        return 0

    r = git("show", "origin/main:VERSION")
    if r.returncode != 0:
        print(f"경고: 원격에 VERSION 이 없다 — 로컬 {local}. 원격이 구판일 수 있다(역전 상태)")
        return 0
    remote = r.stdout.strip()

    if local == remote:
        print(f"통과: 킷 버전 {local} — 원격과 일치, 최신 정책 위에서 생산한다")
        return 0
    print(f"실패: 로컬 {local} ≠ 원격 {remote} — 구판 정책으로 생산하면 안 된다. "
          "생산을 시작하기 전에 `git pull origin main` 하라 "
          "(산출물은 워커마다 독립이지만 정책은 정렬돼야 한다 — CHANGELOG.md)")
    sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
