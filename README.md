# 오늘의 제일기획 뉴스 — 아침 브리핑 킷

매일 아침 Claude Code가 공개자료(DART·IR·업계 매체·글로벌 지주 뉴스룸)를 수집·검증해
**웹판 + 라디오(TTS) + 프레젠테이션** 세 가지 브리핑을 만들어 배포하는 자동화 킷입니다.

- **API 키 없이 동작** — TTS 1순위가 로컬 엔진(Supertonic 3, 키·네트워크 불필요)입니다.
  Claude Max 구독만 있으면 됩니다 (Gemini 키는 선택)
- 모든 사실은 원장(facts)에 등급(1차자료/증권사/보도/관찰)으로 등재, 발행 전 체크리스트
  게이트(A 주어 · B 언어 · C 판형 · D 기술 · E 배포 · F 전시물) 통과 — 일부는 스크립트가
  자동 판정합니다(`tools/check_*.py`)
- 웹판은 **전시물 우선** 편집 — 1차자료 원문 재현에 하이라이트·주석을 다는 방식이
  중심이고, 줄글은 상한이 있습니다 (`templates/exhibit-first.md`)
- 호마다 독립 아티팩트로 출판, 전날 호는 영구 아카이브

## 설치 — 한 줄이면 됩니다

Claude Code(Max 플랜)를 열고 아래 한 줄을 붙여넣으세요:

```
https://github.com/INTEGRITY2077/cheil-briefing-kit 를 읽고 SETUP.md 대로 내 환경에 설치해줘
```

Claude가 저장소를 내려받고, 세 가지를 물어본 뒤(설치 위치 · TTS 엔진 · **실행 시각**),
의존성 설치 → 설정 생성 → 아침 루틴 등록 → 시험 실행까지 스스로 진행합니다.

### 설치 후에 알아둘 것

- **시각은 합의값입니다.** 디폴트는 생성 07:00 / 배포 07:45이지만, 설치 때 정한 값이
  `config.yaml`의 `schedule`에 기록되고, 이후에도 Claude에게 "8시로 바꿔줘" 한마디로
  재설정됩니다. 문서에 적힌 시각은 전부 디폴트 예시입니다.
- **경로는 주입됩니다.** `routine-SKILL.md`의 킷 위치는 `{{KIT_ROOT}}` 플레이스홀더이고
  설치 때 실제 설치 경로로 치환됩니다. 나머지 경로는 전부 킷 루트 기준 상대경로입니다.
- **산출물은 당신 것입니다.** 브리핑은 당신의 claude.ai 계정으로, 당신의 아티팩트 URL로
  발행됩니다. `output/`(산출물)·`sources/`(전시물 원문)·`.env`·`config.yaml`은 커밋되지
  않으며(.gitignore), 저장소 push는 원작자·포크 전용입니다.
- **첫 TTS 실행 때** Supertonic 모델(~99MB)을 HuggingFace에서 한 번 내려받습니다.
  이후에는 오프라인에서도 동작합니다.
- **무인 실행 권한을 확인하세요.** 설치는 설치 위치에만 적용되는 허용 목록을
  `.claude/settings.json`에 만듭니다(SETUP 5절). 여기에는 킷의 파이썬 도구를 매일 아침
  묻지 않고 돌리기 위한 `Bash(python:*)`가 들어갑니다 — `rm`과 `git push`는 제외했습니다.
  넣기 전에 `tools/`의 파이썬 7개를 한 번 훑어보시길 권합니다.

## 구성

| 경로 | 내용 |
|---|---|
| `CLAUDE.md` | **레포를 연 Claude의 역할 계약** — 기본은 설치자·운영자, 저장소 개발·push는 원작자 명시 요청 시에만 |
| `SETUP.md` | Claude가 따라 하는 설치 절차 — 헬스체크 → 질문 3개 → 설치 → 루틴 등록 |
| `routine-SKILL.md` | 매일 아침 루틴의 전체 지시서 (시각·경로는 config·설치 시 주입) |
| `tools/` | TTS 사다리(`make_audio_supertonic.py` → `make_audio_gemini.py` → `make_audio.py`), 오디오 이식(`embed_radio.py`), 자동 게이트(`check_tables.py`·`check_exhibits.py`·`check_css_vars.py`·`check_formats.py`) |
| `voices/` | 확정 보이스 — F1+F2 블렌드 스타일 벡터 (매일 같은 목소리 보장) |
| `templates/` | 발행 전 체크리스트(A~F), 전시물 우선 원칙, 대본 골격, 톤·스타일·TTS 게이트 |
| `profiles/`, `okf/` | 소스 프로파일과 지식 원장 — **원작자 시드**(공개자료 기반). 설치 후 첫 실행부터 루틴이 따라잡아 갱신하며 stale 규칙이 세대교체 |
| `examples/` | 설치 시험용 견본 대본 |
| `config.example.yaml` | 설정 견본 — 복사해서 `config.yaml`로 (엔진·시각·경로가 여기 있습니다) |
| `.env.example` | (선택) 본인 Gemini API 키 — 없어도 전체가 동작합니다 |
| `THIRD-PARTY.md` | 의존성·모델 가중치 라이선스 목록 (supertonic MIT · 모델 OpenRAIL-M · edge-tts LGPL 등) |

## 산출물

- **웹판**: 전시물(공시·IR 원문 재현+하이라이트+주석) 중심의 그날 뉴스, 상단에 라디오
  플레이어(기본 1.3× 배속, −/+ 조절). 오디오는 MP4(AAC)로 실어 호가 3MB 안쪽입니다.
  **아티팩트 안에서 저장은 안 됩니다** — 뷰어 iframe에 `allow-downloads`가 없고,
  런타임의 `downloads` capability를 쓰면 공개 공유 자체가 막힙니다. 오디오 파일이
  필요하면 로컬 `output/audio/YYYY-MM-DD.wav`를 배포 묶음에 첨부하세요
- **라디오**: 1인 낭독이 표준(Supertonic, 영역 전환 접속사 규칙). 2인 앵커·기자 판형은
  Gemini 엔진을 선택한 날만
- **프레젠테이션**: 웹판 전시물을 그대로 옮긴 슬라이드 + PPTX 보관본

## 지원 OS

Windows · macOS · Linux — Claude Code가 도는 곳이면 어디든. 도구와 의존성은 전부
크로스플랫폼입니다. **실측 검증은 Windows 11에서 완료**됐고 macOS/Linux는 미실측이니,
설치 중 막히는 지점이 있으면 이슈로 남겨 주세요. (config의 `sapi` 엔진만 Windows 전용
옵션이며 기본 사다리에는 포함되지 않습니다.)

## 주의

- TTS 대본은 발화용 표기(숫자·약어 한글 풀어쓰기)를 씁니다 — `templates/tts-guard.yaml`
- 이 킷이 만드는 문서는 전부 공개자료 기반이며 투자 조언이 아닙니다.

## 라이선스

이 킷은 MIT입니다. 사용하는 오픈소스 의존성과 Supertonic 모델 가중치(OpenRAIL-M)의
라이선스는 `THIRD-PARTY.md`에 정리돼 있습니다.
