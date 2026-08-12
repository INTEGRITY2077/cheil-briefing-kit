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

### 0-4. TTS 경로 판별
- 기본값 **edge**(무료·키 불필요)로 항상 동작 가능함을 확인한다 (`pip show edge-tts` 또는 설치 예정 표시)
- **gemini**(음질 우수)를 원하면: "Google AI Studio(https://aistudio.google.com/apikey)에서
  본인 키를 발급받아, 설치 후 `.env` 파일의 `GEMINI_API_KEY=` 뒤에 직접 붙여넣어 주세요.
  키는 채팅에 붙여넣지 마세요 — Claude는 키를 보거나 출력하지 않습니다." 라고 안내한다.
  키가 없어도 config의 `on_missing_key: edge` 강등으로 동작한다.

### 0-5. 사용자에게 묻는 것 (한 번에, 세 가지만)
1. 설치 위치 (기본값 제안: 사용자 문서 폴더 아래 `briefing-kit`)
2. TTS 엔진 — `edge`(기본) / `gemini`(본인 키)
3. 루틴 시각 — 기본 06:57 생성 / 07:45 배포

## 1. 저장소 받기
```
git clone https://github.com/INTEGRITY2077/cheil-briefing-kit <설치 위치>
```
git이 없으면 zip 다운로드로 대체한다.

## 2. 의존성
```
python -m pip install edge-tts requests pyyaml
```
gemini 선택 시 추가로: `python -m pip install google-genai`

## 3. 설정 생성
1. `config.example.yaml` → `config.yaml` 복사 후, 선택한 TTS 엔진과 시각을 반영한다.
2. gemini 선택 시: `.env.example` → `.env` 복사를 안내하고 **사용자가 직접** 키를 넣게 한다.

## 4. 루틴 등록 — 현존 세션 우선
1. **1차: 세션 크론** — CronCreate로 매일 생성 시각(기본 06:57)에 `routine-SKILL.md` 실행을
   등록한다. 세션 크론은 7일 자동 만료라는 점을 사용자에게 고지하고, 만료 전 재등록을
   루틴 보고에 포함시킨다.
2. **예비: 스케줄드 태스크** — scheduled-tasks 도구가 있으면 같은 내용을 +10분 시각(기본 07:07)에
   새 세션 태스크로도 등록한다. 이중 생산은 routine-SKILL의 0-a 단일 생산자 규칙이 막는다.
3. `routine-SKILL.md` 안의 킷 절대경로를 이 설치 위치로 치환하고, "발행 이력" URL은 비운다.

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
      "Bash(git push:*)", "Bash(git diff:*)", "Bash(git log:*)",
      "mcp__claude-in-chrome", "mcp__Claude_Browser", "mcp__scheduled-tasks"
    ]
  }
}
```
`rm` 등 파괴 명령은 의도적으로 제외한다 — 루틴에 삭제 작업이 없다.

## 6. 시험 실행
1. TTS 1회: `python tools/make_audio.py output/script/<견본>.md`
2. 루틴을 수동 1회 실행해 `output/web/YYYY-MM-DD.html` 생성 확인
3. Artifact 발행 → **발행 직후 Share "Anyone with the link" 켜기** (비공개 기본값 = 404 함정)
4. 발행 전 `templates/publish-checklist.md` A~E 전 항목 실행·기록

## 7. 설치 완료 보고
헬스체크 표 · 설치 위치 · TTS 엔진 · 루틴 등록 내역(크론 ID, 태스크 ID) · 시험 실행 결과 ·
사용자가 직접 해야 할 남은 일(.env 키 입력, 브라우저 로그인, 첫 공유 확인)을 한 화면으로 보고한다.
