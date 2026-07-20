# Database

MySQL 8.0 기준 DB 설계 파일입니다.

## 파일

- `migrations/001_initial_schema.sql`: 초기 실행 가능 DDL
- `seeds/teams.sql`: 원본 데이터의 23개 팀 seed
- [`../docs/database-design.md`](../docs/database-design.md): ERD와 설계 근거

## 적용 순서

MySQL database를 생성하고 선택한 뒤 다음 순서로 실행합니다.

```powershell
mysql --default-character-set=utf8mb4 -u <user> -p <database> < database/migrations/001_initial_schema.sql
mysql --default-character-set=utf8mb4 -u <user> -p <database> < database/seeds/teams.sql
```

현재 SQL 파일은 3단계 설계 계약입니다. 4단계에서는 SQLAlchemy 모델을 정의하고
Alembic migration으로 관리하므로 운영 배포에서 이 파일과 Alembic을 중복 적용하지
않습니다.

## 데이터 기반 검증

```powershell
python scripts/validate_db_design.py
```

검증 결과는 `reports/db_design_validation.json`에 저장됩니다.
