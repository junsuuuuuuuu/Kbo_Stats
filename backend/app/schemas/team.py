"""구단 목록과 1군 등록 로스터 API schema."""

from datetime import date

from pydantic import BaseModel, Field

from app.models.roster import TeamRoster
from app.models.standing import TeamStanding
from app.repositories.team import TeamRosterSnapshot, TeamRosterSummary

POSITION_LABELS = {"P": "투수", "C": "포수", "IF": "내야수", "OF": "외야수"}


class TeamSummaryResponse(BaseModel):
    team_id: int
    team_code: str
    team_name: str
    season: int
    as_of_date: date
    roster_count: int = Field(ge=0)
    pitcher_count: int = Field(ge=0)
    hitter_count: int = Field(ge=0)

    @classmethod
    def from_result(cls, result: TeamRosterSummary) -> "TeamSummaryResponse":
        return cls(
            team_id=result.team_id,
            team_code=result.team_code,
            team_name=result.team_name,
            season=result.season,
            as_of_date=result.as_of_date,
            roster_count=result.roster_count,
            pitcher_count=result.pitcher_count,
            hitter_count=result.hitter_count,
        )


class TeamListResponse(BaseModel):
    season: int
    items: list[TeamSummaryResponse]


class RosterMemberResponse(BaseModel):
    player_id: int
    player_name: str
    uniform_number: str
    position: str
    position_label: str
    bat_side: str
    throw_side: str
    birth_date: date
    age: int
    height_cm: int | None
    weight_kg: int | None
    source_url: str

    @classmethod
    def from_entity(cls, member: TeamRoster) -> "RosterMemberResponse":
        return cls(
            player_id=member.player_id,
            player_name=member.player.player_name,
            uniform_number=member.uniform_number,
            position=member.position_code,
            position_label=POSITION_LABELS[member.position_code],
            bat_side=member.bat_side,
            throw_side=member.throw_side,
            birth_date=member.player.birth_date,
            age=member.season - member.player.birth_date.year,
            height_cm=member.height_cm,
            weight_kg=member.weight_kg,
            source_url=member.source_url,
        )


class TeamRosterResponse(BaseModel):
    team: TeamSummaryResponse
    members: list[RosterMemberResponse]

    @classmethod
    def from_result(cls, result: TeamRosterSnapshot) -> "TeamRosterResponse":
        return cls(
            team=TeamSummaryResponse.from_result(result.summary),
            members=[RosterMemberResponse.from_entity(member) for member in result.members],
        )


class TeamStandingResponse(BaseModel):
    season: int
    as_of_date: date
    team_code: str
    team_name: str
    ranking: int
    games: int
    wins: int
    losses: int
    draws: int
    winning_percentage: float
    games_behind: float
    recent_ten: str
    streak: str
    home_record: str
    away_record: str
    source_url: str

    @classmethod
    def from_entity(cls, standing: TeamStanding) -> "TeamStandingResponse":
        return cls(
            season=standing.season,
            as_of_date=standing.as_of_date,
            team_code=standing.team_code,
            team_name=standing.team.team_name,
            ranking=standing.ranking,
            games=standing.games,
            wins=standing.wins,
            losses=standing.losses,
            draws=standing.draws,
            winning_percentage=float(standing.winning_percentage),
            games_behind=float(standing.games_behind),
            recent_ten=standing.recent_ten,
            streak=standing.streak,
            home_record=standing.home_record,
            away_record=standing.away_record,
            source_url=standing.source_url,
        )
