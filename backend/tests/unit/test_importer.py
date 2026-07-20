"""CSV 적재기의 DB 비종속 변환 규칙 테스트."""

from datetime import date

import pytest

from app.database.importer import (
    ROLE_BATTING,
    build_player_records,
    build_profile_records,
    normalize_search_name,
    snapshot_metadata,
)


def test_search_name_rule_matches_player_service() -> None:
    assert normalize_search_name(" 김 도 영 ") == "김도영"


def test_player_identity_conflict_fails_before_db_write() -> None:
    rows = [
        {"player_id": "1", "player_name": "선수A", "birth_date": "2000-01-01"},
        {"player_id": "1", "player_name": "선수B", "birth_date": "2000-01-01"},
    ]

    with pytest.raises(ValueError, match="신원이 충돌"):
        build_player_records(rows)


def test_profile_coalesces_later_non_null_physical_data() -> None:
    base = {
        "player_id": "1",
        "source_url": "https://example.test/1",
        "bat_throw": "R/R",
        "career": "경력",
        "draft": "",
    }
    rows = [
        {**base, "height_cm": "", "weight_kg": ""},
        {**base, "height_cm": "180", "weight_kg": "80"},
    ]

    profile = build_profile_records(rows, ROLE_BATTING)[(1, ROLE_BATTING)]

    assert profile["height_cm"] == 180
    assert profile["weight_kg"] == 80


def test_partial_snapshot_requires_and_parses_as_of_date() -> None:
    metadata = snapshot_metadata({"is_partial": "True", "as_of_date": "2026-07-20"})

    assert metadata == {
        "is_partial": True,
        "as_of_date": date(2026, 7, 20),
    }

    with pytest.raises(ValueError, match="as_of_date"):
        snapshot_metadata({"is_partial": "True", "as_of_date": ""})
