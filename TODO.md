## 우선순위 1: 선수 경기별 기록 대시보드

- 선수 그날 경기기록 스탯(완료)
- 투수 상대전적

## 우선순위 2: 팀·경기 분석

- 이번 시즌 팀 성적(완료)
- 구단별 상대전적

  .dockerignore의 2026 데이터 제외 문제 수정
  마이그레이션 Ruff 오류 수정해 CI 복구
  홈 경기 결과를 수집 작업+저장 데이터 방식으로 변경
  선수 상세 API 요청과 DB 반복 조회 통합
  검색 디바운스·요청 취소 적용
  KBO 캐시 크기 제한과 부분 실패 처리
  Plotly 경량화
  UI 테스트 추가
  미사용 CSS·Zod 정리
  시즌 상수와 문서 최신화

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
