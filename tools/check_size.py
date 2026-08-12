# -*- coding: utf-8 -*-
"""호 크기 게이트 (D8) — 발행 전 자동 점검.

사용: python tools/check_size.py output/web/YYYY-MM-DD.html

배경 (2026-08-12 공유 거절 추적에서):
  웹판은 오디오를 data URI 로 싣는다. base64 는 원본의 4/3 로 부풀기 때문에
  「AAC 크기 × 1.34 + 지면」 이 곧 호 크기다.

  이 호의 아티팩트는 **공개 전환이 거절됐다.** UI 문구는 이렇게 뜬다:

      "This version can't be shared publicly. Publish a new version or
       change the shared version, then try again."

  **이 문구는 원인이 아니다.** 같은 조작의 네트워크 응답을 잡아 보면
  PATCH /api/frame/perm/<id> → 409 이고 본문은 이렇다:

      {"error":"frame: public serving requires the served version's
                content scan to be dispatched (unscannable)",
       "reason":"unscannable"}

  즉 공개 서빙은 **콘텐츠 스캔 통과가 전제**이고, 이 호는 스캔이 걸리지 않는다.
  UI 가 제안하는 두 우회로는 그래서 둘 다 소용이 없다 — 새 버전도 같은 내용이고,
  공유 버전 콤보박스는 공개 전환 전까지 `disabled` 다(실측).

  **크기는 확정된 원인이 아니다.** 실측은 여기까지다:
    호 3.28MB (AAC 96k)  → 거절 (reason: unscannable)
    호 2.14MB (AAC 64k)  → 거절 (같은 문구, 사용자 직접 조작)
    1KB 순수 HTML 페이지 → 공개 전환 성공
  크기를 3.28MB→2.14MB 로 내려도 풀리지 않았으므로 「3MB 선」은 반증됐다.
  남은 유력 후보는 **수 MB짜리 단일 base64 data URI 가 스캐너를 막는 것**이지만,
  임계값도, data URI 자체가 원인인지도 아직 확정되지 않았다.

  그래서 이 게이트는 **원인 규명이 아니라 예방**이다: 호를 작게 유지하면
  스캔 가능성이 올라간다는 가정 위에 서 있고, 상한(config 의
  `tts.embed.max_html_mb`, 기본 3.0MB — README 의 「호가 3MB 안쪽」)은
  검증된 임계가 아니라 **편집 규율**이다. 통과했다고 공개 공유가 보장되지 않는다 —
  발행 후 E1·E3(익명 개통 판정)이 여전히 최종 관문이다.

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

    print(f"실패: 호가 상한을 {total - limit:.2f}MB 넘었다 — 편집 규율 위반이다. "
          f"공개 서빙은 콘텐츠 스캔을 통과해야 하고(reason: unscannable), 큰 인라인 "
          f"base64 가 스캔을 막는 것으로 의심된다 — 임계는 미확정")
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
