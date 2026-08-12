# -*- coding: utf-8 -*-
"""라디오 대본 파서 — 단일 정의.

대본 형식이 바뀌면 이 파일만 고친다.

make_audio.py / make_audio_gemini.py / make_audio_supertonic.py / embed_radio.py 에
중복돼 있던 A:/B: 파싱의 정본이다. 규칙은 네 구현과 동일하다:
- 각 줄을 strip 한 뒤 "A: ..." / "B: ..." 패턴(^([AB]):\\s*(.+)$)에 맞는 줄만 취한다
- 그 외(메타·부록·빈 줄)는 무시한다
"""
import io, re, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

USAGE = "사용법: python tools/script_lib.py   (자기시험 — examples/sample-script.md 파싱)"

_LINE = re.compile(r"^([AB]):\s*(.+)$")

def parse_script(path):
    """대본 파일을 읽어 [(speaker, text), ...] 를 돌려준다.

    "A:"/"B:" 로 시작하는 줄만 취한다 (strip 후 매칭). 기존 네 구현과 완전히 같은 동작.
    """
    lines = []
    for raw in io.open(path, encoding="utf-8"):
        m = _LINE.match(raw.strip())
        if m:
            lines.append((m.group(1), m.group(2)))
    return lines

def speakers(lines):
    """parse_script 결과에서 등장 화자 집합을 돌려준다."""
    return {sp for sp, _ in lines}

if __name__ == "__main__":
    import os
    sample = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "examples", "sample-script.md")
    if not os.path.exists(sample):
        sys.exit("자기시험 실패 — 샘플 대본 없음: " + sample + "\n" + USAGE)
    lines = parse_script(sample)
    if not lines:
        sys.exit("자기시험 실패 — A:/B: 줄이 없다: " + sample)
    print("자기시험 통과:", sample)
    print("줄 수:", len(lines))
    print("화자:", sorted(speakers(lines)))
