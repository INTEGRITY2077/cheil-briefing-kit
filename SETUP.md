# SETUP — Claude가 따라 하는 설치 절차

> 이 문서는 사람을 위한 설명이자, Claude Code에게 주는 설치 지시서다.
> 사용자가 이 저장소 링크와 함께 "설치해줘"라고 하면 Claude는 아래를 순서대로 수행한다.
> 각 단계는 실패하면 멈추고 원인을 보고한다 — 조용히 건너뛰지 않는다.

## 0. 확인

- Claude Code가 로컬 파일·Bash·스케줄 작업(scheduled-tasks 도구)을 쓸 수 있는 환경인지 확인한다.
- `python --version` 3.10 이상. 없으면 설치를 안내하고 멈춘다.
- 사용자에게 **세 가지만** 묻는다 (한 번에):
  1. 설치 위치 (기본값 제안: 사용자 문서 폴더 아래 `briefing-kit`)
  2. TTS 엔진 — `edge`(무료·키 불필요, 기본값) 또는 `gemini`(본인 API 키 필요, 음질 우수)
  3. 루틴 시각 — 기본값 07:00 생성 / 07:45 배포

## 1. 저장소 받기

```
git clone https://github.com/INTEGRITY2077/cheil-briefing-kit <설치 위치>
```
git이 없으면 zip 다운로드로 대체한다.

## 2. 의존성

```
python -m pip install edge-tts requests pyyaml
```
gemini를 선택했다면 추가로: `python -m pip install google-genai`

## 3. 설정 생성

1. `config.example.yaml` → `config.yaml` 복사 후, 선택한 TTS 엔진과 시각을 반영한다.
2. gemini 선택 시: `.env.example` → `.env` 복사를 안내하고, **사용자가 직접** 본인 키를
   `GEMINI_API_KEY=` 뒤에 붙여넣게 한다. Claude는 키를 화면에 출력하거나 되묻지 않는다.
   키가 없으면 config의 `on_missing_key: edge` 강등이 동작한다.

## 4. 루틴 등록

1. `routine-SKILL.md`를 읽고, 문서 안의 킷 절대경로를 **이 설치 위치**로 치환한 내용을 프롬프트로 삼아
   scheduled-tasks 도구(`create_scheduled_task`)로 등록한다.
   - cron: 사용자가 고른 생성 시각 (기본 `0 7 * * *`)
   - 설명: "제일기획 일일 브리핑 — 07:00 생성, 07:45 배포"
2. routine-SKILL.md 안의 "발행 이력" URL들은 원작자의 것이다 — 새 설치에서는 비우고 시작한다.

## 5. 무인 실행 권한

스케줄 세션이 승인 대기로 멈추지 않도록, 설치 위치의 `.claude/settings.json`에
아래 허용 목록을 만든다 (이 프로젝트에만 적용된다):

```json
{
  "permissions": {
    "allow": [
      "Read", "Write", "Edit", "Glob", "Grep", "Artifact",
      "WebFetch", "WebSearch",
      "Bash(python:*)", "Bash(py:*)", "Bash(ls:*)", "Bash(cp:*)",
      "Bash(mv:*)", "Bash(mkdir:*)", "Bash(echo:*)", "Bash(cat:*)", "Bash(cd:*)",
      "mcp__claude-in-chrome", "mcp__Claude_Browser", "mcp__scheduled-tasks"
    ]
  }
}
```
`rm` 등 파괴 명령은 의도적으로 제외한다 — 루틴에 삭제 작업이 없다.

## 6. 시험 실행

1. 대본 견본으로 TTS 1회: `python tools/make_audio.py output/script/<아무 날짜>.md` (edge 기준)
2. 루틴을 수동으로 1회 실행해 `output/web/YYYY-MM-DD.html`이 생성되는지 본다.
3. Artifact로 발행하고 **발행 직후 Share → "Anyone with the link"를 켠다**
   (새 아티팩트는 비공개 기본값이라 이 단계를 빠뜨리면 독자에게 404가 뜬다).
4. 발행 전에는 반드시 `templates/publish-checklist.md`의 A~E 전 항목을 돌리고 기록한다.

## 7. 설치 완료 보고

Claude는 마지막에 다음을 한 화면으로 보고한다:
설치 위치 · TTS 엔진 · 루틴 시각과 taskId · 시험 실행 결과 · 사용자가 직접 해야 할 남은 일
(예: .env에 키 입력, 첫 발행물 공유 확인).
