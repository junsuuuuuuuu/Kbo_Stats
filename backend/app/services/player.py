"""선수 검색과 상세 조회 유스케이스."""

from dataclasses import dataclass

from app.core.exceptions import PlayerNotFoundError
from app.models.player import Player
from app.models.stats import BattingSeasonStat, PitchingSeasonStat
from app.repositories.player import PlayerRepository, PlayerSearchCriteria
from app.schemas.player import PlayerRole


@dataclass(frozen=True, slots=True)
class PlayerPage:
    """Service의 HTTP 비종속 페이지 결과."""

    items: list[Player]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class PlayerSeasons:
    """선수 신원과 역할별 시즌 기록 묶음."""

    player: Player
    batting: list[BattingSeasonStat]
    pitching: list[PitchingSeasonStat]


class PlayerService:
    """검색 입력 정규화와 선수 존재 규칙을 담당한다."""

    def __init__(self, repository: PlayerRepository) -> None:
        self._repository = repository

    @staticmethod
    def normalize_search_name(value: str | None) -> str | None:
        """DB의 search_name 생성 규칙과 동일하게 공백을 제거하고 소문자화한다."""

        if value is None:
            return None
        normalized = "".join(value.split()).lower()
        return normalized or None

    def search_players(
        self,
        *,
        query: str | None,
        role: PlayerRole | None,
        season: int | None,
        team: str | None,
        page: int,
        page_size: int,
    ) -> PlayerPage:
        """검색 조건을 Repository 기준으로 변환해 페이지 결과를 만든다."""

        criteria = PlayerSearchCriteria(
            query=self.normalize_search_name(query),
            role=role,
            season=season,
            team=team.strip() if team else None,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        players, total = self._repository.search(criteria)
        return PlayerPage(players, page, page_size, total)

    def get_player(self, player_id: int) -> Player:
        """선수가 없으면 Repository 결과 대신 명시적 도메인 예외를 발생시킨다."""

        player = self._repository.get_by_id(player_id)
        if player is None:
            raise PlayerNotFoundError(player_id)
        return player

    def get_player_seasons(self, player_id: int, role: PlayerRole | None) -> PlayerSeasons:
        """요청 역할만 조회해 불필요한 DB 접근을 피한다."""

        player = self.get_player(player_id)
        batting = (
            self._repository.list_batting_seasons(player_id)
            if role in (None, PlayerRole.BATTING)
            else []
        )
        pitching = (
            self._repository.list_pitching_seasons(player_id)
            if role in (None, PlayerRole.PITCHING)
            else []
        )
        return PlayerSeasons(player, batting, pitching)
