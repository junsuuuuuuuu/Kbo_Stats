"""로스터 적재기의 원본 표기 변환 규칙 테스트."""

import pytest

from scripts.import_2026_rosters import parse_active, parse_physical, parse_sides


def test_korean_bat_throw_mapping_includes_sidearm_and_switch_hitter() -> None:
    assert parse_sides("우언우타") == ("R", "R")
    assert parse_sides("우투양타") == ("S", "R")
    assert parse_sides("좌투좌타") == ("L", "L")


def test_missing_physical_values_become_null() -> None:
    assert parse_physical("183cm, 92kg") == (183, 92)
    assert parse_physical("0cm, 0kg") == (None, None)


def test_active_flag_is_strict() -> None:
    assert parse_active("True") is True
    assert parse_active("false") is False
    with pytest.raises(ValueError, match="IsActive"):
        parse_active("yes")
