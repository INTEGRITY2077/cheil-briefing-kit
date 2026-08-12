# -*- coding: utf-8 -*-
"""대본 → 라디오 오디오 (Supertonic 3 — 로컬 ONNX, 키·네트워크 불필요)

사용: python tools/make_audio_supertonic.py <대본.md> [출력.wav] [보이스]

대본 형식: "A: ..." / "B: ..." 로 시작하는 줄만 읽는다.
보이스: 내장 이름(M1~M5, F1~F5) 또는 voices/*.json 경로(블렌드 보이스).
기본값은 voices/anchor-f1f2-30.json (2026-08-12 실청 채택 — F1 70% + F2 30%).
표준은 1인(A: 줄만). 2인 대본이 들어오면 깨지지 않게 B=M2 로 받아주지만, 2인 판형은 gemini 전용이다.

특성 (2026-08-12 실측):
- 완전 로컬 — 최초 1회만 HuggingFace 모델 다운로드(~99MB), 이후 오프라인
- speed 파라미터 지원(기본 1.5 — tts-guard pace 절), 한국어 자동 청크(120자)
- CPU 실시간 2배속 합성. Windows 네이티브 동작 확인
- 감정 지시는 없다 — 톤은 보이스 블렌딩(voices/*.json)으로 고정한다
"""
import io, os, re, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

USAGE = ("사용법: python tools/make_audio_supertonic.py <대본.md> [출력.wav] [보이스]\n"
         "예: python tools/make_audio_supertonic.py output/script/2026-08-12.md")

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_VOICE = os.path.join(KIT, "voices", "anchor-f1f2-30.json")
# 합성 배속 금지 — speed는 음소 길이 예측을 압축해 합성수사("백사십사만")의
# 음절을 떨어뜨린다 (2026-08-12 실측: 1.5에서 "십사만"으로 씹힘).
# 기본 속도로 합성하고, 청취 배속은 웹판 플레이어의 −/+ 버튼이 담당한다.
SPEED = 1.05
B_VOICE = "M2"   # 안전판 — 표준은 1인(A:만). 2인 판형은 gemini 전용

def parse(path):
    lines = []
    for raw in io.open(path, encoding="utf-8"):
        m = re.match(r"^([AB]):\s*(.+)$", raw.strip())
        if m:
            lines.append((m.group(1), m.group(2)))
    return lines

def load_style(tts, name_or_path):
    if os.path.exists(name_or_path):
        return tts.get_voice_style_from_path(name_or_path)
    return tts.get_voice_style(name_or_path)

def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(src).replace("script", "audio"),
        os.path.splitext(os.path.basename(src))[0] + ".wav")
    voice = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_VOICE

    lines = parse(src)
    if not lines:
        sys.exit("A:/B: 형식의 대사가 없다: " + src)

    from supertonic import TTS
    import numpy as np
    tts = TTS(model="supertonic-3")
    styles = {"A": load_style(tts, voice)}
    if any(sp == "B" for sp, _ in lines):
        styles["B"] = load_style(tts, B_VOICE)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    segs = []
    for i, (sp, text) in enumerate(lines, 1):
        wav, _ = tts.synthesize(text, styles[sp], speed=SPEED, lang="ko")
        segs.append(np.asarray(wav).squeeze())
        print(f"[{i}/{len(lines)}] {sp} {len(text)}자")
    out = np.concatenate(segs)
    tts.save_audio(out, dst)
    print("완료:", dst)

if __name__ == "__main__":
    main()
