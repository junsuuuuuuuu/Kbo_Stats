# 변경 이력

## 2026-07-30

### Boxscore persistence and official metric parsing

- Added `game_boxscore_snapshots`, `game_batting_lines`, and `game_pitching_lines` with Alembic migration `0006_create_game_boxscores`.
- Game-detail collection now upserts one snapshot and replaces its normalized lines, preventing duplicate rows on repeated startup syncs.
- Prediction metrics read persisted boxscores first and fall back to the existing detail API when no stored data exists.
- Fixed compact KBO plate-appearance parsing (`중안`, `좌2`, `유땅`, `희번`, `야선`, `실책`) so total bases and OPS are not incorrectly marked unavailable.
- Added innings parsing for official fractional notation (`1/3`, `1 1/3`) and corrected stored pitching completeness.
- OBP is calculated independently from total bases; SLG and OPS remain null when total-base data is genuinely incomplete.
- Updated prediction schemas and frontend normalization to expose metric status, boxscore coverage, and recent-game counts without breaking existing response fields.
- Prediction UI keeps team batting and pitching metrics separated in tabs and removes the redundant evidence/description cards.
- Added regression coverage for compact KBO outcomes, fractional innings, official recent-stat formulas, and persisted metric aggregation.
- Verified 2026-07-29: 5 snapshots, all `collected`, 0 incomplete batting/pitching lines, and repeated collection did not increase row counts.
- Backend validation: 89 tests passed and Ruff passed.











## 2026-07-29

### 경기 예측 최근 10경기 지표 개선

- 예측 대상 경기일 이전에 종료된 경기만 필터링하고, 최신순 최대 10경기만 예측 입력으로 사용
- 예정·취소·무효성 결과와 대상 경기 이후 데이터가 최근 전적·득점·실점 계산에 포함되지 않도록 보완
- 최근 경기 수, 승률, 경기당 평균 득점·실점·득실차를 `metrics`에 반환하고 확률 계산에도 반영
- 박스스코어가 없는 타율·OPS·ERA·WHIP는 임의 계산하지 않고 `null` 및 `unavailable` 상태로 반환
- 최근 경기 부족 시 `partial` 상태와 실제 사용 경기 수를 반환하고 예측 신뢰도를 낮춤
- 최근 10경기 기준 필터링·평균 계산·박스스코어 부족 처리를 단위 테스트로 추가
- 기존 경기 상세 박스스코어를 재사용해 공식 산식(AVG·OPS·ERA·WHIP·SO/경기)으로 최근 지표를 계산
- 상세 경기 조회는 팀별 최대 10경기, 제한된 동시성 및 기존 TTL 캐시를 사용하고 일부 실패 시 가능한 지표만 반환
- 최근 팀 타격 지표에 OBP·SLG·OPS·경기당 안타·홈런·볼넷을 추가하고 누적 원시 기록으로 계산
- 선발투수 이름을 시즌 팀 로스터와 선수 ID로 검증하고 시즌 ERA·WHIP·이닝·탈삼진·볼넷·피안타·승패·등판 수와 최근 등판일을 반환
- 선발투수의 상대 구단 등판 수·선발 등판 수·이닝·ERA·WHIP·피안타·탈삼진·승패 및 표본 상태를 추가
- 최근 OPS와 선발투수 지표가 실제 확률 계산에 반영되며 데이터 부족·미매칭 시 신뢰도를 낮춤
- 예측 서비스에 선수 Repository를 함께 주입해 일정 선발투수와 기존 선수 분석용 시즌 투수 기록(승·패·ERA·이닝·탈삼진·볼넷·피안타)을 연결
- 예측 화면의 팀 지표를 타격·투수 탭으로 분리하고 박스스코어 확보 상태를 팀별로 설명하도록 개선
- 최근 박스스코어 지표에 확보 경기 수와 지표별 상태를 추가하고, 부분 확보 상태에서도 계산 가능한 AVG·OBP·SLG·OPS를 독립적으로 반환

### 변경
- FastAPI 시작 시 서버를 차단하지 않는 백그라운드 경기 일정 동기화 추가
- 어제·오늘·내일·모레 경기 스냅샷을 자동 갱신하도록 구성
- MySQL advisory lock과 30분 TTL을 적용해 중복 수집 및 불필요한 KBO API 호출 방지
- KBO API 장애 시 기존 DB 데이터를 유지하도록 처리
- 예측 API의 404 더미 데이터 fallback 제거

### 검증
- Backend 관련 테스트 및 Ruff 검사 통과
- Frontend TypeScript 및 ESLint 검사 통과

## 2026-07-28

### 변경
- 메인 화면의 경기·선수·팀 통계 요약 영역 개선
- 프로젝트 주요 지표와 데이터 현황 표시 추가
- 선수 경력 기록 대시보드 표시 보완
- TODO 및 향후 작업 목록 정리

### 검증
- 메인 화면 및 선수 기록 대시보드 변경 사항 확인

## 2026-07-27

### 변경
- 경기 일정 자동 수집 시 어제와 오늘 경기일을 함께 갱신하도록 수정
- 점수가 존재하는 경기를 취소 상태보다 완료 상태로 우선 판정하도록 수정
- 상세 경기 API를 최대 3회 재시도하고 실패 원인과 상세 수집 상태를 저장하도록 개선
- KBO 상세 투수 기록의 `-` 결측 ERA를 허용하도록 파서 수정
- 경기 ID 기반 MVP 승리 확률·예상 스코어·예측 근거 API 추가
- 시즌 전적·최근 10경기·홈·원정·상대전적·최근 득실점 지표를 조합한 교체 가능한 예측 서비스 추가
- 선발투수 및 전적 데이터 부족 시 `unavailable` 상태와 낮은 신뢰도를 반환하도록 보완
- FastAPI 시작 시 서버를 막지 않는 백그라운드 경기 일정 동기화 추가
- MySQL advisory lock과 30분 TTL로 중복 수집 및 불필요한 KBO API 호출 방지
- 예측 API 404 시 프론트 더미 데이터 fallback 제거
- 경기 행 전체가 아닌 취소 상태 영역에서만 취소 문구를 판정하도록 수정
- 상세 기록 수집 실패를 경기 취소와 구분하여 화면에 표시하도록 수정

### 검증
- 경기 일정의 예정 경기 행 전체 클릭 시 `/games/{game_id}/prediction`으로 이동하도록 프론트 라우팅 연결
- 종료 경기는 기존 경기 상세 페이지로 이동하고, 취소 경기는 클릭을 비활성화
- 구단별 경기 결과의 외부 KBO 리뷰 링크를 내부 경기 상세 결과 페이지 링크로 변경
- 경기 행 hover를 팀별 셀 단위가 아닌 전체 경기 행 단위로 통일
- `DragScroll`이 일정 행 클릭 이벤트를 가로채지 않도록 수정하여 행 클릭 이동 보장
- 경기 구장명과 예측 분석 안내를 분리해 일정 테이블 배치 깨짐 수정
- 경기 예측 API DTO와 화면 모델 정규화 및 404 mock fallback 연결

### 검증
- Backend 관련 테스트 10개 통과
- Ruff 및 Backend 문법 검사 통과
- Frontend TypeScript 검사 통과

## 2026-07-26

### 변경

- KBO 경기 일정 조회 시 오늘 날짜와 최신 완료 경기일을 기준으로 데이터를 최신화하도록 개선
- 경기 일정 API에서 DB 스냅샷이 오래된 경우 KBO 공식 일정에서 재수집하고, 수집 결과를 스냅샷으로 저장하도록 개선
- 서울 시간대 기준의 경기일 판정과 미래 경기일 조회를 지원하도록 수정
- 매일 실행할 수 있는 `daily_kbo_update.py` 갱신 작업을 추가하고, 완료 경기 수가 변한 경우에만 대용량 순위·선수 기록 수집을 수행하도록 개선
- 경기일 스냅샷 저장, 미래 일정 사전 수집, 선택적 로스터 갱신을 지원하는 갱신 옵션 추가
- 홈 화면에 KBO 공식 데이터 출처 및 비상업적 분석 목적 안내 추가
- 구단 화면에 최신 등록/말소 선수 비교 API와 UI 추가
- 최신 로스터와 직전 로스터 스냅샷의 선수 차이를 등록·말소로 구분해 표시

### 검증

- 현재 작업 트리에서 구단 로스터 변경 조회 기능의 Backend·Frontend 연동 변경 확인
- 변경 파일 7개, 216줄 추가 및 2줄 수정

## 2026-07-21

### 변경

- 가치 랭킹에서 2020~2026 시즌을 선택할 수 있도록 개선
- 선택한 시즌의 소속팀을 명시해 이적 선수의 과거·현재 소속 혼동 방지
- 2026 진행 중 기록을 가치 랭킹 입력 데이터에 포함하고 기준일 안내 추가
- 구단 목록과 로스터 상세 화면에 KBO 공식 구단 엠블럼 적용
- 선수 상세 화면에 시즌 선택형 연도별 커리어 기록 대시보드 추가
- 커리어 기록 약어에 타자·투수 문맥별 한국어 도움말 추가

### 추가

- KBO 공식 선수 등록 현황의 2026 구단별 1군 로스터 수집기 추가
- 10개 구단 등록 선수 282명 snapshot 및 품질 manifest 생성
- 날짜별 로스터 보존을 위한 `team_rosters` 테이블과 Alembic migration 추가
- 구단 목록 및 최신 로스터 FastAPI API 추가
- 반응형 구단 카드 목록과 포지션 필터 로스터 화면 추가
- 로스터 선수를 기존 선수 분석 페이지로 연결

### 검증

- KBO 선수 ID와 기존 DB 선수 282명 전원 매칭
- MySQL 로스터 282행 적재
- Backend 테스트 49개 통과 및 커버리지 66.57%
- Frontend 테스트 6개, TypeScript, ESLint 및 production build 통과

## 2026-07-20

### 추가

- KBO 공식 기록실의 2026 정규시즌 타자·투수 기록 수집기 추가
- 요청 간격, 재시도, robots.txt 확인 및 ASP.NET 페이지 이동 처리
- 2026 진행 기록 전용 CSV와 데이터 품질 manifest 생성
- 타자 327명, 투수 271명의 2026 시즌 기록 수집
- 진행 시즌 구분을 위한 `is_partial`, `as_of_date` 필드 추가
- 2026 전용 전처리 및 MySQL 적재 스크립트 추가
- Alembic migration을 통한 진행 시즌 메타데이터 컬럼 추가
- 선수 상세 API와 화면에 2026 시즌 기록 및 기준일 표시

### 변경

- 2026 기록은 선수 상세 기록과 그래프에는 포함하되 ML 학습에서는 제외
- 다음 시즌 예측과 유사 선수 분석은 2025 완결 시즌을 기준으로 유지
- KBO의 `0cm/0kg` 미입력 신체 정보는 `NULL`로 정규화
- 동일한 2026 snapshot을 다시 적재할 경우 안전하게 건너뛰도록 개선

### 검증

- MySQL 적재 결과: 타자 327행, 투수 271행
- FastAPI 선수 검색 및 2026 시즌 상세 응답 확인
- Backend 테스트 44개 통과
- Frontend 테스트 6개, TypeScript, ESLint 및 production build 통과

### 저장소 정책

- 원본·정제 2026 CSV와 환경변수 파일은 Git에서 제외
- 수집 코드, DB migration, 테스트, 문서와 품질 manifest만 저장소에 보관
