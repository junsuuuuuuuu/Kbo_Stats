# 기록의 다음

> 1982~2026 KBO 선수·구단 데이터를 탐색하고 선수의 기록과 미래 가능성을 비교하는 AI 야구 데이터 분석 플랫폼

![Project status](https://img.shields.io/badge/status-in%20progress-orange)
![Started](https://img.shields.io/badge/started-2026--07--19-blue)

이 프로젝트는 2026년 7월 19일에 시작한 개인 프로젝트이며 현재 진행 중입니다. KBO 공식 기록을 수집·정제·적재하고, FastAPI와 Next.js를 통해 검색·비교·예측·추천 기능으로 제공하는 것을 목표로 합니다.

## 📌 프로젝트 소개

### 왜 만들었는가

야구 기록은 풍부하지만 여러 시즌의 기록을 직접 비교하고 선수의 현재 가치와 향후 가능성을 함께 판단하기는 어렵습니다. 원본 데이터 수집부터 전처리, DB 적재, ML 추론, 시각화까지 하나의 흐름으로 연결해 기록을 해석 가능한 정보로 바꾸고자 했습니다.

### 해결하려는 문제

- 시즌·타격·투구별로 흩어진 기록의 통합 조회
- 단일 시즌 성적만으로 파악하기 어려운 성장 흐름과 전성기 분석
- 예측·추천 결과의 근거 확인
- 진행 중인 2026 시즌 데이터와 완결 시즌 학습 데이터의 분리

### 핵심 가치

1. **재현성**: 원본, 정제 결과, 적재 batch, 모델 artifact를 분리하고 생성 정보를 기록합니다.
2. **설명 가능성**: 예측값뿐 아니라 모델 정보와 설명 데이터를 함께 관리합니다.
3. **시계열 신뢰성**: 미래 시즌 정보가 학습에 섞이지 않도록 시즌 기준 검증을 사용합니다.
4. **제품화**: 데이터 분석 스크립트와 ML 모델을 실제 API·웹 화면으로 연결합니다.

## 🎬 시연

> 실제 GIF·스크린샷·영상은 아직 저장소에 없습니다. 자료 추가 후 아래 경로를 연결합니다.

![서비스 시연 GIF](images/demo.gif)

- 시연 영상: [추가 필요]
- 온라인 배포 주소: [추가 필요]

## 🧰 기술 스택

| 영역 | 기술 | 사용 목적 |
|---|---|---|
| Frontend | Next.js App Router, React, TypeScript | 화면 구성·라우팅 |
| 상태/API | TanStack Query | 서버 상태·캐시 관리 |
| 시각화 | Plotly, React Plotly | 기록·비교·성장곡선 시각화 |
| Backend | FastAPI, Uvicorn | REST API·Swagger |
| Backend 구조 | SQLAlchemy 2.x, Pydantic, Alembic | ORM·응답 계약·migration |
| Data | Pandas, NumPy | CSV 분석·특징 생성 |
| ML | scikit-learn, LightGBM, XGBoost, TabPFN, SHAP | 예측·추천·설명 |
| Database | MySQL 8.0, PyMySQL | 기록·스냅샷·모델 메타데이터 |
| Infra | Docker, Docker Compose | 로컬 컨테이너 구성 |
| Deployment 설정 | Vercel, Railway, Render | 배포 설정 |
| CI | GitHub Actions | 경기 일정 수집 자동화 |

## ✨ 주요 기능

### 선수 검색·상세 기록

이름 prefix, 역할, 시즌, 팀 조건으로 선수 목록을 페이지 조회합니다. 선수 상세에서는 타격·투구 시즌 기록을 분리해 제공하며 KBO 원본 player_id로 동명이인을 구분합니다.

### 선수 비교·시각화

두 선수의 기록을 동일한 기준으로 비교할 수 있는 Radar·Bar·Line용 데이터를 제공합니다. Backend는 도메인 데이터를 반환하고 차트 표현은 Frontend가 담당합니다.

### 성장곡선·전성기 예측

시즌별 기록 흐름과 성장 이벤트를 분석하고 역할별 전성기 시점을 예측합니다. 학습된 pipeline과 평가 metadata를 별도로 관리해 온라인 요청 중 학습하지 않습니다.

### 다음 시즌 예측

완결 시즌을 기준으로 타자·투수의 다음 시즌 주요 지표를 예측합니다. 2026 진행 중 기록은 최신 현황과 랭킹에 사용하되 예측 학습 데이터와 분리합니다.

### 유사 선수 추천·조건 검색

역할·포지션·시즌 조건을 먼저 적용한 뒤 표준화된 기록으로 유사 선수를 추천합니다. Cosine Similarity와 KNN을 사용하며 PCA는 설명용 시각화에 사용합니다.

### AI 선수 가치 랭킹

시즌·팀·역할별 기록을 정규화해 AI Score를 계산합니다. ERA처럼 낮을수록 좋은 지표는 방향을 반전해 합성합니다.

### 구단·경기 데이터

구단별 1군 등록 로스터, 등록·말소 변경, 최신 전적, 경기 일정, 경기별 결과와 박스스코어를 제공합니다. KBO 경기 데이터는 날짜별 snapshot으로 저장합니다.

### 2026 시즌 수집

KBO 공식 기록에서 2026 시즌 진행 기록, 구단 로스터, 팀 순위, 경기 일정을 수집합니다. 진행 중 데이터는 is_partial과 as_of_date로 완결 시즌과 구분합니다.

## 🏗️ 시스템 아키텍처

~~~mermaid
flowchart TD
    U[사용자 브라우저] --> F[Next.js App Router<br/>TanStack Query · Plotly]
    F -->|HTTPS / JSON| B[FastAPI REST API<br/>Router → Service → Repository]
    B --> D[(MySQL 8.0)]
    B --> M[ML Inference<br/>저장된 Pipeline · SHAP]
    K[KBO 공식 기록] --> C[수집·전처리 스크립트]
    C -->|CSV·JSON snapshot| D
    D --> A[오프라인 학습·검증]
    A --> M
~~~

브라우저는 DB와 모델에 직접 접근하지 않습니다. FastAPI가 HTTP 계약과 도메인 규칙의 진입점이며, 수집·전처리·학습은 오프라인 작업으로 분리합니다.

## 🗂️ 프로젝트 구조

~~~text
Kbo_Stats/
├─ backend/
│  ├─ app/
│  │  ├─ api/v1/          # 선수·구단·분석·health API
│  │  ├─ services/        # 유스케이스·도메인 규칙
│  │  ├─ repositories/    # SQLAlchemy 조회·저장
│  │  ├─ models/          # SQLAlchemy 모델
│  │  ├─ schemas/         # Pydantic 응답 계약
│  │  ├─ ml/              # 특징·학습·추론·설명
│  │  └─ database/        # Session·적재기
│  ├─ scripts/            # 수집·적재·학습·검증 CLI
│  ├─ alembic/            # DB migration
│  └─ tests/              # unit·API·ML 테스트
├─ frontend/
│  ├─ app/                # Next.js route·페이지
│  ├─ components/         # 공용 UI
│  ├─ features/           # players·teams·rankings 모듈
│  ├─ lib/                # API client·metrics·favorites
│  └─ types/              # API TypeScript 타입
├─ data/                  # raw / processed
├─ database/              # 초기 migration·seed
├─ docs/                  # 설계·API·model card
├─ reports/               # 품질·검증·manifest
├─ scripts/               # profiling·전처리
├─ docker-compose.yml
└─ README.md
~~~

## 🗃️ ERD

현재 ERD는 문서에 Mermaid로 관리되어 있습니다.

- [ERD 및 DB 설계 문서](docs/database-design.md)

![ERD 이미지](images/erd.png)

> images/erd.png는 실제 이미지가 추가되면 표시됩니다. [추가 필요]

## 🖥️ 주요 화면

| 화면 | 설명 | 스크린샷 |
|---|---|---|
| 홈 / | KBO 경기 일정·결과와 현재 가치 랭킹 | images/screenshots/home.png [추가 필요] |
| 선수 검색 /players | 이름·역할·시즌·팀 검색 | images/screenshots/players.png [추가 필요] |
| 선수 상세 /players/{id} | 기록·예측·성장곡선·전성기·유사 선수 | images/screenshots/player-detail.png [추가 필요] |
| 조건 검색 /discover | OPS·OBP·SLG·홈런·ERA·탈삼진 조건 탐색 | images/screenshots/discover.png [추가 필요] |
| 가치 랭킹 /rankings | 시즌·역할·팀별 AI 랭킹 | images/screenshots/rankings.png [추가 필요] |
| 선수 비교 /compare | 두 선수 Radar·Line Chart 비교 | images/screenshots/compare.png [추가 필요] |
| 구단 정보 /teams | 구단·로스터·전적·일정 | images/screenshots/teams.png [추가 필요] |

## 🧠 기술적 도전

### 진행 시즌과 학습 데이터의 경계

2026 시즌은 수집 시점에 따라 기록이 변합니다. 1982~2025 완결 시즌과 2026 진행 데이터를 별도 정제 폴더와 snapshot으로 관리하고, API 응답에 is_partial과 as_of_date를 포함했습니다.

### 외부 수집과 사용자 요청 분리

KBO 페이지를 매번 사용자 요청에서 직접 호출하면 지연과 외부 장애가 화면에 전파됩니다. 경기 일정·결과를 game_day_snapshots에 저장하고 저장 데이터를 우선 조회하며, 필요한 경우 최신 데이터를 수집해 저장합니다.

### 계층형 Backend

Router에는 SQL과 비즈니스 계산을 두지 않고, Service는 유스케이스와 도메인 예외를 담당하며, Repository는 SQLAlchemy 조회를 담당합니다. Repository Protocol로 DB 없이 Service를 테스트할 수 있습니다.

### 타격·투구 데이터 분리

타격과 투구는 지표 의미·결측 규칙·최소 자격 기준이 다릅니다. 별도 모델·스키마·특징 집합으로 관리해 통계 의미가 다른 데이터를 무리하게 통합하지 않았습니다.

### ML 추론 일관성

전처리기와 모델을 하나의 pipeline으로 저장하고 모델 버전·학습 기간·feature schema·평가 지표를 metadata로 기록합니다.

## 🛠️ 트러블 슈팅

### 1. KBO 최신 경기일과 저장 데이터 불일치

#### 문제

DB 최신 경기일이 오늘의 경기 상태를 반영하지 못할 수 있었습니다.

#### 원인

경기 결과는 시간이 지나며 완료 상태로 바뀌므로 DB의 최신 row만 조회하면 오래된 snapshot을 반환할 수 있습니다.

#### 해결 과정

서울 시간대 기준으로 오늘을 판단하고, 저장 snapshot이 오래되면 KBO 일정에서 최신 완료 경기일을 재수집하도록 수정했습니다. 수집 실패 시 기존 snapshot을 fallback으로 사용합니다.

#### 결과

최신 경기일 API가 최신화와 fallback을 갖게 되었고 응답은 game_day_snapshots에 저장됩니다.

### 2. 동일 원본 데이터 중복 적재

#### 문제

수집 스크립트를 반복 실행하면 같은 시즌 기록이 중복 적재될 수 있었습니다.

#### 원인

파일 동일성 확인 없이 적재하면 재실행과 새로운 데이터 갱신을 구분하기 어렵습니다.

#### 해결 과정

원본 SHA-256과 dataset 유형을 data_import_batches에 기록하고 동일 hash의 재적재를 차단했습니다. 적재는 transaction 단위로 처리하고 실패 시 rollback합니다.

#### 결과

원본 재현성과 적재 이력을 추적할 수 있게 되었습니다. 검증 리포트에는 타자 9,703행, 투수 7,625행의 적재 결과가 있습니다.

### 3. 동명이인 선수 식별

#### 문제

선수 이름만으로는 서로 다른 선수를 정확히 구분할 수 없습니다.

#### 원인

실제 데이터에서 타자 88개 이름, 투수 75개 이름에 동명이인이 확인되었습니다.

#### 해결 과정

KBO 원본 player_id를 내부 식별자로 사용하고, 검색 결과에 생년월일·팀·포지션을 함께 표시하도록 설계했습니다.

#### 결과

상세 조회는 이름이 아닌 player_id 기준으로 동작합니다.

### 4. 진행 데이터의 미래 정보 누수

#### 문제

2026 진행 기록을 과거 완결 시즌 학습 데이터에 섞으면 평가와 실제 예측 기준이 달라질 수 있습니다.

#### 원인

진행 중인 시즌은 수집 시점마다 변하고 다음 시즌 target이 완성되지 않았습니다.

#### 해결 과정

2026 데이터를 partial snapshot으로 분리하고 다음 시즌·전성기 예측은 완결 시즌 기준으로 학습·평가합니다. 연도 기반 split과 walk-forward validation을 사용합니다.

#### 결과

현재 기록 조회와 모델 학습 데이터의 사용 목적을 분리했습니다.

## 📈 성능 및 품질 개선

서비스 평균 latency, 동시 요청 처리량, cache hit ratio는 아직 별도 벤치마크하지 않았습니다. [추가 필요]

| 항목 | 적용 내용 | 확인된 결과 |
|---|---|---|
| DB 조회 | prefix 검색, 시즌·팀·역할 조건, 복합 인덱스 | 설계 검증 통과 |
| 적재 안정성 | SHA-256 batch, transaction rollback | 동일 hash 중복 적재 방지 |
| 스냅샷 조회 | 날짜별 JSON snapshot | 외부 수집 장애 시 fallback |
| ML 재현성 | pipeline·artifact checksum·metadata | checksum validation 통과 |
| Backend 품질 | Ruff, Pytest, MySQL smoke test | Pytest 37개 통과, 실패 0 |
| Frontend 품질 | TypeScript, ESLint, Vitest, build | Vitest 2개 통과, 실패 0 |
| 데이터 규모 | 1982~2025 완결 시즌 | 선수 3,506명, 타격 9,703행, 투구 7,625행 |

적용한 설계상 최적화는 목록 API page/page_size 제한, 선수 검색용 search_name 인덱스, 타격·투구 테이블 분리, 저장 모델 artifact 재사용, 경기 snapshot 우선 조회입니다.

## 🔌 API 예시

모든 API prefix는 /api/v1입니다. 전체 계약은 [API Contract](docs/api-contract.md)와 Swagger에서 확인할 수 있습니다.

| Method | URL | 설명 |
|---|---|---|
| GET | /players?query=이름&role=BATTING&season=2025 | 선수 검색·페이지 조회 |
| GET | /players/{player_id}/overview | 선수 프로필·시즌 기록 |
| GET | /players/{player_id}/benchmarks?role=BATTING&season=2025 | 리그 평균·백분위 |
| GET | /analytics/predictions/{role}/{player_id} | 다음 시즌 성적 예측 |
| GET | /analytics/similar/{role}/{player_id} | 유사 선수 추천 |
| GET | /analytics/discover?role=BATTING&season=2025&min_ops=0.8 | 조건 기반 탐색 |
| GET | /analytics/growth/{role}/{player_id} | 성장곡선 분석 |
| GET | /analytics/peak/{role}/{player_id} | 전성기 예측 |
| GET | /analytics/rankings?role=BATTING&season=2025 | AI 가치 랭킹 |
| GET | /teams/{team_code}/roster?season=2026 | 구단 1군 로스터 |
| GET | /teams/{team_code}/roster/changes?season=2026 | 등록·말소 |
| GET | /teams/games/latest?season=2026 | 최신 경기일 |
| GET | /teams/{team_code}/games/{game_id}?season=2026 | 경기 박스스코어 |
| GET | /health | Backend 상태 |

~~~bash
curl "http://localhost:8000/api/v1/players?query=김&role=BATTING&season=2025&page=1&page_size=20"
curl "http://localhost:8000/api/v1/analytics/rankings?role=BATTING&season=2025&limit=10"
~~~

## 🚀 실행 방법

### 사전 요구사항

- Python >=3.12,<3.15
- Node.js 및 npm
- MySQL 8.0
- ML 학습용 Backend optional dependencies
- TabPFN benchmark용 별도 환경

### Backend

~~~powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -e ".\\backend[dev]"
Copy-Item backend\\.env.example backend\\.env

Set-Location backend
..\\.venv\\Scripts\\python.exe -m alembic upgrade head
..\\.venv\\Scripts\\python.exe scripts\\import_data.py
..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload
~~~

API는 http://localhost:8000, Swagger는 http://localhost:8000/docs입니다.

### Frontend

~~~powershell
Set-Location frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
~~~

Web은 http://localhost:3000에서 실행합니다.

### AI·데이터 파이프라인

~~~powershell
Set-Location backend
..\\.venv\\Scripts\\python.exe -m pip install -e ".[ml]"
..\\.venv\\Scripts\\python.exe scripts\\train_next_season.py
..\\.venv\\Scripts\\python.exe scripts\\validate_recommendations.py
..\\.venv\\Scripts\\python.exe scripts\\validate_growth_analysis.py
..\\.venv\\Scripts\\python.exe scripts\\train_peak_models.py
..\\.venv\\Scripts\\python.exe scripts\\validate_value_ranking.py
~~~

2026 시즌 원본 수집:

~~~powershell
Set-Location ..
.\\.venv\\Scripts\\python.exe scripts\\fetch_kbo_2026.py --delay 1.0
.\\.venv\\Scripts\\python.exe scripts\\preprocess_data.py
~~~

원본 수집 전에는 [데이터 출처 및 사용 주의사항](docs/data-provenance.md)을 확인해야 합니다.

## ⚙️ 설치 및 환경 변수

### Backend .env

~~~env
APP_ENV=local
DATABASE_URL=mysql+pymysql://kbo_user:change_me@localhost:3306/kbo_stats?charset=utf8mb4
CORS_ORIGINS=["http://localhost:3000"]
SQL_ECHO=false
ML_N_JOBS=1
~~~

### Frontend .env.local

~~~env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
~~~

비밀번호와 운영 DB 정보는 .env에만 저장하고 Git에 커밋하지 않습니다. 운영 Secret·도메인은 [추가 필요]입니다.

## ☁️ 배포

저장소에는 Vercel Frontend, Railway 또는 Render Backend, MySQL 8.0, Dockerfile·docker-compose, GitHub Actions 경기 일정 수집 workflow 설정이 포함되어 있습니다.

배포 절차는 [배포 가이드](docs/deployment.md)를 참고하세요. 실제 운영 URL과 최종 smoke test 결과는 [추가 필요]이며, Docker CLI가 없는 환경에서는 Docker image build를 완료하지 못했습니다.

## 👤 팀 소개

| 구분 | 내용 |
|---|---|
| 프로젝트 유형 | 개인 프로젝트 |
| 개발자 | [이름·GitHub 프로필 추가 필요] |
| 개발 기간 | 2026-07-19 ~ 현재 진행 중 |
| 담당 | 데이터 수집·전처리, DB, Backend, ML, Frontend, 테스트, 배포 설정, 문서화 전체 |

## 📝 회고

### 배운 점

- 야구 시계열 데이터에서는 랜덤 분할보다 시즌 기준 검증과 미래 정보 통제가 중요합니다.
- ML 모델과 함께 데이터 계약, artifact 버전, 온라인 추론 경계를 설계해야 재현 가능한 기능이 됩니다.
- 외부 수집은 화면 기능과 분리하고 snapshot·fallback을 두어야 서비스 안정성을 확보할 수 있습니다.

### 아쉬운 점

- 실제 latency, 동시 요청 처리량, cache hit ratio 리포트가 없습니다. [추가 필요]
- 실제 운영 배포 주소와 시연 자료가 연결되지 않았습니다. [추가 필요]
- E2E 테스트와 Docker 실빌드는 현재 검증 범위에 포함되지 않았습니다.

### 다음 개선 사항

- [추가 필요] 운영 환경 latency·error rate·DB query plan 측정
- 주요 사용자 흐름 E2E 테스트 추가
- 운영 수집 job 모니터링·실패 알림·재시도 정책 보강
- 스크린샷·시연 영상·ERD 이미지·배포 링크 추가

## 📚 문서

- [전체 아키텍처](docs/architecture.md)
- [DB 설계 및 ERD](docs/database-design.md)
- [API 계약](docs/api-contract.md)
- [데이터 사전](docs/data-dictionary.md)
- [데이터 출처 및 사용 주의사항](docs/data-provenance.md)
- [데이터 품질 및 전처리 보고서](reports/data-quality-report.md)
- [모델 카드 모음](docs/)
- [배포 가이드](docs/deployment.md)
- [변경 이력](CHANGE.md)

## ⚠️ 데이터 이용 안내

이 서비스는 KBO 공식 기록실의 공개 데이터를 기반으로 비상업적 분석 목적으로 개발되었습니다. 데이터는 수집 시점에 따라 공식 기록과 차이가 있을 수 있으며, 원본 데이터 공개·재배포 전에는 [데이터 출처 및 사용 주의사항](docs/data-provenance.md)을 확인해야 합니다.
