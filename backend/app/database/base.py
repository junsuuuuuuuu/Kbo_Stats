"""모든 SQLAlchemy 모델이 공유하는 Declarative Base."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Alembic이 안정적인 constraint 이름을 생성하도록 metadata를 공유한다."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
