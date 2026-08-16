# -*- coding: utf-8 -*-
"""E8 상행 사전판정 게이트 — 이 기기가 표준 호를 **한 번에** 올릴 수 있는가.

사용법:
  python tools/check_uplink.py [--target-mb 3.0] [--endpoint URL]

왜 이 게이트가 있는가 (2026-08-16 맥 워커 규명):
  맥 워커가 두 주 넘게 「API 연결 끊김」으로 발행을 못 했다. 원인은 회선도 NIC 도
  TCP 도 PMTU 도 아니었고, **버스트 허용량을 가진 폴리서**였다 — 512KB 까지는
  8.6MB/s 로 올라가다가 그 위부터 60KB/s 로 무너지고, 무제한 전송은 15.0초에
  ECONNRESET 로 죽었다. 같은 파일을 45KB/s 로 흘리면 22.8초에 완주했다.
  즉 **대역이 모자라서가 아니라 셰이퍼보다 빨리 밀어서** 끊긴 것이다.

  이 실패는 발행 시점에만 드러나고, 그때는 이미 호를 다 만든 뒤다. 게다가 증상이
  「연결 끊김」이라 회선 탓으로 오진되기 쉽고, 오진의 결말은 호 크기를 깎는 것
  (D8 이 경계하는 바로 그 행동 — 킷 판형을 한 기기의 셰이퍼에 맞춰 내리는 것)이다.
  그래서 판정을 **생산 전으로 당긴다**.

판정:
  ① 크기 사다리     — 64KB → 256KB → 512KB → 1MB → 2MB → 목표(기본 3MB) 를 차례로
                      올리고 각 단의 완주 여부와 실효속도를 잰다
  ② 목표 완주        — 목표 크기가 완주하면 통과(0). 이 기기는 표준 호를 낼 수 있다
  ③ 실패의 성격 구분 — 목표가 못 가면 실패(1)이되, **셰이퍼인지 좁은 상행인지**를
                      가려서 보고한다. 작은 단이 빠른데 큰 단이 무너지면 셰이퍼이고,
                      무너지기 직전 크기가 버스트 허용량·무너진 뒤 속도가 지속 상한이다.
                      전 구간이 고르게 느리면 그때는 실제로 상행이 좁은 것이다

종료코드 (이슈 #37 3분법):
  0  통과 — 목표 크기 완주
  1  판정 결과 실패 — 셰이퍼 또는 좁은 상행으로 목표를 못 올림
  2  판정 불가 — 최소 단(64KB)조차 못 보냈다. 기기가 아니라 판정 자체가 성립 안 한 것
                (망 단절·종단 장애·차단). 통과도 아니고 「실패」와도 다르다
  64 사용법 오류 (EX_USAGE)

게이트의 정직성(F5): 이 게이트는 **증상만** 판정한다 — 셰이퍼가 있는지, 버스트가
얼마인지까지다. 그 셰이퍼가 이 기기의 커널(dummynet/pf)에 있는지 망의 QoS 에 있는지는
관리자 자격이 필요해 여기서 답하지 않는다. 소재 판별 절차는 publish-checklist D8 ⑷ 에 있다.
"""
import io
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함)

USAGE = "사용법: python tools/check_uplink.py [--target-mb 3.0] [--endpoint URL]"

EX_USAGE = 64
UNDECIDED = 2   # 판정 불가 — 통과가 아니고 「판정 결과 실패」와도 다르다 (이슈 #37)

# 기본 종단. 업로드 본문을 받아 버려주는 공개 계측 종단이면 무엇이든 된다.
DEFAULT_ENDPOINT = "https://speed.cloudflare.com/__up"

# 사다리. 마지막 단은 --target-mb 로 대체된다.
LADDER_BASE = [65536, 262144, 524288, 1048576, 2097152]

# 한 단의 상한 시간. 넉넉히 준다 — 느리다고 실패로 몰면 「좁은 상행」과 「셰이퍼」를
# 구분할 수 없다. 실측에서 조여진 1MB 는 51초에 완주했다.
PER_STEP_TIMEOUT = 90

# 최고속도가 무너진 속도의 몇 배 이상이면 셰이퍼로 본다. 실측 붕괴는 82배였고,
# 회선이 고르게 느린 경우의 단 간 편차는 통상 2배 안쪽이다.
COLLAPSE_RATIO = 5.0

# 셰이퍼라고 부르려면 작은 단이 이 속도는 나와야 한다. 이보다 느리면 붕괴비가
# 커도 그냥 느린 회선의 요동으로 본다.
FAST_ENOUGH = 500_000  # B/s


def human(n):
    """바이트를 사람이 읽는 단위로. 사다리 단 이름과 보고에 같은 함수를 쓴다."""
    if n >= 1048576:
        v = n / 1048576.0
        return ("%.1fMB" % v).replace(".0MB", "MB")
    return "%dKB" % (n // 1024)


def rate(n):
    if n >= 1048576:
        return "%.2f MB/s" % (n / 1048576.0)
    return "%.0f KB/s" % (n / 1024.0)


def upload(endpoint, payload, timeout=PER_STEP_TIMEOUT):
    """한 단을 올린다. (완주여부, 초, 오류문자열) 을 돌려준다.

    끊김(ECONNRESET)·타임아웃·프로토콜 오류를 모두 「못 갔다」로 접는다 —
    이 게이트가 묻는 것은 원인이 아니라 **한 번에 올라가는가** 하나다.
    """
    req = urllib.request.Request(endpoint, data=payload, method="POST")
    req.add_header("Content-Type", "application/octet-stream")
    ctx = ssl.create_default_context()
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            r.read(1024)
        return True, time.monotonic() - t0, ""
    except urllib.error.HTTPError as e:
        # 종단이 4xx/5xx 를 줘도 본문은 다 올라간 것이다 — 전송은 완주로 친다.
        try:
            e.read(1024)
        except Exception:
            pass
        if 400 <= e.code < 600:
            return True, time.monotonic() - t0, ""
        return False, time.monotonic() - t0, "HTTP %s" % e.code
    except Exception as e:  # URLError·socket.timeout·ConnectionReset 등
        return False, time.monotonic() - t0, type(e).__name__


def run_ladder(endpoint, target_bytes):
    """사다리를 올리며 각 단을 기록한다. 한 단이 못 가면 거기서 멈춘다
    (더 큰 단은 볼 것도 없고, 조여진 망에 부하만 준다)."""
    sizes = [s for s in LADDER_BASE if s < target_bytes] + [target_bytes]
    rows = []
    for size in sizes:
        payload = os.urandom(size)
        ok, secs, err = upload(endpoint, payload)
        speed = (size / secs) if (ok and secs > 0) else 0.0
        rows.append({"size": size, "ok": ok, "seconds": secs, "speed": speed, "err": err})
        print("  %-8s %s  %s" % (
            human(size),
            ("완주 %5.1f초" % secs) if ok else ("끊김 %5.1f초" % secs),
            rate(speed) if ok else ("(%s)" % (err or "실패")),
        ))
        if not ok:
            break
    return rows


def diagnose(rows, target_bytes):
    """사다리 결과를 판정으로 접는다. (종료코드, 보고줄들).

    순수 함수다 — 망 없이 selftest 가 합성 사다리로 이 계약을 검증한다.
    """
    out = []
    if not rows:
        return UNDECIDED, ["판정 불가: 사다리가 한 단도 돌지 않았다"]

    okay = [r for r in rows if r["ok"]]
    if not okay:
        return UNDECIDED, [
            "판정 불가: 최소 단(%s)조차 보내지 못했다 (%s)" % (human(rows[0]["size"]), rows[0]["err"] or "실패"),
            "  기기의 상행이 아니라 판정 자체가 성립하지 않았다 — 망 단절·종단 장애·차단을 먼저 본다",
        ]

    best = max(r["speed"] for r in okay)
    reached = max(r["size"] for r in okay)

    if reached >= target_bytes:
        out.append("통과: %s 를 한 번에 올렸다 (%s)" % (human(target_bytes), rate(best)))
        return 0, out

    # 목표 미달 — 셰이퍼인지 좁은 상행인지 가른다.
    #
    # 버스트 허용량 = 아직 최고속도급으로 올라간 **가장 큰** 단.
    # 지속 상한 = 그 위에서 완주는 했으나 무너진 단들의 최저속도.
    # 첫 단(64KB)은 TLS 수립 비용이 섞여 느리게 나온다 — 그걸 「무너졌다」로 읽으면
    # 지속 상한을 엉뚱하게 보고하므로, 붕괴 판정은 **버스트 위 구간만** 본다.
    burst = max(r["size"] for r in okay if r["speed"] * COLLAPSE_RATIO >= best)
    after = [r for r in okay if r["size"] > burst]
    collapsed = min((r["speed"] for r in after), default=0.0)
    stalled = [r for r in rows if not r["ok"]]
    is_shaper = best >= FAST_ENOUGH and (bool(stalled) or (collapsed and best / collapsed >= COLLAPSE_RATIO))

    if is_shaper:
        out.append("실패: %s 는 못 올린다 — **셰이퍼**다 (회선 문제가 아니다)" % human(target_bytes))
        out.append("  이 기기는 %s 까지 %s 로 올렸다 — 버스트 허용량이 그만큼이다" % (human(burst), rate(best)))
        if collapsed:
            out.append("  그 위부터 %s 로 무너진다 — 이것이 지속 상한이다" % rate(collapsed))
        if stalled:
            out.append("  %s 는 아예 완주하지 못한다 (%s) — 버킷이 마른 뒤 폴리서가 드롭한다"
                       % (human(stalled[0]["size"]), stalled[0]["err"] or "끊김"))
        out.append("  대역이 모자란 게 아니라 셰이퍼보다 빨리 밀어서 끊긴다.")
        out.append("  **호 크기를 깎지 마라** — 셰이퍼를 없애는 것이 정공법이다 (D8 ⑷: 소재 판별).")
    else:
        out.append("실패: %s 는 못 올린다 — 상행이 고르게 좁다 (최고 %s)" % (human(target_bytes), rate(best)))
        out.append("  단 간 붕괴가 없으므로 셰이퍼가 아니라 실제 대역 부족이다.")
        out.append("  회선·랜포트·케이블을 먼저 보고, 그래도 좁으면 그때 호 크기를 논한다 (D8).")
    return 1, out


# ── 시험 후크 ───────────────────────────────────────────────────────────────
# `--fixture <이름>` 은 기능이 아니라 selftest 전용이다. 이 게이트의 판정은 망을 타므로
# 실행 자체를 시험할 수 없다 — 그래서 판정을 순수 함수(diagnose)로 떼고, 합성 사다리로
# **계약만** 시험한다. (size, ok, B/s) 순.
FIXTURES = {
    # 정상 기기 — 목표까지 완주
    "pass": [(65536, True, 1.2e6), (262144, True, 6.9e6), (524288, True, 6.9e6),
             (1048576, True, 12.9e6), (2097152, True, 13.3e6), (3145728, True, 13.1e6)],
    # 셰이퍼 — 버스트 위에서 완주는 하되 무너지고, 더 위는 끊긴다
    "shaper": [(65536, True, 1.0e6), (262144, True, 6.0e6), (524288, True, 8.0e6),
               (1048576, True, 7.0e4), (2097152, False, 0.0)],
    # 맥 워커 실측(2026-08-16) — 첫 단이 TLS 수립 때문에 느리다. 이 287KB/s 를
    # 「무너진 속도」로 읽어 지속 상한이라 보고하던 버그의 재발 방지 케이스다.
    "tls-noise": [(65536, True, 2.87e5), (262144, True, 3.12e6), (524288, True, 8.28e6),
                  (1048576, True, 8.01e6), (2097152, False, 0.0)],
    # 셰이퍼가 아니라 실제로 좁은 상행 — 단 간 붕괴가 없다
    "narrow": [(65536, True, 1.9e5), (262144, True, 2.1e5), (524288, True, 2.0e5),
               (1048576, True, 2.0e5), (2097152, False, 0.0)],
    # 최소 단조차 못 보냄 — 기기가 아니라 판정이 성립하지 않는다
    "undecided": [(65536, False, 0.0)],
}


def fixture_rows(name):
    return [{"size": s, "ok": ok, "seconds": (s / sp) if sp else 0.0,
             "speed": sp, "err": "" if ok else "URLError"}
            for (s, ok, sp) in FIXTURES[name]]


def main(argv):
    endpoint = DEFAULT_ENDPOINT
    target_mb = 3.0
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--fixture" and i + 1 < len(argv):
            name = argv[i + 1]
            if name not in FIXTURES:
                print(USAGE)
                return EX_USAGE
            code, lines = diagnose(fixture_rows(name), 3145728)
            for ln in lines:
                print(ln)
            return code
        elif a == "--endpoint" and i + 1 < len(argv):
            endpoint = argv[i + 1]
            i += 2
        elif a == "--target-mb" and i + 1 < len(argv):
            try:
                target_mb = float(argv[i + 1])
            except ValueError:
                print(USAGE)
                return EX_USAGE
            i += 2
        else:
            print(USAGE)
            return EX_USAGE
    if target_mb <= 0:
        print(USAGE)
        return EX_USAGE

    target_bytes = int(target_mb * 1048576)
    print("E8 상행 사전판정 — 목표 %s · 종단 %s" % (human(target_bytes), endpoint))
    rows = run_ladder(endpoint, target_bytes)
    code, lines = diagnose(rows, target_bytes)
    print("")
    for ln in lines:
        print(ln)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
