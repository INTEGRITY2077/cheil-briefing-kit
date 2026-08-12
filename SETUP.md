# SETUP — Claude가 따라 하는 설치 매니저

> 이 문서는 사람을 위한 설명이자, Claude에게 주는 설치 지시서다.
> 사용자가 이 저장소 링크와 함께 "설치해줘"라고 하면 Claude는 아래를 순서대로 수행한다.
> 각 단계는 실패하면 멈추고 원인과 해결 방법을 보고한다 — 조용히 건너뛰지 않는다.

## 0. 헬스체크 — 진행 가능한 환경인지 스스로 판별한다

체크 결과를 통과/실패 표로 먼저 보여준 뒤 진행한다.

### 0-1. 세션 유형 판별
- **Bash·파일 도구(Read/Write)가 없는 세션**(claude.ai 웹 채팅 등)이면 설치가 불가능하다.
  이렇게 안내하고 멈춘다: "이 킷은 Claude Code에서 설치됩니다. Claude 데스크톱 앱의
  Claude Code 탭이나 터미널 `claude`에서 이 링크를 다시 붙여넣어 주세요.
  Claude Code가 없다면: https://claude.com/claude-code"
- Bash·파일 도구가 있으면 통과.

### 0-2. 실행 환경
- `python --version` — 3.10 이상. 없으면 https://www.python.org/downloads/ 안내 후 중단
- `git --version` — 없으면 zip 다운로드로 대체 가능하다고 표시
- 디스크 여유 1GB 이상 (오디오 산출물 누적 대비)
- 스케줄 도구 확인: scheduled-tasks MCP 또는 세션 크론(CronCreate) 중 무엇이 가능한지
  판별해 표에 적는다. 둘 다 없으면 "루틴 자동 실행 불가 — 수동 실행 모드로 설치"를 고지

### 0-3. 브라우저와 claude.ai 로그인 (아티팩트 배포에 필요)
- 앱 내장 브라우저(Claude_Browser)로 https://claude.ai 를 열어 **"Sign in"이 보이는지**로
  로그인 여부를 판별한다.
- 로그아웃 상태면: "브라우저 패널에서 claude.ai에 한 번 로그인해 주세요 — 공유 설정
  자동화에 필요합니다. 로그인은 본인이 직접 해야 하며 Claude는 비밀번호·인증코드를
  대신 입력하지 않습니다." 로그인 전에도 설치는 계속 가능하고, 배포 단계에서
  공유 켜기만 수동 안내로 강등된다고 표시한다.
- 내장 브라우저가 없으면 claude-in-chrome(크롬 확장) 여부를 확인하고, 둘 다 없으면
  "발행은 되지만 공유 설정은 매일 수동"이라고 고지한다.
- 로그인이 확인되면 이렇게 고지한다: "로그인은 이번 한 번이면 됩니다 — 내장 브라우저에
  세션이 유지되므로, 앞으로 매일의 공유 켜기·버전 고정·검증은 Claude가 이 안에서
  자동으로 합니다. 사용자의 크롬 브라우저는 건드리지 않습니다." 

### 0-4. TTS 경로 판별 — 사다리: supertonic → gemini → edge
- 기본값 **supertonic**(로컬 ONNX, 키·네트워크 불필요, Windows 네이티브 동작 확인):
  `python -m pip install supertonic soundfile` 가능한지 확인한다. 최초 1회 실행 때
  모델(~99MB)을 HuggingFace에서 자동 다운로드한다고 미리 안내한다.
  기본 보이스는 킷의 `voices/anchor-f1f2-30.json` — 합성 배속은 걸지 않는다(음절 씹힘,
  tts-guard pace 절). 청취 배속은 웹판 플레이어가 기본 1.3×.
- **gemini**(2순위, 감정·톤 지시가 필요할 때)를 원하면: "Google AI Studio
  (https://aistudio.google.com/apikey)에서 본인 키를 발급받아, 설치 후 `.env` 파일의
  `GEMINI_API_KEY=` 뒤에 직접 붙여넣어 주세요. 키는 채팅에 붙여넣지 마세요 —
  Claude는 키를 보거나 출력하지 않습니다." 라고 안내한다.
- **edge**(3순위 예비, 네트워크 필요·키 불필요): `pip show edge-tts`. 위 둘이 모두
  불가한 환경에서만 쓴다.

### 0-5. 사용자에게 묻는 것 (한 번에, 세 가지만)
1. 설치 위치 (기본값 제안: 사용자 문서 폴더 아래 `briefing-kit`)
2. TTS 엔진 — `supertonic`(기본, 키 불필요) / `gemini`(본인 키, 감정 지시) / `edge`(예비)
3. 루틴 시각 — **디폴트: 생성 07:00 / 배포 07:45.** 사용자가 원하는 시각을 물어
   합의한 값을 config.yaml `schedule`(daily 크론·publish_at)에 기록한다. 하드코딩하지
   않는다 — 이후에도 사용자가 요청하면 config 를 고쳐 재설정한다. 배포 시각은 생성
   시각보다 최소 30분 뒤를 권한다(게이트·음성 시간)

## 1. 저장소 받기
```
git clone https://github.com/INTEGRITY2077/cheil-briefing-kit <설치 위치>
```
git이 없으면 zip 다운로드로 대체한다.

## 2. 의존성
```
python -m pip install supertonic soundfile edge-tts requests pyyaml
```
gemini 선택 시 추가 설치는 없다 — `tools/make_audio_gemini.py` 는 표준 라이브러리
(urllib)로 REST 를 직접 호출하므로 google-genai 패키지가 필요 없다. `.env` 의
GEMINI_API_KEY 만 있으면 된다.
(supertonic 은 최초 실행 때 모델 ~99MB 를 자동 다운로드한다 — 0-4에서 이미 고지)

**선택 의존성 — 웹판 오디오 MP4(AAC 96k) 변환용**: `python -m pip install imageio-ffmpeg`
(설치 약 87MB, ffmpeg 바이너리 동봉이라 별도 ffmpeg 설치가 필요 없다.
`tools/embed_radio.py` 가 WAV/MP3 입력을 자동 변환하는 데 쓴다(D2) — 없으면
경고를 내고 WAV 원본 임베드로 강등되어 호가 10MB 를 넘고 첫 렌더가 느려진다.
2026-08-12 실측: 12.26MB WAV → 1.79MB MP4, 길이·표본율 동일)

## 3. 설정 생성
1. `config.example.yaml` → `config.yaml` 복사 후, 선택한 TTS 엔진과 시각을 반영한다.
2. gemini 선택 시: `.env.example` → `.env` 복사를 안내하고 **사용자가 직접** 키를 넣게 한다.
3. 원장(`okf/`)과 수집 커서(`profiles/*.yaml` 의 last_checked)는 **원작자 시드**다 —
   지우지 않는다. 첫 실행이 last_checked 이후의 새 사실을 자동으로 따라잡고,
   낡은 개념은 stale_after·SUPERSEDE 가 정리한다. 사용자에게 "원장은 시드에서
   출발하며 첫 호부터 최신으로 갱신된다"고 한 줄 안내한다.

## 4. 루틴 등록 — 현존 세션 우선
1. **1차: 세션 크론** — CronCreate로 합의된 생성 시각 3분 전(디폴트 06:57)에 `routine-SKILL.md` 실행을
   등록한다. 세션 크론은 7일 자동 만료라는 점을 사용자에게 고지하고, 만료 전 재등록을
   루틴 보고에 포함시킨다.
2. **예비: 스케줄드 태스크** — scheduled-tasks 도구가 있으면 같은 내용을 생성 시각 +7분(디폴트 07:07)에
   새 세션 태스크로도 등록한다. 이중 생산은 routine-SKILL의 0-a 단일 생산자 규칙이 막는다.
2b. **운영 구조를 사용자에게 설명한다** (등록 직후, 세 문장으로):
   ① "지금 이 세션이 루틴의 1차 실행자입니다 — 이 대화를 닫지 않고 두면 매일 같은
   세션에서 브리핑이 만들어집니다 (규칙·브라우저 로그인을 쥔 채로)."
   ② "이 세션이 닫혀 있는 날은 예비 태스크가 새 세션으로 대신 만듭니다 — 그때의
   기억은 대화가 아니라 파일(config·원장·routine-SKILL·CLAUDE.md)로 이어집니다."
   ③ "어느 쪽이든 그 시각에 이 컴퓨터와 Claude 앱이 켜져 있어야 합니다 — 꺼져 있던
   날의 호는 건너뛰고, 다음 실행이 원장 커서로 그 기간을 따라잡습니다." 
3. `routine-SKILL.md`의 「킷 위치」 절에 있는 `{{KIT_ROOT}}` 플레이스홀더를 실제 설치
   경로(절대경로)로 치환한다. 치환 후 `{{KIT_ROOT}}` 문자열이 파일에 남아 있으면 안 된다.
   (발행 이력은 `output/artifact-url-*.txt` 파일이 유일한 소스다 — 문서 안에 비우거나
   채울 URL 블록은 없다.)

## 5. 무인 실행 권한
설치 위치의 `.claude/settings.json`에 아래 허용 목록을 만든다 (이 프로젝트에만 적용):
```json
{
  "permissions": {
    "allow": [
      "Read", "Write", "Edit", "Glob", "Grep", "Artifact",
      "WebFetch", "WebSearch",
      "Bash(python:*)", "Bash(py:*)", "Bash(ls:*)", "Bash(cp:*)",
      "Bash(mv:*)", "Bash(mkdir:*)", "Bash(echo:*)", "Bash(cat:*)", "Bash(cd:*)",
      "Bash(git status:*)", "Bash(git add:*)", "Bash(git commit:*)",
      "Bash(git diff:*)", "Bash(git log:*)",
      "mcp__claude-in-chrome", "mcp__Claude_Browser", "mcp__scheduled-tasks",
      "CronCreate", "CronList",
      "PowerShell(Invoke-WebRequest:*)"
    ]
  }
}
```
`CronCreate`·`CronList` 는 세션 크론 7일 만료 전 재등록(4-1)이 무인으로 돌게 하기 위한
것이고, `PowerShell(Invoke-WebRequest:*)` 는 4b 배포 검증(공유 링크 실측 다운로드)용이다 —
빠지면 무인 아침 실행이 권한 프롬프트에서 정지한다. PowerShell 도구가 없는 환경
(macOS/Linux)이면 이 항목은 무시되고, 검증은 `Bash(python:*)` 로 커버되는
python urllib 로 대신한다.
`rm` 등 셸 파괴 명령은 의도적으로 제외한다. 단, 루틴에 삭제가 아예 없는 것은 아니다 —
루틴 8절의 보존 정리(`retention.audio_days`, 기본 30일 초과 오디오 삭제)가 매달
`Bash(python:*)` 로 수행된다. 사용자에게 이 삭제 범위(오디오 산출물, 30일 초과분)를
고지하고 동의를 받는다. 그 외의 파일 삭제는 루틴에 없다.
`git push` 도 제외한다 — 매일 루틴은 로컬 `output/` 에만 쓰고, 저장소 push 는
원작자·포크 전용이다. 포크에 밀어 올릴 일이 생기면 그때 사용자가 직접 승인한다.
사용자에게 고지할 것: 이 목록의 `Bash(python:*)` 는 **설치 위치의 파이썬 실행을 매일
아침 묻지 않고 승인**한다는 뜻이다. 목록을 만들기 전에 `tools/` 의 파이썬 파일 전부를
(개수는 `ls tools/*.py` 로 그때그때 센다 — 하드코딩하지 않는다) 훑어볼 기회를 준다.

## 6. 시험 실행
1. TTS 1회(기본 사다리): `python tools/make_audio_supertonic.py examples/sample-script.md output/audio/smoke-test.wav`
   — 소리 파일이 0바이트가 아니면 통과. supertonic 실패 시
   `python tools/make_audio.py examples/sample-script.md output/audio/smoke-test.mp3`(edge)로
   강등 확인하고 어느 단으로 통과했는지 보고에 남긴다
2. 루틴을 수동 1회 실행해 `output/web/YYYY-MM-DD.html` 생성 확인
3. Artifact 발행 → **발행 직후 Share "Anyone with the link" 켜기** (비공개 기본값 = 404 함정)
4. 발행 전 `templates/publish-checklist.md` A~E 전 항목 실행·기록

## 7. 설치 완료 보고
헬스체크 표 · 설치 위치 · TTS 엔진 · 루틴 등록 내역(크론 ID, 태스크 ID) · 시험 실행 결과 ·
운영 구조 요약(4절 2b의 세 문장: 이 세션이 1차 실행자 / 닫히면 예비가 파일 승계로 대행 /
그 시각에 컴퓨터·앱이 켜져 있어야 함) ·
사용자가 직접 해야 할 남은 일(.env 키 입력, 브라우저 로그인, 첫 공유 확인)을 한 화면으로 보고한다.
