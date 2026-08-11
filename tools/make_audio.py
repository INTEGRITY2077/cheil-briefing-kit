# -*- coding: utf-8 -*-
"""대본 → 2인 라디오 오디오 (Edge TTS)

사용: python tools/make_audio.py output/script/YYYY-MM-DD.md [output/audio/YYYY-MM-DD.mp3]

대본 형식: "A: ..." / "B: ..." 로 시작하는 줄만 읽는다. 그 외(메타·부록)는 무시.
음성: A(앵커)=ko-KR-SunHiNeural, B(기자)=ko-KR-InJoonNeural — config.yaml tts.voices 로 덮어쓸 수 있다.
키·로그인 불필요. 대본을 한 글자 그대로 읽는다 — 노트북LM과 달리 재구성하지 않는다.

한계: 감정 연기 지시는 안 된다. rate/pitch 만 조절 가능.
세그먼트별 mp3 를 바이트 연결한다. 동일 코덱 파라미터라 재생에 문제없고 ffmpeg 이 필요 없다.
"""
import asyncio, io, re, sys, os

VOICES = {"A": "ko-KR-SunHiNeural", "B": "ko-KR-InJoonNeural"}
RATE = "+50%"         # 1.5배속 — tts-guard pace 절
PAUSE_MS = 420        # 화자 전환 간격

def parse(path):
    lines = []
    for raw in io.open(path, encoding="utf-8"):
        m = re.match(r"^([AB]):\s*(.+)$", raw.strip())
        if m:
            lines.append((m.group(1), m.group(2)))
    return lines

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
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(src).replace("script", "audio"),
        os.path.splitext(os.path.basename(src))[0] + ".mp3")
    lines = parse(src)
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
