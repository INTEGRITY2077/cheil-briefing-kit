# -*- coding: utf-8 -*-
"""연간 주제 정렬 게이트 (IG3) — 마지막 전체검수. issue: 편집장 지시 2026-08-13.

사용: python tools/check_theme.py output/web/YYYY-MM-DD.html

이 게이트가 답하는 물음(편집장 지시 ③):
  「연간 주제와 비정렬된 에피소드들이 필요한 토픽인지 재평가하는 게이트는 없는가」

연간 주제(profiles/cheil.yaml spine.windows[year].annual_theme)를 기준으로,
지면의 **모든 단위**를 정렬/보조/무관으로 전수 판정한 원본이 eval/theme-YYYY-MM-DD.md 에
있어야 한다. 판정의 정본은 그 eval 파일(사람 판정)이고, 이 스크립트는 계약만 본다:

  ① 주제 로딩       — profiles/cheil.yaml 에서 annual_theme 를 읽는다(없으면 실패)
  ② 단위 계수        — 화두(h1) 1 + 01절 단신 각각 + section.sec(data-axis) 각각 +
                       figure.exhibit 각각. HTML 에서 센 수와 eval 판정표 행 수가 같아야 한다
  ③ 판정표 전수      — 각 행 판정은 정렬/보조/무관 중 하나. '무관' 이 1건이라도 있으면 실패
                       (무관은 지면에서 빼고 나서 발행하라는 뜻). 화두 행은 반드시 '정렬'.
                       '보조' 는 허용하되 근거 한 줄 필수(필요한 토픽인지 재평가의 흔적) —
                       모든 행이 근거를 갖는다
  ④ 검수 메타 스윕   — 출판물 오염 금지(편집장 지시 ③). HTML 가시 텍스트에
                       「규명(」·「표본 —」·「주장 강도」·「보류 슬롯」·「게이트」·「검수」·
                       「판정 불가」 가 1건도 없어야 한다(검수 설명을 지면에 늘어놓지 않는다)

게이트의 정직성(F5): 이 스크립트는 판정표의 **존재·형식·전수·무관 0**만 본다.
각 판정이 옳은지(요지가 주제와 실제로 정렬/보조인지)는 eval 원본의 사람 판정이다.
"""
import io
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함)

USAGE = "사용법: python tools/check_theme.py <웹판.html>"

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE = os.path.join(KIT_ROOT, "profiles", "cheil.yaml")
EVAL_DIR = os.path.join(KIT_ROOT, "eval")

VERDICTS = ("정렬", "보조", "무관")
# 검수 메타 언어 — 지면에 나오면 오염(편집장 지시 ③). em-dash 는 U+2014.
META_TOKENS = ["규명(", "표본 —", "주장 강도", "보류 슬롯", "게이트", "검수", "판정 불가"]


def load_annual_theme():
    """profiles/cheil.yaml 의 spine.windows[id=year].annual_theme 를 읽는다.

    이 필드가 [[연간 주제]] 플레이스홀더의 유일한 정본이다(article-skeleton).
    비었거나 못 읽으면 게이트 판정 불가 → 실패.
    """
    if not os.path.exists(PROFILE):
        print(f"실패: 프로파일 없음 — {os.path.relpath(PROFILE, KIT_ROOT)} 없이는 주제 판정 불가")
        sys.exit(1)
    import yaml
    data = yaml.safe_load(io.open(PROFILE, encoding="utf-8").read())
    theme = None
    try:
        for w in data["spine"]["windows"]:
            if w.get("id") == "year":
                theme = w.get("annual_theme")
                break
    except (KeyError, TypeError):
        theme = None
    if not theme or not str(theme).strip():
        print("실패: annual_theme 이 비어 있다 — 연간 주제 없이는 정렬 판정 불가 (profiles/cheil.yaml spine.windows[year])")
        sys.exit(1)
    return str(theme).strip()


def strip_visible(html):
    """가시 텍스트만 남긴다 — script/style 제거 후 태그 제거.

    base64 오디오·플레이어 스크립트는 태그·속성 안에 있어 이 단계에서 사라진다.
    """
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", html)


def count_units(html):
    """지면 단위 수 — 화두 + 단신 + 축 절 + 전시물."""
    n_h1 = len(re.findall(r"<h1\b", html))
    n_news = len(re.findall(r'<li\b[^>]*class="[^"]*\bnews\b', html))
    n_axis = len(re.findall(r"data-axis\s*=", html))
    n_exhibit = len(re.findall(r'<figure\b[^>]*class="[^"]*\bexhibit\b', html))
    return {"화두(h1)": n_h1, "01절 단신": n_news, "축 절(data-axis)": n_axis, "전시물(figure.exhibit)": n_exhibit}


def parse_eval_table(path):
    """eval/theme-DATE.md 의 판정표를 읽는다 — 4열(단위·요지·판정·근거) 데이터 행 목록."""
    text = io.open(path, encoding="utf-8").read()
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        # 구분선(---|:--) 행은 건너뛴다
        if all(set(c) <= set("-: ") and c for c in cells):
            continue
        # 헤더 행(단위·판정 라벨)은 건너뛴다 — 라벨이 「판정(정렬/보조/무관)」처럼
        # 괄호를 달고 오므로 셀 완전일치가 아니라 부분일치로 본다
        if any("판정" in c for c in cells) and any("단위" in c for c in cells):
            continue
        rows.append(cells)
    return rows


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        sys.exit(USAGE)
    path = sys.argv[1]
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    if not m:
        print("실패: 파일명에서 YYYY-MM-DD 를 찾지 못했다 — eval/theme-날짜.md 를 특정할 수 없다")
        sys.exit(1)
    date_str = m.group(1)
    eval_path = os.path.join(EVAL_DIR, f"theme-{date_str}.md")

    theme = load_annual_theme()
    html = io.open(path, encoding="utf-8").read()
    errors = []

    # ── ② 단위 계수 ────────────────────────────────────────────────
    units = count_units(html)
    unit_total = sum(units.values())
    print(f"①: 연간 주제 「{theme}」")
    print("②: 단위 — " + " · ".join(f"{k} {v}" for k, v in units.items()) + f" = 합 {unit_total}")

    # ── eval 판정표 필수 ──────────────────────────────────────────
    if not os.path.exists(eval_path):
        print(f"실패: 판정표 원본 없음 — {os.path.relpath(eval_path, KIT_ROOT)} 필수 "
              "(단위별 정렬/보조/무관 전수 판정). 없으면 이 발행은 실패다")
        sys.exit(1)
    rows = parse_eval_table(eval_path)
    print(f"③: 판정표 행 {len(rows)}개")

    # ── ③ 판정표 전수 ─────────────────────────────────────────────
    if len(rows) != unit_total:
        errors.append(f"판정표 행 {len(rows)}개 ≠ 지면 단위 {unit_total}개 — 전수 판정이 아니다 "
                      "(단위마다 한 행씩. 새 단위를 넣고 판정을 빠뜨렸거나 그 반대다)")
    tally = {v: 0 for v in VERDICTS}
    hwadu_rows = 0
    for i, cells in enumerate(rows, 1):
        if len(cells) != 4:
            errors.append(f"판정표 {i}행 열 수 {len(cells)} ≠ 4 (| 단위 | 요지 | 판정 | 근거 |)")
            continue
        unit, gist, verdict, ground = cells
        if verdict not in VERDICTS:
            errors.append(f"판정표 {i}행 판정 「{verdict}」 이 정렬/보조/무관 아님 ({unit})")
            continue
        tally[verdict] += 1
        if verdict == "무관":
            errors.append(f"판정표 {i}행 「무관」 — {unit}: {gist} "
                          "(무관 단위는 지면에서 빼고 나서 발행하라는 뜻이다)")
        if not ground:
            errors.append(f"판정표 {i}행 근거 비어 있음 ({unit}) — 필요한 토픽인지 재평가의 흔적이 없다")
        if ("화두" in unit) or ("h1" in unit.lower()):
            hwadu_rows += 1
            if verdict != "정렬":
                errors.append(f"화두 행 판정이 「{verdict}」 — 화두는 반드시 정렬이어야 한다 ({unit})")
    if hwadu_rows == 0:
        errors.append("판정표에 화두(h1) 행이 없다 — 화두는 전수 판정의 첫 단위다")
    elif hwadu_rows > 1:
        errors.append(f"판정표에 화두 행이 {hwadu_rows}개 — 화두는 1개다")
    print("   판정 분포 — " + " · ".join(f"{v} {tally[v]}" for v in VERDICTS))

    # ── ④ 검수 메타 스윕 ──────────────────────────────────────────
    visible = strip_visible(html)
    hits = [t for t in META_TOKENS if t in visible]
    if hits:
        shown = ", ".join(t.replace("—", "—") for t in hits)
        errors.append(f"검수 메타 언어가 지면에 남아 있다 — 「{shown}」 (편집장 지시 ③: 검수 설명은 출판물 오염)")
    print(f"④: 검수 메타 스윕 — 매치 {len(hits)}건")

    # ── 결과 ──────────────────────────────────────────────────────
    for e in errors:
        print("실패:", e)
    print(f"— 단위 {unit_total}개 · 판정표 {len(rows)}행 · 무관 {tally['무관']} · 메타 {len(hits)} · 실패 {len(errors)}")
    if errors:
        sys.exit(1)
    print(f"통과: 연간 주제 정렬 전수 판정 — 화두=정렬·무관 0·메타 0 (판정 원본 {os.path.relpath(eval_path, KIT_ROOT)}). "
          "각 판정의 옳고 그름은 eval 사람 판정이다 (F5)")


if __name__ == "__main__":
    main()
