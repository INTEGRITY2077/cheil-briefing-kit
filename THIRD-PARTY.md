# 서드파티 의존성과 라이선스

이 킷 자체는 MIT입니다. 킷은 아래 오픈소스를 **번들하지 않고**, 설치 시 각자의 배포처
(PyPI·HuggingFace)에서 받아 사용합니다. 버전·라이선스는 2026-08-12 PyPI 실조회 기준.

## 파이썬 패키지

| 패키지 | 용도 | 라이선스 |
|---|---|---|
| [supertonic](https://github.com/supertone-inc/supertonic) | TTS 1순위 — 로컬 ONNX 합성 | MIT |
| [onnxruntime](https://onnxruntime.ai) | supertonic 추론 런타임 | MIT |
| [soundfile](https://github.com/bastibe/python-soundfile) | WAV 입출력·리샘플 | BSD-3-Clause |
| [huggingface-hub](https://github.com/huggingface/huggingface_hub) | supertonic 모델 다운로드 | Apache-2.0 |
| [edge-tts](https://github.com/rany2/edge-tts) | TTS 3순위 예비 | **LGPL-3.0** |
| [google-genai](https://github.com/googleapis/python-genai) | TTS 2순위(Gemini, 선택) | Apache-2.0 |
| pyyaml | 설정 파일 파싱 | MIT |
| requests | HTTP 수집 | Apache-2.0 |
| numpy | 오디오 배열 처리 | BSD-3-Clause |

## 모델 가중치

| 모델 | 라이선스 | 비고 |
|---|---|---|
| [Supertonic 3](https://huggingface.co/Supertone/supertonic) (Supertone Inc.) | **OpenRAIL-M** (샘플 코드는 MIT) | 최초 실행 시 HuggingFace에서 자동 다운로드(~99MB). 상업적 사용 허용이되 책임 있는 사용 제한 조항이 있는 라이선스 — 원문은 모델 카드의 LICENSE 참조. `voices/anchor-f1f2-30.json`은 이 모델의 내장 보이스 스타일 벡터를 블렌드한 파생물이다 |

## 외부 서비스 (라이선스가 아니라 약관이 적용되는 것)

- **edge-tts**는 Microsoft Edge의 온라인 낭독 서비스를 호출합니다 — 라이브러리는 LGPL이지만
  음성 합성 자체는 Microsoft 서비스 약관 하에 있고, 예고 없이 막힐 수 있어 예비로만 씁니다.
- **Gemini TTS**는 본인 API 키로 Google 약관 하에 사용합니다. 키는 `.env`에만 둡니다.
- **DART·회사 IR·뉴스룸** 수집물은 각 출처의 공개자료 이용 조건을 따르며, 킷의 전시물
  화이트리스트(`templates/publish-checklist.md` F4)가 전시 가능 범위를 제한합니다 —
  기사·유료 리포트는 재현하지 않고 링크만 겁니다.

## LGPL 관련 참고

edge-tts(LGPL-3.0)는 수정 없이 pip 의존성으로 import만 하므로 킷의 MIT 배포에 영향을
주지 않습니다. edge-tts 소스를 수정해 재배포하는 경우에만 LGPL 의무가 발생합니다.
