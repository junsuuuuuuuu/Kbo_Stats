# AI 선수 추천 모델 카드

## 목적

동일 시즌의 KBO 선수 중 기록 성향이 비슷한 선수를 찾고, 조건에 맞는 선수를 안전하게
검색한다. 생성형 AI API는 사용하지 않으며 정제 CSV와 scikit-learn만으로 재현할 수 있다.

## 후보 품질 기준

- 타자: 해당 시즌 100타석 이상
- 투수: 해당 시즌 30이닝(90 outs) 이상
- 기준 선수는 표본 기준과 관계없이 조회할 수 있지만 추천 후보에는 위 기준을 적용한다.
- 서로 다른 시즌의 리그 환경이 섞이지 않도록 동일 시즌 선수만 비교한다.

## 조건 검색

외부에서 임의 컬럼을 전달해 검색할 수 없도록 역할별 허용 컬럼 목록을 사용한다. 나이,
OPS, 출루율, 장타율, 홈런, ERA, 탈삼진 등의 최솟값과 최댓값을 조합할 수 있으며 팀과
타자 포지션 조건도 지원한다.

## 유사 선수 계산

1. 결측값을 해당 시즌 중앙값으로 대체한다.
2. 기록 단위 차이를 제거하기 위해 StandardScaler로 표준화한다.
3. Cosine Similarity와 KNN Euclidean Distance를 각각 0~1 점수로 변환한다.
4. 두 점수의 평균으로 최종 유사도 순위를 계산한다.
5. 핵심 기록 중 표준편차 대비 차이가 가장 작은 3개를 추천 이유로 반환한다.
6. 전체 후보로 PCA를 학습하고 기준 선수와 TOP10의 2차원 좌표를 반환한다.

선수 ID나 이름은 feature에 포함하지 않아 특정 선수를 암기하는 추천을 방지한다.

## 재현 방법

```powershell
Set-Location backend
..\.venv\Scripts\python.exe scripts\validate_recommendations.py
..\.venv\Scripts\python.exe -m pytest tests\ml\test_recommendation.py
```

검증 결과는 `backend/app/ml/reports/recommendation_validation.json`에 저장된다.

## 한계와 개선 방향

- 현재는 포지션·구장·리그 환경을 보정하지 않은 기록 기반 유사도다.
- 가중치는 동일하게 적용되므로 사용자 목적별 가중치 프리셋을 추후 추가할 수 있다.
- PCA 좌표는 시각화용이며 두 선수의 유사도를 직접 의미하지 않는다.
- 추천 API는 `/api/v1/analytics/similar/{role}/{player_id}`에 연결되어 있다.
