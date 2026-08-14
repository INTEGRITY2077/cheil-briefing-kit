# -*- coding: utf-8 -*-
"""routine-SKILL 동기화 — 마스터 SKILL.md 를 레포 routine-SKILL.md 로 복사하며
「# 킷 위치」의 로컬 절대경로를 {{KIT_ROOT}} 플레이스홀더 블록으로 치환한다.

사용: python tools/sync_skill.py <마스터SKILL경로>
출력: 킷 루트의 routine-SKILL.md (고정)

검사만: python tools/sync_skill.py --check <마스터SKILL경로>
  치환·누출 검사를 전부 돌리되 **routine-SKILL.md 를 쓰지 않는다** (2026-08-14
  이슈 #31 — dry-run 이 없어 검사만 하고 싶을 때도 덮어쓰기가 강제됐다).

역방향 판정: python tools/sync_skill.py --verify-installed <설치본경로>
  "이 파일이 설치본인가"를 판정한다 — 「# 킷 위치」 절 **안에만** {{KIT_ROOT}}
  가 남아 있는지 본다. 다른 절(예: 저장소 동기화 절)의 정당한 언급은 무시한다.
  통과(치환 완료) = 종료코드 0, 잔존 = 1. 레포 원본(치환 전 배포본)은 이 명령이
  1로 끝나는 것이 **정상**이다 — 설치 절차(SETUP 4-3)는 치환을 마친 설치본에만
  이 명령을 돌린다.

배경 (2026-08-12 검출): 수동 cp 로 동기화하다 원작자 절대경로가 그대로
배포된 사고. 치환을 스크립트로 강제하고, 결과물에 드라이브 절대경로나
사용자 홈 경로 흔적이 남으면 실패시킨다. 실패 시 종료코드 1.
역방향 판정은 이슈 #10 에서: 파일 전체 문자열 검사는 동기화 규칙을 설명하는
정당한 {{KIT_ROOT}} 언급(당시 375행) 때문에 정상 설치도 항상 실패로 떠서,
판정 범위를 「# 킷 위치」 절로 좁힌 도구를 설치 게이트로 삼는다.
"""
import io, os, re, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

USAGE = ("사용법: python tools/sync_skill.py <마스터SKILL경로>\n"
         "       python tools/sync_skill.py --check <마스터SKILL경로>   (검사만 — 쓰지 않음)\n"
         "       python tools/sync_skill.py --verify-installed <설치본경로>")

HEADING = "# 킷 위치"

# 레포 routine-SKILL.md 의 표준 플레이스홀더 블록 (4줄) — 문구를 바꾸지 않는다
PLACEHOLDER_BLOCK = [
    "{{KIT_ROOT}}",
    "(설치 시 SETUP 4-3이 이 자리를 실제 설치 경로로 치환한다. {{KIT_ROOT}} 가",
    "그대로 남아 있으면 설치가 끝나지 않은 것이다 — 루틴은 시작하자마자 이 값이",
    "실존 디렉토리인지 확인하고, 아니면 생성하지 말고 그 사실만 보고한다.)",
]

# 안전판: 드라이브 문자 절대경로(백슬래시 — URL 의 "s://" 오탐 방지) / 홈 경로 흔적
LEAK_PATTERNS = [
    (re.compile(r"[A-Za-z]:\\"), "드라이브 문자 절대경로 (예: X:\\...)"),
    (re.compile(r"[/\\]Users[/\\]"), "사용자 홈 경로 (.../Users/...)"),
    (re.compile(r"%USERPROFILE%|\$HOME|~[/\\]", re.I), "홈 디렉토리 참조"),
    # 유닉스 절대경로 (2026-08-14 이슈 #31 — 종전 패턴이 Windows 중심이라 리눅스
    # 원작 환경의 /home/<계정> 류 누출이 exit 0 통과했다(실측). URL 경로 속의
    # host/home/… 은 앞 문자가 단어 문자라 lookbehind 로 제외된다)
    (re.compile(r"(?<![\w.\-])/(?:home|root|mnt|media|srv)/[A-Za-z0-9._\-]+"),
     "유닉스 절대경로 (/home·/root·/mnt/...)"),
]


def substitute(lines):
    """「# 킷 위치」 다음 줄(절대경로)을 플레이스홀더 블록으로 치환한 새 리스트를 돌려준다."""
    out, i, done = [], 0, False
    while i < len(lines):
        out.append(lines[i])
        if not done and lines[i].strip() == HEADING and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt == PLACEHOLDER_BLOCK[0]:
                pass  # 이미 플레이스홀더 형식 — 그대로 둔다 (멱등)
            else:
                out.extend(PLACEHOLDER_BLOCK)
                i += 1  # 절대경로 한 줄을 버린다
            done = True
        i += 1
    if not done:
        sys.exit(f"실패: 마스터에서 「{HEADING}」 절을 찾지 못했다")
    return out


def check_leaks(text):
    """드라이브 절대경로·홈 경로 흔적이 있으면 (줄번호, 이유, 줄) 목록을 돌려준다."""
    leaks = []
    for n, line in enumerate(text.splitlines(), 1):
        for pat, why in LEAK_PATTERNS:
            if pat.search(line):
                leaks.append((n, why, line.strip()))
    return leaks


def kit_section(lines):
    """「# 킷 위치」 절 본문(헤딩 다음 줄부터 다음 「# 」 헤딩 전까지)을
    (시작 줄번호(1기준), 줄 리스트) 로 돌려준다. 절이 없으면 None."""
    for i, line in enumerate(lines):
        if line.strip() == HEADING:
            body = []
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("# "):
                    break
                body.append(lines[j])
            return i + 2, body
    return None


def verify_installed(path):
    """설치본 판정 — 「# 킷 위치」 절 안의 {{KIT_ROOT}} 잔존만 본다.
    다른 절의 정당한 언급은 무시한다. 잔존 시 exit 1."""
    lines = io.open(path, encoding="utf-8").read().splitlines()
    sec = kit_section(lines)
    if sec is None:
        sys.exit(f"실패: {path} 에서 「{HEADING}」 절을 찾지 못했다 — 판정 대상이 아니다")
    start, body = sec
    hits = [(start + k, ln.strip()) for k, ln in enumerate(body) if "{{KIT_ROOT}}" in ln]
    if hits:
        print(f"실패: 「{HEADING}」 절에 {{{{KIT_ROOT}}}} 가 남아 있다 — 치환(SETUP 4-3)이 끝나지 않았다")
        print("  (레포 원본·치환 전 배포본이면 이 실패가 정상이다 — 설치본에만 이 판정을 돌린다)")
        for n, ln in hits:
            print(f"  {n}행: {ln}")
        sys.exit(1)
    print(f"통과: {path} — 「{HEADING}」 절에 플레이스홀더 잔존 없음 (설치본 판정)")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--verify-installed":
        if len(sys.argv) < 3 or not os.path.exists(sys.argv[2]):
            sys.exit(USAGE)
        verify_installed(sys.argv[2])
        return
    check_only = len(sys.argv) >= 2 and sys.argv[1] == "--check"
    args = sys.argv[2:] if check_only else sys.argv[1:]
    if not args or not os.path.exists(args[0]):
        sys.exit(USAGE)
    master = args[0]
    kit_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest = os.path.join(kit_root, "routine-SKILL.md")

    lines = io.open(master, encoding="utf-8").read().splitlines()
    result = "\n".join(substitute(lines)) + "\n"

    leaks = check_leaks(result)
    if leaks:
        print("실패: 결과물에 로컬 경로 흔적이 남아 있다 — 커밋하면 배포 사고가 된다")
        for n, why, line in leaks:
            print(f"  {n}행 [{why}] {line}")
        sys.exit(1)

    if check_only:
        print(f"통과(검사만): 치환·누출 검사 이상 없음 ({len(result.splitlines())}줄) — "
              "routine-SKILL.md 는 쓰지 않았다 (--check, 이슈 #31)")
        return
    io.open(dest, "w", encoding="utf-8", newline="\n").write(result)
    print(f"통과: {dest} 재생성 ({len(result.splitlines())}줄, 플레이스홀더 블록 유지)")


if __name__ == "__main__":
    main()
