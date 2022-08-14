#!/usr/bin/env python3

import argparse
from dataclasses import dataclass, field


@dataclass
class Env:
    """Class to represent the environment state"""

    args: argparse.Namespace


def get_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Compute fantasy football "
            "expected points based on player prop lines"
        )
    )

    parser.add_argument(
        "-d",
        "--debug",
        dest="do_debug",
        action="store_true",
        default=False,
        help="enable debug output",
    )

    return parser


def props_ev():
    env = Env(get_parser().parse_args())


if __name__ == "__main__":
    props_ev()
