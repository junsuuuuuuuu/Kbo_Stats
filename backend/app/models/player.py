"""선수 공통 신원과 데이터 출처별 프로필 모델."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common import TimestampMixin


class Player(TimestampMixin, Base):
    """두 CSV에서 충돌하지 않는 KBO 선수 신원만 보관한다."""

    __tablename__ = "players"
    __table_args__ = (
        CheckConstraint("CHAR_LENGTH(TRIM(player_name)) > 0", name="player_name_not_blank"),
        CheckConstraint("CHAR_LENGTH(search_name) > 0", name="search_name_not_blank"),
    )

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    player_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    search_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)

    profiles: Mapped[list["PlayerSourceProfile"]] = relationship(
        back_populates="player", cascade="all, delete-orphan", lazy="selectin"
    )
    batting_stats = relationship("BattingSeasonStat", back_populates="player")
    pitching_stats = relationship("PitchingSeasonStat", back_populates="player")


class PlayerSourceProfile(TimestampMixin, Base):
    """타자/투수 원본 사이에서 충돌할 수 있는 프로필을 역할별로 보존한다."""

    __tablename__ = "player_source_profiles"
    __table_args__ = (
        CheckConstraint("profile_role IN ('BATTING', 'PITCHING')", name="profile_role"),
        CheckConstraint("bat_side IN ('L', 'R', 'S')", name="profile_bat_side"),
        CheckConstraint("throw_side IN ('L', 'R')", name="profile_throw_side"),
        CheckConstraint(
            "height_cm IS NULL OR height_cm BETWEEN 140 AND 230", name="profile_height"
        ),
        CheckConstraint("weight_kg IS NULL OR weight_kg BETWEEN 40 AND 180", name="profile_weight"),
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.player_id", ondelete="CASCADE"), primary_key=True
    )
    profile_role: Mapped[str] = mapped_column(String(20), primary_key=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    bat_side: Mapped[str] = mapped_column(String(1), nullable=False)
    throw_side: Mapped[str] = mapped_column(String(1), nullable=False)
    height_cm: Mapped[int | None] = mapped_column(SmallInteger)
    weight_kg: Mapped[int | None] = mapped_column(SmallInteger)
    career: Mapped[str | None] = mapped_column(Text)
    draft: Mapped[str | None] = mapped_column(String(255))

    player: Mapped[Player] = relationship(back_populates="profiles")
