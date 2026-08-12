# -*- coding: utf-8 -*-
"""호 크기 게이트 (D8) — 발행 전 자동 점검.

사용: python tools/check_size.py output/web/YYYY-MM-DD.html

규칙 (2026-08-12 공유 거절에서 나온 것):
  웹판은 오디오를 data URI 로 싣는다. base64 는 원본의 4/3 로 부풀기 때문에
  「AAC 크기 × 1.34 + 지면」 이 곧 호 크기다. 이 값이 커지면 아티팩트의
  **공개 공유가 거절된다** — 그런데 플랫폼이 내는 문구는 크기를 말하지 않는다:

      "This version can't be shared publicly. Publish a new version or
       change the shared version, then try again."

  문구가 버전 이야기만 하므로 원인처럼 보이지 않고, 안내가 준 두 우회로
  (새 버전 발행 · 공유 버전 변경)는 둘 다 막힌다 — 새 버전도 같은 크기이고,
  공유 버전 콤보박스는 공개 전환 전까지 잠겨 있다. 그래서 눈으로는 영영
  안 풀리고, 크기를 내리면 한 번에 풀린다.

  실측 (2026-08-12, 3분 20초 대본):
    AAC 96k → 2.45MB → base64 3,338KB → 호 3.28MB → 공유 거절
    AAC 64k → 1.59MB → base64 2,166KB → 호 2.14MB → 통과

  상한의 정본은 config 의 `tts.embed.max_html_mb` 다 (README 의 「호가 3MB 안쪽」).
  config 가 없으면 3.0MB 로 본다.

정적 검사라 네트워크 없이 돌릴 수 있다. 상한 초과 시 종료코드 1.
"""
import io, os, re, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함)

USAGE = "사용법: python tools/check_size.py <웹판.html>"
DEFAULT_MAX_MB = 3.0
DATA_URI = re.compile(r'data:audio/[^;]+;base64,([A-Za-z0-9+/=]+)')


def max_mb(kit):
    """config 의 tts.embed.max_html_mb. 읽지 못하면 기본값."""
    try:
        import yaml
        with io.open(os.path.join(kit, "config.yaml"), encoding="utf-8") as f:
            v = (((yaml.safe_load(f) or {}).get("tts") or {}).get("embed") or {}).get("max_html_mb")
        return float(v) if v is not None else DEFAULT_MAX_MB
    except Exception:
        return DEFAULT_MAX_MB


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    path = sys.argv[1]
    kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    limit = max_mb(kit)

    total = os.path.getsize(path) / 1048576
    html = io.open(path, encoding="utf-8").read()
    audio_b64 = sum(len(m) for m in DATA_URI.findall(html)) / 1048576
    page = total - audio_b64

    print(f"호 {total:.2f}MB = 오디오(base64) {audio_b64:.2f}MB + 지면 {page:.2f}MB · 상한 {limit:.2f}MB")

    if total <= limit:
        print(f"통과: 상한 대비 {total/limit*100:.0f}%")
        return

    print(f"실패: 호가 상한을 {total - limit:.2f}MB 넘었다 — 이 크기에서 공개 공유가 "
          f"거절된 전례가 있다(2026-08-12). 거절 문구는 크기를 말해 주지 않는다")
    if audio_b64 > 0:
        # 지면을 그대로 두고 상한에 맞추려면 AAC 를 얼마로 내려야 하는지 계산해 준다
        room = max(limit - page, 0.0)
        ratio = room / audio_b64 if audio_b64 else 0
        print(f"  오디오가 호의 {audio_b64/total*100:.0f}% 다. "
              f"지면을 그대로 두면 오디오를 지금의 {ratio*100:.0f}% 로 줄여야 한다 "
              f"— config 의 tts.embed.bitrate 를 그만큼 내리거나 대본을 줄여라")
    else:
        print("  오디오 data URI 가 없다 — 지면 자체가 크다. 전시물 이미지·인라인 자산을 본다")
    sys.exit(1)


if __name__ == "__main__":
    main()
