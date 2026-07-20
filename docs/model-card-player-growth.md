# 선수 성장곡선 분석 모델 카드

## 목적

선수의 시즌별 기록 변화, 전년 대비 성장률, 최고 시즌, 급성장 시즌과 하락 시즌을
일관된 규칙으로 제공한다. 결과는 Plotly line chart와 이벤트 annotation에서 바로 사용할 수
있는 long-format 데이터로 반환한다.

## 지원 지표

- 타자: AVG, OBP, SLG, OPS, HR, RBI, SB, BB, SO
- 투수: ERA, IP(outs), SO, BB, SV, HLD

ERA와 허용 볼넷처럼 낮을수록 좋은 지표는 방향을 반전한다. 따라서 ERA가 감소하면
`absolute_change`는 음수지만 `performance_change`는 양수로 표현된다.

## 계산 및 이벤트 판정

1. 같은 선수의 연속된 두 시즌만 비교한다.
2. 타자 100타석, 투수 30이닝 이상을 두 시즌 모두 만족해야 이벤트를 판정한다.
3. 전년 대비 절대 변화량과 성장률을 계산한다.
4. 전체 KBO 선수의 유효한 연속 시즌 변화량으로 지표별 경험적 분포를 만든다.
5. 경기력 방향을 보정한 변화가 상위 10%면 `breakout`, 하위 10%면 `decline`으로 판정한다.
6. 동점이 많은 정수 기록은 mid-rank 백분위를 사용한다.

표본 미달 시즌과 비연속 시즌은 그래프에는 유지하지만 이벤트 및 최고 시즌 판정에서는
제외한다. 고정 수치가 아니라 리그 분포를 사용하므로 OPS와 홈런처럼 단위가 다른 지표도
같은 기준으로 해석할 수 있다.

## 재현 방법

```powershell
Set-Location backend
..\.venv\Scripts\python.exe scripts\validate_growth_analysis.py
..\.venv\Scripts\python.exe -m pytest tests\ml\test_growth.py
```

검증 결과는 `backend/app/ml/reports/growth_analysis_validation.json`에 저장된다.

## 한계와 개선 방향

- 리그 득점 환경과 구장 효과는 아직 보정하지 않는다.
- 누적 기록은 출장 기회 변화의 영향을 받으므로 비율 기록과 함께 해석해야 한다.
- 상·하위 10%는 설명 가능한 기본 정책이며 API 연결 후 설정값으로 확장할 수 있다.
- 이벤트는 통계적 이상 변화 탐지이며 부상, 포지션 변경 등의 원인을 직접 설명하지 않는다.
