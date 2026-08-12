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
  - 현재 판형(`.fseg.on`) 정확히 1개
  - 프레젠테이션 세그먼트 요구는 **당일 덱 URL 기록 파일이 있는 날만** 건다
    (`output/artifact-url-slides-YYYY-MM-DD.txt` 실존 여부로 판정 —
    routine 4c 는 덱을 '선택, 심층인 날만'으로 규정하므로, 덱을 만들지 않은
    표준/간략 호는 프레젠테이션 세그먼트 없이도 통과한다. 2026-08-12 수리:
    종전에는 무조건 실패라 routine 5 '종료코드 0 필수'와 4c '선택'이 서로를 배제했다)
      · 덱 기록 있음 → 세그먼트(`.fseg`) ≥ 2 + 프레젠테이션 세그먼트 필수
      · 덱 기록 없음 → 세그먼트 ≥ 1, 프레젠테이션 부재는 안내만
  - `a.fseg` 는 href 필수 + claude.ai 아티팩트 절대 URL
  - 링크 없는 라벨은 경고 — 아카이브 호의 「PPTX 배포본」 라벨만 허용된다
    (routine-SKILL 4c). `--archive` 를 주면 경고도 내지 않는다

`--check-links` (발행·공유 완료 이후 전용 — routine-SKILL 4b 검증 절):
  기본 실행은 위의 정적 검사만 한다. 이 플래그를 주면 각 a.fseg href 를
  익명 GET(쿠키 없음, User-Agent 명시, timeout 10초)으로 실제로 열어 본다.
    ① 익명으로 열리는가 — 아니면 공유 OFF 의심 (2026-08-11 실측: 발표판이
       private 인 채로 남아 독자에게 404 였는데 정적 검사는 통과했다)
    ② 응답에 그 호의 제목 문자열이 있는가 — 제목은 `--title "..."` 이
       우선이고, 없으면 검사 대상 HTML 의 <title> 에서 추출한다. 제목 전체가
       없으면 「—」 앞의 헤드라인 부분으로도 본다 (checklist A4: 덱 표지
       헤드라인 = 웹판 헤드라인 — 덱 아티팩트에는 웹판 제목 접미가 없다).

  판정 경로 (2026-08-12 실측 기반):
  - claude.ai/code/artifact/<uuid> 페이지는 셸이라 **없는 uuid 도 200 이 뜬다**
    (실측: 공유본·무작위 uuid 모두 동일 14KB 셸). 그래서 셸이 실제로 부르는
    `claude.ai/api/frame/<uuid>` 를 익명 GET 한다 — 공유 ON 이면 200 +
    `"mode":"public"` + 아티팩트 제목 JSON, 공유 OFF/부재면 401 unauthorized.
  - 제목이 JSON 에 없으면 응답의 ver 로 본문 frame
    (`https://<uuid>.frame.claudeusercontent.com/_f/<ver>`)을 한 단계만
    따라가 본문에서 확인한다.
  - claude.ai 아티팩트 형식이 아닌 URL 은 일반 경로: 그 URL 을 직접 GET 해
    200 + 제목 확인, 응답에 frame URL 이 보이면 한 단계 따라간다.
  표준라이브러리 urllib.request 만 쓴다 — 새 의존성 없음. UA 는 통상 브라우저
  문자열을 쓴다 (실측: 비정상 UA 는 CDN 이 403 으로 거른다 — 판정이 오염된다).

실패 시 종료코드 1. 경고만 있으면 0.
"""
import io, os, re, sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")  # cp949 콘솔에서도 죽지 않게 (stderr 포함 — USAGE 모지바케 방지)

USAGE = ("사용법: python tools/check_formats.py <웹판.html> "
         "[--expect-deck|--no-deck] [--archive] [--check-links] [--title \"호 제목\"]")

BAR = re.compile(r"""<div[^>]*class\s*=\s*["'][^"']*\bfmtbar\b[^"']*["'][^>]*>(.*?)</div>""", re.S | re.I)
SEG = re.compile(r"""<(a|span)\b([^>]*\bfseg\b[^>]*)>(.*?)</\1>""", re.S | re.I)
HREF = re.compile(r"""href\s*=\s*["']([^"']*)["']""", re.I)
ARTIFACT_URL = re.compile(r"^https://claude\.ai/[^\s\"']+$", re.I)
DECK_WORDS = ("프레젠테이션", "발표", "슬라이드", "덱", "PPTX")


def text_of(fragment):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment)).strip()


def slides_record_path(html_path):
    """웹판 파일명의 날짜로 당일 덱 URL 기록 파일 경로를 유도한다.
    output/web/YYYY-MM-DD.html → output/artifact-url-slides-YYYY-MM-DD.txt"""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(html_path))
    if not m:
        return None
    root = os.path.dirname(os.path.dirname(os.path.abspath(html_path)))
    return os.path.join(root, f"artifact-url-slides-{m.group(1)}.txt")


# --- 링크 실개통 검사 (--check-links) ------------------------------------
# 아티팩트 페이지가 본문을 싣는 iframe 호스트. JS 안에 \/ 이스케이프로 들어
# 있을 수 있어 두 형태를 다 잡고, 찾은 뒤 unescape 한다. (일반 URL 폴백용)
FRAME_URL = re.compile(
    r"https:(?:\\/\\/|//)[A-Za-z0-9.-]+\.frame\.claudeusercontent\.com(?:\\/|/)[^\s\"'<>\\]*"
)
TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
# claude.ai 아티팩트 URL → uuid (셸 200 함정을 피해 /api/frame 으로 판정한다)
CODE_ARTIFACT = re.compile(
    r"^https://claude\.ai/(?:code/artifact|public/artifacts)/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I)
# 통상 브라우저 UA — 비정상 UA 는 CDN 이 403 으로 걸러 판정이 오염된다 (2026-08-12 실측)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ANON_HEADERS = {"User-Agent": UA, "Accept": "*/*",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
# /api/frame 은 셸 JS 가 붙이는 X-Frame-* 헤더가 없으면 무조건 404 다 (2026-08-12 실측:
# 헤더를 붙이면 공유 ON → 200 + "mode":"public" JSON, 공유 OFF/부재 → 401 unauthorized)
FRAME_API_HEADERS = {"X-Frame-CP": "go", "X-Frame-Platform": "web",
                     "X-Frame-Surface": "standalone"}


def fetch_anon(url, extra_headers=None):
    """익명 GET — 쿠키 없음, UA 명시, timeout 10초. (HTTP코드, 본문) 반환.

    표준라이브러리만 쓴다. urllib 은 쿠키 저장소를 따로 달지 않는 한 쿠키를
    보내지 않으므로 그 자체로 '로그아웃 독자' 시뮬레이션이 된다.
    """
    import urllib.request, urllib.error
    headers = dict(ANON_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # URLError·timeout 등 — 판정 불가도 통과가 아니다
        return None, str(e)


def title_probes(title):
    """제목 판정 문자열 후보 — 제목 전체 + 「—」류 구분자 앞의 헤드라인.

    checklist A4: 덱 표지 헤드라인 = 웹판 헤드라인. 덱 아티팩트 제목·본문에는
    웹판 제목의 접미(「— 오늘의 제일기획 뉴스 MM.DD」)가 없으므로 헤드라인
    부분으로도 그 호의 것인지 판정한다 (2026-08-12 실측).
    """
    probes = [title]
    for sep in ("—", "–", "|"):
        if sep in title:
            head = title.split(sep)[0].strip()
            if len(head) >= 4 and head not in probes:
                probes.append(head)
    # 덱은 헤드라인 구두점을 재조판하기도 한다 (2026-08-12 실측: 웹판 「144만대, 역대
    # 최다」 → 덱 표지 「144만대 — 역대 최다」). 쉼표 앞 첫 절도 후보로 삼되,
    # 8자 이상일 때만 — 너무 짧은 조각은 다른 호와 구분이 안 된다
    for p in list(probes):
        if "," in p:
            first = p.split(",")[0].strip()
            if len(first) >= 8 and first not in probes:
                probes.append(first)
    return probes


def check_link_open(label, url, title):
    """한 링크를 익명으로 열어 ①공유 개통 ②호 제목 포함을 판정. 오류 문자열 또는 None."""
    probes = title_probes(title)
    m = CODE_ARTIFACT.match(url)
    if m:
        # claude.ai 아티팩트: 셸 페이지는 없는 uuid 도 200 이라(실측) /api/frame 으로 판정
        uuid = m.group(1).lower()
        code, body = fetch_anon(f"https://claude.ai/api/frame/{uuid}?via=user_open",
                                FRAME_API_HEADERS)
        if code is None:
            return f"[{label}] 링크 검사 자체가 실패했다 (네트워크: {body[:80]}) — 판정 불가는 통과가 아니다"
        if code != 200:
            return f"[{label}] 링크가 익명으로 열리지 않는다(HTTP {code}) — 공유 OFF 의심"
        if any(p in body for p in probes):
            return None
        # 제목이 메타 JSON 에 없으면 본문 frame 을 ver 로 유도해 한 단계만 따라간다
        vm = re.search(r'"ver"\s*:\s*"([^"]+)"', body)
        if vm:
            fcode, fbody = fetch_anon(
                f"https://{uuid}.frame.claudeusercontent.com/_f/{vm.group(1)}")
            if fcode == 200 and any(p in fbody for p in probes):
                return None
            if fcode != 200:
                return f"[{label}] 본문 frame 이 익명으로 열리지 않는다(HTTP {fcode}) — 공유 OFF 의심"
        return f"[{label}] 익명 응답에 호 제목 「{probes[-1]}」 이 없다 — 다른 호가 걸렸거나 옛 버전 핀 의심"

    # 일반 URL: 직접 GET → 200 + 제목, 없으면 응답 속 frame URL 을 한 단계 따라간다
    code, body = fetch_anon(url)
    if code is None:
        return f"[{label}] 링크 검사 자체가 실패했다 (네트워크: {body[:80]}) — 판정 불가는 통과가 아니다"
    if code != 200:
        return f"[{label}] 링크가 익명으로 열리지 않는다(HTTP {code}) — 공유 OFF 의심"
    if any(p in body for p in probes):
        return None
    fm = FRAME_URL.search(body)
    if fm:
        fcode, fbody = fetch_anon(fm.group(0).replace("\\/", "/"))
        if fcode == 200 and any(p in fbody for p in probes):
            return None
        if fcode != 200:
            return f"[{label}] 본문 frame 이 익명으로 열리지 않는다(HTTP {fcode}) — 공유 OFF 의심"
    return f"[{label}] 익명 응답에 호 제목 「{probes[-1]}」 이 없다 — 다른 호가 걸렸거나 옛 버전 핀 의심"


def parse_args(argv):
    """수동 파싱 — --title 은 값을 하나 먹는다. (파일들, archive, check_links, title, deck) 반환.

    deck: True(--expect-deck) / False(--no-deck) / None(플래그 없음 — 파일 추론 강등).
    """
    files, archive, check_links, title, deck = [], False, False, None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--archive":
            archive = True
        elif a == "--check-links":
            check_links = True
        elif a == "--expect-deck":
            deck = True
        elif a == "--no-deck":
            deck = False
        elif a == "--title":
            i += 1
            if i >= len(argv):
                sys.exit(USAGE)
            title = argv[i]
        elif a.startswith("--"):
            sys.exit(f"모르는 옵션: {a}\n{USAGE}")
        else:
            files.append(a)
        i += 1
    return files, archive, check_links, title, deck


def main():
    args, archive, check_links, cli_title, deck_flag = parse_args(sys.argv[1:])
    if not args or not os.path.exists(args[0]):
        sys.exit(USAGE)
    html = io.open(args[0], encoding="utf-8").read()

    bar = BAR.search(html)
    if not bar:
        print("실패: .fmtbar 가 없다 — 판형 바 없이 발행하면 다른 판형으로 갈 문이 없다")
        sys.exit(1)

    segs = [(tag.lower(), attrs, text_of(body)) for tag, attrs, body in SEG.findall(bar.group(1))]
    errors, warnings = [], []

    # 덱 요구의 정본은 **의도**다 — 루틴이 EVAL 판정(심층=덱 생산)에 따라
    # --expect-deck / --no-deck 을 넘긴다 (이슈 #5: 파일 실존 추론은 '덱을 만들고
    # 기록을 빠뜨린 날'을 '안 만든 날'로 오독해 08.11 사고 재발에 눈을 감는다).
    # 플래그가 없으면 종전 파일 추론으로 강등하되 그 사실을 출력에 남긴다.
    if deck_flag is not None:
        deck_expected = deck_flag
    else:
        srec = slides_record_path(args[0])
        deck_expected = bool(srec and os.path.exists(srec))
        print("안내: --expect-deck/--no-deck 없음 — 덱 URL 기록 파일 실존으로 강등 추론"
              f" ({'있음' if deck_expected else '없음'}). 놓친 날과 안 만든 날을 구분하지"
              " 못하는 판정이니 루틴에서는 플래그를 명시하라 (routine 5)")

    min_segs = 2 if deck_expected else 1
    if len(segs) < min_segs:
        errors.append(f"세그먼트가 {len(segs)}개다 — 최소 {min_segs}개"
                      + (" (라디오·프레젠테이션)" if deck_expected else ""))

    on = [s for s in segs if re.search(r"\bon\b", s[1])]
    if len(on) != 1:
        errors.append(f"현재 판형(.fseg.on)이 {len(on)}개 — 정확히 1개여야 한다")

    deck = [s for s in segs if any(w in s[2] for w in DECK_WORDS)]
    if not deck:
        if deck_expected:
            errors.append("프레젠테이션 세그먼트가 없다 — 덱을 발행했어도 독자에겐 없는 것과 같다"
                          " (이 호는 덱 생산 호로 판정됨)")
        else:
            print("안내: 덱 없는 호로 판정 — 프레젠테이션 세그먼트 요구를 걸지 않는다"
                  " (routine 4c — 덱은 심층인 날만)")

    links = []  # --check-links 대상: (라벨, URL)
    for tag, attrs, label in segs:
        if tag == "a":
            m = HREF.search(attrs)
            url = m.group(1).strip() if m else ""
            if not url:
                errors.append(f"[{label}] a.fseg 인데 href 가 없다 — 죽은 라벨")
            elif not ARTIFACT_URL.match(url):
                errors.append(f"[{label}] href 가 claude.ai 절대 URL 이 아니다: {url[:60]}")
            else:
                links.append((label, url))
        elif tag == "span" and not re.search(r"\bon\b", attrs) and not archive:
            warnings.append(f"[{label}] 링크 없는 라벨 — 아카이브 호의 PPTX 배포본이면 --archive")

    # 링크 실개통 검사 — 정적 검사를 통과한 링크만, 플래그가 있을 때만 (4b 발행·공유 완료 후)
    if check_links and not errors:
        title = cli_title
        if not title:
            tm = TITLE_TAG.search(html)
            title = text_of(tm.group(1)) if tm else ""
        if not title:
            errors.append("--check-links 인데 호 제목을 모른다 — --title \"...\" 을 주거나 HTML 에 <title> 을 넣어라")
        else:
            for label, url in links:
                err = check_link_open(label, url, title)
                if err:
                    errors.append(err)
                else:
                    print(f"링크 개통: [{label}] 익명 200 + 제목 확인")

    for w in warnings:
        print("경고:", w)
    for e in errors:
        print("실패:", e)
    if errors:
        sys.exit(1)
    suffix = " · 익명 개통 확인" if check_links else ""
    print(f"통과: 판형 세그먼트 {len(segs)}개 · 현재 판형 「{on[0][2]}」 · 링크 전부 유효{suffix}")


if __name__ == "__main__":
    main()
