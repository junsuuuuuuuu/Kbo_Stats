# KBO AI Player Analytics Backend

FastAPI와 SQLAlchemy 2.x로 구현한 계층형 Backend입니다. 현재 4단계에서는 선수 검색,
기본 정보 및 시즌 기록 조회 API를 제공합니다.

## 계층 구조

```text
app/
├─ api/             # HTTP 입력/출력과 dependency wiring
├─ core/            # 설정과 애플리케이션 예외
├─ database/        # Session, Base, CSV 적재기
├─ models/          # SQLAlchemy 영속성 모델
├─ repositories/    # SQL과 loading 전략
├─ schemas/         # Pydantic 요청/응답 계약
├─ services/        # 검색/상세 유스케이스와 도메인 규칙
└─ main.py          # application factory, middleware, exception handler
```

Router에는 SQL을 작성하지 않고, Repository에는 HTTP 예외를 작성하지 않습니다.
Service는 Repository Protocol에 의존하므로 DB 없이 단위 테스트할 수 있습니다.

## 로컬 실행 준비

프로젝트 루트에서 가상환경과 의존성을 설치합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
Copy-Item backend\.env.example backend\.env
```

`backend/.env`의 `DATABASE_URL`을 로컬 MySQL 8.0 접속 정보로 변경합니다. 비밀번호가
포함된 `.env`는 Git에 커밋하지 않습니다.

## Migration과 데이터 적재

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe scripts\import_data.py
```

Migration이 23개 팀 seed를 먼저 넣고, 적재기가 타자와 투수 파일을 별도 transaction으로
적재합니다. 동일 원본 SHA-256은 다시 적재하지 않습니다.

## API 실행

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/api/v1/health`
- AI Analytics: `http://localhost:8000/api/v1/analytics/*`

## 품질 검사

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m ruff check app scripts tests alembic
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

마지막 명령은 DB 연결 없이 MySQL용 migration SQL을 생성해 문법과 revision 순서를
확인합니다.

## ML 학습

기본 ML 선택 의존성과 TabPFN 호환 환경을 분리합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".\backend[ml]"
py -3.13 -m venv .venv-tabpfn
.\.venv-tabpfn\Scripts\python.exe -m pip install -e ".\backend[tabpfn]"

Set-Location backend
..\.venv\Scripts\python.exe scripts\train_next_season.py
..\.venv-tabpfn\Scripts\python.exe scripts\benchmark_tabpfn.py
..\.venv\Scripts\python.exe scripts\validate_recommendations.py
..\.venv\Scripts\python.exe scripts\validate_growth_analysis.py
..\.venv\Scripts\python.exe scripts\train_peak_models.py
..\.venv\Scripts\python.exe scripts\validate_value_ranking.py
```

평가 방법과 해석상의 한계는
[`../docs/model-card-next-season.md`](../docs/model-card-next-season.md)를 참고합니다.
AI 선수 추천의 후보 기준과 점수 계산 방식은
[`../docs/model-card-player-recommendation.md`](../docs/model-card-player-recommendation.md)를
참고합니다.
성장률과 급성장·하락 판정 규칙은
[`../docs/model-card-player-growth.md`](../docs/model-card-player-growth.md)를 참고합니다.
전성기 label, 시간 코호트 평가와 한계는
[`../docs/model-card-player-peak.md`](../docs/model-card-player-peak.md)를 참고합니다.
