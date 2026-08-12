# -*- coding: utf-8 -*-
"""대본 → 라디오 오디오 (Supertonic 3 — 로컬 ONNX, 키·네트워크 불필요)

사용: python tools/make_audio_supertonic.py <대본.md> [출력.wav] [보이스]

대본 형식: "A: ..." / "B: ..." 로 시작하는 줄만 읽는다.
보이스: 내장 이름(M1~M5, F1~F5) 또는 voices/*.json 경로(블렌드 보이스).
기본값은 voices/anchor-f1f2-30.json (2026-08-12 실청 채택 — F1 70% + F2 30%).
표준은 1인(A: 줄만). 2인 대본이 들어오면 깨지지 않게 B=M2 로 받아주지만, 2인 판형은 gemini 전용이다.

특성 (2026-08-12 실측):
- 완전 로컬 — 최초 1회만 HuggingFace 모델 다운로드(~99MB), 이후 오프라인
- 합성 speed 1.05 고정(배속은 플레이어 담당 — tts-guard pace 절), 한국어 자동 청크(120자)
- CPU 실시간 2배속 합성. Windows 네이티브 동작 확인
- 감정 지시는 없다 — 톤은 보이스 블렌딩(voices/*.json)으로 고정한다

강등 사다리: supertonic 실패(import·합성 예외) 시 tools/make_audio_gemini.py 로 강등한다.
gemini 도구는 키가 없으면 스스로 edge 로 강등하므로 supertonic→gemini→edge 체인이 완성된다.
"""
import io, os, subprocess, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script_lib import parse_script  # 대본 형식이 바뀌면 script_lib.py 만 고친다

USAGE = ("사용법: python tools/make_audio_supertonic.py <대본.md> [출력.wav] [보이스]\n"
         "예: python tools/make_audio_supertonic.py output/script/2026-08-12.md")

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_VOICE = os.path.join(KIT, "voices", "anchor-f1f2-30.json")
# 합성 배속 금지 — speed는 음소 길이 예측을 압축해 합성수사("백사십사만")의
# 음절을 떨어뜨린다 (2026-08-12 실측: 1.5에서 "십사만"으로 씹힘).
# 기본 속도로 합성하고, 청취 배속은 웹판 플레이어의 −/+ 버튼이 담당한다.
SPEED = 1.05
B_VOICE = "M2"   # 안전판 — 표준은 1인(A:만). 2인 판형은 gemini 전용

def load_config_overrides():
    """킷 루트 config.yaml 의 tts.supertonic 값이 있으면 기본 보이스를 덮어쓴다. 없으면 조용히 기본값.

    SPEED 는 config 로 열지 않는다 — 합성수사 씹힘 방지 고정값(모듈 상단 주석 참조).
    """
    global DEFAULT_VOICE, B_VOICE
    cfg = os.path.join(KIT, "config.yaml")
    if not os.path.exists(cfg):
        return
    try:
        import yaml
        c = yaml.safe_load(io.open(cfg, encoding="utf-8")) or {}
        s = ((c.get("tts") or {}).get("supertonic") or {})
        if s.get("voice"):
            v = str(s["voice"])
            # 상대경로(./voices/...)는 킷 루트 기준으로 푼다. 내장 이름(M1~F5)은 그대로.
            DEFAULT_VOICE = os.path.normpath(os.path.join(KIT, v)) if ("/" in v or "\\" in v) else v
        if s.get("voice_reporter"):
            B_VOICE = str(s["voice_reporter"])
    except Exception:
        pass

def demote_to_gemini(src, dst):
    """supertonic 실패 시 gemini 도구로 강등한다 (gemini 는 키 없으면 스스로 edge 로 강등)."""
    print("강등: supertonic→gemini(→edge)")
    tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_audio_gemini.py")
    raise SystemExit(subprocess.call([sys.executable, tool, src, dst]))

def load_style(tts, name_or_path):
    if os.path.exists(name_or_path):
        return tts.get_voice_style_from_path(name_or_path)
    return tts.get_voice_style(name_or_path)

def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    load_config_overrides()
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(src).replace("script", "audio"),
        os.path.splitext(os.path.basename(src))[0] + ".wav")
    voice = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_VOICE

    lines = parse_script(src)
    if not lines:
        sys.exit("A:/B: 형식의 대사가 없다: " + src)

    try:
        from supertonic import TTS
        import numpy as np
        tts = TTS(model="supertonic-3")
        styles = {"A": load_style(tts, voice)}
        if any(sp == "B" for sp, _ in lines):
            styles["B"] = load_style(tts, B_VOICE)
        print("보이스: A=" + str(voice) + (" B=" + B_VOICE if "B" in styles else ""))

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        segs = []
        for i, (sp, text) in enumerate(lines, 1):
            wav, _ = tts.synthesize(text, styles[sp], speed=SPEED, lang="ko")
            segs.append(np.asarray(wav).squeeze())
            print(f"[{i}/{len(lines)}] {sp} {len(text)}자")
        out = np.concatenate(segs)
        tts.save_audio(out, dst)
    except SystemExit:
        raise
    except Exception as e:
        print("supertonic 실패:", type(e).__name__, e)
        demote_to_gemini(src, dst)
    print("완료:", dst)

if __name__ == "__main__":
    main()
