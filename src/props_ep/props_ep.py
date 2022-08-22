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


def props_ev():
    env = Env()

    # props_url = "https://www.vegasinsider.com/nfl/odds/player-prop-betting-odds/"
    # props_req = urllib.request.Request(props_url, headers={'User-Agent': 'Mozilla/5.0'})
    # props_html = urllib.request.urlopen(props_req)

    # 2022-23 NFL PASSING YARDS TOTALS
    # 2022-23 NFL PASSING TD TOTALS
    # 2022-23 NFL INTERCEPTIONS THROWN TOTALS
    # 2022-23 NFL RUSHING YARDS TOTALS
    # 2022-23 NFL RUSHING TD TOTALS
    # 2022-23 NFL RECEIVING YARDS TOTALS
    # 2022-23 NFL RECEIVING TD TOTALS
    # 2022-23 NFL RECEPTIONS TOTALS

    player_dict = {}
    init_player_dict(env, player_dict)

    fname = "in_html/vegasinsider-2022-08-14.html"
    with open(fname) as f:
        props_soup = BeautifulSoup(f, "html.parser")
        # print(props_soup.prettify())
        for header in props_soup.find_all("h2"):
            print(header.text)
            print(header.string)
            if header.text == "2022-23 NFL PASSING YARDS TOTALS":
                ul = header.find_next("ul")
                print(ul)
                for li in ul.find_all("li"):
                    print(li.text)
                    print(li.contents[0].strip())
                    print(li.contents[1].text)


if __name__ == "__main__":
    props_ev()
