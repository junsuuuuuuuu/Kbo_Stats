## 우선순위 1: 선수 경기별 기록 대시보드

- 선수 그날 경기기록 스탯(완료)
- 투수 상대전적

## 우선순위 2: 팀·경기 분석

- 이번 시즌 팀 성적(완료)
- 구단별 상대전적(완료)

  .dockerignore의 2026 데이터 제외 문제 수정
  마이그레이션 Ruff 오류 수정해 CI 복구
  홈 경기 결과를 수집 작업+저장 데이터 방식으로 변경
  선수 상세 API 요청과 DB 반복 조회 통합
  검색 디바운스·요청 취소 적용
  KBO 캐시 크기 제한과 부분 실패 처리
  Plotly 경량화ㅌㅌ
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




(투수 상대전적)



## 데이터 자동 최신화 시스템 구축

### 목표
현재 KBO 데이터를 수동으로 크롤링하여 로컬 MySQL에 저장하고 있다.
이를 실제 서비스처럼 자동으로 최신화되는 구조로 개선한다.

### 요구사항

#### 1. 크롤러와 웹 서비스 분리
- 크롤링 로직을 Next.js/FastAPI와 분리한다.
- crawler 디렉터리를 생성하여 독립적인 데이터 수집 모듈로 관리한다.

예시

crawler/
├── schedule.py
├── team_rank.py
├── player.py
├── game_result.py
├── updater.py
└── scheduler.py

---

#### 2. 통합 업데이트 기능

update_all() 함수를 구현한다.

실행 순서

1. 경기 일정 업데이트
2. 경기 결과 업데이트
3. 팀 순위 업데이트
4. 선수 기록 업데이트
5. AI Feature 생성(필요 시)

모든 작업이 완료되면 성공 로그를 출력한다.

---

#### 3. Upsert 적용

기존 INSERT만 사용하는 구조를 제거한다.

모든 저장 로직은

- 존재하면 UPDATE
- 없으면 INSERT

방식으로 변경한다.

중복 데이터가 절대 발생하지 않도록 Primary Key 또는 Unique Key를 설계한다.

---

#### 4. 트랜잭션 적용

업데이트 도중 오류가 발생하면

ROLLBACK

성공 시

COMMIT

하도록 구현한다.

DB 무결성을 유지해야 한다.

---

#### 5. 스케줄러 적용

APScheduler를 사용한다.

매일 오전 7시에

update_all()

이 자동 실행되도록 구현한다.

시간은 환경변수 또는 설정파일에서 변경 가능하도록 만든다.

---

#### 6. 로그 시스템

logs/

폴더를 생성한다.

예시

2026-07-28.log

로그 내용

[07:00]

Schedule Update Success
Team Rank Update Success
Player Update Success
Game Result Update Success

Elapsed Time : xx sec

Finished

오류 발생 시

- 오류 위치
- 예외 메시지
- 실행 시간

을 기록한다.

---

#### 7. 관리자 수동 업데이트

FastAPI에 관리자 API를 추가한다.

POST /admin/update

호출 시

update_all()

이 실행되도록 구현한다.

개발 중에는 버튼 하나로 최신화를 수행할 수 있도록 한다.

---

#### 8. 프로젝트 구조 개선

backend/
frontend/
crawler/
database/
logs/
tests/

형태로 구조를 정리한다.

---

#### 9. 예외 처리

다음 상황을 고려한다.

- KBO 사이트 접속 실패
- HTML 구조 변경
- 일부 경기 데이터 누락
- DB 연결 실패
- 중복 데이터
- 크롤링 중 예외 발생

각 경우 프로그램이 종료되지 않고
로그를 남긴 후 다음 작업을 수행하도록 구현한다.

---

#### 10. README 작성

다음 내용을 README에 추가한다.

- 데이터 수집 구조
- 자동 업데이트 방식
- APScheduler 사용 이유
- Upsert 적용 이유
- 트랜잭션 적용 이유
- 로그 관리 방식

취업 포트폴리오에서 운영까지 고려한 프로젝트임을 보여줄 수 있도록 문서화한다.

### 완료 기준

- 하루 1회 자동으로 최신 데이터가 반영된다.
- 중복 데이터가 발생하지 않는다.
- 오류 발생 시 로그가 남는다.
- 관리자 API로 언제든 수동 업데이트가 가능하다.
- DB 무결성이 유지된다.
- 유지보수가 쉬운 구조로 리팩토링되어 있다.

