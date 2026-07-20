# Backend REST API 계약

## 1. 공통 규칙

- Base URL: `/api/v1`
- Content-Type: `application/json`
- 선수 식별자: KBO `player_id`
- 목록 기본 페이지 크기: 20, 최대 100
- 응답 헤더: `X-Request-ID`
- Swagger: `/docs`
- OpenAPI JSON: `/openapi.json`

예상 오류는 공통 envelope로 반환한다.

```json
{
  "error": {
    "code": "PLAYER_NOT_FOUND",
    "message": "선수를 찾을 수 없습니다.",
    "details": {"player_id": 99999}
  }
}
```

## 2. Health

### `GET /api/v1/health`

DB와 무관하게 API process의 생존 여부를 반환한다. 배포 플랫폼의 liveness check에
사용한다.

```json
{"status": "ok", "environment": "local"}
```

## 3. 선수 검색

### `GET /api/v1/players`

| Query | 타입 | 필수 | 설명 |
|---|---|:---:|---|
| `query` | string | N | 공백이 제거된 선수명 prefix 검색 |
| `role` | `BATTING \| PITCHING` | N | 역할 필터 |
| `season` | integer | N | 1982~2200 시즌 필터 |
| `team` | string | N | 원본 팀 표시명 exact filter |
| `page` | integer | N | 기본 1 |
| `page_size` | integer | N | 기본 20, 최대 100 |

동명이인을 구분할 수 있도록 생년월일과 역할을 함께 반환한다.

```json
{
  "items": [
    {
      "player_id": 68050,
      "player_name": "김도영",
      "birth_date": "2003-10-02",
      "roles": ["BATTING"]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

## 4. 선수 기본 정보

### `GET /api/v1/players/{player_id}`

선수 공통 신원과 타자/투수 출처별 프로필을 반환한다. 두 CSV의 투타/신체 정보가
다를 수 있으므로 profile에 `role`을 포함한다.

- `200`: 선수 상세
- `404 PLAYER_NOT_FOUND`: 존재하지 않는 선수 ID
- `422 VALIDATION_ERROR`: 0 이하 ID 등 잘못된 입력

## 5. 선수 시즌 기록

### `GET /api/v1/players/{player_id}/seasons`

선택 Query `role`을 생략하면 타격과 투구 기록을 모두 반환한다. `role=BATTING` 또는
`role=PITCHING`을 지정하면 요청하지 않은 테이블은 조회하지 않는다.

```json
{
  "player_id": 68050,
  "batting": [
    {
      "season": 2026,
      "is_partial": true,
      "as_of_date": "2026-07-20",
      "age": 23,
      "team": "KIA",
      "position": "3B",
      "games": 141,
      "batting_average": 0.347,
      "on_base_plus_slugging": 1.067
    }
  ],
  "pitching": []
}
```

실제 응답에는 데이터 사전에 정의된 모든 누적/비율 기록이 포함된다. 투수 이닝은
사용자 표시용 `innings_pitched`와 계산용 `innings_pitched_outs`를 함께 제공한다.
진행 중 시즌은 `is_partial=true`이며 `as_of_date`가 해당 누적 기록의 기준일이다.

## 6. 계층별 오류 처리

```text
Pydantic 입력 실패 → VALIDATION_ERROR / 422
Service 선수 없음   → PLAYER_NOT_FOUND / 404
예상하지 못한 오류  → INTERNAL_SERVER_ERROR / 500
```

내부 stack trace와 DB 오류 문자열은 API 응답에 노출하지 않고 서버 로그에만 기록한다.

## 7. AI 분석 API

모든 역할 값은 `batting` 또는 `pitching`을 사용한다.

| Method | Path | 설명 |
|---|---|---|
| GET | `/analytics/predictions/{role}/{player_id}` | 다음 시즌 AVG·OPS·HR 또는 ERA·SO 예측 |
| GET | `/analytics/similar/{role}/{player_id}` | Cosine·KNN TOP10과 PCA 좌표 |
| GET | `/analytics/discover` | 나이·OPS·OBP·HR·ERA·SO 조건 검색 |
| GET | `/analytics/growth/{role}/{player_id}` | 성장률, 급성장·하락 이벤트와 곡선 |
| GET | `/analytics/peak/{role}/{player_id}` | Peak Age와 Peak 기록 예측 |
| GET | `/analytics/rankings` | 시즌·팀별 AI 가치 랭킹 |

분석 최소 표본을 만족하지 못하면 `404 ANALYTICS_NOT_AVAILABLE`을 반환한다. 실제 Query의
범위, 기본값과 모든 응답 필드는 실행 중인 `/docs`의 OpenAPI 문서를 단일 기준으로 사용한다.
