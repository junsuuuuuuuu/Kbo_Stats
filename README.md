# KBO AI Player Analytics

1982~2025 KBO 선수 시즌 기록을 바탕으로 검색, 비교, 성장 분석, 성적 예측,
유사 선수 추천 및 선수 가치 랭킹을 제공하는 AI 데이터 분석 플랫폼입니다.

단순 CRUD가 아니라 **재현 가능한 데이터 파이프라인**, **오프라인 ML 학습**,
**설명 가능한 온라인 추론**, **대화형 시각화**를 하나의 제품으로 구성하는 것을
목표로 합니다.

## 기술 스택

- Frontend: Next.js(App Router), TypeScript, Tailwind CSS, TanStack Query, Plotly
- Backend: FastAPI, SQLAlchemy, Pydantic, Pandas, NumPy
- ML: scikit-learn, LightGBM, XGBoost, TabPFN, SHAP
- Database: MySQL
- Deployment: Vercel(Frontend), Railway 또는 Render(Backend)

## 핵심 설계 원칙

- FastAPI는 Router → Service → Repository → Database의 계층형 구조를 사용합니다.
- HTTP 스키마, DB 모델, ML 입력 모델을 분리해 계층 간 결합을 줄입니다.
- CSV 적재와 모델 학습은 오프라인 작업으로, 예측 제공은 온라인 API로 분리합니다.
- 모델과 전처리기를 하나의 파이프라인으로 저장해 학습/추론 불일치를 방지합니다.
- 도메인별 Frontend 기능 모듈을 사용하고 서버 상태는 TanStack Query로 관리합니다.
- 모든 API는 `/api/v1` 하위에 버전 관리하며 공통 응답/예외 규약을 적용합니다.

## 문서

- [전체 프로젝트 아키텍처](docs/architecture.md)
- [데이터 사전](docs/data-dictionary.md)
- [데이터 출처 및 사용 주의사항](docs/data-provenance.md)
- [데이터 품질 및 전처리 보고서](reports/data-quality-report.md)
- [MySQL DB 설계 및 ERD](docs/database-design.md)
- [Backend REST API 계약](docs/api-contract.md)
- [다음 시즌 예측 모델 카드](docs/model-card-next-season.md)
- [AI 선수 추천 모델 카드](docs/model-card-player-recommendation.md)
- [선수 성장곡선 분석 모델 카드](docs/model-card-player-growth.md)
- [선수 전성기 예측 모델 카드](docs/model-card-player-peak.md)
- [AI 선수 가치 랭킹 모델 카드](docs/model-card-player-value-ranking.md)
- [배포 가이드](docs/deployment.md)
- [프로젝트 완료 보고서](docs/project-completion.md)

## 개발 단계

전체 10단계 구현과 로컬 검증을 완료했습니다.

- 완료: 다음 시즌 성적 예측
- 완료: 조건 검색 및 유사 선수 추천
- 완료: 선수 성장곡선 분석
- 완료: 선수 전성기 예측
- 완료: AI 선수 가치 랭킹
- 완료: 2026 구단별 1군 등록 로스터
- 완료: 선수 상세 연도별 커리어 기록 대시보드

- 완료: FastAPI ML API와 Swagger
- 완료: Next.js 반응형 UI와 Plotly 시각화
- 완료: Backend 테스트, Frontend typecheck·lint·production build, GitHub Actions CI
- 완료: Railway·Render·Vercel·Docker 배포 설정

> Docker CLI가 설치되지 않은 현재 로컬 환경에서는 이미지 실빌드까지 검증하지 못했습니다.
> Railway·Render·Vercel 배포도 계정과 배포 Secret을 설정한 뒤 최종 smoke test가 필요합니다.

1. 전체 프로젝트 아키텍처 설계
2. 데이터 분석 및 전처리
3. DB 설계
4. Backend 구축
5. ML 모델 개발
6. API 연결
7. Frontend 개발
8. 시각화
9. 테스트
10. 배포

각 단계는 검토 후 다음 단계로 진행하며, 기능 단위로 작게 구현합니다.

## 빠른 실행

Backend:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend:

```powershell
Set-Location frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

- Web: `http://localhost:3000`
- Swagger: `http://localhost:8000/docs`
- 배포 방법: [배포 가이드](docs/deployment.md)

## 데이터 분석 재현

원본 CSV는 `data/raw`, 정제 결과는 `data/processed`에 분리합니다.

```powershell
python scripts/profile_data.py
python scripts/preprocess_data.py
```

원본 및 정제 데이터의 공개·재배포 전에는 반드시
[데이터 출처 및 사용 주의사항](docs/data-provenance.md)을 확인하세요.

### 2026 시즌 진행 기록 수집

KBO 공식 기록 페이지에서 2026 시즌 기록만 로컬 snapshot으로 수집할 수 있습니다.
시즌 중 데이터이므로 수집일 기준의 미완료 기록이며 기존 1982~2025 학습 데이터에는
자동으로 합치지 않습니다.

```powershell
.\.venv\Scripts\python.exe scripts\fetch_kbo_2026.py --delay 1.0
```

- 결과: `data/raw/kbo_batting_stats_season_2026_partial.csv`
- 결과: `data/raw/kbo_pitching_stats_season_2026_partial.csv`
- 품질 요약: `reports/kbo-2026-snapshot.json`

원본 snapshot은 Git에서 제외됩니다. 재수집 전 KBO 이용정책과 robots.txt를 확인하고,
서버 부하 방지를 위해 요청 간격을 1초 미만으로 낮추지 마세요.

수집한 진행 기록을 로컬 MySQL과 선수 상세 화면에 반영하려면 다음 명령을 실행합니다.
2026 전용 정제 폴더를 사용하므로 기존 1982~2025 학습 데이터는 변경되지 않습니다.

```powershell
.\.venv\Scripts\python.exe scripts\preprocess_data.py `
  --batting data\raw\kbo_batting_stats_season_2026_partial.csv `
  --pitching data\raw\kbo_pitching_stats_season_2026_partial.csv `
  --output-dir data\processed\2026 `
  --manifest reports\kbo-2026-preprocessing.json

Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe scripts\import_2026_data.py
```

API는 2026 기록에 `is_partial: true`와 수집 기준일 `as_of_date`를 반환합니다. 선수 화면의
다음 시즌·전성기 예측 모델은 계속 2025까지의 완결 시즌만 사용합니다. 가치 랭킹은
2020~2026을 선택할 수 있으며, 2026 랭킹만 최신 수집일 기준의 진행 중 기록으로 계산합니다.

### 2026 구단별 1군 로스터

KBO 공식 선수 등록 현황에서 10개 구단의 날짜별 1군 등록 명단을 수집합니다. 감독과
코치는 제외하며, 투수·포수·내야수·외야수만 기존 KBO `player_id`와 연결합니다.

```powershell
.\.venv\Scripts\python.exe scripts\fetch_kbo_2026_rosters.py --delay 1.0

Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe scripts\import_2026_rosters.py
```

- 화면: `/teams`, `/teams/{team_code}`
- API: `GET /api/v1/teams?season=2026`
- API: `GET /api/v1/teams/{team_code}/roster?season=2026`
- 품질 요약: `reports/kbo-2026-roster-snapshot.json`

등록 명단은 경기 출전 선수 전체나 구단 소속 선수 전체가 아니라 해당 기준일의 1군
등록 snapshot입니다. 원본 CSV는 다른 KBO 원본 데이터와 동일하게 Git에서 제외됩니다.
