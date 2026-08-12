# -*- coding: utf-8 -*-
"""미정의 CSS 변수 게이트 (D4) — 발행 전 자동 점검.

사용: python tools/check_css_vars.py output/web/YYYY-MM-DD.html

규칙:
  var(--x) 가 참조하는 --x 는 문서 안에 반드시 정의돼 있어야 한다.
  미정의 변수는 선언 전체를 무효로 만든다 — 배경·테두리가 조용히 사라지고
  에러도 안 난다. 눈으로는 "좀 밋밋하네" 로 넘어간다.

  실측 두 건:
    2026-08-12 — 바차트가 --key 등 미정의 토큰을 참조해 투명 렌더
    2026-08-11 — 라디오 블록·판형 바가 --card/--line/--ink2/--ink3/--key/
                 --line2/--disp 를 참조했는데 :root 에 없어서 카드가 통째로
                 배경·테두리 없이 떴다 (다른 스킴에서 절을 옮겨오며 발생)

  var(--x, 기본값) 처럼 폴백이 있으면 통과시킨다 — 무효가 되지 않는다.

검사 범위는 <style> 블록과 style="" 속성뿐이다. 본문 텍스트나 data: URI 는
보지 않는다. 실패 시 종료코드 1.
"""
import io, os, re, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게

USAGE = "사용법: python tools/check_css_vars.py <웹판.html>"

STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
STYLE_ATTR = re.compile(r"""\sstyle\s*=\s*(["'])(.*?)\1""", re.S | re.I)
DEFINE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
# 폴백 없는 참조만 잡는다: var(--x) / var( --x )
REFERENCE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*([,)])")


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    html = io.open(sys.argv[1], encoding="utf-8").read()

    css = "\n".join(STYLE_BLOCK.findall(html))
    css += "\n" + "\n".join(m.group(2) for m in STYLE_ATTR.finditer(html))
    if not css.strip():
        print("style 없음 — 통과")
        return

    defined = set(DEFINE.findall(css))
    missing = {}
    for name, closer in REFERENCE.findall(css):
        if closer == ",":
            continue  # 폴백이 있다 — 선언이 무효가 되지 않는다
        if name not in defined:
            missing[name] = missing.get(name, 0) + 1

    if missing:
        for name in sorted(missing):
            print(f"실패: {name} 정의 없음 — var({name}) 참조 {missing[name]}곳, "
                  f"그 선언들이 전부 무효가 된다")
        print(f"정의된 변수 {len(defined)}개 · 미정의 {len(missing)}개")
        sys.exit(1)

    refs = len(REFERENCE.findall(css))
    print(f"통과: 변수 정의 {len(defined)}개 · var() 참조 {refs}곳 전부 해소")


if __name__ == "__main__":
    main()
