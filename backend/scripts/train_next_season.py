"""다음 시즌 성적 예측 모델 학습 CLI."""

from __future__ import annotations

import argparse

from app.ml.config import TARGET_SPECS
from app.ml.training import train_targets


def parse_args() -> argparse.Namespace:
    """전체 또는 선택 target만 학습할 수 있게 한다."""

    parser = argparse.ArgumentParser(description="KBO 다음 시즌 성적 예측 모델 학습")
    parser.add_argument(
        "--targets",
        nargs="+",
        choices=sorted(TARGET_SPECS),
        default=list(TARGET_SPECS),
        help="생략하면 다섯 target을 모두 학습합니다.",
    )
    return parser.parse_args()


def main() -> None:
    """선택한 명세 순서로 모델 학습을 실행한다."""

    args = parse_args()
    train_targets([TARGET_SPECS[target] for target in args.targets])


if __name__ == "__main__":
    main()
