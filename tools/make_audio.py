# -*- coding: utf-8 -*-
"""대본 → 2인 라디오 오디오 (Edge TTS)

사용: python tools/make_audio.py output/script/YYYY-MM-DD.md [output/audio/YYYY-MM-DD.mp3]

대본 형식: "A: ..." / "B: ..." 로 시작하는 줄만 읽는다. 그 외(메타·부록)는 무시.
음성: A(앵커)=ko-KR-SunHiNeural, B(기자)=ko-KR-InJoonNeural — config.yaml tts.voices 로 덮어쓸 수 있다.
키·로그인 불필요. 대본을 한 글자 그대로 읽는다 — 노트북LM과 달리 재구성하지 않는다.

한계: 감정 연기 지시는 안 된다. rate/pitch 만 조절 가능.
세그먼트별 mp3 를 바이트 연결한다. 동일 코덱 파라미터라 재생에 문제없고 ffmpeg 이 필요 없다.
"""
import asyncio, io, sys, os

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script_lib import parse_script

USAGE = ("사용법: python tools/make_audio.py <대본.md> [출력.mp3]\n"
         "예: python tools/make_audio.py examples/sample-script.md output/audio/smoke-test.mp3")

VOICES = {"A": "ko-KR-SunHiNeural", "B": "ko-KR-InJoonNeural"}
RATE = "+50%"         # 1.5배속 — tts-guard pace 절

def load_config_overrides():
    """킷 루트 config.yaml 의 tts.edge 값이 있으면 VOICES/RATE 를 덮어쓴다. 없으면 조용히 기본값."""
    global VOICES, RATE
    cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
    if not os.path.exists(cfg):
        return
    try:
        import yaml
        c = yaml.safe_load(io.open(cfg, encoding="utf-8")) or {}
        e = ((c.get("tts") or {}).get("edge") or {})
        if e.get("voice_anchor"):   VOICES["A"] = e["voice_anchor"]
        if e.get("voice_reporter"): VOICES["B"] = e["voice_reporter"]
        if e.get("rate"):           RATE = str(e["rate"])
    except Exception:
        pass
PAUSE_MS = 420        # 화자 전환 간격

async def synth(text, voice):
    import edge_tts
    buf = b""
    com = edge_tts.Communicate(text, voice, rate=RATE)
    async for chunk in com.stream():
        if chunk["type"] == "audio":
            buf += chunk["data"]
    return buf

def silence_mp3(ms):
    # edge-tts 로 짧은 무음을 만들 수 없어, 문장부호 낭독 간격에 맡긴다.
    # 필요하면 세그먼트 사이에 미리 만든 무음 mp3 를 끼운다. 현재는 빈 바이트.
    return b""

async def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    load_config_overrides()
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(src).replace("script", "audio"),
        os.path.splitext(os.path.basename(src))[0] + ".mp3")
    lines = parse_script(src)  # 대본 파싱은 script_lib 가 정본
    if not lines:
        print("A:/B: 형식의 대사가 없다:", src); sys.exit(1)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    out = b""
    for i, (sp, text) in enumerate(lines):
        seg = await synth(text, VOICES[sp])
        out += seg + silence_mp3(PAUSE_MS)
        print(f"[{i+1}/{len(lines)}] {sp} {len(text)}자 → {len(seg)}b")
    with open(dst, "wb") as f:
        f.write(out)
    print("완료:", dst, f"{len(out)/1024:.0f}KB")

if __name__ == "__main__":
    asyncio.run(main())
