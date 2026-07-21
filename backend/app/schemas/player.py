"""선수 검색, 상세 및 시즌 기록 응답 schema."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.batting_metrics import BattingMetricValues
from app.models.player import Player, PlayerSourceProfile
from app.models.stats import BattingSeasonStat, PitchingSeasonStat


class PlayerRole(StrEnum):
    """선수 통계 역할. DB의 profile_role 값과 동일한 대문자 값을 사용한다."""

    BATTING = "BATTING"
    PITCHING = "PITCHING"


class PlayerProfileResponse(BaseModel):
    """타자/투수 출처별 프로필."""

    model_config = ConfigDict(from_attributes=True)

    role: PlayerRole
    source_url: str
    bat_side: str
    throw_side: str
    height_cm: int | None
    weight_kg: int | None
    career: str | None
    draft: str | None

    @classmethod
    def from_entity(cls, profile: PlayerSourceProfile) -> "PlayerProfileResponse":
        """ORM 필드명을 외부 계약의 간결한 role 이름으로 변환한다."""

        return cls(
            role=PlayerRole(profile.profile_role),
            source_url=profile.source_url,
            bat_side=profile.bat_side,
            throw_side=profile.throw_side,
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            career=profile.career,
            draft=profile.draft,
        )


class PlayerSummaryResponse(BaseModel):
    """검색 목록에서 동명이인을 구분할 수 있는 최소 선수 정보."""

    player_id: int
    player_name: str
    birth_date: date
    roles: list[PlayerRole]

    @classmethod
    def from_entity(cls, player: Player) -> "PlayerSummaryResponse":
        """중복 role 없이 항상 같은 순서로 검색 결과를 직렬화한다."""

        roles = sorted({PlayerRole(profile.profile_role) for profile in player.profiles})
        return cls(
            player_id=player.player_id,
            player_name=player.player_name,
            birth_date=player.birth_date,
            roles=roles,
        )


class PlayerPageResponse(BaseModel):
    """선수 검색 페이지 응답."""

    items: list[PlayerSummaryResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class PlayerDetailResponse(BaseModel):
    """선수 공통 신원과 역할별 원본 프로필."""

    player_id: int
    player_name: str
    birth_date: date
    profiles: list[PlayerProfileResponse]

    @classmethod
    def from_entity(cls, player: Player) -> "PlayerDetailResponse":
        """역할별 프로필을 안정적인 순서로 조립한다."""

        profiles = sorted(
            (PlayerProfileResponse.from_entity(profile) for profile in player.profiles),
            key=lambda profile: profile.role,
        )
        return cls(
            player_id=player.player_id,
            player_name=player.player_name,
            birth_date=player.birth_date,
            profiles=profiles,
        )


class BattingSeasonResponse(BaseModel):
    """그래프와 표에 직접 사용할 수 있는 타자 시즌 기록."""

    season: int
    is_partial: bool
    as_of_date: date | None
    age: int
    team: str
    position: str
    games: int
    plate_appearances: int
    at_bats: int
    runs: int
    hits: int
    doubles: int
    triples: int
    home_runs: int
    total_bases: int
    runs_batted_in: int
    stolen_bases: int
    caught_stealing: int
    walks: int
    hit_by_pitch: int
    strikeouts: int
    grounded_into_double_play: int
    sacrifice_flies: int
    sacrifice_hits: int
    errors: int
    batting_average: float | None
    slugging_percentage: float | None
    on_base_percentage: float | None
    on_base_plus_slugging: float | None
    defensive_efficiency: float | None
    team_rank: int | None
    walk_percentage: float | None
    strikeout_percentage: float | None
    walk_to_strikeout_ratio: float | None
    isolated_power: float | None
    batting_average_on_balls_in_play: float | None
    stolen_base_percentage: float | None
    speed_score: float | None
    weighted_stolen_base_runs: float | None
    weighted_double_play_runs: float | None
    weighted_on_base_average: float | None
    weighted_runs_above_average: float | None
    weighted_runs_created: float | None
    weighted_runs_created_plus: float | None

    @classmethod
    def from_entity(
        cls,
        stat: BattingSeasonStat,
        birth_date: date,
        defensive_efficiency: float | None = None,
        metrics: BattingMetricValues | None = None,
        team_rank: int | None = None,
    ) -> "BattingSeasonResponse":
        """DB 중복 저장 없이 시즌 연도 기준 나이를 계산한다."""

        return cls(
            season=stat.season,
            is_partial=stat.is_partial,
            as_of_date=stat.as_of_date,
            age=stat.season - birth_date.year,
            team=stat.team.team_name,
            position=stat.position_code,
            games=stat.games,
            plate_appearances=stat.plate_appearances,
            at_bats=stat.at_bats,
            runs=stat.runs,
            hits=stat.hits,
            doubles=stat.doubles,
            triples=stat.triples,
            home_runs=stat.home_runs,
            total_bases=stat.total_bases,
            runs_batted_in=stat.runs_batted_in,
            stolen_bases=stat.stolen_bases,
            caught_stealing=stat.caught_stealing,
            walks=stat.walks,
            hit_by_pitch=stat.hit_by_pitch,
            strikeouts=stat.strikeouts,
            grounded_into_double_play=stat.grounded_into_double_play,
            sacrifice_flies=stat.sacrifice_flies,
            sacrifice_hits=stat.sacrifice_hits,
            errors=stat.errors,
            batting_average=stat.batting_average,
            slugging_percentage=stat.slugging_percentage,
            on_base_percentage=stat.on_base_percentage,
            on_base_plus_slugging=stat.on_base_plus_slugging,
            defensive_efficiency=defensive_efficiency,
            team_rank=team_rank,
            walk_percentage=metrics.walk_percentage if metrics else None,
            strikeout_percentage=metrics.strikeout_percentage if metrics else None,
            walk_to_strikeout_ratio=metrics.walk_to_strikeout_ratio if metrics else None,
            isolated_power=metrics.isolated_power if metrics else None,
            batting_average_on_balls_in_play=(
                metrics.batting_average_on_balls_in_play if metrics else None
            ),
            stolen_base_percentage=metrics.stolen_base_percentage if metrics else None,
            speed_score=metrics.speed_score if metrics else None,
            weighted_stolen_base_runs=metrics.weighted_stolen_base_runs if metrics else None,
            weighted_double_play_runs=metrics.weighted_double_play_runs if metrics else None,
            weighted_on_base_average=metrics.weighted_on_base_average if metrics else None,
            weighted_runs_above_average=(
                metrics.weighted_runs_above_average if metrics else None
            ),
            weighted_runs_created=metrics.weighted_runs_created if metrics else None,
            weighted_runs_created_plus=(
                metrics.weighted_runs_created_plus if metrics else None
            ),
        )


class PitchingSeasonResponse(BaseModel):
    """그래프와 표에 직접 사용할 수 있는 투수 시즌 기록."""

    season: int
    is_partial: bool
    as_of_date: date | None
    age: int
    team: str
    earned_run_average: float | None
    games: int
    complete_games: int
    shutouts: int
    wins: int
    losses: int
    saves: int
    holds: int
    winning_percentage: float | None
    batters_faced: int
    innings_pitched: str
    innings_pitched_outs: int
    hits_allowed: int
    home_runs_allowed: int
    walks_allowed: int
    hit_batters: int
    strikeouts: int
    runs_allowed: int
    earned_runs: int

    @classmethod
    def from_entity(cls, stat: PitchingSeasonStat, birth_date: date) -> "PitchingSeasonResponse":
        """아웃 수는 계산용으로 유지하며 사용자 표시용 이닝도 함께 만든다."""

        whole_innings, remainder = divmod(stat.innings_pitched_outs, 3)
        if remainder == 0:
            innings_display = str(whole_innings)
        elif whole_innings == 0:
            innings_display = f"{remainder}/3"
        else:
            innings_display = f"{whole_innings} {remainder}/3"

        return cls(
            season=stat.season,
            is_partial=stat.is_partial,
            as_of_date=stat.as_of_date,
            age=stat.season - birth_date.year,
            team=stat.team.team_name,
            earned_run_average=stat.earned_run_average,
            games=stat.games,
            complete_games=stat.complete_games,
            shutouts=stat.shutouts,
            wins=stat.wins,
            losses=stat.losses,
            saves=stat.saves,
            holds=stat.holds,
            winning_percentage=stat.winning_percentage,
            batters_faced=stat.batters_faced,
            innings_pitched=innings_display,
            innings_pitched_outs=stat.innings_pitched_outs,
            hits_allowed=stat.hits_allowed,
            home_runs_allowed=stat.home_runs_allowed,
            walks_allowed=stat.walks_allowed,
            hit_batters=stat.hit_batters,
            strikeouts=stat.strikeouts,
            runs_allowed=stat.runs_allowed,
            earned_runs=stat.earned_runs,
        )


class PlayerSeasonsResponse(BaseModel):
    """선수의 두 역할 시즌 기록을 한 번에 또는 선택적으로 반환한다."""

    player_id: int
    batting: list[BattingSeasonResponse]
    pitching: list[PitchingSeasonResponse]


class PitchingAppearanceResponse(BaseModel):
    """한 경기의 투수 등판 기록."""

    game_date: date
    opponent: str
    appearance_type: str
    result: str | None
    game_era: float
    batters_faced: int
    innings_pitched: str
    hits_allowed: int
    home_runs_allowed: int
    walks_allowed: int
    hit_batters: int
    strikeouts: int
    runs_allowed: int
    earned_runs: int
    season_era: float


class PitchingAppearancesResponse(BaseModel):
    player_id: int
    season: int
    source_url: str
    items: list[PitchingAppearanceResponse]


class BattingAppearanceResponse(BaseModel):
    """한 경기의 타자 출장 기록."""

    game_date: date
    opponent: str
    game_average: float | None
    plate_appearances: int
    at_bats: int
    runs: int
    hits: int
    doubles: int
    triples: int
    home_runs: int
    runs_batted_in: int
    stolen_bases: int
    caught_stealing: int
    walks: int
    hit_by_pitch: int
    strikeouts: int
    grounded_into_double_play: int
    season_average: float


class BattingAppearancesResponse(BaseModel):
    player_id: int
    season: int
    source_url: str
    items: list[BattingAppearanceResponse]


class LeagueBenchmarkResponse(BaseModel):
    metric: str
    player_value: float
    league_average: float
    percentile: float = Field(ge=0, le=100)
    sample_size: int = Field(ge=1)
    higher_is_better: bool


class PlayerBenchmarksResponse(BaseModel):
    player_id: int
    role: str
    season: int
    qualification: str
    items: list[LeagueBenchmarkResponse]
