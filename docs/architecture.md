# KBO AI Player Analytics 전체 아키텍처

## 1. 설계 목표

이 문서는 구현 전 시스템 경계와 책임을 합의하기 위한 1단계 산출물이다.
구체적인 CSV 컬럼, 데이터 타입, 결측률과 실제 표본 수는 2단계 탐색적 데이터
분석(EDA) 결과를 근거로 확정한다.

설계의 우선순위는 다음과 같다.

1. 데이터 누수를 방지한 신뢰 가능한 ML 평가
2. 변경하기 쉬운 계층 및 도메인 경계
3. 학습과 서비스 추론의 일관성
4. 사용자에게 예측/추천 근거를 설명할 수 있는 구조
5. 포트폴리오에서 기술적 의사결정을 재현할 수 있는 문서화

## 2. 시스템 구성

```text
사용자 브라우저
    │
    ▼
Next.js (Vercel)
  - App Router / 화면 조합
  - TanStack Query / 서버 상태
  - Plotly / 대화형 차트
    │ HTTPS / JSON
    ▼
FastAPI (Railway 또는 Render)
  Router → Service → Repository → SQLAlchemy
               │              │
               │              ▼
               │            MySQL
               ▼
         ML Inference
         - 저장된 Pipeline
         - 모델 메타데이터
         - SHAP 설명 결과

오프라인 파이프라인
  CSV 2개 → 검증/정제 → MySQL 적재
  MySQL/정제 데이터 → 특징 생성 → 시계열 검증 → 모델 저장
```

브라우저는 DB나 모델에 직접 접근하지 않는다. FastAPI가 도메인 규칙과 접근
권한의 단일 진입점이 되며, 모델 학습은 API 요청 중 실행하지 않는다.

## 3. 모노레포 구조

```text
Kbo_Stats/
├─ README.md
├─ docs/
│  ├─ architecture.md
│  ├─ data-dictionary.md          # 2단계
│  ├─ database-design.md          # 3단계
│  ├─ api-contract.md             # 4~6단계
│  └─ model-card.md               # 5단계
├─ data/
│  ├─ raw/                        # 원본 CSV, 수정 금지
│  └─ processed/                  # 재생성 가능한 중간 결과
├─ backend/
│  ├─ app/
│  │  ├─ main.py                  # 앱 생성 및 Router 등록
│  │  ├─ core/                    # 설정, 로깅, 예외, 보안/CORS
│  │  ├─ database/                # Engine, Session, Base, migration 연결
│  │  ├─ models/                  # SQLAlchemy 영속성 모델
│  │  ├─ schemas/                 # Pydantic 요청/응답 DTO
│  │  ├─ repositories/            # DB 조회와 저장만 담당
│  │  ├─ services/                # 유스케이스와 도메인 규칙
│  │  ├─ routers/v1/              # HTTP 변환과 의존성 주입
│  │  ├─ ml/
│  │  │  ├─ features/             # 공용 특징 생성
│  │  │  ├─ training/             # 학습/평가/튜닝
│  │  │  ├─ inference/            # 모델 로딩/예측
│  │  │  ├─ explainability/       # SHAP 및 추천 이유
│  │  │  └─ artifacts/            # 버전이 지정된 모델 산출물
│  │  └─ utils/                   # 도메인 비종속 소형 유틸리티
│  ├─ scripts/                    # CSV 적재, 학습 CLI
│  ├─ alembic/                    # DB migration
│  └─ tests/
│     ├─ unit/
│     ├─ integration/
│     └─ api/
└─ frontend/
   ├─ src/
   │  ├─ app/                     # 라우트, layout, error/loading UI
   │  ├─ components/              # 범용 UI 컴포넌트
   │  ├─ features/                # players/predictions/recommendations 등
   │  ├─ hooks/                   # 범용 React hooks
   │  ├─ lib/                     # QueryClient, Plotly, formatter
   │  ├─ api/                     # 타입 안전 API client
   │  └─ types/                   # 공용 TypeScript 타입
   └─ tests/
```

`utils`를 만능 폴더로 사용하지 않는다. 선수 검색, 성장곡선, 추천처럼 도메인에
속한 로직은 각각의 Service 또는 `features` 안에 둔다.

## 4. Backend 계층별 책임

### Router

- URL, Query/Path parameter와 HTTP 상태 코드를 정의한다.
- Pydantic으로 입력을 검증하고 Response Model을 명시한다.
- DB Session과 Service를 의존성 주입으로 전달한다.
- 비즈니스 계산이나 SQL을 작성하지 않는다.

### Service

- 검색, 비교, 성장 시즌 탐지, 예측, 추천 등 유스케이스를 구현한다.
- 여러 Repository 및 ML inference 결과를 조합한다.
- 도메인 예외를 발생시키며 FastAPI 예외에 직접 의존하지 않는다.

### Repository

- SQLAlchemy 쿼리와 영속성만 담당한다.
- ORM 객체를 외부 응답 형식으로 직접 노출하지 않는다.
- 인터페이스를 통해 Service와 분리해 단위 테스트 대역 사용을 쉽게 한다.

### ML

- 특징 생성 코드는 학습과 추론이 함께 사용한다.
- 모델 로더는 애플리케이션 시작 시 필요한 artifact를 한 번 로드하고 재사용한다.
- 모델 버전, 학습 기간, feature 목록과 평가지표를 모델 메타데이터에 기록한다.

## 5. 도메인 모듈

| 모듈 | 책임 | 주요 결과 |
|---|---|---|
| Players | 이름 검색, 기본 정보, 시즌 기록 | 선수 목록/상세 |
| Analytics | 성장률, 급성장/하락 탐지 | 커리어 시계열 분석 |
| Predictions | 다음 시즌 및 전성기 예측 | 예측값, 구간, 모델 정보 |
| Recommendations | 조건 필터, 유사 선수 검색 | TOP N, 유사도, 추천 이유 |
| Rankings | 정규화된 AI Score 산출 | 시즌별/팀별 순위 |
| Comparisons | 동일 기준으로 두 선수 통계 정규화 | Radar/Bar/Line용 데이터 |

타자와 투수는 공통 선수 정보만 공유하고, 통계 스키마와 특징 집합은 분리한다.
두 역할을 모두 수행한 선수도 표현할 수 있도록 선수의 역할을 단일 enum 값으로
고정하지 않는다.

## 6. 데이터 및 DB 경계 초안

CSV는 유일한 원천 데이터(source of truth)이며 원본 파일을 직접 수정하지 않는다.
DB는 조회 성능과 무결성을 위한 서비스 저장소로 사용한다.

예상 핵심 엔터티는 다음과 같다.

- `players`: 내부 선수 식별자와 정규화된 이름
- `teams`: 팀 식별자, 표시명
- `batting_season_stats`: 선수-시즌-팀 단위 타격 기록
- `pitching_season_stats`: 선수-시즌-팀 단위 투구 기록
- `model_versions`: 모델 종류, 버전, 학습 범위, 지표, artifact 위치
- `prediction_results`: 필요할 때만 예측 캐시와 생성 시점 저장

정확한 테이블, PK/FK, 인덱스, 숫자 정밀도는 3단계에서 확정한다. 동일 선수가 한
시즌에 여러 팀에서 뛴 경우와 합계 행의 존재 여부는 2단계에서 확인 후 중복 계산
규칙을 정한다.

### 데이터 제약 위험

요구사항에는 25세 이하 검색과 Peak Age 예측이 있지만, 현재 보장된 컬럼은
`Player`, `Season`, `Team` 및 시즌 기록뿐이다. 생년월일이나 나이 컬럼이 두 CSV에
없다면 외부 데이터를 추가하지 않는 조건에서는 실제 나이를 계산할 수 없다.
이 경우 2단계 결과에 따라 다음 중 하나로 범위를 정해야 한다.

- 나이 컬럼이 있으면 검증 후 기능을 유지한다.
- 나이 컬럼이 없으면 `데뷔 후 N년차` 기반 분석으로 대체하고 한계를 명시한다.
- 외부 데이터 사용 승인을 별도로 받아 선수 생년 정보를 추가한다.

동명이인을 구분할 고유 ID가 없다면 이름만으로 완전한 식별이 불가능하다는 점도
동일하게 데이터 품질 보고서에 기록한다.

## 7. API 경계 초안

모든 endpoint는 `/api/v1`을 prefix로 사용한다.

```text
GET  /players                         선수 검색/필터/페이지네이션
GET  /players/{player_id}             선수 기본 정보
GET  /players/{player_id}/seasons     시즌별 타격/투구 기록
GET  /players/{player_id}/growth      성장곡선과 변곡 시즌
POST /comparisons                     두 선수 비교 데이터
POST /predictions/next-season         다음 시즌 예측
POST /predictions/peak                전성기 예측
GET  /recommendations/similar/{id}    유사 선수 TOP N
POST /recommendations/filter          조건 기반 추천
GET  /rankings                         시즌별/팀별 AI 랭킹
GET  /models/metrics                  모델별 평가 결과
GET  /health                          배포 상태 확인
```

목록 API에는 기본 페이지 크기와 최대 크기를 둔다. 응답은 기능별 명시적 Pydantic
모델을 사용하며, 오류는 아래와 같은 일관된 형태를 사용한다.

```json
{
  "error": {
    "code": "PLAYER_NOT_FOUND",
    "message": "선수를 찾을 수 없습니다.",
    "details": null
  }
}
```

차트 API는 Plotly 설정 전체가 아니라 `season`, `metric`, `value`, 비교 기준처럼
도메인 데이터를 반환한다. 표현 방식은 Frontend가 결정한다.

## 8. ML 아키텍처

### 다음 시즌 예측

- 하나의 행은 선수의 특정 기준 시즌이며 target은 그 다음 시즌 성적이다.
- 최근 3~5년 lag, 이동 평균, 변동성, 출장량, 직전 시즌 추세를 후보 특징으로 둔다.
- 타율/OPS/홈런과 ERA/탈삼진은 target별 모델로 분리한다.
- RandomForest를 baseline으로 두고 LightGBM, XGBoost, TabPFN과 비교한다.
- 선수의 미래 시즌이 학습 데이터에 섞이지 않도록 연도 기반 split과 walk-forward
  validation을 사용한다. 무작위 K-Fold는 기본 평가로 사용하지 않는다.
- MAE, RMSE, R²를 함께 기록하되 표본 수와 단순 baseline(직전 시즌 값)도 비교한다.

### 추천과 랭킹

- 유사 선수 추천은 포지션/역할 및 비교 시즌을 먼저 제한한 뒤 표준화한다.
- Cosine Similarity와 KNN을 같은 feature matrix에서 평가한다.
- PCA는 2차원 설명용 시각화에만 사용하고 원본 유사도와 혼동하지 않는다.
- 추천 이유는 유사도에 가장 크게 기여한 지표 차이를 기반으로 생성한다.
- AI Score의 가중치, 스케일링 범위, 최소 출장 기준을 버전 관리한다.
- 투수의 ERA처럼 낮을수록 좋은 지표는 방향을 반전한 뒤 합성한다.

### 전성기 예측

나이 데이터가 존재한다는 전제에서만 Peak Age를 학습한다. 선수별 커리어 길이에
따른 생존 편향과 아직 전성기를 지나지 않은 현역 선수의 우측 중도절단을 분석한다.
데이터가 부족하면 복잡한 모델보다 연령별 스무딩 성장곡선을 baseline으로 제시한다.

### 산출물

모델 artifact에는 전처리기, feature 순서, estimator를 함께 저장한다. 별도 JSON
metadata에는 다음 정보를 기록한다.

- 모델명과 semantic version
- 학습 데이터 시작/종료 시즌 및 생성 시각
- feature 목록, target, 전처리 버전
- validation 방식과 MAE/RMSE/R²
- Python 및 핵심 라이브러리 버전

SHAP은 비용이 크므로 공통/global 설명은 학습 시 생성하고, 개별/local 설명은
상위 feature만 반환하거나 캐시한다.

## 9. Frontend 아키텍처

예상 route는 다음과 같다.

```text
/                          대시보드 및 통합 검색
/players                   선수 검색/조건 필터
/players/[playerId]        상세, 시즌 기록, 성장곡선, 예측
/compare                   선수 비교
/recommendations           조건/유사 선수 추천
/rankings                  시즌/팀별 AI 랭킹
/models                    모델 성능과 설명
```

- Server Component는 초기 화면 뼈대와 SEO가 필요한 영역에 사용한다.
- 검색, 차트 조작, 비교 선택처럼 상호작용이 필요한 부분만 Client Component로 둔다.
- API 호출은 `features` 내부 Query hook으로 감싸고 컴포넌트에서 URL을 직접 만들지
  않는다.
- 로딩은 route-level `loading.tsx`와 component skeleton을 함께 사용한다.
- 예상 오류는 사용자 메시지와 재시도 UI로, 예상하지 못한 오류는 `error.tsx`로
  처리한다.
- Dark Mode 색상은 CSS 변수와 Tailwind token으로 관리하고 차트 색상에도 같은
  token을 적용한다.
- Backend 응답 타입과 화면 전용 view model을 분리한다.

## 10. 설정, 관측성과 보안

- Backend 설정은 Pydantic Settings, Frontend 공개 설정은 `NEXT_PUBLIC_` 환경변수로
  관리하며 secret을 저장소에 커밋하지 않는다.
- 개발/배포 환경의 CORS origin을 명시적으로 제한한다.
- 구조화 로그에 request ID, route, status, latency를 기록하되 개인정보는 남기지
  않는다.
- `/health`는 process 상태, 필요 시 `/ready`는 DB 및 모델 준비 상태를 구분한다.
- 입력 범위, 정렬 컬럼과 페이지 크기를 allowlist로 제한한다.
- 학습 중 경고와 API 오류를 무시하지 않고 모델/도메인 예외로 분류한다.

## 11. 테스트 전략

```text
Unit        Service 계산, feature engineering, formatter
Integration Repository ↔ 테스트 DB, 모델 artifact 로딩
API         상태 코드, response schema, 예외 계약
Frontend    컴포넌트 상태와 사용자 상호작용
E2E         검색 → 상세 → 비교/예측의 핵심 사용자 흐름
ML          데이터 누수, feature 순서, 재현성, 성능 하한
```

테스트 피라미드를 유지하며 ML 성능 테스트는 동일 seed와 고정 validation 구간에서
baseline 대비 허용 기준을 확인한다.

## 12. 단계별 산출물과 완료 기준

| 단계 | 주요 산출물 | 완료 기준 |
|---|---|---|
| 1. 아키텍처 | README, 본 문서 | 경계/책임/위험 합의 |
| 2. 데이터 분석 | EDA, 데이터 사전, 정제 규칙 | 컬럼·결측·중복·범위 검증 |
| 3. DB 설계 | ERD, migration, 적재 설계 | 무결성/인덱스/재적재 검증 |
| 4. Backend | 계층형 앱, 핵심 조회 API | 테스트와 Swagger 계약 통과 |
| 5. ML | baseline/후보 모델, model card | 누수 없는 평가 및 artifact 저장 |
| 6. API 연결 | 추론/추천/랭킹 endpoint | 모델 버전 포함 응답 검증 |
| 7. Frontend | route와 기능 UI | 타입/상태/반응형 동작 |
| 8. 시각화 | Plotly chart와 설명 UI | 모바일/다크모드/접근성 검토 |
| 9. 테스트 | 통합/E2E/성능 점검 | 핵심 흐름 자동화 및 품질 기준 통과 |
| 10. 배포 | Vercel/Backend/MySQL 설정 | health check와 운영 문서 확인 |

## 13. 주요 아키텍처 결정 기록

1. **모노레포**: Frontend, Backend, 문서와 ML 계약을 한 변경 단위로 추적한다.
2. **계층형 Backend**: 작은 초기 규모에서도 SQL/HTTP/도메인/ML 책임을 분리한다.
3. **오프라인 학습**: API 안정성과 배포 재현성을 위해 요청 중 학습하지 않는다.
4. **연도 기반 검증**: 야구 시계열의 미래 정보 누수를 방지한다.
5. **도메인 데이터 API**: Plotly에 종속된 JSON을 Backend가 만들지 않는다.
6. **타자/투수 모델 분리**: 의미와 분포가 다른 지표를 무리하게 하나로 합치지 않는다.
