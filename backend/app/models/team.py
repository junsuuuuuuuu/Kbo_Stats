"""원본 팀명 참조 모델."""

from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common import TimestampMixin


class Team(TimestampMixin, Base):
    """역사적 팀명을 임의 통합하지 않고 원본 표시명 그대로 관리한다."""

    __tablename__ = "teams"

    team_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    team_name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    batting_stats = relationship("BattingSeasonStat", back_populates="team")
    pitching_stats = relationship("PitchingSeasonStat", back_populates="team")
    rosters = relationship("TeamRoster", back_populates="team")
    standings = relationship("TeamStanding", back_populates="team")
