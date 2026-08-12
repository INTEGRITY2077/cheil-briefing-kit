# -*- coding: utf-8 -*-
"""routine-SKILL 동기화 — 마스터 SKILL.md 를 레포 routine-SKILL.md 로 복사하며
「# 킷 위치」의 로컬 절대경로를 {{KIT_ROOT}} 플레이스홀더 블록으로 치환한다.

사용: python tools/sync_skill.py <마스터SKILL경로>
출력: 킷 루트의 routine-SKILL.md (고정)

배경 (2026-08-12 검출): 수동 cp 로 동기화하다 원작자 절대경로가 그대로
배포된 사고. 치환을 스크립트로 강제하고, 결과물에 드라이브 절대경로나
사용자 홈 경로 흔적이 남으면 실패시킨다. 실패 시 종료코드 1.
"""
import io, os, re, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

USAGE = "사용법: python tools/sync_skill.py <마스터SKILL경로>"

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


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    master = sys.argv[1]
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

    io.open(dest, "w", encoding="utf-8", newline="\n").write(result)
    print(f"통과: {dest} 재생성 ({len(result.splitlines())}줄, 플레이스홀더 블록 유지)")


if __name__ == "__main__":
    main()
