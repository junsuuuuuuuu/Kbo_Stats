# 배포 가이드

## 구성

- Frontend: Vercel, 프로젝트 Root Directory `frontend`
- Backend: Railway 권장 또는 Render, 저장소 루트 Docker context
- Database: Railway MySQL plugin 또는 외부 MySQL 8

## Backend 환경변수

```text
APP_ENV=production
DATABASE_URL=mysql+pymysql://<user>:<encoded-password>@<host>:3306/<database>?charset=utf8mb4
CORS_ORIGINS=["https://<vercel-domain>"]
ML_N_JOBS=1
```

비밀번호의 `@`, `:`, `/`, `#` 등은 URL encoding해야 한다. 실제 값은 플랫폼 Secret에만
저장하고 저장소에 커밋하지 않는다.

## Railway

1. 저장소를 Railway 프로젝트에 연결한다.
2. MySQL 서비스를 추가하고 `DATABASE_URL`을 SQLAlchemy PyMySQL 형식으로 설정한다.
3. 저장소 루트의 `railway.json`을 사용한다.
4. pre-deploy 단계에서 Alembic migration이 실행된다.
5. `/api/v1/health`가 성공한 후 트래픽을 받는다.
6. 최초 1회 `python scripts/import_data.py`를 Railway shell에서 실행한다.

## Render

`render.yaml` Blueprint를 사용한다. Render는 관리형 MySQL을 제공하지 않으므로 외부 MySQL
접속 URL을 `DATABASE_URL` Secret으로 입력한다. ML 라이브러리 메모리를 고려해 인스턴스
크기를 선택한다.

## Vercel

1. 같은 저장소를 새 Vercel 프로젝트에 연결한다.
2. Root Directory를 `frontend`로 지정한다.
3. `NEXT_PUBLIC_API_URL`에 배포된 Backend의 `/api/v1` URL을 입력한다.
4. Backend `CORS_ORIGINS`를 실제 Vercel 도메인으로 갱신한 뒤 재배포한다.

## Docker 로컬 검증

```powershell
docker compose up --build
```

Backend container는 시작 전에 Alembic migration을 자동 실행한다. 첫 실행 후 CSV를 적재한다.

```powershell
docker compose exec backend python scripts/import_data.py
```

MySQL volume과 플랫폼 DB는 별도 backup 정책을 적용한다. 모델 artifact는 이미지에 포함되며
새 모델 버전은 학습·테스트 후 이미지 재배포로 반영한다.

현재 개발 환경에는 Docker CLI가 없어 Compose 이미지 실빌드는 미검증 상태다. Docker가
설치된 환경에서 `docker compose up --build`와 health check를 최종 확인해야 한다.
