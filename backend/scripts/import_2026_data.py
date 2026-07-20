"""전처리된 2026 진행 시즌 snapshot을 MySQL에 적재한다."""

from __future__ import annotations

import json
from pathlib import Path

from app.database.importer import (
    ROLE_BATTING,
    ROLE_PITCHING,
    AlreadyImportedError,
    import_dataset,
)
from app.database.session import SessionLocal

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "reports" / "kbo-2026-preprocessing.json"
PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed" / "2026"


def main() -> None:
    """역할별 snapshot을 적재하며 동일 파일의 재실행은 안전하게 건너뛴다."""

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    datasets = (
        (ROLE_BATTING, PROCESSED_DIRECTORY / "batting_stats_clean.csv", "batting"),
        (ROLE_PITCHING, PROCESSED_DIRECTORY / "pitching_stats_clean.csv", "pitching"),
    )

    with SessionLocal() as session:
        for dataset_type, cleaned_path, source_key in datasets:
            source = manifest["sources"][source_key]
            try:
                batch_id = import_dataset(
                    session,
                    dataset_type=dataset_type,
                    cleaned_path=cleaned_path,
                    raw_file_name=Path(source["path"]).name,
                    raw_sha256=source["sha256"],
                )
            except AlreadyImportedError as error:
                print(f"{dataset_type} 건너뜀: {error}")
            else:
                print(f"{dataset_type} 2026 적재 완료: batch_id={batch_id}")


if __name__ == "__main__":
    main()
