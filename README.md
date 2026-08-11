# 오늘의 제일기획 뉴스 — 아침 브리핑 킷

매일 아침 7시, Claude Code가 공개자료(DART·IR·업계 매체·글로벌 지주 뉴스룸)를 수집·검증해
**웹판 + 라디오(TTS) + 프레젠테이션** 세 가지 브리핑을 만들어 7시 45분에 배포하는 자동화 킷입니다.

- API 키 배포 없음 — Claude Max 구독과 (선택) 본인의 Gemini API 키만 사용
- 모든 사실은 원장(facts)에 등급(1차자료/증권사/보도/관찰)으로 등재, 발행 전 체크리스트 게이트 통과
- 호마다 독립 아티팩트로 출판, 전날 호는 영구 아카이브

## 설치 — 한 줄이면 됩니다

Claude Code(Max 플랜)를 열고 아래 한 줄을 붙여넣으세요:

```
https://github.com/INTEGRITY2077/cheil-briefing-kit 를 읽고 SETUP.md 대로 내 환경에 설치해줘
```

Claude가 저장소를 내려받고, 몇 가지를 물어본 뒤(설치 위치·TTS 엔진·실행 시각),
의존성 설치 → 설정 생성 → 아침 루틴 등록 → 시험 실행까지 스스로 진행합니다.

## 구성

| 경로 | 내용 |
|---|---|
| `SETUP.md` | Claude가 따라 하는 설치 절차 (사람이 읽어도 됩니다) |
| `routine-SKILL.md` | 매일 07:00에 실행되는 루틴의 전체 지시서 |
| `tools/` | TTS 생성(`make_audio_gemini.py`·`make_audio.py`), 오디오 이식(`embed_radio.py`) |
| `templates/` | 발행 전 체크리스트, 톤·스타일·TTS 게이트, 평가 루브릭 |
| `profiles/`, `okf/` | 소스 프로파일과 지식 원장(전부 공개자료 기반) |
| `config.example.yaml` | 설정 견본 — 복사해서 `config.yaml`로 |
| `.env.example` | (선택) 본인 Gemini API 키 — 없으면 무료 Edge TTS로 동작 |

## 산출물 예시

- 웹판: 그날의 헤드라인·뉴스·숫자·일정·자료실 링크, 상단에 2인 라디오 플레이어(배속 조절·다운로드)
- 라디오: 앵커·기자 2인 대본을 TTS로 낭독 (약 1.5~2분)
- 프레젠테이션: Claude 디자인으로 만든 슬라이드 + PPTX 보관본

## 주의

- `.env`와 `config.yaml`, `output/`은 커밋되지 않습니다 (.gitignore).
- 이 킷이 만드는 문서는 전부 공개자료 기반이며 투자 조언이 아닙니다.

MIT License
