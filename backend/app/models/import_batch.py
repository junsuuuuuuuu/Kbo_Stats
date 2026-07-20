"""원본 CSV 적재 이력 모델."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DataImportBatch(Base):
    """파일 해시와 적재 상태를 남겨 데이터 계보를 추적한다."""

    __tablename__ = "data_import_batches"
    __table_args__ = (
        UniqueConstraint("dataset_type", "source_sha256", name="import_dataset_hash"),
        CheckConstraint("dataset_type IN ('BATTING', 'PITCHING')", name="import_dataset_type"),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="import_status",
        ),
        CheckConstraint(
            "imported_row_count IS NULL OR imported_row_count <= source_row_count",
            name="imported_row_count",
        ),
    )

    import_batch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    imported_row_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    quality_report: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
