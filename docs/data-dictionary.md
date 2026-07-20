# KBO 데이터 사전

## 1. 데이터셋 기준

- 원본 범위: 1982~2025 시즌
- 원본 인코딩: UTF-8
- 핵심키: `player_id + season + team`
- 선수 식별: 이름이 아닌 KBO `player_id` 사용
- 나이 정의: `season - 출생연도`인 시즌 연도 기준 나이
- 구조적 결측은 0으로 바꾸지 않고 `NULL`로 유지

원본 컬럼은 대문자 약어가 많아 정제본에서 snake_case 의미명으로 변환했다.
아래 타입은 향후 DB 설계 시 사용할 논리 타입이며 실제 MySQL 타입은 3단계에서
확정한다.

## 2. 공통 컬럼

| 정제 컬럼 | 논리 타입 | NULL | 설명 |
|---|---:|:---:|---|
| `player_id` | integer | N | KBO 선수 고유 ID |
| `source_url` | string | N | 원본에 포함된 KBO 선수 페이지 URL |
| `player_name` | string | N | 선수 표시명, 식별키로 사용하지 않음 |
| `age` | integer | N | 시즌 연도에서 출생연도를 뺀 나이 |
| `birth_date` | date | N | 생년월일 |
| `position` | string | N | P/C/IF/OF 등 원본 대표 포지션 |
| `bat_throw` | string | N | 타격/투구 손 조합(예: R/R, L/L) |
| `height_weight` | string | Y | 원본 신장/체중 표시값 |
| `height_cm` | integer | Y | `height_weight`에서 추출한 신장(cm) |
| `weight_kg` | integer | Y | `height_weight`에서 추출한 체중(kg) |
| `career` | string | Y | 원본 경력 문자열 |
| `draft` | string | Y | 원본 지명 정보 |
| `season` | integer | N | 시즌 연도 |
| `team` | string | N | 해당 시즌 원본 팀명 |
| `age_was_corrected` | boolean | N | 원본 나이를 생년 기준으로 교정했는지 여부 |

`position`, `height_weight`, `career`, `draft`는 선수 페이지의 대표 정보일 수 있어
반드시 시즌 당시 상태를 나타낸다고 가정하지 않는다.

## 3. 타격 기록

| 정제 컬럼 | 원본 | 논리 타입 | NULL | 설명 |
|---|---|---:|:---:|---|
| `games` | G | integer | N | 경기 |
| `plate_appearances` | PA | integer | N | 타석 |
| `at_bats` | AB | integer | N | 타수 |
| `runs` | R | integer | N | 득점 |
| `hits` | H | integer | N | 안타 |
| `doubles` | 2B | integer | N | 2루타 |
| `triples` | 3B | integer | N | 3루타 |
| `home_runs` | HR | integer | N | 홈런 |
| `total_bases` | TB | integer | N | 루타 |
| `runs_batted_in` | RBI | integer | N | 타점 |
| `stolen_bases` | SB | integer | N | 도루 성공 |
| `caught_stealing` | CS | integer | N | 도루 실패 |
| `walks` | BB | integer | N | 볼넷 |
| `hit_by_pitch` | HBP | integer | N | 사구 |
| `strikeouts` | SO | integer | N | 삼진 |
| `grounded_into_double_play` | GDP | integer | N | 병살타 |
| `sacrifice_flies` | SF | integer | N | 희생플라이 |
| `sacrifice_hits` | SH | integer | N | 희생번트 |
| `errors` | E | integer | N | 실책 |
| `batting_average` | AVG | decimal | Y | 타율, 0타수이면 NULL |
| `slugging_percentage` | SLG | decimal | Y | 장타율, 0타수이면 NULL |
| `on_base_percentage` | OBP | decimal | Y | 출루율, 0타수이면 NULL |
| `on_base_plus_slugging` | OPS | decimal | Y | OPS, 0타수이면 NULL |

## 4. 투구 기록

| 정제 컬럼 | 원본 | 논리 타입 | NULL | 설명 |
|---|---|---:|:---:|---|
| `earned_run_average` | ERA | decimal | Y | 평균자책점, 0이닝이면 NULL |
| `games` | G | integer | N | 경기 |
| `complete_games` | CG | integer | N | 완투 |
| `shutouts` | SHO | integer | N | 완봉 |
| `wins` | W | integer | N | 승 |
| `losses` | L | integer | N | 패 |
| `saves` | SV | integer | N | 세이브 |
| `holds` | HLD | integer | N | 홀드 |
| `winning_percentage` | WPCT | decimal | Y | 승률, 승패 결정이 없으면 NULL |
| `batters_faced` | TBF | integer | N | 상대 타자 수 |
| `innings_pitched_display` | IP | string | N | `10 1/3` 형태의 표시용 원본 이닝 |
| `innings_pitched_outs` | 파생 | integer | N | 계산용 투구 아웃 수 |
| `hits_allowed` | H | integer | N | 피안타 |
| `home_runs_allowed` | HR | integer | N | 피홈런 |
| `walks_allowed` | BB | integer | N | 허용 볼넷 |
| `hit_batters` | HBP | integer | N | 사구 허용 |
| `strikeouts` | SO | integer | N | 탈삼진 |
| `runs_allowed` | R | integer | N | 실점 |
| `earned_runs` | ER | integer | N | 자책점 |

이닝은 소수로 저장하면 `10.2`를 10.2이닝으로 잘못 계산할 위험이 있다. 모든 계산은
`innings_pitched_outs`를 사용하며 화면 표시에는 원본 값을 사용한다.

## 5. 팀명

원본에는 23개 팀명이 존재하며 과거 구단명과 현재 구단명이 별도 값이다.

```text
KIA, KT, LG, MBC, NC, OB, SK, SSG, 넥센, 두산, 롯데, 빙그레,
삼미, 삼성, 쌍방울, 우리, 청보, 키움, 태평양, 한화, 해태, 현대, 히어로즈
```

정제 단계에서는 역사적 사실을 잃지 않도록 팀명을 합치지 않는다. 구단 계보를 통한
통합 조회가 필요하면 3단계 DB 설계에서 별도 franchise/alias 구조로 표현한다.
