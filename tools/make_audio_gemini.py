# -*- coding: utf-8 -*-
"""대본 → 2인 라디오 오디오 (Gemini TTS, AI Studio 무료층)

사용: python tools/make_audio_gemini.py output/script/YYYY-MM-DD.md [출력.wav]

키: briefing-kit/.env 의 GEMINI_API_KEY, 또는 환경변수. 채팅·코드에 키를 박지 않는다.
.env 는 .gitignore 대상이다. 배포 킷에는 키가 포함되지 않는다 — 이 엔진은 본인용이다.

Edge TTS 와의 차이: 멀티스피커 한 호출 + 스타일 지시(뉴스 앵커 톤)가 된다.
대본은 한 글자 그대로 읽는다 — 노트북LM과 달리 재구성하지 않는다.

무료층 한도(분당 요청 수)가 있어 대본이 아주 길면 나눠 호출한다.
출력은 24kHz 16bit mono WAV.
"""
import subprocess as _sp
import io, os, sys, json, struct, base64, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script_lib import parse_script

MODEL = "gemini-2.5-flash-preview-tts"
VOICES = {"A": "Kore", "B": "Charon"}   # A 앵커(여) / B 기자(남)
STYLE = ("한국 아침 라디오 경제뉴스 낭독이다. 명료하게, 잡담과 감탄사 없이. "
         "속도는 표준 낭독보다 1.5배 빠르게 — 바쁜 아침 경제 라디오의 경쾌한 템포다. 단 발음은 뭉개지 않는다. "
         "Anchor 는 앵커, Reporter 는 기자다. 숫자는 또박또박 읽는다. "
         "'제일기획'은 반드시 '제일기획'으로 정확히 발음한다.")

def load_key():
    k = os.environ.get("GEMINI_API_KEY")
    if k: return k.strip()
    env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env):
        for line in io.open(env, encoding="utf-8"):
            if line.strip().startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None  # 키 없음 — 호출부가 edge 로 강등한다
    sys.exit("GEMINI_API_KEY 가 없다. briefing-kit/.env 에 GEMINI_API_KEY=... 를 넣어라. "
             "발급: https://aistudio.google.com/apikey")

def wav_header(pcm_len, rate=24000, ch=1, width=2):
    byte_rate = rate * ch * width
    return (b"RIFF" + struct.pack("<I", 36 + pcm_len) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, ch, rate, byte_rate, ch * width, width * 8) +
            b"data" + struct.pack("<I", pcm_len))

def call(key, dialog_text):
    body = {
        "contents": [{"parts": [{"text": STYLE + "\n\nTTS the following conversation:\n" + dialog_text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
                {"speaker": "Anchor",   "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICES["A"]}}},
                {"speaker": "Reporter", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICES["B"]}}},
            ]}},
        },
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    part = res["candidates"][0]["content"]["parts"][0]["inlineData"]
    return base64.b64decode(part["data"])

def main():
    key = load_key()
    if not key:
        _fallback_edge(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1].replace("script","audio").rsplit(".",1)[0]+".wav")
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(src).replace("script", "audio"),
        os.path.splitext(os.path.basename(src))[0] + "-gemini.wav")
    lines = parse_script(src)  # 대본 파싱은 script_lib 가 정본
    if not lines: sys.exit("A:/B: 대사가 없다: " + src)
    dialog = "\n".join(("Anchor: " if sp == "A" else "Reporter: ") + tx for sp, tx in lines)
    # 무료층 안전선: 4000자 넘으면 절반씩 나눠 호출
    chunks, cur = [], ""
    for ln in dialog.split("\n"):
        if len(cur) + len(ln) > 4000 and cur: chunks.append(cur); cur = ln
        else: cur = (cur + "\n" + ln).strip()
    chunks.append(cur)
    pcm = b""
    for i, ch in enumerate(chunks):
        print(f"[{i+1}/{len(chunks)}] {len(ch)}자 호출...")
        pcm += call(key, ch)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(wav_header(len(pcm)) + pcm)
    print("완료:", dst, f"{len(pcm)/48000:.0f}초 · {len(pcm)/1048576:.1f}MB")

if __name__ == "__main__":
    main()


def _fallback_edge(src, dst):
    """GEMINI_API_KEY 부재 시 edge 로 자동 강등 (config on_missing_key: edge)."""
    out = dst.rsplit(".", 1)[0] + ".mp3"
    print("GEMINI_API_KEY 없음 - edge 로 강등:", out)
    tool = __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "make_audio.py")
    raise SystemExit(_sp.call([__import__("sys").executable, tool, src, out]))
