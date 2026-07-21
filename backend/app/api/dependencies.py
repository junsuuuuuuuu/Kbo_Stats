"""Router에서 사용할 Repository와 Service 의존성 조립."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.repositories.player import SqlAlchemyPlayerRepository
from app.repositories.team import SqlAlchemyTeamRepository
from app.services.analytics import AnalyticsService
from app.services.player import PlayerService
from app.services.team import TeamService

DatabaseSession = Annotated[Session, Depends(get_db_session)]


def get_player_repository(session: DatabaseSession) -> SqlAlchemyPlayerRepository:
    """request-scoped Session으로 Repository를 생성한다."""

    return SqlAlchemyPlayerRepository(session)


PlayerRepositoryDependency = Annotated[SqlAlchemyPlayerRepository, Depends(get_player_repository)]


def get_player_service(repository: PlayerRepositoryDependency) -> PlayerService:
    """구체 Repository를 Service의 interface 자리에 주입한다."""

    return PlayerService(repository)


PlayerServiceDependency = Annotated[PlayerService, Depends(get_player_service)]


def get_team_repository(session: DatabaseSession) -> SqlAlchemyTeamRepository:
    """request-scoped Session으로 구단 Repository를 생성한다."""

    return SqlAlchemyTeamRepository(session)


TeamRepositoryDependency = Annotated[SqlAlchemyTeamRepository, Depends(get_team_repository)]


def get_team_service(repository: TeamRepositoryDependency) -> TeamService:
    """구단 로스터 Service를 조립한다."""

    return TeamService(repository)


TeamServiceDependency = Annotated[TeamService, Depends(get_team_service)]


@lru_cache
def get_analytics_service() -> AnalyticsService:
    """CSV와 모델 artifact를 요청마다 다시 초기화하지 않는 singleton service."""

    return AnalyticsService()


AnalyticsServiceDependency = Annotated[AnalyticsService, Depends(get_analytics_service)]
