"""
FACE FOOD FIGHT 실행 진입점
"""

import argparse
import sys

import config
from game import FaceFoodFightGame


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FACE FOOD FIGHT — 표정으로 음식 잡기")
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        default=config.DEBUG_MODE_DEFAULT,
        help="카메라 없이 W/M/E 키로 동작 테스트",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=None,
        help=f"카메라 번호 (기본 {config.CAMERA_INDEX}, 내장 cam은 보통 0)",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args(sys.argv[1:])
    if args.camera_index is not None:
        config.CAMERA_INDEX = args.camera_index
    game = FaceFoodFightGame(debug_mode=args.debug)
    game.run()


if __name__ == "__main__":
    main()
