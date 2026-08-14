# -*- coding: utf-8 -*-
"""킷 자가 회귀 시험 — 게이트의 게이트 (2026-08-14 신설).

사용: python tools/selftest.py

임시 디렉토리에 킷 사본(tools·templates·profiles·okf)을 만들고, 합성 입력
(심사 기록·지면·뼈대·run_log·마스터 SKILL)으로 각 게이트의 통과/차단 계약을
실측한다 — 정상 입력은 exit 0, 우회·위반 입력은 exit 1 이어야 한다.

왜 있는가: 2026-08-14 메커니즘 감사에서 게이트 12종+봉인은 정작 자기 자신을
지키는 시험이 없었다 — 도구를 고치면 그 수리가 무엇을 깨는지 아무도 몰랐다.
그 감사의 회귀 케이스(우회 실측 전건)를 여기 정본화한다. **게이트(check_*.py)·
게이트가 읽는 정본(templates)을 고친 커밋은 이 시험을 먼저 돌린다.**

플랫폼: 표준 라이브러리 + pyyaml(게이트 자체의 의존)만 쓴다. 리눅스에서 실측
확정(2026-08-14) — macOS·Windows 설치 실측 시 이 스크립트 한 방이 도구층 검증이다.
이 스크립트는 발행 게이트가 아니다 (required-gates 로스터 밖 — 개발용 도구).

레포를 건드리지 않는다 — 모든 입력·변형은 임시 사본 안에서만 일어난다.
전 케이스 기대 일치 시 exit 0, 하나라도 어긋나면 exit 1.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIMS = ["R1 이해관계 계량", "R2 함의 실행가능성", "R3 축 교차",
        "R4 새로움", "R5 근거-주장 정합", "R6 카피 인테그리티"]


def score_table(scores, reason="사유 한 줄이다"):
    rows = "\n".join(f"| {d} | {s} | {reason} |" for d, s in zip(DIMS, scores))
    avg = sum(scores) / len(scores)
    return (f"| 차원 | 점수 | 사유 한 줄 |\n|---|---:|---|\n{rows}\n"
            f"| **평균** | {avg:.2f} | |")


def review_record(date, target=None, headings=None, scores=None, stated="7.61",
                  reason="사유 한 줄이다", issues=True):
    """review-form 정본 골격의 합성 심사 기록. 인자로 위반을 주입한다."""
    target = target or f"eval/proto-{date}.md"
    headings = headings or ["### reader (독자 렌즈)", "### refuter (반증 렌즈)",
                            "### crosser (교차 렌즈)"]
    scores = scores or [[8, 7, 8, 7, 8, 8], [7, 8, 7, 8, 7, 8], [8, 8, 7, 8, 8, 7]]
    parts = [f"# 정성 심사 — {date} 호", "", "## 머리", "", "| 항목 | 값 |", "|---|---|",
             f"| 호 날짜 | {date} |", f"| 심사 대상 파일 | {target} |",
             "| 루브릭 버전 | insight-rubric.yaml v2 |", "", "## 심사자별 채점", ""]
    for h, s in zip(headings, scores):
        if h:
            parts += [h, ""]
        parts += [score_table(s, reason), ""]
    parts += ["## 종합", "", "| 항목 | 값 |", "|---|---|",
              f"| 3인 평균 | {stated} |", "| 판정 | 통과 |", ""]
    if issues:
        parts += ["## 지적 목록", "", "| # | 렌즈 | 지적 | 처리 (반영 / 기각-사유) |",
                  "|---:|---|---|---|", "| 1 | refuter | 시험 지적 | 반영 |", ""]
    return "\n".join(parts)


PAGE = """<h1>광고 자본은 GPT로 움직이는가 — 답의 한 조각이 우리 손에 있다</h1>
<p class="standfirst">유료 미디어 +17.5%, 구글 62%→57% (F-038). 해야 하는 확인이 있다 (F-042)</p>
<section class="sec" data-macro="MA3" data-axis="채널 편입" data-side-a="F-042, F-041" data-side-b="F-038, F-012">
<h2>챗GPT 채널 편입</h2>
<p class="note">담당 캠페인의 챗GPT 픽셀 설치 여부를 8월 17일 전에 확인하라</p>
</section>"""

PROTO = """# 오늘의 제일기획 뉴스 — {date}

## 오늘의 화두

### 광고 자본은 GPT로 움직이는가 — 답의 한 조각이 우리 손에 있다

**함의** — 담당 캠페인의 챗GPT 픽셀 설치 여부를 8월 17일 전에 확인하라(F-042).
"""

GATES_FULL = ["check_tables:0", "check_exhibits:0", "check_css_vars:0",
              "check_ledger:0", "check_size:0", "check_insight:0", "check_formats:0",
              "check_theme:0", "check_review:0", "check_publish:0"]

THEME_EVAL = """| 단위 | 요지 | 판정 | 근거 |
|---|---|---|---|
| 화두(h1) | 시험 | 정렬 | 시험 근거 |
| 축 절 | 시험 | 정렬 | 시험 근거 |
"""

THEME_PAGE = """<h1>시험 화두</h1>
<section class="sec" data-macro="{macro}" data-axis="시험 축"><h2>시험</h2></section>
"""

MASTER_CLEAN = ("# 킷 위치\n/tmp/somewhere/kit\n\n# 본문\n"
                "https://dart.fss.or.kr/api/todayRSS.xml 를 본다.\n")
MASTER_LEAKY = ("# 킷 위치\n/tmp/somewhere/kit\n\n# 본문\n"
                "원장은 /home/author/briefing/okf 에 있다.\n")


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def edit(path, old, new):
    t = io.open(path, encoding="utf-8").read()
    if old not in t:
        raise RuntimeError(f"시험 픽스처 오류 — {os.path.basename(path)} 에 「{old[:30]}」 이 없다")
    w(path, t.replace(old, new))


def main():
    tmp = tempfile.mkdtemp(prefix="kit-selftest-")
    try:
        for d in ("tools", "templates", "profiles", "okf"):
            shutil.copytree(os.path.join(KIT_ROOT, d), os.path.join(tmp, d))
        j = lambda *p: os.path.join(tmp, *p)

        # ── 픽스처 ────────────────────────────────────────────────
        import json
        # check_review — 정상·우회 6종 (날짜당 기록 하나)
        w(j("eval", "review-2026-08-20.md"), review_record("2026-08-20"))
        w(j("eval", "review-2026-08-21.md"), review_record(
            "2026-08-21", headings=["### 심사", "", ""]))                # 렌즈 무정체
        w(j("eval", "review-2026-08-22.md"), review_record(
            "2026-08-22", scores=[[99, 7, 8, 7, 8, 8], [7, 8, 7, 8, 7, 8],
                                  [8, 8, 7, 8, 8, 7]], stated="12.67"))  # 점수 인플레
        w(j("eval", "review-2026-08-23.md"), review_record(
            "2026-08-23", reason=""))                                    # 사유 공백
        w(j("eval", "review-2026-08-24.md"), review_record(
            "2026-08-24", issues=False))                                 # 지적 표 부재
        w(j("eval", "review-2026-08-25.md"), review_record(
            "2026-08-25", target="output/web/2026-08-25.html"))          # 웹판 대상
        for d in ("20", "21", "22", "23", "24", "25"):
            w(j("output", "web", f"2026-08-{d}.html"), "<h1>x</h1>")

        # check_insight — 정상 / 뼈대 배신 / 가짜 좌표
        w(j("output", "web", "2026-08-30.html"), PAGE)
        w(j("eval", "proto-2026-08-30.md"), PROTO.format(date="2026.08.30"))
        w(j("output", "web", "2026-08-31.html"),
          PAGE.replace("광고 자본은 GPT로 움직이는가 — 답의 한 조각이 우리 손에 있다",
                       "다른 화두가 실렸다"))
        w(j("eval", "proto-2026-08-31.md"), PROTO.format(date="2026.08.31"))
        w(j("output", "web", "2026-09-01.html"), PAGE.replace("(F-038)", "(F-999)"))
        w(j("output", "web", "2026-09-04.html"), PAGE.replace(
            "광고 자본은 GPT로 움직이는가 — 답의 한 조각이 우리 손에 있다",
            "전환의 값은 세계가 먼저 매겼다 — 우리 증거는 오늘이 법정기한인 반기보고서부터다"))  # 34자 — 간명 상한 위반

        # check_run — 로스터 전수 / 한 줄 / 실패코드
        rows = [
            {"event": "end", "started_at": "2026-08-30T07:00:00",
             "ended_at": "2026-08-30T08:00:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL},
            {"event": "end", "started_at": "2026-08-31T07:00:00",
             "ended_at": "2026-08-31T08:00:00", "mode": "생산", "result": "산출",
             "gates": ["check_tables:0"]},
            {"event": "end", "started_at": "2026-09-01T07:00:00",
             "ended_at": "2026-09-01T08:00:00", "mode": "생산", "result": "산출",
             "gates": GATES_FULL[:-1] + ["check_publish:1"]},
        ]
        w(j("output", "ledger", "run_log.jsonl"),
          "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")

        # check_theme — data-macro 정상 / 오타
        w(j("output", "web", "2026-09-02.html"), THEME_PAGE.format(macro="M2A"))
        w(j("eval", "theme-2026-09-02.md"), THEME_EVAL)
        w(j("output", "web", "2026-09-03.html"), THEME_PAGE.format(macro="MA1"))
        w(j("eval", "theme-2026-09-03.md"), THEME_EVAL)

        # sync_skill — 마스터 합성
        w(j("master-clean.md"), MASTER_CLEAN)
        w(j("master-leaky.md"), MASTER_LEAKY)

        # ── 케이스 ────────────────────────────────────────────────
        # (라벨, 도구, 인자, 기대 exit, 사전 변형 or None, 사후 복원 or None)
        A = j("okf", "axes.md")
        F98 = j("okf", "facts", "f-098.md")
        cases = [
            ("review 정상 기록(뼈대 대상·config 부재 rubric 폴백)", "check_review.py",
             ["output/web/2026-08-20.html"], 0, None, None),
            ("review 렌즈 무정체 — 단일 제목 표 3개", "check_review.py",
             ["output/web/2026-08-21.html"], 1, None, None),
            ("review 점수 99 인플레", "check_review.py",
             ["output/web/2026-08-22.html"], 1, None, None),
            ("review 사유 전 칸 공백", "check_review.py",
             ["output/web/2026-08-23.html"], 1, None, None),
            ("review 지적 목록 표 부재", "check_review.py",
             ["output/web/2026-08-24.html"], 1, None, None),
            ("review 심사 대상=웹판 (비소급)", "check_review.py",
             ["output/web/2026-08-25.html"], 1, None, None),
            ("review 심사 대상=웹판 (--retro)", "check_review.py",
             ["output/web/2026-08-25.html", "--retro"], 0, None, None),
            ("insight 정상 — 좌표 실존·뼈대 일치", "check_insight.py",
             ["output/web/2026-08-30.html"], 0, None, None),
            ("insight 뼈대 배신 — 화두 실종", "check_insight.py",
             ["output/web/2026-08-31.html"], 1, None, None),
            ("insight 가짜 좌표 (F-999)", "check_insight.py",
             ["output/web/2026-09-01.html"], 1, None, None),
            ("insight h1 간명 상한 초과 (공백 제외 34자 > 30)", "check_insight.py",
             ["output/web/2026-09-04.html"], 1, None, None),
            ("run 로스터 전수 기록", "check_run.py",
             ["--date", "2026-08-30", tmp], 0, None, None),
            ("run 한 줄 기록 — 로스터 미달", "check_run.py",
             ["--date", "2026-08-31", tmp], 1, None, None),
            ("run 실패코드 :1 기록", "check_run.py",
             ["--date", "2026-09-01", tmp], 1, None, None),
            ("theme data-macro 정상(MA1)", "check_theme.py",
             ["output/web/2026-09-03.html"], 0, None, None),
            ("theme data-macro 오타(M2A)", "check_theme.py",
             ["output/web/2026-09-02.html"], 1, None, None),
            ("ledger 원본 정합", "check_ledger.py", [tmp], 0, None, None),
            ("ledger 미태깅 신규 사실", "check_ledger.py", [tmp], 1,
             lambda: w(F98, io.open(j("okf", "facts", "f-055.md"),
                                    encoding="utf-8").read().replace("f-055", "f-098")),
             lambda: os.remove(F98)),
            ("ledger 점수판 오기", "check_ledger.py", [tmp], 1,
             lambda: edit(A, "**점수판** 지지 12", "**점수판** 지지 13"),
             lambda: edit(A, "**점수판** 지지 13", "**점수판** 지지 12")),
            ("sync 유닉스 경로 누출", "sync_skill.py",
             ["--check", j("master-leaky.md")], 1, None, None),
            ("sync 클린 마스터 (--check 무기록)", "sync_skill.py",
             ["--check", j("master-clean.md")], 0, None, None),
        ]

        failed = []
        for label, tool, args, want, setup, teardown in cases:
            if setup:
                setup()
            try:
                r = subprocess.run([sys.executable, j("tools", tool)] + args,
                                   capture_output=True, text=True, cwd=tmp)
                got = r.returncode
            finally:
                if teardown:
                    teardown()
            ok = got == want
            print(f"{'OK  ' if ok else 'FAIL'} [{tool[:-3]}] {label} — exit {got} (기대 {want})")
            if not ok:
                failed.append((label, r.stdout.strip().splitlines()[-3:]))

        print(f"— 케이스 {len(cases)} · 불일치 {len(failed)}")
        if failed:
            for label, tail in failed:
                print(f"불일치 상세 [{label}]:")
                for ln in tail:
                    print("   ", ln)
            sys.exit(1)
        print("통과: 게이트 통과/차단 계약 전 케이스 기대 일치 — 게이트를 고쳤다면 이 줄을 근거로 커밋하라")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
