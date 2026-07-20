# 다음 시즌 성적 예측 모델 카드

## 1. 모델 목적

선수의 기준 시즌까지 연속된 최근 3년 기록을 사용해 다음 시즌의 타율, OPS, 홈런,
ERA, 탈삼진을 예측한다. 선수 ID는 feature로 사용하지 않으며, 과거에 없던 선수에게도
통계 패턴을 기반으로 일반화하는 것을 목표로 한다.

이 모델은 선수의 실제 가치나 계약 금액을 확정하는 도구가 아니다. 부상, 외국 리그
경력, 구장 효과, 포지션별 수비와 시즌 중 제도 변화처럼 두 CSV에 없는 요인은 반영하지
못한다.

## 2. 데이터와 표본 정의

- 데이터: 1982~2025 KBO 정제 시즌 기록
- history: 기준 시즌 `t`, `t-1`, `t-2`의 연속 3시즌
- target: 동일 선수의 `t+1` 시즌
- tuning: target season 2020
- walk-forward test: target season 2021, 2022, 2023, 2024, 2025
- 2026 예측: 2023~2025 기록이 연속된 선수

| Target | 최소 target 출장량 | 학습 표본 | 2026 후보 |
|---|---:|---:|---:|
| AVG | 100 PA | 3,132 | 186 |
| OPS | 100 PA | 3,132 | 186 |
| HR | 20 PA | 3,945 | 186 |
| ERA | 150 outs(50 IP) | 1,488 | 138 |
| SO(투수) | 3 outs | 2,822 | 138 |

ERA는 10이닝 기준에서 `R²=-0.02`로 나타나 소표본 변동성이 지나치게 컸다. 30이닝과
50이닝을 비교한 뒤 50이닝 기준을 선택했다. 이는 성능을 숨기기 위한 사후 삭제가
아니라 의미 있는 시즌 ERA라는 target 정의를 강화한 것이며, 변경 전/후 실험 결과를
작업 기록과 통합 JSON 보고서에 보존한다.

## 3. Feature Engineering

각 역할의 주요 누적/비율 기록에 대해 다음 값을 생성한다.

- `lag_0`, `lag_1`, `lag_2`
- 최근 3년 평균
- 최신 시즌과 2년 전의 차이인 3년 추세
- 기준 시즌 연도와 시즌 기준 나이
- 현재 팀 및 타자 포지션 category

숫자 결측은 각 학습 fold의 median으로 처리하고 missing indicator를 추가한다. 범주는
학습 fold에서만 최빈값/one-hot mapping을 학습한다. 전처리기와 estimator는 하나의
scikit-learn Pipeline으로 저장해 학습/추론 불일치를 방지한다.

## 4. 비교 모델과 Tuning

- RandomForestRegressor
- LightGBM Regressor
- XGBoost Regressor
- TabPFN Regressor(격리 CPU benchmark)
- 직전 시즌 동일 지표를 그대로 쓰는 naive baseline

RandomForest, LightGBM, XGBoost는 target별 두 parameter 후보를 2020 holdout MAE로
선택한 뒤 동일한 2021~2025 walk-forward fold에서 비교했다. 최종 배포 후보는 MAE가
가장 낮은 Pipeline을 2025 target까지 전체 재학습했다.

TabPFN 2.2.1은 `scikit-learn < 1.7`을 요구해 Python 3.14 Backend와 호환되지 않는다.
Python 3.13 전용 환경에서 CPU, `n_estimators=1`, fold당 최대 1,000개 학습 표본으로
동일 test year를 평가했다. 조건이 다르므로 결과는 benchmark로만 제공하며 현재 API
artifact로 선택하지 않는다.

## 5. Walk-forward 결과

| Target | 선택 모델 | MAE | RMSE | R² | Baseline MAE | TabPFN MAE* |
|---|---|---:|---:|---:|---:|---:|
| AVG | RandomForest | 0.0270 | 0.0346 | 0.2434 | 0.0380 | 0.0273 |
| OPS | RandomForest | 0.0692 | 0.0881 | 0.3417 | 0.0948 | 0.0711 |
| HR | XGBoost | 3.3451 | 4.8974 | 0.5528 | 3.7456 | **3.0831** |
| ERA | RandomForest | 0.9266 | 1.1647 | 0.0418 | 1.3057 | 0.9408 |
| SO | XGBoost | 19.6750 | 26.5152 | 0.4756 | 21.3023 | 19.7481 |

`*` TabPFN은 축소 CPU benchmark이므로 선택 모델과 직접 동일한 학습 조건은 아니다.

모든 선택 모델의 MAE는 직전 시즌 baseline보다 낮다. ERA는 MAE 개선에도 R²가 0.0418로
매우 낮아 선수별 변동을 충분히 설명하지 못한다. UI와 API에서는 이 한계를 노출하고
확정적 수치처럼 표현하지 않아야 한다.

## 6. SHAP 해석

선택 모델의 최대 300개 재현 가능 표본에서 평균 절대 SHAP 값을 계산했다.

| Target | 주요 feature |
|---|---|
| AVG | 3년 평균 AVG, 직전 안타, 3년 평균 안타 |
| OPS | 3년 평균 OPS, 3년 평균 SLG, 직전 OPS |
| HR | 직전 HR, 3년 평균 HR, 현재 나이 |
| ERA | 3년 평균 ERA, 직전 ERA, 기준 시즌 |
| SO | 직전 SO, 3년 평균 SO, 전년도 SO |

SHAP 값은 인과관계가 아니라 해당 모델 예측에 대한 기여도다. 추천 이유나 선수 평가의
사실 문장으로 과도하게 해석하지 않는다.

## 7. Artifact

각 target의 `1.0.0` 디렉터리에 다음 파일을 저장한다.

```text
backend/app/ml/artifacts/next_season/{role}_{target}/1.0.0/
├─ pipeline.joblib
├─ metadata.json
├─ shap_importance.json
└─ predictions_2026.csv
```

`metadata.json`에는 데이터 SHA-256, feature 목록, 라이브러리 버전, tuning parameter,
fold별 지표와 Pipeline checksum이 포함된다. 추론 시 checksum 불일치가 발생하면 모델을
로드하지 않는다.

통합 결과:

- `backend/app/ml/reports/next_season_training_report.json`
- `backend/app/ml/reports/tabpfn_benchmark.json`

## 8. 재현 방법

기본 세 모델 학습:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe scripts\train_next_season.py
```

TabPFN 격리 benchmark:

```powershell
Set-Location backend
..\.venv-tabpfn\Scripts\python.exe scripts\benchmark_tabpfn.py
```

Windows sandbox처럼 병렬 worker가 제한된 환경에서는 `ML_N_JOBS=1`을 사용한다. 일반
개발 환경에서는 재현성/리소스를 확인한 뒤 이 값을 늘릴 수 있다.

## 9. 알려진 한계와 개선 계획

- 생존자 편향: 다음 시즌에 출전한 선수만 label을 갖는다.
- 2025 기록이 있어도 연속 3년이 아니면 2026 예측에서 제외된다.
- 팀 이동, 부상, 구장과 리그 환경 feature가 없다.
- 출장량 자체를 별도로 예측하지 않아 HR/SO count 예측 오차가 커질 수 있다.
- ERA는 설명력이 낮아 향후 FIP 유사 feature, 역할 구분과 예측 구간이 필요하다.
- TabPFN을 운영 후보로 승격하려면 Python runtime 통합, 기본 8 estimator와 전체 표본
  조건에서 재평가해야 한다.
