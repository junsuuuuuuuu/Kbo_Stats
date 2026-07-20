"""Python 3.13 전용 TabPFN 다음 시즌 예측 benchmark CLI."""

from __future__ import annotations

import argparse

from app.ml.config import TARGET_SPECS
from app.ml.tabpfn_benchmark import run_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TabPFN CPU benchmark")
    parser.add_argument(
        "--targets",
        nargs="+",
        choices=sorted(TARGET_SPECS),
        default=list(TARGET_SPECS),
    )
    return parser.parse_args()


if __name__ == "__main__":
    run_benchmark(parse_args().targets)
