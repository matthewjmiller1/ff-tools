#!/usr/bin/env python3

import argparse
import csv
import typing
import urllib.request
from dataclasses import dataclass, field
from bs4 import BeautifulSoup


@dataclass
class Env:
    """Class to represent the environment state"""

    parser: argparse.ArgumentParser = None
    args: argparse.Namespace = None

    def __post_init__(self):
        self.parser = self.get_parser()
        self.args = self.parser.parse_args()

    def get_parser(self):
        parser = argparse.ArgumentParser(
            description=(
                "Compute fantasy football "
                "expected points based on player prop lines"
            )
        )

        parser.add_argument(
            "-v",
            "--verbose",
            dest="vlevel",
            action="count",
            default=0,
            help="enable verbose output",
        )

        return parser


@dataclass
class Player:
    """Class to represent a player"""

    name: str
    position: str
    adp: int
    fp_rank: int
    xrank: int
    props: dict = field(default_factory=dict)


def init_player_dict(env: Env, player_dict: typing.Dict[str, Player]):

    csv_fname = "in_csv/draft_rankings_yahoo_half-2022-08-15.csv"
    with open(csv_fname, newline="") as f:

        reader = csv.DictReader(f)

        for row in reader:
            # Remove blank key
            row.pop("")

            if env.args.vlevel > 3:
                print(row)

            player_dict[row["Name"]] = Player(
                row["Name"],
                row["Pos"],
                int(row["ADP"]),
                int(row["FantasyPros"]),
                int(row["YahooXRank"]),
            )

            if env.args.vlevel > 2:
                print(player_dict[row["Name"]])


def parse_props(env: Env, player_dict: dict[Player]):

    fname = "in_html/vegasinsider-2022-08-14.html"
    with open(fname) as f:
        props_soup = BeautifulSoup(f, "html.parser")

        if env.args.vlevel > 5:
            print(props_soup.prettify())

        stat_dict = header_to_stat_dict()
        fixup_dict = name_fixup_dict()

        for header in props_soup.find_all("h2"):
            if env.args.vlevel > 4:
                print(header.text)
                print(header.string)

            if header.text in stat_dict:
                ul = header.find_next("ul")
                if env.args.vlevel > 4:
                    print(ul)
                for li in ul.find_all("li"):
                    name = li.contents[0].strip()
                    val = li.contents[1].text

                    if env.args.vlevel > 4:
                        print(li.text)
                        print(name)
                        print(val)

                    if name in fixup_dict:
                        name = fixup_dict[name]

                    if name not in player_dict:
                        raise RuntimeError(f"{name} not found in database")

                    player_dict[name].props[stat_dict[header.text]] = val


def header_to_stat_dict() -> dict[str]:
    return {
        "2022-23 NFL PASSING YARDS TOTALS": "pass_yards",
        "2022-23 NFL PASSING TD TOTALS": "pass_tds",
        "2022-23 NFL INTERCEPTIONS THROWN TOTALS": "ints",
        "2022-23 NFL RUSHING YARDS TOTALS": "rush_yards",
        "2022-23 NFL RUSHING TD TOTALS": "rush_tds",
        "2022-23 NFL RECEIVING YARDS TOTALS": "receive_yards",
        "2022-23 NFL RECEIVING TD TOTALS": "receive_tds",
        "2022-23 NFL RECEPTIONS TOTALS": "receptions",
    }


def name_fixup_dict() -> dict[str]:
    return {
        # Initials
        "A.J. Dillon": "AJ Dillon",
        "D.J. Moore": "DJ Moore",
        "D.K. Metcalf": "DK Metcalf",
        # Suffixes
        "Travis Etienne, Jr.": "Travis Etienne",
        "Michael Pittman, Jr.": "Michael Pittman",
        # Misspellings
        "Devin Montgomery": "David Montgomery",
        "Jacobi Meters": "Jakobi Meyers",
    }


def get_props_html() -> str:
    props_url = (
        "https://www.vegasinsider.com/nfl/odds/player-prop-betting-odds/"
    )
    props_req = urllib.request.Request(
        props_url, headers={"User-Agent": "Mozilla/5.0"}
    )
    props_html = urllib.request.urlopen(props_req)

    return props_html


def remove_players_with_no_props(
    env: Env, player_dict: dict[Player]
) -> dict[Player]:
    new_dict = {}

    for k, v in player_dict.items():
        if v.props:
            new_dict[k] = v

    return new_dict


def props_ev():
    env = Env()

    player_dict = {}
    init_player_dict(env, player_dict)
    parse_props(env, player_dict)
    player_dict = remove_players_with_no_props(env, player_dict)

    if env.args.vlevel > 0:
        for k, v in player_dict.items():
            print(v)


if __name__ == "__main__":
    props_ev()
