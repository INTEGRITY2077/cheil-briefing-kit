# -*- coding: utf-8 -*-
"""표 판형 게이트 (D6) — 발행 전 자동 점검.

사용: python tools/check_tables.py output/web/YYYY-MM-DD.html

규칙 (2026-08-12 모바일 반려에서 나온 것):
  일괄 min-width 를 좁은 표에 적용하면 남는 폭이 전부 1열로 몰려
  다음 열이 화면 밖으로 밀린다. 그래서 표는 열 수로 판형을 고른다.

  - 3열 이하  → class="fit" 필수 (min-width 해제, 화면 폭에 맞춤)
  - 4열 이상  → fit 금지 (가로 스크롤 판형 유지)
  - fit 용 CSS(.scroll table.fit{min-width:0…})가 문서에 정의돼 있어야 한다

전부 정적 검사라 렌더링 없이 돌릴 수 있다. 실패 시 종료코드 1.
"""
import io, os, re, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

USAGE = "사용법: python tools/check_tables.py <웹판.html>"
FIT_CSS = "table.fit{min-width:0"

def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    h = io.open(sys.argv[1], encoding="utf-8").read()
    errors, checked = [], 0
    has_fit_css = FIT_CSS in h
    for m in re.finditer(r"<table([^>]*)>(.*?)</table>", h, re.S):
        attrs, body = m.group(1), m.group(2)
        thead = re.search(r"<thead>.*?<tr>(.*?)</tr>", body, re.S)
        cols = len(re.findall(r"<th[^>]*>", thead.group(1))) if thead else 0
        cap = re.search(r"<caption>(.*?)</caption>", body, re.S)
        name = re.sub(r"<[^>]+>", "", cap.group(1)).strip()[:40] if cap else "(caption 없음)"
        # 속성 전체 부분일치("profit" 등 오검출) 방지 — class 속성 안의 단어 단위로만 본다
        is_fit = bool(re.search(r'class="[^"]*\bfit\b[^"]*"', attrs))
        checked += 1
        if cols == 0:
            errors.append(f"[{name}] thead 첫 행에서 열 수를 못 셌다 — thead 구조 확인")
        elif cols <= 3 and not is_fit:
            errors.append(f"[{name}] {cols}열인데 fit 클래스가 없다 — 1열 과대 여백으로 다음 열이 밀린다")
        elif cols >= 4 and is_fit:
            errors.append(f"[{name}] {cols}열인데 fit 이다 — 모바일 폭에 구겨진다, 스크롤 판형으로")
        if is_fit and not has_fit_css:
            errors.append(f"[{name}] fit 을 썼는데 문서에 fit CSS({FIT_CSS}…)가 없다")
    if not checked:
        print("표 없음 — 통과")
        return
    for e in errors:
        print("실패:", e)
    if errors:
        sys.exit(1)
    print(f"통과: 표 {checked}개 전부 판형 규칙 충족")

if __name__ == "__main__":
    main()
