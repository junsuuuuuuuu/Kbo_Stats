"""HTTP 프레임워크와 분리된 도메인/애플리케이션 예외."""

from typing import Any


class ApplicationError(Exception):
    """사용자에게 안전하게 노출할 수 있는 애플리케이션 예외의 기반 클래스."""

    code = "APPLICATION_ERROR"
    status_code = 400

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class PlayerNotFoundError(ApplicationError):
    """요청한 player_id가 존재하지 않을 때 발생한다."""

    code = "PLAYER_NOT_FOUND"
    status_code = 404

    def __init__(self, player_id: int) -> None:
        super().__init__("선수를 찾을 수 없습니다.", {"player_id": player_id})


class TeamRosterNotFoundError(ApplicationError):
    """요청 시즌과 구단 코드에 해당하는 로스터가 없을 때 발생한다."""

    code = "TEAM_ROSTER_NOT_FOUND"
    status_code = 404

    def __init__(self, team_code: str, season: int) -> None:
        super().__init__(
            "구단 로스터를 찾을 수 없습니다.",
            {"team_code": team_code, "season": season},
        )


class AnalyticsNotAvailableError(ApplicationError):
    """선수 기록이 분석 기능의 최소 표본 조건을 만족하지 못한 경우."""

    code = "ANALYTICS_NOT_AVAILABLE"
    status_code = 404

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message, details)


class UpstreamDataError(ApplicationError):
    """외부 공식 데이터 페이지를 일시적으로 읽지 못한 경우."""

    code = "UPSTREAM_DATA_UNAVAILABLE"
    status_code = 502

    def __init__(self) -> None:
        super().__init__("KBO 경기 기록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
