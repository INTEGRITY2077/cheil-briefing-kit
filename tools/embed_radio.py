# -*- coding: utf-8 -*-
"""웹판 HTML에 라디오(오디오+대본)를 이식한다.

사용: python tools/embed_radio.py <웹판.html> <오디오.wav|mp3|mp4|m4a> <대본.md>

- 웹판 표준 컨테이너는 **MP3(audio/mpeg)** 다 (2026-08-13 개정 — 종전 표준
  MP4(AAC)는 공개 공유의 콘텐츠 스캔이 못 다뤄 409 unscannable, 이슈 #14 진범.
  WAV 그대로 실으면 호가 10MB 를 넘는다). **WAV 입력은 이 도구가 자동 변환한다**:
  imageio-ffmpeg(선택 의존성, SETUP §2)가 있으면 MP3 로 변환해 audio/mpeg 로
  임베드하고 (2026-08-12 실측: 7.42MB → 2.09MB, 길이·표본율 동일), 없거나 변환이
  실패하면 경고 후 원본 그대로 임베드로 강등한다 (종료코드 0 유지 — D2 는 경고로 남는다).
  이미 .mp4/.m4a 면 변환 없이 임베드한다. 변환 산출물은 임시 디렉토리에만 쓰고
  원본 오디오 파일은 절대 건드리지 않는다.
- **비트레이트·채널·호 상한은 config 의 `tts.embed` 가 정본이다** (하드코딩 금지).
  종전에는 96k 가 코드에 박혀 있어 호 길이가 늘면 조정할 지점이 없었다. config 가
  없으면 64k/1ch 로 돈다 — 종전 기본값 96k 로 되돌아가지 않는다.
- 이식 후 호 크기를 재서 `tts.embed.max_html_mb` 를 넘으면 경고한다. 판정(종료코드)은
  `tools/check_size.py` (D8) 가 한다 — 이 도구는 이식이 일이고 게이트가 아니다.
  **호를 작게 유지하는 것은 편집 규율이지 공개 공유의 보증이 아니다** — 2026-08-12 에
  3.28MB 호와 2.14MB 호가 둘 다 공개 전환에서 거절됐고, 실제 사유는 크기가 아니라
  `{"reason":"unscannable"}`(콘텐츠 스캔 미착수)였다. publish-checklist E5 참조.
- HTML에 플레이어 블록(data:audio URI + 대본 details)이 이미 있으면 교체하고,
  **없으면 <body> 직후에 플레이어 블록을 새로 삽입한다** (뼈대 HTML도 그대로 사용 가능).
- 플레이어 JS: data:→blob: 전환(대용량 data URI 의 탐색·재생 안정화 — 다운로드는
  아티팩트 뷰어 iframe sandbox 에 allow-downloads 가 없어 어차피 불가, D2b 실측),
  배속 −/+ 버튼(1.0~2.0).
- 대본: <summary>대본</summary> ... </details> 사이를 대본 md의 A:/B: 줄로 재구성한다.
- 실패 시 원본을 건드리지 않는다 (전부 검증 후 한 번에 쓴다).
"""
import base64, io, os, re, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script_lib import parse_script

USAGE = "사용법: python tools/embed_radio.py <웹판.html> <오디오.wav|mp3|mp4|m4a> <대본.md>"

# 확장자 → MIME (없는 확장자는 audio/mpeg 로 강등)
AUDIO_MIME = {".wav": "audio/wav", ".mp3": "audio/mpeg",
              ".mp4": "audio/mp4", ".m4a": "audio/mp4"}

# 강등 경고 — 원인을 갈라서 낸다 (이슈 #4: 설치 문제와 입력 문제를 로그로 구분)
WARN_NO_FFMPEG = "경고: imageio-ffmpeg 미설치 — 원본 그대로 임베드, 호 용량 커짐(D2). SETUP §2 선택 의존성"
WARN_CONV_FAIL = "경고: MP3 변환 실패(ffmpeg 비정상 종료/빈 출력) — 원본 그대로 임베드, 호 용량 커짐(D2)"

# 오디오 최소 크기 — 빈 파일·토막 파일 차단 (이슈 #4). 실측 최소 정상치:
# 3줄 견본 AAC 96k ≈ 96KB, edge mp3 ≈ 128KB. 30KB 미만은 정상 합성일 수 없다.
AUDIO_MIN_BYTES = 30 * 1024

# config 의 tts.embed 기본값 — config 가 없거나 항목이 비었을 때만 쓴다.
# 96k 로 되돌리지 않는다: 그 값이 호를 3MB 선 위로 올려 공유 거절을 냈다 (2026-08-12).
EMBED_DEFAULTS = {"bitrate": "64k", "channels": 1, "max_html_mb": 3.0}


def load_embed_cfg():
    """킷 루트의 config.yaml 에서 tts.embed 를 읽는다. 없으면 기본값.

    pyyaml 은 SETUP §2 의 필수 의존성이지만, 없거나 config 가 깨져도 이식 자체는
    돌아야 하므로 실패는 조용히 기본값으로 흡수한다 (게이트는 check_size 가 따로 건다).
    """
    cfg = dict(EMBED_DEFAULTS)
    kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(kit, "config.yaml")
    try:
        import yaml
        with io.open(path, encoding="utf-8") as f:
            got = ((yaml.safe_load(f) or {}).get("tts") or {}).get("embed") or {}
        for k in cfg:
            if got.get(k) is not None:
                cfg[k] = got[k]
    except Exception:
        pass
    return cfg


def validate_audio(path):
    """임베드 전 오디오 판정 — 실패 사유 문자열 또는 None (이슈 #4: 조용한 실패 차단).

    ① 크기 하한 ② 컨테이너 헤더 매직(WAV RIFF/WAVE, MP3 ID3·프레임싱크, MP4 ftyp).
    형식 판정만 한다 — 내용(무음 여부)은 게이트 밖, 발행 전 실청이 담당.
    """
    size = os.path.getsize(path)
    if size < AUDIO_MIN_BYTES:
        return f"오디오가 {size}바이트 — 최소 {AUDIO_MIN_BYTES//1024}KB 미만은 빈/깨진 합성이다"
    head = open(path, "rb").read(12)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".wav":
        if not (head[:4] == b"RIFF" and head[8:12] == b"WAVE"):
            return "WAV 헤더(RIFF/WAVE)가 아니다 — 깨진 파일"
    elif ext == ".mp3":
        if not (head[:3] == b"ID3" or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)):
            return "MP3 헤더(ID3/프레임싱크)가 아니다 — 깨진 파일"
    elif ext in (".mp4", ".m4a"):
        if head[4:8] != b"ftyp":
            return "MP4 헤더(ftyp)가 아니다 — 깨진 파일"
    else:
        return f"지원하지 않는 확장자: {ext} — wav/mp3/mp4/m4a 만 받는다"
    return None


def to_mp3(src, bitrate, channels):
    """WAV 를 MP3 로 변환한다. 성공 시 변환 파일 경로, 실패 시 None.

    코덱이 MP3 인 것은 규명 결과다 — 2026-08-13 실측: AAC(audio/mp4) data URI 는
    아티팩트 공개 공유의 콘텐츠 스캔이 못 다뤄 409 unscannable 로 거절된다
    (이슈 #14 의 진범 — 클라이언트 버전 가설은 오진). MP3(audio/mpeg)는 같은
    비트레이트에서 스캔을 통과했다. audio/mp4 로 임베드하지 마라.
    비트레이트·채널은 config 의 `tts.embed` 에서 온다 (하드코딩 금지 — 2026-08-12
    공유 거절의 원인이 코드에 박힌 96k 였다).
    imageio-ffmpeg 는 선택 의존성(SETUP §2, 약 87MB) — ImportError 나 변환 실패
    (비0 종료·0바이트 출력)면 경고만 내고 None 을 돌려준다 (원본 임베드로 강등).
    산출물은 임시 디렉토리에만 쓴다 — 원본 오디오는 읽기만 한다.
    """
    try:
        import imageio_ffmpeg
    except ImportError:
        print(WARN_NO_FFMPEG)
        return None
    import subprocess, tempfile
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    out = os.path.join(tempfile.mkdtemp(prefix="embed_radio_"), "audio.mp3")
    try:
        r = subprocess.run([exe, "-y", "-i", src, "-vn", "-c:a", "libmp3lame",
                            "-b:a", str(bitrate), "-ac", str(channels), out],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        print(WARN_CONV_FAIL)
        return None
    if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
        print(WARN_CONV_FAIL)
        return None
    return out

PLAYER_CSS = """
<style>
.kit-radio{border:1px solid #d6d3ca;padding:14px 18px;margin:14px 0;display:flex;flex-direction:column;gap:9px;font-family:system-ui,sans-serif}
.kit-radio audio{width:100%}
.kit-radio details{border-top:1px solid #e2e0d8;padding-top:8px}
.kit-radio summary{cursor:pointer;font-size:13px}
.kit-radio .spd{display:flex;align-items:center;gap:10px;font-size:11px}
.kit-radio .spd button{width:34px;height:30px;border:1px solid #b9b5a8;background:none;font-size:16px;cursor:pointer}
.kit-radio .spd b{font-size:12px;font-weight:400;min-width:38px;text-align:center}
.kit-radio .rl{display:grid;grid-template-columns:40px 1fr;gap:11px;padding:8px 0;border-bottom:1px solid #eceae2}
.kit-radio .rl:last-child{border-bottom:none}
.kit-radio .rl i{font-style:normal;font-size:10px;padding-top:4px;color:#8a877d}
.kit-radio .rl p{margin:0;font-size:14px;line-height:1.6}
</style>
"""

PLAYER_HTML = """<div class="kit-radio">
  <audio id="radioA" controls preload="none" src="data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA="></audio>
  <div class="spd"><span>배속</span><button type="button" id="spdDn">−</button><b id="spdV">1.0×</b><button type="button" id="spdUp">+</button></div>
  <details><summary>대본</summary>
  </details>
</div>
<script>
(function(){
  var a=document.getElementById('radioA'),v=document.getElementById('spdV');
  var dn=document.getElementById('spdDn'),up=document.getElementById('spdUp');
  if(!a||!v)return;
  var spd=1.3;
  function apply(){a.playbackRate=spd;v.textContent=spd.toFixed(1)+'\\u00d7';}
  function step(d){spd=Math.min(2,Math.max(1,Math.round((spd+d)*10)/10));apply();}
  var srcU=a.getAttribute('src');
  function swap(b){var t=a.currentTime,p=!a.paused;a.src=URL.createObjectURL(b);a.currentTime=t;if(p)a.play();apply();}
  function viaAtob(){
    try{
      var m=srcU.match(/^data:([^;,]+)(;base64)?,([\\s\\S]*)$/);
      if(m&&m[2]){
        var bin=atob(m[3].replace(/\\s+/g,'')),n=bin.length,u8=new Uint8Array(n);
        for(var i=0;i<n;i++)u8[i]=bin.charCodeAt(i);
        swap(new Blob([u8],{type:m[1]}));
      }
    }catch(e){}
  }
  try{fetch(srcU).then(function(r){return r.blob()}).then(swap).catch(viaAtob);}catch(e){viaAtob();}
  if(dn)dn.addEventListener('click',function(){step(-0.1)});
  if(up)up.addEventListener('click',function(){step(0.1)});
  a.addEventListener('play',apply);
  apply();
})();
</script>
"""

def main():
    if len(sys.argv) < 4:
        sys.exit(USAGE)
    html_p, wav_p, scr_p = sys.argv[1], sys.argv[2], sys.argv[3]
    for f in (html_p, wav_p, scr_p):
        if not os.path.exists(f):
            sys.exit(f"파일 없음: {f}\n{USAGE}")
    bad = validate_audio(wav_p)
    if bad:
        sys.exit(f"중단: {bad} — HTML 은 건드리지 않았다 ({os.path.basename(wav_p)})")
    html = io.open(html_p, encoding="utf-8").read()

    # 0) 플레이어 블록이 없으면 <body> 직후에 삽입한다
    n = len(re.findall(r'data:audio/[^;]+;base64,[A-Za-z0-9+/=]+', html))
    if n == 0:
        m = re.search(r'<body[^>]*>', html)
        block = PLAYER_CSS + PLAYER_HTML
        if m:
            html = html[:m.end()] + "\n" + block + html[m.end():]
        else:
            html = block + html
        n = 1
        print("플레이어 블록이 없어 새로 삽입했다")
    if n != 1:
        sys.exit(f"중단: data:audio 데이터 URI가 {n}개다 (1개여야 한다)")

    # 1) 오디오 준비 — WAV/MP3 는 AAC 자동 변환 (D2), 실패 시 원본 강등.
    #    비트레이트·채널은 config 의 tts.embed 가 정본이다
    cfg = load_embed_cfg()
    ext = os.path.splitext(wav_p)[1].lower()
    audio_src = wav_p
    if ext in (".wav", ".mp3"):
        conv = to_mp3(wav_p, cfg["bitrate"], cfg["channels"])
        if conv:
            audio_src = conv
            print(f"변환: {os.path.basename(wav_p)} "
                  f"{os.path.getsize(wav_p)/1048576:.2f}MB → MP3 {cfg['bitrate']} "
                  f"{cfg['channels']}ch {os.path.getsize(conv)/1048576:.2f}MB")
    mime = AUDIO_MIME.get(os.path.splitext(audio_src)[1].lower(), "audio/mpeg")
    b64 = base64.b64encode(open(audio_src, "rb").read()).decode()
    html = re.sub(r'data:audio/[^;]+;base64,[A-Za-z0-9+/=]+',
                  f'data:{mime};base64,' + b64, html, count=1)

    # 2) 대본 교체
    lines = []
    for sp, text in parse_script(scr_p):  # 대본 파싱은 script_lib 가 정본
        cls, who = ('ra', '앵커') if sp == 'A' else ('rb', '기자')
        lines.append(f'<div class="rl {cls}"><i>{who}</i><p>{text}</p></div>')
    if not lines:
        sys.exit("중단: 대본에 A:/B: 줄이 없다")
    pat = re.compile(r'(<summary>대본</summary>).*?(</details>)', re.S)
    if not pat.search(html):
        sys.exit("중단: HTML에서 대본 블록을 못 찾았다")
    html = pat.sub(lambda m: m.group(1) + '\n' + '\n'.join(lines) + '\n  ' + m.group(2), html, count=1)

    io.open(html_p, "w", encoding="utf-8").write(html)
    print(f"완료: {os.path.basename(html_p)} ← {os.path.basename(wav_p)} ({len(b64)//1024}KB b64), 대사 {len(lines)}줄")

    # 3) 호 크기 고지 — 판정은 tools/check_size.py (D8) 가 한다
    mb = os.path.getsize(html_p) / 1048576
    limit = float(cfg["max_html_mb"])
    if mb > limit:
        print(f"경고: 호가 {mb:.2f}MB 로 상한 {limit:.2f}MB 를 넘었다 — "
              f"공개 공유가 거절될 수 있다(2026-08-12 실측). "
              f"config 의 tts.embed.bitrate 를 내리거나 대본을 줄여라")
    else:
        print(f"호 크기 {mb:.2f}MB / 상한 {limit:.2f}MB")

if __name__ == "__main__":
    main()
