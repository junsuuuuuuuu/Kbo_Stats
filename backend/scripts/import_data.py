"""두 정제 CSV를 MySQL에 순서대로 적재하는 CLI."""

from __future__ import annotations

import json
from pathlib import Path

from app.database.importer import ROLE_BATTING, ROLE_PITCHING, import_dataset
from app.database.session import SessionLocal

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "reports" / "preprocessing_manifest.json"


def main() -> None:
    """전처리 manifest의 원본 hash를 사용해 역할별 batch를 적재한다."""

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    datasets = [
        (
            ROLE_BATTING,
            PROJECT_ROOT / "data" / "processed" / "batting_stats_clean.csv",
            manifest["sources"]["batting"],
        ),
        (
            ROLE_PITCHING,
            PROJECT_ROOT / "data" / "processed" / "pitching_stats_clean.csv",
            manifest["sources"]["pitching"],
        ),
    ]

    with SessionLocal() as session:
        for dataset_type, cleaned_path, source in datasets:
            batch_id = import_dataset(
                session,
                dataset_type=dataset_type,
                cleaned_path=cleaned_path,
                raw_file_name=Path(source["path"]).name,
                raw_sha256=source["sha256"],
            )
            print(f"{dataset_type} 적재 완료: batch_id={batch_id}")


if __name__ == "__main__":
    main()
