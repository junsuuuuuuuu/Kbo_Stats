# KBO AI Player Analytics Frontend

Next.js App Router, TypeScript, Tailwind CSS, TanStack Query와 Plotly로 구성한 분석 UI입니다.

## 로컬 실행

```powershell
Set-Location frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

`http://localhost:3000`에서 접속하며 FastAPI가 `http://localhost:8000`에서 실행 중이어야
합니다.

## 화면

- `/`: 프로젝트 소개와 타자 가치 TOP5
- `/players`: 선수 검색
- `/players/{id}`: 시즌 기록, 예측, 성장곡선, 전성기, 유사 선수, PCA
- `/discover`: 나이·OPS·ERA 등 조건 스카우팅
- `/rankings`: 시즌별 AI 가치 랭킹
- `/compare`: 두 선수 Radar/Line Chart 비교

## 품질 검사

```powershell
npm run typecheck
npm run lint
npm run build
```

## Vercel

Vercel 프로젝트 Root Directory를 `frontend`로 지정하고 다음 환경변수를 설정합니다.

```text
NEXT_PUBLIC_API_URL=https://<backend-domain>/api/v1
```
