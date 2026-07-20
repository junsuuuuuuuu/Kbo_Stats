# 선수 전성기 예측 모델 카드

## 목적과 예측값

초기 3개 유효 시즌 기록으로 커리어 전성기 나이와 최고 기록을 예측한다.

- 타자 Peak Age: 커리어 최고 OPS 시즌의 나이
- 타자 Peak OPS / Peak HR: 커리어 최고값
- 투수 Peak Age: 커리어 최저 ERA 시즌의 나이
- 투수 Peak ERA / Peak SO: 커리어 최저·최고값

타자는 시즌 100타석 이상, 투수는 30이닝 이상을 유효 시즌으로 본다. 추론에는 유효 시즌
3년이 필요하다.

## 학습 표본과 누수 방지

- 학습 대상: 유효 시즌 4년 이상이고 마지막 기록이 2022년 이전인 완료 커리어 후보
- 학습 표본: 타자 368명, 투수 307명
- 입력 feature: 첫 3개 유효 시즌의 기록, 평균, 추세, 최솟값, 최댓값
- 3번째 유효 시즌 이후 기록은 label 계산에만 사용하고 feature에는 포함하지 않는다.
- 2005~2009 초기 커리어 코호트에서 모델과 파라미터를 선택한다.
- 2010년 이후 코호트는 최종 성능 평가에만 사용한다.

2022년 이후 기록이 없다는 조건은 은퇴 여부를 직접 제공하지 않는 CSV에서 사용하는
검열 완화용 대리 조건이다.

## 모델링

RandomForest, LightGBM, XGBoost를 비교한다. 전성기 값 자체보다 초기 3시즌 기준선 이후의
추가 성장분(residual)을 학습한다. 0 변화가 많은 비대칭 분포이므로 각 모델의 손실함수를
MAE에 맞췄다.

Peak OPS·HR·SO는 초기 최고 기록보다 낮게, Peak ERA는 초기 최저 기록보다 높게 예측되지
않도록 도메인 제약을 적용한다. 최종 모델과 전처리기는 하나의 pipeline으로 저장하며
checksum으로 무결성을 검증한다.

## 최신 코호트 평가

| Target | 선택 모델 | MAE | RMSE | R² | 초기 기록 기준선 MAE |
|---|---:|---:|---:|---:|---:|
| 타자 Peak Age | XGBoost | 2.2145 | 2.6331 | 0.2161 | 2.2632 |
| Peak OPS | LightGBM | 0.0538 | 0.0782 | 0.4162 | 0.0564 |
| Peak HR | LightGBM | 2.2811 | 3.4506 | 0.8743 | 2.1754 |
| 투수 Peak Age | LightGBM | 2.0648 | 2.7496 | 0.5972 | 1.6615 |
| Peak ERA | LightGBM | 0.5025 | 0.6895 | 0.3362 | 0.2615 |
| Peak SO | LightGBM | 8.7807 | 14.7852 | 0.8947 | 7.0615 |

타자 Peak Age와 Peak OPS는 MAE 기준선을 개선했다. 나머지 target은 선수 간 순위 설명력인
R²는 양수지만 강한 초기 기록 기준선보다 MAE가 높다. 온라인 추론은 격리된 검증 MAE가
기준선보다 나쁜 target에 `naive_baseline` fallback을 적용한다. API의 `model_details`와 화면은
실제 배포 모델, 후보 모델, 양쪽 MAE와 fallback 여부를 함께 제공한다.

## SHAP 해석

주요 feature는 debut age, 초기 최고 OPS·ERA, 초기 탈삼진 추세 등이다. SHAP은 모델이 어떤
입력을 사용했는지 설명하지만 해당 기록이 전성기의 원인이라는 인과관계를 뜻하지 않는다.

## 재현 방법

```powershell
Set-Location backend
..\.venv\Scripts\python.exe scripts\train_peak_models.py
..\.venv\Scripts\python.exe -m pytest tests\ml\test_peak_features.py tests\ml\test_peak_inference.py
```

통합 결과는 `backend/app/ml/reports/peak_training_report.json`, 모델은
`backend/app/ml/artifacts/peak/<target>/1.0.0`에 저장된다.

## 한계

- 긴 커리어를 보낸 선수만 label을 가질 수 있어 생존자 편향이 있다.
- 아직 현역인 선수의 실제 peak는 확정되지 않았으므로 평가에서 제외한다.
- 부상, 군 복무, 포지션 변경, 구장 및 리그 환경은 직접 반영하지 않는다.
- Peak Age는 연속값 회귀 결과이므로 화면에서는 소수점과 반올림 나이를 함께 표시한다.
