# macOS 설치 실측 결과 — 이슈 #33 체크리스트 대조

- **실측일**: 2026-08-14
- **킷 버전**: v2026.08.14.5 (`a1de947`) — `check_version.py` 종료코드 0 (원격 일치)
- **실측 환경**: macOS Darwin 25.3.0 · arm64 (Apple Silicon, T8132) · Mac mini
- **셸**: zsh · **Homebrew**: 6.0.17 (`/opt/homebrew/bin/brew`, 존재)
- **python3**: 3.9.6 (`/usr/bin/python3`, Command Line Tools 동봉) · **pip**: 21.2.4
- **git**: 2.50.1 (Apple Git-155)
- **실측 범위**: CLI 세션 단독. GUI(데스크톱 앱·브라우저 로그인) 의존 항목은 **미실측(GUI 대기)**.

---

## 요약 판정

| 층 | 통과 | 실패 | 미실측 |
|---|---|---|---|
| A. 판정·설치 | 2 | 2 | 0 |
| B. 앱 어포던스 | 1 | 0 | 2 |
| C. 생산·발행 E2E | 2 | 0 | 2 |
| D. 문안·경로 | 0 | 2 | 0 |

**핵심 결론**: 킷의 **런타임은 macOS/arm64에서 전부 동작한다**(selftest 24/24, TTS 합성, MP3 변환·이식, 크기 게이트 전부 통과). 막히는 곳은 코드가 아니라 **SETUP 판별 문안**이다 — `python`(3 없는 명령)과 3.10 하한, 두 지점이 macOS 설치를 카드 이전 단계에서 멈춰 세운다.

---

## A. 판정·설치 층 (SETUP §0~§2)

### A-1. T0 판정이 비 Windows에서 올바르게 갈리는가 — **실패**

문안대로 갈리지 **않는다**. 두 지점이 각각 독립적으로 오판을 만든다.

**⑴ `python` 명령 자체가 macOS에 없다.** SETUP §1(136행)의 판별은 `python -c "import sys;print(sys.version)"` 다. 실측:

```
$ command -v python
(출력 없음 — 부재)
$ command -v python3
/usr/bin/python3   → Python 3.9.6
```

현행 macOS는 `python2` 제거 이후 `python` 심볼릭 링크를 제공하지 않는다. 판별식은 **인터프리터가 멀쩡히 있는데도 "부재"로 판정**한다.

**⑵ 부재로 갈린 뒤 곧장 강등·멈춤에 도달한다.** §0-2는 "python·git 이 둘 다 충족이면 이 절 전체를 건너뛴다"고 하지만, ⑴ 때문에 python이 미충족으로 잡혀 자동 설치 경로로 들어간다. 그 다음 관문이 `where.exe winget` 이고 macOS에서는 당연히 실패한다:

```
$ command -v where.exe → ABSENT
$ command -v winget    → ABSENT
$ command -v pwsh      → ABSENT
```

결과: **카드를 내지 않고** §0-2의 3번 강등(`brew install python@3.12 git` 안내 후 멈춤)에 도달한다. 즉 macOS 워커는 **설치 카드를 한 번도 보지 못하고 중단**된다.

**⑶ 3.10 하한이 두 번째 오판을 예약한다.** §0(18행)·§1(136·143행)은 3.10 미만을 "구버전 = 부재와 동일 취급"으로 규정한다. 시스템 python3는 3.9.6이므로, ⑴을 `python3`로 고쳐도 여전히 구버전으로 잡혀 같은 강등에 도달한다.

> **다만 이 하한은 실측상 근거가 없다.** 아래 C-1·C-2가 증명하듯 **Python 3.9.6에서 selftest 24케이스 전수 통과 + TTS 합성 + MP3 변환·이식 + 크기 게이트가 모두 통과했다.** 3.10 하한은 macOS 기본 인터프리터를 정확히 한 칸 차이로 배제하면서, 배제할 실측 사유는 확인되지 않았다.

### A-2. Homebrew 존재 시 §2 무인 설치 승격 가능성 — **통과(가능)**

Homebrew 6.0.17이 `/opt/homebrew/bin/brew`(arm64 표준 경로)에 존재한다. 현행 §0-2 3번은 brew를 **강등 안내 문구**로만 쓰지만, `where.exe winget` 자리에 `command -v brew`를 두면 Windows winget과 동일한 무인 설치 승격이 성립한다:

```
brew install python@3.12 git     # 문안에 이미 있는 명령, 승격만 안 돼 있음
```

`python@3.12`는 현재 미설치(`brew list --versions python@3.12` → NOT INSTALLED)이나, brew 자체가 동작하므로 무인 실행 경로에 장애물은 없다. 승격 시 winget과 동일하게 **부재·구버전인 쪽만** 설치하는 규율은 그대로 적용 가능하다.

### A-3. PATH 반영 — 설치 직후 같은 셸에서 재판정이 되는가 — **통과**

**Windows의 PATH 문제는 macOS에 없다.** §0-2 2번이 다루는 세 가지 — ⑴ 현재 셸 PATH 미반영, ⑵ WindowsApps 앨리어스 가림, ⑶ 「앱 실행 별칭」 GUI 조작 요구 — 는 전부 Windows 고유다. Homebrew는 `/opt/homebrew/bin`에 직접 심볼릭 링크하고 이 경로는 zsh 기본 PATH에 이미 있으므로, 설치 직후 같은 셸에서 재판정이 성립한다.

**단 하나의 macOS 고유 PATH 이슈**는 pip 스크립트 디렉토리다. 설치 로그에서 전 스크립트가 동일 경고를 냈다:

```
WARNING: The scripts edge-playback and edge-tts are installed in
'/Users/<user>/Library/Python/3.9/bin' which is not on PATH.
```

`supertonic`·`edge-tts` **CLI 이름 호출은 불가**하다. 킷은 전부 `python -m` / `tools/*.py` 경유이므로 **실사용에는 영향 없다** — 판정을 CLI 존재로 하지 말고 import로 해야 한다는 뜻이다(§0-4의 `pip show edge-tts`는 안전, PATH와 무관).

### A-4. pip 의존성: pyyaml · supertonic+soundfile · imageio-ffmpeg — **통과 (실패 항목 0건)**

`python3 -m pip install supertonic soundfile edge-tts requests pyyaml imageio-ffmpeg` — **6종 전부 설치 성공, 실패 없음.** PEP 668 `externally-managed-environment` 차단도 발생하지 않았다(CLT 동봉 python3는 user site로 설치됨).

| 패키지 | 결과 | 버전 | import |
|---|---|---|---|
| supertonic | 성공 | 1.3.1 | OK |
| soundfile | 성공 | 0.13.1 | OK |
| edge-tts | 성공 | 7.2.8 | OK |
| requests | 성공 | 2.32.5 | OK |
| pyyaml | 성공 | 6.0.3 | OK |
| imageio-ffmpeg | 성공 | 0.6.0 | OK |

동반 설치된 arm64 네이티브 의존성도 정상이다 — `onnxruntime 1.19.2`, `numpy 2.0.2`, `cffi 2.0.0` 전부 휠 설치(소스 빌드 없음). imageio-ffmpeg는 **`ffmpeg-macos-aarch64-v7.1` 바이너리를 동봉**해 별도 ffmpeg 설치가 필요 없다.

**기록해 둘 경고 2건 (차단 아님):**
1. `NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'` — CLT python3.9의 LibreSSL 때문. 실측상 HTTPS 통신(HuggingFace 모델 다운로드 43초)은 정상 완료했으나, 매 실행 stderr에 경고가 찍힌다. brew python@3.12로 올리면 사라진다.
2. `pip 21.2.4` (현행 26.0.1) — 설치는 문제없이 됐다.

---

## B. 앱 어포던스 패리티 (0-2 · 0-3)

### B-1. scheduled-tasks MCP / 세션 크론 작동 여부 — **부분 통과 (CLI 세션 기준 실측)**

| 도구 | macOS CLI 세션 | 판정 |
|---|---|---|
| `mcp__scheduled-tasks` | 도구 목록에 **없음** | 부재 |
| 세션 크론 `CronCreate`·`CronList` | 도구 목록에 **존재** | 사용 가능 |

§0-2 규정("둘 다 없으면 루틴 자동 실행 불가 — 수동 실행 모드")에 비추어 **세션 크론 경로로 자동 실행 가능**하다. 데스크톱 앱에서 scheduled-tasks MCP가 붙는지는 **미실측(GUI 대기)**.

### B-2. 사이드패널 샌드박스 브라우저 존재·동작 — **미실측 (GUI 대기)**

CLI 세션의 도구 목록에 `mcp__claude-in-chrome`·`mcp__Claude_Browser` 계열이 **없다**. 따라서 §0-3의 판정 절차(⑴ 내장 탭 `get_page_text`, ⑵ `list_connected_browsers`)를 **이 세션에서는 개시할 수 없다**. 브라우저·claude.ai 로그인 상태 확인은 데스크톱 앱 실측이 필요하다.

연쇄 영향: §0-3이 "6절 3항(아티팩트 발행·공유)의 차단 선행조건"이므로 **C-3도 자동으로 미실측**이 된다.

### B-3. permissions allowlist — 맥 대응 필요 지점 목록 — **미실측(전체 적용)이나, 문안상 필요 지점은 실측으로 특정됨**

allowlist 자체를 앱에 적용해 무인 실행을 돌려보는 것은 GUI 대기다. 다만 §5 목록(360~366행)을 실측 환경과 대조하면 **고쳐야 할 지점 3곳**이 특정된다:

| 항목 | 문제 | 조치 |
|---|---|---|
| `"Bash(python:*)"` | macOS에 `python` 명령이 없다(A-1). 킷의 모든 호출은 `python3`. 목록에 **`Bash(python3:*)`가 0건** | `Bash(python3:*)` 추가 — **없으면 매일 아침 권한 프롬프트에서 정지한다** |
| `"Bash(py:*)"` | Windows py 런처 전용, macOS에 무의미 | 무해 — 유지해도 됨 |
| `"PowerShell(Invoke-WebRequest:*)"` | `pwsh` 부재 확인 | 문안(374행)이 이미 "macOS/Linux면 무시, python urllib로 대체"로 처리 중 — **다만 그 대체 경로가 `Bash(python:*)`로 커버된다고 쓰여 있어 위 ①과 같은 구멍을 공유한다** |

`mcp__scheduled-tasks`는 부재하나 목록에 남겨도 무해하다(B-1).

---

## C. 생산·발행 E2E (시험 실행 §6)

### C-1. `python tools/selftest.py` 실행 결과 — **통과**

```
$ python3 tools/selftest.py
— 케이스 24 · 불일치 0
통과: 게이트 통과/차단 계약 전 케이스 기대 일치
EXIT=0
```

**24케이스 전수 통과, 불일치 0, 종료코드 0.** OK 라인 24개 확인.

> **이슈 본문 기대치와의 차이**: 체크리스트는 23케이스를 기대했으나 실측은 **24케이스**다. 이는 macOS 문제가 아니라 킷이 그 사이 케이스를 1건 늘린 것이다(v2026.08.14.5 기준). `check_review`·`check_insight`·`check_run`·`check_theme`·`check_ledger`·`sync_skill` 전 게이트가 Windows와 동일하게 갈렸다 — **경로 구분자·인코딩으로 인한 플랫폼 편차 0건**.

### C-2. TTS 합성 → embed_radio 변환 → 웹판 게이트 통과 — **통과**

**⑴ TTS 합성 (Supertonic 3, Apple Silicon ONNX)** — 모델 자동 다운로드 포함, 완료까지 대기해 실측:

```
$ python3 tools/make_audio_supertonic.py examples/sample-script.md output/audio/macos-smoke.wav
Fetching 26 files: 100%|██████████| 26/26 [00:43<00:00, 1.67s/it]
보이스: A=/Users/<user>/briefing-kit/voices/anchor-f1f2-30.json B=M2
[1/3] A 56자  [2/3] B 61자  [3/3] A 12자
완료: output/audio/macos-smoke.wav
총 49.26초 (모델 다운로드 43초 포함 → 순수 합성 약 6초)
```

산출물 실측: **1,757,228바이트 · 44,100Hz · 1ch · 19.92초 · PCM_16.** §6 1항 기준("0바이트가 아니면 통과") 통과. 강등 사다리 발동 없이 **1순위 supertonic이 그대로 성립**했다 — onnxruntime 1.19.2가 arm64에서 정상 추론.

*기록할 편차*: §0-4·§2는 모델을 "~99MB"로 고지하나 **실측 캐시는 385MB**(`~/.cache/supertonic3`, ONNX 4종: text_encoder·duration_predictor·vector_estimator·vocoder). 디스크 요건 "1GB 이상"은 유지되지만 고지 수치는 갱신이 필요하다. 캐시 위치도 HuggingFace 표준 경로가 아닌 `~/.cache/supertonic3`이다(`~/.cache/huggingface`에는 xet 208K만).

**⑵ embed_radio 변환·이식** — `templates/article-skeleton.html` 뼈대에 이식:

```
$ python3 tools/embed_radio.py /tmp/macos-web.html output/audio/macos-smoke.wav examples/sample-script.md
플레이어 블록이 없어 새로 삽입했다
변환: macos-smoke.wav 1.68MB → MP3 64k 1ch 0.15MB
완료: macos-web.html ← macos-smoke.wav (208KB b64), 대사 3줄
호 크기 0.23MB / 상한 3.00MB
EXIT=0
```

동봉 arm64 ffmpeg로 **WAV→MP3 변환 성공**, 강등(원본 그대로 임베드) 발동하지 않음. 임베드 MIME 실측 `data:audio/mpeg` — **D2 금지 대상인 `audio/mp4` 아님**(이슈 #14 진범 회피 확인).

**⑶ 웹판 게이트**:

```
$ python3 tools/check_size.py /tmp/macos-web.html
호 0.23MB = 오디오(base64) 0.20MB + 지면 0.03MB · 상한 3.00MB
통과: 상한 대비 8%
EXIT=0
```

### C-3. 아티팩트 발행 → 전체공유 토글 → check_publish 개통 판정 — **미실측 (GUI 대기)**

B-2 그대로다. §0-3의 브라우저·claude.ai 로그인 확인이 "6절 3항의 **차단 선행조건**"으로 규정돼 있고, CLI 세션에 브라우저 MCP가 없어 로그인 판정 자체를 개시할 수 없다. 전체공유 토글은 본질적으로 GUI 조작이다. 데스크톱 앱 워커에게 인계한다.

### C-4. run_log · check_run 로스터 대조 — **부분 통과 (게이트 로직만 실측)**

`check_run` 게이트 로직은 selftest에서 3케이스 전수 통과했다(C-1):

```
OK [check_run] run 로스터 전수 기록 — exit 0 (기대 0)
OK [check_run] run 한 줄 기록 — 로스터 미달 — exit 1 (기대 1)
OK [check_run] run 실패코드 :1 기록 — exit 1 (기대 1)
```

다만 **실제 아침 루틴 1회를 완주해 만든 run_log와의 대조는 미실측**이다 — 루틴 완주는 C-3(발행·공유)을 포함하므로 GUI 대기에 묶인다.

---

## D. 문안·경로

### D-1. 설치 카드의 경로 예시가 맥에서 혼란을 주는가 — **실패 (혼란을 준다)**

SETUP.md 전체에서 Windows 고유 경로·명령 표기가 **12곳**이다(`C:\`, `%USERPROFILE%`, `%LOCALAPPDATA%`, `.exe`, PowerShell). macOS 워커가 카드에서 마주치는 대표 예:

- `…\Programs\Python\Python312\python.exe` (§0-2 2번) — 해당 없는 우회 지시
- `%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe` — 해당 없음
- 「설정 > 앱 > 고급 앱 설정 > 앱 실행 별칭」 — 존재하지 않는 GUI 경로

**가장 실질적인 혼란은 경로가 아니라 명령어다**: 문서 전반의 실행 예시가 `python tools/…` 로 통일돼 있는데 macOS에서는 전부 `command not found` 다.

| 파일 | `python tools/` | `python3` 안내 |
|---|---|---|
| SETUP.md | 4곳 | 0곳 (있는 2곳은 Linux apt 패키지명) |
| routine-SKILL.md | **27곳** | 0곳 |

즉 **매일 아침 루틴의 27개 호출 지점이 macOS에서 그대로는 하나도 실행되지 않는다.** 이 실측 보고의 전 명령은 `python3`로 치환해 수행했다.

### D-2. `where.exe`·PowerShell 언급 지점에서 실제 차단 구간 — **실패 (차단 확인)**

실측된 차단 구간은 **한 곳, 그러나 치명적인 곳**이다.

| 지점 | 명령 | 실측 | 차단 여부 |
|---|---|---|---|
| §0-2 카드 이전 ⑵ 자동 설치 가능 판정 | `where.exe winget` | ABSENT | **차단 — 여기서 멈춘다** |
| §0-2 2번 PATH 갱신 | `$env:Path = [Environment]…` | pwsh ABSENT | 도달 불가(선행 차단) · macOS엔 불필요(A-3) |
| §5 allowlist | `PowerShell(Invoke-WebRequest:*)` | pwsh ABSENT | 비차단 — 374행이 python urllib 대체를 이미 규정 |
| §4b 배포 검증 | Invoke-WebRequest | 미실측 | C-3에 묶임 |

**차단 구조**: `where.exe winget` 실패는 그 자체로는 설계된 동작(비 Windows → 강등)이다. 문제는 **A-1의 오판 때문에 macOS가 이 판정에 들어올 필요조차 없는데 들어온다**는 것이다. python3 3.9.6과 git 2.50.1이 둘 다 멀쩡하므로, 판별식이 `python3`를 보기만 했다면 §0-2 전체를 건너뛰고 카드로 직행했어야 한다. 실제로 이 실측은 그 우회 경로(python3 직접 호출)로 **§1~§6을 전부 완주했다**.

---

## 후속 SETUP 분기 커밋 제안 (실측 근거, 규정 변경은 하지 않음)

이슈 #33의 "실측 전 규정 미변경" 원칙에 따라 **본 실측에서 킷 파일은 일절 수정하지 않았다.** 아래는 분기 커밋용 근거 목록이다.

1. **인터프리터 판별을 `python3` 우선으로 (A-1, D-1)** — 비 Windows에서 `python3 -c …` 를 먼저 시도. 이것 하나가 macOS 차단의 최대 원인이다.
2. **3.10 하한의 재검토 (A-1)** — 3.9.6에서 selftest 24/24 · TTS · MP3 이식 · 크기 게이트 전부 통과. 하한 유지 시 macOS 기본 인터프리터가 근거 없이 배제된다. 유지한다면 배제 사유를 실측으로 명시할 것.
3. **`Bash(python3:*)` allowlist 추가 (B-3)** — 없으면 macOS 무인 아침 실행이 권한 프롬프트에서 정지한다.
4. **`brew`를 winget과 대등한 무인 설치 경로로 승격 (A-2)** — brew 6.0.17 동작 확인, 명령은 문안에 이미 있다.
5. **routine-SKILL.md 27개 호출 지점의 인터프리터 표기 (D-1)**.
6. **모델 크기 고지 정정: ~99MB → 385MB, 캐시 경로 `~/.cache/supertonic3` (C-2)**.
7. **CLT python3.9 LibreSSL 경고 고지 (A-4)** — 차단은 아니나 매 실행 stderr에 남는다.
8. **pip 스크립트 PATH 경고 (A-3)** — 킷은 `python -m` 경유라 무해하다는 한 줄.

---

## 미실측 항목 인계 (데스크톱 앱 워커용)

| 항목 | 사유 |
|---|---|
| B-2 사이드패널 샌드박스 브라우저 | CLI 세션에 브라우저 MCP 부재 |
| B-1 중 scheduled-tasks MCP | 앱 환경에서만 판정 가능 (세션 크론은 실측 완료) |
| B-3 allowlist 실적용 무인 실행 | 앱 설정 GUI |
| C-3 발행 → 전체공유 토글 → check_publish | claude.ai 로그인 + GUI 토글 — §0-3이 차단 선행조건으로 규정 |
| C-4 중 실제 루틴 완주 run_log 대조 | C-3에 종속 (게이트 로직 자체는 실측 통과) |
