# -*- coding: utf-8 -*-
"""원장 정합 게이트 (D7) — 배포본 시드 원장의 자기모순을 정적으로 판정.

사용: python tools/check_ledger.py [킷루트]   (생략 시 이 스크립트의 상위 디렉토리)

규칙 (2026-08-12 이슈 #7에서 나온 것):
  JSONL 정본(output/ledger — gitignore 대상)에만 쓰고 okf/ 미러를 빠뜨리면,
  배포본에는 실체 없는 손가락(F-###)만 남는다. 새 설치본은 그걸 조회할 방법이
  없고, 대체된 수치를 유효한 최신값으로 방송한다. 셋 다 정적으로 판정 가능하다.

  ① 매달린 참조 — okf/**·profiles/** 텍스트의 F-###(-x) 참조는 전부
     okf/facts/f-###.md 로 실존해야 한다 (매달린 참조 0건)
  ② 상태 정합 — status: deprecated 인 개념이 index.md 「사실 — 유효」에
     남아 있으면 실패. 「사실 — 대체됨」에 등재돼 있어야 한다
  ③ 인덱스 신선도 — index.md 의 generated.at 이 facts 최신 파일의
     generated.at 보다, 그리고 log.md 최신 항목 날짜보다 오래되면 실패
     (routine 7절 재생성 누락 검출)

전부 정적 검사라 네트워크 없이 돌릴 수 있다. 실패 시 종료코드 1.
"""
import io, os, re, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

USAGE = "사용법: python tools/check_ledger.py [킷루트]"

REF_RE = re.compile(r"\b[Ff]-\d{3}(?:-[xX])?\b")  # f-100 이후 세 자리 전체 커버 (첫 자리 0 고정이면 f-1## 매달림을 놓친다)
GEN_AT_RE = re.compile(r"^generated:\s*\{[^}]*\bat:\s*([0-9T:\-]+)Z?\s*[},]", re.M)
STATUS_RE = re.compile(r"^status:\s*(\S+)", re.M)
LOG_DATE_RE = re.compile(r"^##\s*(\d{4}-\d{2}-\d{2})", re.M)


def read(path):
    """BOM 이 섞인 파일도 있으므로 utf-8-sig 로 읽는다."""
    return io.open(path, encoding="utf-8-sig").read()


def iter_text_files(*roots):
    for root in roots:
        if not os.path.isdir(root):
            continue
        for d, _, files in os.walk(root):
            for f in files:
                if f.lower().endswith((".md", ".yaml", ".yml", ".txt")):
                    yield os.path.join(d, f)


def main():
    kit = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    okf = os.path.join(kit, "okf")
    facts_dir = os.path.join(okf, "facts")
    index_path = os.path.join(okf, "index.md")
    log_path = os.path.join(okf, "log.md")
    for p in (okf, facts_dir, index_path, log_path):
        if not os.path.exists(p):
            sys.exit(f"{USAGE}\n실패: {p} 가 없다 — 킷루트가 맞는지 확인")

    errors = []

    # ① 매달린 참조 — okf/**·profiles/** 의 F-### 참조 전수 대조
    refs = {}  # id(소문자) -> 첫 발견 위치
    for path in iter_text_files(okf, os.path.join(kit, "profiles")):
        text = read(path)
        for n, line in enumerate(text.splitlines(), 1):
            for m in REF_RE.finditer(line):
                rid = m.group(0).lower()
                refs.setdefault(rid, f"{os.path.relpath(path, kit)}:{n}")
    for rid in sorted(refs):
        if not os.path.exists(os.path.join(facts_dir, rid + ".md")):
            errors.append(f"[매달린 참조] {rid.upper()} — {refs[rid]} 에서 참조되는데 okf/facts/{rid}.md 가 없다")

    # 사실 파일 전수 파싱 (②·③ 공용)
    fact_status, fact_gen = {}, {}
    for f in sorted(os.listdir(facts_dir)):
        if not f.endswith(".md"):
            continue
        text = read(os.path.join(facts_dir, f))
        rid = f[:-3]
        m = STATUS_RE.search(text)
        fact_status[rid] = m.group(1) if m else None
        if fact_status[rid] is None:
            errors.append(f"[형식] okf/facts/{f} 에 status 프론트매터가 없다")
        g = GEN_AT_RE.search(text)
        if g:
            fact_gen[rid] = g.group(1)

    # ② 상태 정합 — deprecated 가 index 「유효」에 남아 있으면 실패
    index_text = read(index_path)
    m_valid = re.search(r"^# 사실 — 유효\n(.*?)(?=^# )", index_text, re.M | re.S)
    m_dep = re.search(r"^# 사실 — 대체됨\n(.*)", index_text, re.M | re.S)
    if not m_valid or not m_dep:
        errors.append("[인덱스] index.md 에 「사실 — 유효」/「사실 — 대체됨」 절이 없다")
    else:
        valid_ids = set(re.findall(r"facts/(f-\d{3}(?:-x)?)\.md", m_valid.group(1)))
        dep_ids = set(re.findall(r"facts/(f-\d{3}(?:-x)?)\.md", m_dep.group(1)))
        for rid, st in sorted(fact_status.items()):
            if st == "deprecated":
                if rid in valid_ids:
                    errors.append(f"[상태 충돌] {rid} 는 status: deprecated 인데 index 「사실 — 유효」에 남아 있다")
                if rid not in dep_ids:
                    errors.append(f"[상태 충돌] {rid} 는 status: deprecated 인데 index 「사실 — 대체됨」에 없다")
            elif st == "stable" and rid in dep_ids:
                errors.append(f"[상태 충돌] {rid} 는 status: stable 인데 index 「사실 — 대체됨」에 있다")

    # ③ 인덱스 신선도 — generated.at 이 facts 최신·log 최신보다 오래되면 실패
    g = GEN_AT_RE.search(index_text)
    if not g:
        errors.append("[신선도] index.md 에서 generated.at 을 읽지 못했다")
    else:
        idx_at = g.group(1)  # ISO8601(Z 제외) — 사전순 비교가 시간순 비교와 같다
        if fact_gen:
            newest_id = max(fact_gen, key=fact_gen.get)
            if idx_at < fact_gen[newest_id]:
                errors.append(
                    f"[신선도] index generated.at({idx_at}Z) 이 facts 최신({newest_id}: {fact_gen[newest_id]}Z)보다 오래됐다 — 7절 재생성 누락"
                )
        log_dates = LOG_DATE_RE.findall(read(log_path))
        if log_dates and idx_at[:10] < max(log_dates):
            errors.append(
                f"[신선도] index generated.at({idx_at[:10]}) 이 log.md 최신 항목({max(log_dates)})보다 오래됐다 — 7절 재생성 누락"
            )

    for e in errors:
        print("실패:", e)
    if errors:
        sys.exit(1)
    dep_n = sum(1 for s in fact_status.values() if s == "deprecated")
    print(f"통과: 참조 {len(refs)}건 전부 실존, 사실 {len(fact_status)}건(대체 {dep_n}) 상태 정합, 인덱스 신선")


if __name__ == "__main__":
    main()
