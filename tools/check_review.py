# -*- coding: utf-8 -*-
"""심사 봉인 게이트 (IG4) — 발행 전, 그 호의 심사 기록이 봉인됐는지 판정한다.

사용: python tools/check_review.py output/web/YYYY-MM-DD.html

판정 다섯:
  ① 심사 기록 실존   — eval/review-<날짜>.md 가 있는가
  ② 점수 전수        — 심사자 3인 × 전 차원 점수가 전부 있는가 (누락 행 실패).
                       차원 전수는 **루브릭 버전 스코핑**이다 — 기록 머리의
                       「루브릭 버전 … vN」을 읽어, rubric 차원 중 since ≤ N 인
                       것만 요구한다 (v1 기록은 R1~R5 5차원, v2 기록은 R6 포함 6차원.
                       R6 v2 신설이 v1 기록을 소급 실패시키던 2026-08-13 검수 결함 수리)
  ③ 평균 ≥ 임계      — 전 점수 평균이 임계 이상인가.
                       임계의 정본은 templates/insight-rubric.yaml 의 threshold —
                       단 config.yaml 에 review.threshold 가 있으면 그것이 우선한다
                       (check_size 의 config 로딩 방식과 같은 pyyaml 읽기)
  ④ 처리 칸 0빈칸    — 지적 목록(정본 | # | 렌즈 | 지적 | 처리 … |)의 처리 칸에 빈 칸이 없는가
  ⑤ 재심사 정책      — 본심사 평균이 임계 미달이면 재심사 섹션이 있어야 한다
                       (재조판 1회 → 재심사 정책 강제). 재심사 평균이 임계 이상이면
                       통과, 재심사 후에도 미달이면 「발행 가능하되 보고 명기」 —
                       exit 0 에 경고를 출력한다 (막지 않고 명기를 강제한다)

양식 파싱 — **정본은 templates/review-form.md** (2026-08-13 대조 완료 — 파서를
정본에 맞췄다. 정본 이전에 쓰인 기록의 구형 표기도 함께 받는다):
  - 심사자별 마크다운 표 — 헤더 | 차원 | 점수 | 사유 한 줄 | (구형 | 사유 | 도 허용).
    표 하나 = 심사자 한 명. 심사자 이름은 표 바로 앞의 가장 가까운 제목(#)에서 읽는다.
    차원 라벨은 「R1 이해관계 계량」처럼 id+이름 결합도, 이름 단독도 받는다.
    표 끝의 「**평균**」 요약 행은 차원이 아니다 — 점수 집계에서 제외한다.
  - 종합 평균 — 종합 표의 | 3인 평균 | 값 | 행(정본), 또는 비표 줄의
    「종합 평균 N」 문구(구형). 이 스크립트는 점수에서 직접 평균을
    재계산해 판정하고, 적힌 값이 재계산과 0.05 넘게 어긋나면 실패시킨다
    (적힌 평균이 판정 근거가 아니다 — 점수가 근거다).
  - 지적 목록 — 헤더에 「지적」 칸과 「처리…」 칸이 있는 표. 정본은
    | # | 렌즈 | 지적 | 처리 (반영 / 기각-사유) | — 칸 위치는 헤더에서 읽으므로
    구형 | 지적 | 처리 | 도 받는다. 처리 칸이 공백뿐이면 빈 칸으로 판정한다.
  - 재심사 — 「재심사」 를 포함한 제목(#) 이후 전체. 그 안의 점수 표는 본심사와
    같은 규칙(3인 × 전 차원, 버전 스코핑 동일)으로 판정한다.

관할 중복 명기 (2026-08-13 검수) — check_insight ⑥Q1(유보 종결 1/2 초과 = 발행
차단)은 rubric R2/floor(전원 유보)와 판정 대상이 겹친다. 이 스크립트는 내용 판정을
하지 않아 황금률(정성은 기계가 대신 답하지 않는다)을 지키지만, R2 는 사람 패널과
check_insight 의 정적 근사가 이중으로 보는 영역이다 — 패널이 수용한 유보 비중을
check_insight 가 하드 실패로 뒤집을 수 있다(H6 류 정적 근사 선례에 따른 의도적 중복).

차원의 이름·개수 정본은 templates/insight-rubric.yaml — dimensions 류 목록을
읽을 수 있으면 이름 대조까지 하고(누락 차원을 이름으로 지목), 못 읽으면
행 수(기록 버전의 차원 수 — v1은 5, v2는 6)로만 판정하고 경고를 남긴다.
게이트의 정직성(F5): 못 재는 것을 재는 척하지 않는다.

정적 검사라 네트워크 없이 돈다. 실패 시 종료코드 1.
"""
import io
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함)

USAGE = ("사용법: python tools/check_review.py <웹판.html> [--retro]  (예: output/web/2026-08-13.html)\n"
         "  --retro : 소급 심사 — 임계 판정은 하되, 미달이어도 재심사(재조판)를 요구하지 않고 경고로 명기한다\n"
         "            (review-form.md 「소급 심사 예외」 각주 — 편집장이 발행된 호의 소급 재조판을 하지 않기로 결정한 경우)")

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUBRIC = os.path.join(KIT_ROOT, "templates", "insight-rubric.yaml")
CONFIG = os.path.join(KIT_ROOT, "config.yaml")
EVAL_DIR = os.path.join(KIT_ROOT, "eval")

REVIEWERS_REQUIRED = 3
# 버전별 차원 수 — rubric 을 못 읽을 때의 행 수 판정 폴백 (v1: R1~R5, v2: +R6)
DIMS_REQUIRED_BY_VERSION = {1: 5, 2: 6}
RUBRIC_VER_ROW = re.compile(r"^\|\s*루브릭\s*버전\s*\|[^|]*\bv(\d+)\b[^|]*\|")

# 정본(review-form.md) 헤더 | 차원 | 점수 | 사유 한 줄 | — 구형 | 사유 | 도 허용
SCORE_HEADER = re.compile(r"^\|\s*차원\s*\|\s*점수\s*\|\s*사유(\s*한\s*줄)?\s*\|")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
RULE_ROW = re.compile(r"^\|[\s:|-]+\|\s*$")  # |---|---:| 류 구분선
HEADING = re.compile(r"^#{1,6}\s*(.+?)\s*$")
REREVIEW_HEADING = re.compile(r"^#{1,6}\s*.*재심사")
AVG_LINE = re.compile(r"종합\s*평균[^0-9]*([0-9]+(?:\.[0-9]+)?)")  # 구형 — 비표 줄
# 정본 — 종합 표의 | 3인 평균 | 값 | 행 (「종합 평균」 표기도 받는다)
AVG_ROW = re.compile(r"^\|\s*(?:3인|종합)\s*평균\s*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|")
DIM_ID_PREFIX = re.compile(r"^[A-Za-z]\d+\s+")  # 「R1 이해관계 계량」 → 「이해관계 계량」
SUMMARY_ROW_LABELS = ("평균", "합계")  # 점수 표 끝의 요약 행 — 차원이 아니다


def norm_dim(label):
    """차원 라벨 정규화 — 굵게(**)·id 접두(R1 등)를 벗겨 rubric name 과 대조 가능하게."""
    return DIM_ID_PREFIX.sub("", label.strip().strip("*").strip()).strip()


def issue_cols(line):
    """지적 목록 헤더면 (지적 칸 index, 처리 칸 index), 아니면 None.

    정본 | # | 렌즈 | 지적 | 처리 (반영 / 기각-사유) | 도, 구형 | 지적 | 처리 | 도
    헤더 칸 위치를 읽어 받는다 — 위치 하드코딩이 ④ 무판정 침묵 실패의 원인이었다.
    """
    if not TABLE_ROW.match(line):
        return None
    cells = split_cells(line)
    ji = next((i for i, c in enumerate(cells) if c == "지적"), None)
    ci = next((i for i, c in enumerate(cells) if c.startswith("처리")), None)
    if ji is None or ci is None:
        return None
    return ji, ci


def load_threshold(warns):
    """임계 — config.yaml 의 review.threshold 우선, 없으면 rubric 의 threshold.

    (check_size.max_mb 와 같은 io.open + yaml.safe_load 로딩.)
    둘 다 못 읽으면 게이트 판정 불가로 실패시킨다 — 임계 없는 평균 판정은 없다.
    """
    import yaml

    if os.path.exists(CONFIG):
        try:
            with io.open(CONFIG, encoding="utf-8") as f:
                v = ((yaml.safe_load(f) or {}).get("review") or {}).get("threshold")
            if v is not None:
                return float(v), "config.yaml review.threshold"
        except Exception:
            warns.append("config.yaml 을 읽지 못했다 — rubric 의 threshold 로 진행")
    if os.path.exists(RUBRIC):
        try:
            with io.open(RUBRIC, encoding="utf-8") as f:
                y = yaml.safe_load(f) or {}
            v = _find_key(y, "threshold")
            if v is not None:
                return float(v), "templates/insight-rubric.yaml threshold"
            print("실패: templates/insight-rubric.yaml 에 threshold 가 없다 — 임계 없이는 ③ 판정 불가")
        except Exception as e:
            print(f"실패: templates/insight-rubric.yaml 을 읽지 못했다 ({e}) — 임계 없이는 ③ 판정 불가")
    else:
        print("실패: 임계 정본 없음 — templates/insight-rubric.yaml 도 config.yaml review.threshold 도 없다")
    sys.exit(1)


def _find_key(node, key):
    """매핑 트리에서 key 를 깊이 우선으로 찾는다 — rubric 의 절 구조가 확정 전이라 관대하게.

    key 의 값이 스칼라면 그대로, `threshold: {value: 7.0, basis: …}` 처럼 중첩
    매핑이면 그 안의 value 스칼라를 돌려준다 (이슈 #22 — 스칼라만 찾던 구현이
    rubric 의 중첩 threshold 를 못 읽어, config 부재 환경의 폴백이 전 케이스
    실패했다. config.example 의 「비우면 rubric 값이 기본」 약속을 실동작으로).
    """
    if isinstance(node, dict):
        if key in node and not isinstance(node[key], (dict, list)):
            return node[key]
        if key in node and isinstance(node[key], dict):
            inner = node[key].get("value")
            if inner is not None and not isinstance(inner, (dict, list)):
                return inner
        for v in node.values():
            found = _find_key(v, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find_key(v, key)
            if found is not None:
                return found
    return None


def load_dimensions(warns):
    """rubric 에서 (차원 (이름, since) 목록, rubric 버전)을 읽는다.

    since 는 그 차원이 신설된 루브릭 버전(기본 1) — 기록 버전 스코핑의 정본이다.
    못 읽으면 (None, None) — 행 수로만 판정 (경고).
    """
    if not os.path.exists(RUBRIC):
        warns.append("templates/insight-rubric.yaml 이 없다 — 차원 이름 대조 생략, 행 수로만 판정")
        return None, None
    try:
        import yaml
        with io.open(RUBRIC, encoding="utf-8") as f:
            y = yaml.safe_load(f) or {}
        ver = _find_key(y, "version")
        ver = int(ver) if ver is not None else None
        for key in ("dimensions", "차원", "axes"):
            dims = _find_list(y, key)
            if dims:
                names = []
                for d in dims:
                    if isinstance(d, str):
                        names.append((d, 1))
                    elif isinstance(d, dict):
                        for nk in ("name", "id", "이름", "차원"):
                            if d.get(nk):
                                names.append((str(d[nk]), int(d.get("since") or 1)))
                                break
                if len(names) == len(dims):
                    return names, ver
        warns.append("rubric 에서 차원 목록(dimensions)을 찾지 못했다 — 행 수로만 판정")
    except Exception:
        warns.append("rubric 을 읽지 못했다 — 차원 이름 대조 생략, 행 수로만 판정")
    return None, None


def record_rubric_version(lines, warns, fallback):
    """기록 머리의 「루브릭 버전 … vN」 행에서 N 을 읽는다 — 차원 전수의 스코프.

    행이 없으면 현행 rubric 버전(fallback)으로 간주하고 경고한다 — 버전 무표기
    기록은 현행 전 차원을 요구받는다 (양식 review-form.md 가 버전 행을 정본으로 갖는다).
    """
    for ln in lines:
        m = RUBRIC_VER_ROW.match(ln)
        if m:
            return int(m.group(1))
    warns.append(f"기록에 루브릭 버전 행이 없다 — 현행 rubric v{fallback} 전 차원으로 판정 (양식 위반 의심)")
    return fallback


def _find_list(node, key):
    if isinstance(node, dict):
        if key in node and isinstance(node[key], list):
            return node[key]
        for v in node.values():
            found = _find_list(v, key)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find_list(v, key)
            if found:
                return found
    return None


def split_cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_part(lines, label, dims, errors, warns, known=None, dims_required=None):
    """한 파트(본심사 / 재심사)에서 심사자 점수 표·종합 평균 줄·지적 목록을 읽는다.

    돌려주는 값: (점수 전체 목록, 심사자 수, 적힌 종합 평균 or None)
    지적 목록의 빈 처리 칸은 errors 에 직접 쌓는다.
    """
    scores, reviewers = [], []
    stated_avg = None
    last_heading = "(제목 없음)"
    i = 0
    while i < len(lines):
        line = lines[i]
        m = HEADING.match(line)
        if m:
            last_heading = m.group(1)
        if stated_avg is None:
            m = AVG_ROW.match(line)  # 정본 — 종합 표 | 3인 평균 | 값 |
            if m:
                stated_avg = float(m.group(1))
            elif not line.lstrip().startswith("|"):
                m = AVG_LINE.search(line)  # 구형 — 비표 줄 「종합 평균 N」
                if m:
                    stated_avg = float(m.group(1))
        if SCORE_HEADER.match(line):
            i += 1
            rows = []
            while i < len(lines) and TABLE_ROW.match(lines[i]):
                if not RULE_ROW.match(lines[i]):
                    rows.append(split_cells(lines[i]))
                i += 1
            reviewer = last_heading
            reviewers.append(reviewer)
            seen = {}
            for cells in rows:
                if len(cells) < 2:
                    errors.append(f"[{label}·{reviewer}] 표 행의 칸이 모자란다: | {' | '.join(cells)} |")
                    continue
                dim, raw = norm_dim(cells[0]), cells[1]
                if dim in SUMMARY_ROW_LABELS:
                    continue  # 표 끝 「**평균**」 요약 행 — 차원 아님, 집계 제외
                try:
                    seen[dim] = float(re.sub(r"[^0-9.]", "", raw) or "x")
                except ValueError:
                    errors.append(f"[{label}·{reviewer}] 차원 [{dim}] 점수가 숫자가 아니다: 「{raw}」 (② 전수)")
            if dims:
                for d in dims:
                    if d not in seen:
                        errors.append(f"[{label}·{reviewer}] 차원 [{d}] 행이 없다 (② 3인×전차원 전수, 버전 스코핑 — 누락 행 실패)")
                extra = [d for d in seen if d not in (known or dims)]
                if extra:
                    warns.append(f"[{label}·{reviewer}] rubric 에 없는 차원 {extra} — rubric 정본과 대조 필요")
            elif dims_required and len(seen) < dims_required:
                errors.append(f"[{label}·{reviewer}] 차원 {len(seen)}행 < {dims_required} (② 전수 — 누락 행 실패)")
            scores.extend(seen.values())
            continue
        cols = issue_cols(line)
        if cols:
            ji, ci = cols
            i += 1
            n_issues, n_empty = 0, 0
            while i < len(lines) and TABLE_ROW.match(lines[i]):
                if not RULE_ROW.match(lines[i]):
                    cells = split_cells(lines[i])
                    issue_text = cells[ji] if len(cells) > ji else ""
                    n_issues += 1
                    if len(cells) <= ci or not cells[ci]:
                        n_empty += 1
                        errors.append(f"[{label}] 지적 「{issue_text[:40]}」 의 처리 칸이 비어 있다 (④ 빈 칸 0건)")
                i += 1
            print(f"[{label}] 지적 {n_issues}건 · 처리 빈 칸 {n_empty}건")
            continue
        i += 1
    if len(reviewers) != REVIEWERS_REQUIRED:
        errors.append(f"[{label}] 심사자 표 {len(reviewers)}개 ≠ {REVIEWERS_REQUIRED} (② 심사자 3인 — {', '.join(reviewers) or '없음'})")
    return scores, reviewers, stated_avg


def main():
    retro = "--retro" in sys.argv[1:]
    argv = [a for a in sys.argv[1:] if a != "--retro"]
    if not argv or not os.path.exists(argv[0]):
        sys.exit(USAGE)
    sys.argv = [sys.argv[0]] + argv
    base = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", base):
        sys.exit(f"실패: 파일명에서 날짜를 읽지 못했다 — {base}\n{USAGE}")

    review_path = os.path.join(EVAL_DIR, f"review-{base}.md")
    if not os.path.exists(review_path):
        print(f"실패: 심사 기록 없음 — eval/review-{base}.md 가 없다 (① 심사 없이 봉인 없음)")
        sys.exit(1)
    print(f"①: 심사 기록 실존 — eval/review-{base}.md")

    warns, errors = [], []
    threshold, src = load_threshold(warns)
    all_dims, rubric_ver = load_dimensions(warns)
    if rubric_ver is None:
        rubric_ver = max(DIMS_REQUIRED_BY_VERSION)

    text = io.open(review_path, encoding="utf-8").read()
    lines = text.splitlines()
    rec_ver = record_rubric_version(lines, warns, rubric_ver)
    if rec_ver > rubric_ver:
        warns.append(f"기록의 루브릭 버전 v{rec_ver} > 현행 rubric v{rubric_ver} — rubric 정본 갱신 누락 의심")
    # 버전 스코핑 — 기록 버전 이후 신설(since > rec_ver)된 차원은 그 기록에 요구하지 않는다
    dims = [n for n, s in all_dims if s <= rec_ver] if all_dims else None
    known = [n for n, _ in all_dims] if all_dims else None
    dims_required = DIMS_REQUIRED_BY_VERSION.get(rec_ver, max(DIMS_REQUIRED_BY_VERSION.values()))
    print(f"임계 {threshold} ({src}) · 기록 루브릭 v{rec_ver}" + (f" · 요구 차원 {dims}" if dims else ""))

    split_at = next((idx for idx, ln in enumerate(lines) if REREVIEW_HEADING.match(ln)), None)
    main_lines = lines[:split_at] if split_at is not None else lines
    re_lines = lines[split_at:] if split_at is not None else []

    scores, reviewers, stated = parse_part(main_lines, "본심사", dims, errors, warns, known, dims_required)
    avg = sum(scores) / len(scores) if scores else 0.0
    print(f"②③: 본심사 심사자 {len(reviewers)}인 · 점수 {len(scores)}개 · 평균 {avg:.2f} (임계 {threshold})")
    if stated is None:
        warns.append("[본심사] 종합 평균 줄이 없다 — 양식(review-form.md) 위반 의심, 재계산 값으로 판정")
    elif abs(stated - avg) > 0.05:
        errors.append(f"[본심사] 적힌 종합 평균 {stated} ≠ 재계산 {avg:.2f} — 점수가 근거다, 적힌 값을 고쳐라")

    below_after_rereview = False
    below_retro = False
    if not scores:
        errors.append("[본심사] 점수 표가 하나도 없다 (②)")
    elif avg < threshold:
        if not re_lines:
            if retro:
                below_retro = True
            else:
                errors.append(f"본심사 평균 {avg:.2f} < 임계 {threshold} 인데 재심사 섹션이 없다 "
                              "(⑤ 재조판 1회 → 재심사 정책 — 미달 호는 재조판하고 다시 심사받는다)")
        else:
            r_scores, r_reviewers, r_stated = parse_part(re_lines, "재심사", dims, errors, warns, known, dims_required)
            if not r_scores:
                errors.append("재심사 섹션은 있는데 점수 표가 없다 (⑤ — 제목만 있는 재심사는 재심사가 아니다)")
            else:
                r_avg = sum(r_scores) / len(r_scores)
                print(f"⑤: 재심사 심사자 {len(r_reviewers)}인 · 점수 {len(r_scores)}개 · 평균 {r_avg:.2f}")
                if r_stated is not None and abs(r_stated - r_avg) > 0.05:
                    errors.append(f"[재심사] 적힌 종합 평균 {r_stated} ≠ 재계산 {r_avg:.2f}")
                if r_avg < threshold:
                    below_after_rereview = True

    for w in warns:
        print("경고:", w)
    for e in errors:
        print("실패:", e)
    print(f"— 임계 {threshold} · 실패 {len(errors)} · 경고 {len(warns)}")
    if errors:
        sys.exit(1)
    if below_after_rereview:
        print("경고: 재심사 후에도 평균이 임계 미달 — 발행은 가능하되, 발행 보고에 "
              "「재심사 미달 발행」과 미달 평균을 명기하라 (⑤ 정책 문면)")
    if below_retro:
        print(f"경고: 소급 심사(--retro) — 본심사 평균 {avg:.2f} < 임계 {threshold} 미달 확정. "
              "편집장 결정(소급 재조판 없음)으로 재심사를 요구하지 않는다 — 심사 기록에 "
              "「소급 미달 확정」과 미달 평균을 명기하고, 지적은 차기 호 반영으로 처리하라 "
              "(review-form.md 「소급 심사 예외」 각주)")
    print("통과: 심사 봉인 게이트(IG4 ①~⑤) — 양식 정본은 templates/review-form.md")


if __name__ == "__main__":
    main()
