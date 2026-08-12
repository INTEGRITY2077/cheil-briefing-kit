# -*- coding: utf-8 -*-
"""판형 바 게이트 (C5) — 발행 전 자동 점검.

사용: python tools/check_formats.py output/web/YYYY-MM-DD.html

웹판 상단 `.fmtbar` 는 그날 만든 판형 전부로 가는 문이다. 라디오만 있고
프레젠테이션 세그먼트가 없으면, 덱을 만들어 놓고도 독자에겐 없는 것과 같다.

  2026-08-11 실측 — 덱(발표판)을 발행해 놓고 웹판 fmtbar 에는 「라디오 버전」
  세그먼트 하나만 있었다. 독자에게 프레젠테이션은 존재하지 않았다.
  routine-SKILL 4c 가 "당일 웹판 fmtbar의 프레젠테이션 링크에 당일 덱 URL을
  넣는다" 고 이미 요구하지만, 눈으로만 보면 없는 것을 못 본다.

판정:
  - `.fmtbar` 가 있어야 한다
  - 세그먼트(`.fseg`) ≥ 2
  - 현재 판형(`.fseg.on`) 정확히 1개
  - 「프레젠테이션」 세그먼트가 있어야 한다
  - `a.fseg` 는 href 필수 + claude.ai 아티팩트 절대 URL
  - 링크 없는 라벨은 경고 — 아카이브 호의 PPTX 배포본 라벨만 허용된다
    (routine-SKILL 4c). `--archive` 를 주면 경고도 내지 않는다

실패 시 종료코드 1. 경고만 있으면 0.
"""
import io, os, re, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게

USAGE = "사용법: python tools/check_formats.py <웹판.html> [--archive]"

BAR = re.compile(r"""<div[^>]*class\s*=\s*["'][^"']*\bfmtbar\b[^"']*["'][^>]*>(.*?)</div>""", re.S | re.I)
SEG = re.compile(r"""<(a|span)\b([^>]*\bfseg\b[^>]*)>(.*?)</\1>""", re.S | re.I)
HREF = re.compile(r"""href\s*=\s*["']([^"']*)["']""", re.I)
ARTIFACT_URL = re.compile(r"^https://claude\.ai/[^\s\"']+$", re.I)
DECK_WORDS = ("프레젠테이션", "발표", "슬라이드", "덱")


def text_of(fragment):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment)).strip()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    archive = "--archive" in sys.argv[1:]
    if not args or not os.path.exists(args[0]):
        sys.exit(USAGE)
    html = io.open(args[0], encoding="utf-8").read()

    bar = BAR.search(html)
    if not bar:
        print("실패: .fmtbar 가 없다 — 판형 바 없이 발행하면 다른 판형으로 갈 문이 없다")
        sys.exit(1)

    segs = [(tag.lower(), attrs, text_of(body)) for tag, attrs, body in SEG.findall(bar.group(1))]
    errors, warnings = [], []

    if len(segs) < 2:
        errors.append(f"세그먼트가 {len(segs)}개다 — 라디오·프레젠테이션 최소 2개")

    on = [s for s in segs if re.search(r"\bon\b", s[1])]
    if len(on) != 1:
        errors.append(f"현재 판형(.fseg.on)이 {len(on)}개 — 정확히 1개여야 한다")

    deck = [s for s in segs if any(w in s[2] for w in DECK_WORDS)]
    if not deck:
        errors.append("프레젠테이션 세그먼트가 없다 — 덱을 발행했어도 독자에겐 없는 것과 같다")

    for tag, attrs, label in segs:
        if tag == "a":
            m = HREF.search(attrs)
            url = m.group(1).strip() if m else ""
            if not url:
                errors.append(f"[{label}] a.fseg 인데 href 가 없다 — 죽은 라벨")
            elif not ARTIFACT_URL.match(url):
                errors.append(f"[{label}] href 가 claude.ai 절대 URL 이 아니다: {url[:60]}")
        elif tag == "span" and not re.search(r"\bon\b", attrs) and not archive:
            warnings.append(f"[{label}] 링크 없는 라벨 — 아카이브 호의 PPTX 배포본이면 --archive")

    for w in warnings:
        print("경고:", w)
    for e in errors:
        print("실패:", e)
    if errors:
        sys.exit(1)
    print(f"통과: 판형 세그먼트 {len(segs)}개 · 현재 판형 「{on[0][2]}」 · 링크 전부 유효")


if __name__ == "__main__":
    main()
