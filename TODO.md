# TODO

## 우선순위 1: 선수 경기별 기록 대시보드

- 선수 그날 경기기록 스탯
- 투수 상대전적

## 우선순위 2: 팀·경기 분석

- 이번 시즌 팀 성적
- 구단별 상대전적

## 우선순위 3: 경기 결과 예측

- [ ] 시계열 데이터 누수를 차단한 학습 데이터셋 구성
- [ ] Logistic Regression 기준 모델 구현
- [ ] LightGBM·XGBoost 승패 확률 모델 비교
- [ ] Log Loss, Brier Score, ROC-AUC 및 Calibration 평가
- [ ] SHAP 기반 승리 확률 설명 구현
- [ ] 예측 결과와 실제 경기 결과 저장 및 모델 성능 모니터링

## 운영 및 배포

- [ ] Railway 또는 Render Backend 배포
- [ ] Vercel Frontend 배포
- [ ] 배포 환경 MySQL migration 및 초기 데이터 적재
- [ ] 정기 데이터 수집 작업과 실패 알림 구성
- [ ] 배포 후 API·화면 smoke test
