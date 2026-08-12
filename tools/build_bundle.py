#!/usr/bin/env python3
"""
JSONL 원장 -> OKF v0.2 지식 번들 변환기

Open Knowledge Format (OKF) 스펙: GoogleCloudPlatform/knowledge-catalog
이 스크립트는 frontmatter 규약만 따른다. Attested Computation 의 executor/receipt
계층은 쓰지 않는다. 이 규모에는 과하다.

사용법:
    python tools/build_bundle.py --src output/ledger --out ./okf
"""

import argparse
import json
import pathlib
import datetime
import re
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (sys.exit 안내는 stderr)

NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
PRODUCER = "claude/opus-5"

# 티어별 신선도 만료일. 다음 확인 시점에 자동으로 낡는다.
STALE_BY_TIER = {
    "T1": "2026-10-23",   # 3분기 실적발표 예상일
    "T2": "2026-11-30",
    "T3": "2027-01-31",
}

GRADE_TAG = {
    "1차자료": "grade-primary",
    "증권사": "grade-broker",
    "보도": "grade-press",
    "관찰": "grade-observed",
    "해석": "grade-interpretation",
}


def yaml_str(s):
    """YAML 스칼라로 안전하게 감싼다."""
    s = str(s).replace('"', "'")
    return f'"{s}"'


def write_concept(path: pathlib.Path, frontmatter: list, body: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "---\n" + "\n".join(frontmatter) + "\n---\n\n" + body.rstrip() + "\n"
    path.write_text(text, encoding="utf-8")


def build_facts(src: pathlib.Path, out: pathlib.Path):
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    made = []
    for r in rows:
        cid = r["id"].lower()
        tier = r.get("tier", "T2")
        grade = r.get("grade", "관찰")
        active = r.get("status") == "active"

        fm = [
            "type: Fact",
            f"title: {yaml_str(r['fact'][:70])}",
            f"description: {yaml_str(r['fact'])}",
        ]

        # provenance
        fm.append("sources:")
        fm.append(f"  - id: {r.get('source','unknown').split()[0].lower().replace('(','').replace(')','')}")
        if r.get("url"):
            fm.append(f"    resource: {r['url']}")
        fm.append(f"    title: {yaml_str(r.get('source','unknown'))}")
        fm.append(f"    last_modified: {r.get('added')}")

        # trust
        fm.append(f"generated: {{ by: {PRODUCER}, at: {NOW} }}")
        # verified 는 사람이 검토한 뒤에만 채운다. 지금은 비운다.

        # lifecycle
        fm.append(f"status: {'stable' if active else 'deprecated'}")
        if active:
            fm.append(f"stale_after: {STALE_BY_TIER.get(tier, '2026-12-31')}")

        tags = [tier, GRADE_TAG.get(grade, "grade-observed")]
        fm.append(f"tags: [{', '.join(tags)}]")
        fm.append(f"grade: {yaml_str(grade)}")

        # body
        body = [f"{r['fact']}\n"]
        if r.get("note"):
            body.append(f"**단서** — {r['note']}\n")
        if r.get("supersedes"):
            body.append(f"이 개념은 [{r['supersedes'].lower()}]({r['supersedes'].lower()}.md) 를 대체한다.\n")
        if r.get("superseded_by"):
            body.append(f"> 이 개념은 더 이상 현재가 아니다. "
                        f"[{r['superseded_by'].lower()}]({r['superseded_by'].lower()}.md) 로 대체됐다.\n")
        body.append(f"출처: {r.get('source','unknown')}")
        if r.get("url"):
            body.append(f"<{r['url']}>")

        write_concept(out / "facts" / f"{cid}.md", fm, "\n".join(body))
        made.append((cid, r["fact"][:60], "stable" if active else "deprecated", tier))
    return made


def build_agenda(src: pathlib.Path, out: pathlib.Path):
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    made = []
    for r in rows:
        cid = r["id"].lower()
        fm = [
            "type: Agenda Item",
            f"title: {yaml_str(r['title'][:70])}",
            f"description: {yaml_str(r['title'])}",
            f"event_date: {r['date']}",
        ]
        if r.get("date_end"):
            fm.append(f"event_date_end: {r['date_end']}")
        fm.append("sources:")
        fm.append(f"  - id: {r['id'].lower()}-src")
        fm.append(f"    title: {yaml_str(r.get('source','unknown'))}")
        fm.append(f"generated: {{ by: {PRODUCER}, at: {NOW} }}")
        fm.append("status: stable")
        # 일정은 지나면 낡는다
        fm.append(f"stale_after: {r.get('date_end', r['date'])}")
        fm.append(f"tags: [{r.get('tier','T2')}, certainty-{r.get('certainty','estimated')}]")
        fm.append(f"certainty: {r.get('certainty','estimated')}")

        body = [f"{r['title']}\n"]
        if r.get("date_hint"):
            body.append(f"시점: {r['date_hint']} (`{r['date']}` 로 기록)\n")
        if r.get("note"):
            body.append(f"{r['note']}\n")
        body.append(f"근거: {r.get('source','unknown')}")

        write_concept(out / "agenda" / f"{cid}.md", fm, "\n".join(body))
        made.append((cid, r["title"][:60], r["date"], r.get("certainty")))
    return made


def build_index(out: pathlib.Path, facts, agenda):
    active = [f for f in facts if f[2] == "stable"]
    dep = [f for f in facts if f[2] == "deprecated"]
    lines = [
        "---",
        "type: Index",
        'title: "브리핑 지식 번들"',
        'description: "매일 갱신되는 추적 대상 사실과 일정. 진입점."',
        f"generated: {{ by: {PRODUCER}, at: {NOW} }}",
        "status: stable",
        "---",
        "",
        "# 브리핑 지식 번들",
        "",
        "매일 실행이 읽는 범위는 이 파일과 `agenda/`, 그리고 `status: stable` 인 `facts/` 까지다.",
        "`archive/` 는 읽지 않는다. 읽기 비용을 여기서 자른다.",
        "",
        f"- 사실: 유효 {len(active)}건 / 대체됨 {len(dep)}건",
        f"- 일정: {len(agenda)}건",
        "",
        "# 일정",
        "",
    ]
    for cid, title, date, cert in sorted(agenda, key=lambda x: x[2]):
        mark = "" if cert == "confirmed" else " (추정)"
        lines.append(f"- `{date}`{mark} [{title}](agenda/{cid}.md)")
    lines += ["", "# 사실 — 유효", ""]
    for cid, title, _, tier in active:
        lines.append(f"- [{tier}] [{title}](facts/{cid}.md)")
    if dep:
        lines += ["", "# 사실 — 대체됨", "",
                  "링크와 이력을 위해 남긴다. 현재 값으로 쓰지 않는다.", ""]
        for cid, title, _, tier in dep:
            lines.append(f"- ~~[{title}](facts/{cid}.md)~~")
    (out / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_log(out: pathlib.Path, n_facts, n_agenda):
    p = out / "log.md"
    today = datetime.date.today().isoformat()
    entry = (f"## {today}\n\n"
             f"- JSONL 원장에서 번들 초기 생성. 사실 {n_facts}건, 일정 {n_agenda}건\n"
             f"- 생성자 {PRODUCER}. `verified` 는 비어 있다 (사람 검토 전)\n")
    if p.exists():
        old = p.read_text(encoding="utf-8")
        head, _, rest = old.partition("\n\n")
        p.write_text(f"{head}\n\n{entry}\n{rest}", encoding="utf-8")
    else:
        p.write_text("# 갱신 이력\n\n" + entry, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    src, out = pathlib.Path(a.src), pathlib.Path(a.out)

    # 원장 부재를 트레이스백 대신 한국어 안내로 (킷 규약: 안내 후 exit 1)
    for name in ("facts.jsonl", "agenda.jsonl"):
        p = src / name
        if not p.exists():
            sys.exit(f"원장 파일 없음: {p} — --src 에 facts.jsonl·agenda.jsonl 이 있는 디렉터리를 지정하라")

    facts = build_facts(src / "facts.jsonl", out)
    agenda = build_agenda(src / "agenda.jsonl", out)
    build_index(out, facts, agenda)
    build_log(out, len(facts), len(agenda))
    (out / "archive").mkdir(parents=True, exist_ok=True)

    print(f"facts   {len(facts)}건")
    print(f"agenda  {len(agenda)}건")
    print(f"-> {out.resolve()}")


if __name__ == "__main__":
    main()
