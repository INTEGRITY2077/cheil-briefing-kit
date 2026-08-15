# -*- coding: utf-8 -*-
"""판정 대상 프로파일을 **정본에서** 고르는 공용 해석기 (2026-08-15 수리).

왜 있는가 (실측 반려, 검수 문제 7): `check_run.load_sweep_roster()` 와
`check_ledger` ④⑤⑥ 가 각각 `profiles/cheil.yaml` 이라는 **파일명 리터럴**을 코드에
박고 있었다. 킷 문서는 `profiles/<profile>.yaml` 다중 프로파일을 전제하는데
도구가 특정 파일명을 알면, 다른 프로파일을 얹은 설치본에 cheil.yaml 이 남아 있는
순간 **엉뚱한 프로파일의 sources·macro_axes 로 판정한다**. 규율 ② (정본-판정 분리)
위반이라 여기로 뺀다 — 도구는 「어느 프로파일인가」를 스스로 알지 않는다.

우선순위 (앞의 것이 이긴다):
  1. 명시 인자 — `--profile <이름>` (도구가 넘겨준 값)
  2. `config.yaml` 의 `profile:` 키 — 킷의 선언된 정본
     (`config.example.yaml` 30행 「추적 대상. profiles/ 아래 파일명에서 .yaml 을 뺀 값」)
  3. `profiles/` 에 파일이 **하나뿐이면** 그것 — 설치본이 프로파일을 갈아끼운 경우
  4. 그 외(둘 이상인데 고를 근거가 없음) → None + 사유. 도구는 판정을 생략하고
     경고로 강등한다 (⑤ⓑ 선례 — 못 읽으면 조용히 통과시키지 말고 시끄럽게 강등)

config.yaml 은 배포본에 포함되지 않으므로(설정 파일 머리 주석) 2번은 없을 수 있다.
그래서 3번 폴백이 필요하고, 그 폴백은 파일명을 모른다 — 개수만 본다.
"""
import io
import os
import re

__all__ = ["resolve_profile"]

# config.yaml 을 파싱하려고 pyyaml 을 강제하지 않는다 — 최상위 `profile: <이름>` 한 줄만
# 읽으면 되고, 이 도구들은 pyyaml 이 없어도 나머지 판정이 돌아야 한다(지연 임포트 선례).
_PROFILE_KEY_RE = re.compile(r"^profile:\s*([A-Za-z0-9._\-]+)\s*(?:#.*)?$", re.M)


def _from_config(kit_root):
    for name in ("config.yaml", "config.yml"):
        p = os.path.join(kit_root, name)
        if not os.path.exists(p):
            continue
        try:
            m = _PROFILE_KEY_RE.search(io.open(p, encoding="utf-8-sig").read())
        except OSError:
            continue
        if m:
            return m.group(1)
    return None


def resolve_profile(kit_root, name=None):
    """(경로, 사유) 를 돌려준다. 고르지 못하면 (None, 사유 문자열).

    사유는 통과 시에도 「어디서 골랐는가」를 담는다 — 판정 로그에 그대로 찍어서
    「어느 프로파일로 판정했는지」가 출력에 남게 한다.
    """
    prof_dir = os.path.join(kit_root, "profiles")
    if not os.path.isdir(prof_dir):
        return None, "profiles/ 디렉토리가 없다"
    cands = sorted(f for f in os.listdir(prof_dir) if f.endswith((".yaml", ".yml")))
    if not cands:
        return None, "profiles/ 에 프로파일 파일이 없다"

    picked = name or _from_config(kit_root)
    if picked:
        for ext in (".yaml", ".yml"):
            if picked + ext in cands:
                src = "인자" if name else "config.yaml profile:"
                return os.path.join(prof_dir, picked + ext), f"{picked}{ext} ({src})"
        return None, (f"지정된 프로파일 {picked!r} 의 파일이 profiles/ 에 없다 "
                      f"(있는 것: {', '.join(cands)})")

    if len(cands) == 1:
        return os.path.join(prof_dir, cands[0]), f"{cands[0]} (profiles/ 유일 파일)"
    return None, ("profiles/ 에 파일이 둘 이상인데 고를 근거가 없다 "
                  f"({', '.join(cands)}) — config.yaml 에 `profile:` 을 적거나 "
                  "--profile 로 지정하라")
