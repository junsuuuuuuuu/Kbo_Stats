"""Guarded daily KBO update job.

The job first stores the light game-day snapshot. Expensive season-stat
scraping runs only when at least one completed game is present and the stored
snapshot has not already processed the same completed-game count.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.game_day import GameDaySnapshot
from app.schemas.team import LatestGameDayResponse
from app.services.kbo_team_schedule import kbo_team_schedule_client
from scripts.collect_game_day import save_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SnapshotState:
    exists: bool
    completed_games: int


def completed_game_count(response: LatestGameDayResponse) -> int:
    return sum(1 for game in response.games if game.status == "completed")


def collect_game_day(season: int, game_date: date | None = None) -> LatestGameDayResponse:
    collected = (
        kbo_team_schedule_client.game_day(game_date.isoformat(), season)
        if game_date
        else kbo_team_schedule_client.latest_game_day(season)
    )
    return LatestGameDayResponse.model_validate(collected, from_attributes=True)


def save_game_day_response(response: LatestGameDayResponse, season: int) -> SnapshotState:
    with SessionLocal() as session:
        previous = stored_snapshot_state(session, season, response.game_date)
        save_snapshot(session, response, season)
    completed_count = completed_game_count(response)
    print(
        "game-day snapshot saved: "
        f"date={response.game_date} games={len(response.games)} completed={completed_count}",
        flush=True,
    )
    return previous


def prefetch_future_game_days(season: int, base_date: date, days: int) -> None:
    for offset in range(1, days + 1):
        game_date = base_date + timedelta(days=offset)
        if game_date.year != season:
            continue
        try:
            response = collect_game_day(season, game_date)
        except Exception as exception:
            print(
                f"future game-day prefetch skipped: date={game_date} error={exception}",
                flush=True,
            )
            continue
        save_game_day_response(response, season)


def stored_snapshot_state(session: Session, season: int, game_date: date) -> SnapshotState:
    snapshot = session.scalar(
        select(GameDaySnapshot).where(
            GameDaySnapshot.season == season,
            GameDaySnapshot.game_date == game_date,
        )
    )
    if snapshot is None:
        return SnapshotState(exists=False, completed_games=0)
    games = snapshot.payload.get("games", [])
    completed = sum(1 for game in games if game.get("status") == "completed")
    return SnapshotState(exists=True, completed_games=completed)


def run_command(args: list[str], *, cwd: Path) -> None:
    print(f"running: {' '.join(args)}", flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def run_heavy_updates(delay: float) -> None:
    run_command(
        [sys.executable, "scripts/fetch_kbo_2026_standings.py", "--delay", str(delay)],
        cwd=PROJECT_ROOT,
    )
    run_command([sys.executable, "-m", "scripts.import_2026_standings"], cwd=BACKEND_ROOT)

    run_command(
        [sys.executable, "scripts/fetch_kbo_2026.py", "--delay", str(delay)],
        cwd=PROJECT_ROOT,
    )
    run_command(
        [
            sys.executable,
            "scripts/preprocess_data.py",
            "--batting",
            "data/raw/kbo_batting_stats_season_2026_partial.csv",
            "--pitching",
            "data/raw/kbo_pitching_stats_season_2026_partial.csv",
            "--output-dir",
            "data/processed/2026",
            "--manifest",
            "reports/kbo-2026-preprocessing.json",
        ],
        cwd=PROJECT_ROOT,
    )
    run_command([sys.executable, "scripts/import_2026_data.py"], cwd=BACKEND_ROOT)


def run_roster_update(delay: float) -> None:
    run_command(
        [sys.executable, "scripts/fetch_kbo_2026_rosters.py", "--delay", str(delay)],
        cwd=PROJECT_ROOT,
    )
    run_command([sys.executable, "scripts/import_2026_rosters.py"], cwd=BACKEND_ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run guarded daily KBO update")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run heavy updates even if already processed",
    )
    parser.add_argument("--include-rosters", action="store_true")
    parser.add_argument("--game-day-only", action="store_true")
    parser.add_argument(
        "--prefetch-days",
        type=int,
        default=0,
        help="Also store lightweight game-day snapshots for N future days",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.delay < 1.0:
        raise ValueError("--delay must be at least 1.0 seconds")
    if args.prefetch_days < 0:
        raise ValueError("--prefetch-days must not be negative")

    base_date = args.date or datetime.now(ZoneInfo("Asia/Seoul")).date()
    if args.date is not None:
        collection_dates = [args.date]
    else:
        # A snapshot collected before yesterday's games finish must be refreshed.
        # Collecting today alone can otherwise leave the previous game day stale.
        collection_dates = [
            game_date
            for game_date in (base_date - timedelta(days=1), base_date)
            if game_date.year == args.season
        ]

    collected_states: list[tuple[LatestGameDayResponse, SnapshotState]] = []
    for game_date in collection_dates:
        response_for_date = collect_game_day(args.season, game_date)
        previous_for_date = save_game_day_response(response_for_date, args.season)
        collected_states.append((response_for_date, previous_for_date))

    # Use the day with the most completed games for the guarded heavy update.
    # This keeps a completed yesterday snapshot from being hidden by today's
    # scheduled or empty slate.
    response, previous = max(
        collected_states,
        key=lambda item: (completed_game_count(item[0]), item[0].game_date),
    )
    completed_count = completed_game_count(response)

    if args.prefetch_days:
        prefetch_future_game_days(args.season, base_date, args.prefetch_days)

    if args.include_rosters:
        run_roster_update(args.delay)

    if args.game_day_only:
        print("game-day-only mode: skipping standings and player stats", flush=True)
        return

    if completed_count == 0 and not args.force:
        print("no completed games found: skipping standings and player stats", flush=True)
        return

    if (
        previous.exists
        and previous.completed_games >= completed_count
        and completed_count > 0
        and not args.force
    ):
        print(
            "completed game count already processed: "
            f"previous={previous.completed_games} current={completed_count}",
            flush=True,
        )
        return

    run_heavy_updates(args.delay)


if __name__ == "__main__":
    main()
