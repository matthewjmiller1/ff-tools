#!/usr/bin/env python3

import argparse
import csv
import typing
import re
import shutil
import json
from datetime import datetime
import urllib.request
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from tabulate import tabulate


@dataclass
class Env:
    """Class to represent the environment state"""

    points_dict: dict
    parser: argparse.ArgumentParser = None
    args: argparse.Namespace = None

    def __post_init__(self):
        self.parser = self.get_parser()
        self.args = self.parser.parse_args()
        self.update_points_dict()

    def update_points_dict(self):
        if self.args.cfg_file is None:
            return

        with open(self.args.cfg_file, "r") as f:
            for line in f:
                # Skip blank lines and comments
                if line.strip() == "" or line.strip()[0] == "#":
                    continue

                line_list = line.split(":")

                if len(line_list) != 2:
                    raise RuntimeError(
                        f"{f.name} contains a line with an "
                        f"invalid format: {line}"
                    )

                stat = line_list[0]
                val = line_list[1]

                if stat not in self.points_dict:
                    raise RuntimeError(
                        f"{f.name} contains an invalid stat: {stat}"
                    )

                self.points_dict[stat] = float(val)

    def get_parser(self):
        parser = argparse.ArgumentParser(
            description=(
                "Compute fantasy football "
                "expected points based on player prop lines"
            )
        )

        stats = ", ".join(sorted([v for _, v in header_to_stat_dict().items()]))
        parser.add_argument(
            "-c",
            "--config-file",
            dest="cfg_file",
            help=f"""
            Specify a config file to use for points computation.
            Valid values are: {stats}.
            Format of the file is, e.g., "pass_tds: 4.0" with one state per
            line.
            """,
        )

        parser.add_argument(
            "-d",
            "--download-props",
            dest="do_download",
            default=False,
            action="store_true",
            help="""
            Download the props site data.
            """,
        )

        parser.add_argument(
            "--directory",
            help="""
            The directory to download props data.
            """,
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
    prop_points: float = 0.0

    def update_total_yards_stat(
        self, existing_stat: str, update_stat: str, total_yards: str
    ):
        if existing_stat in self.props and update_stat not in self.props:
            self.props[update_stat] = str(
                float(total_yards) - float(self.props[existing_stat])
            )

    def adjust_for_total_yards(self, total_yards: str):
        # If total yards is given for a player, update, e.g., projected receive
        # yards for RBs by computing their projected total yards minus their
        # projected rush yards.
        self.update_total_yards_stat("receive_yards", "rush_yards", total_yards)
        self.update_total_yards_stat("rush_yards", "receive_yards", total_yards)


@dataclass
class DataDownload:
    """Class to represent data download info"""

    url: str
    local_file_prefix: str
    local_file_ext: str


def init_player_dict(env: Env, player_dict: typing.Dict[str, Player]):
    csv_fname = "in_rankings/draft_rankings_yahoo_half-2023-07-23.csv"
    with open(csv_fname, "r", newline="") as f:
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


def parse_total_yards(env: Env, player_dict: dict[Player]):
    fixup_dict = name_fixup_dict()

    fname = "in_props/dk_total_yards-2022-08-24.json"
    with open(fname, "r") as f:
        data = json.load(f)

        player_totals = None
        for category in data["eventGroup"]["offerCategories"]:
            if category["name"] == "Player Totals":
                player_totals = category
                break

        total_yards = None
        for subcategory in player_totals["offerSubcategoryDescriptors"]:
            if subcategory["name"] == "Rushing + Receiving Yards":
                total_yards = subcategory
                break

        offers = total_yards["offerSubcategory"]["offers"][0]

        pat_name = re.compile("(.*) Regular Season Rush & Rec Yards")
        pat_yards = re.compile("(?:Over|Under)\s+(\d+[.]?\d*)")
        for offer in offers:
            m = pat_name.match(offer["label"])
            if m != None:
                name = m.group(1)
                outcomes = offer["outcomes"][0]["label"]
                m2 = pat_yards.match(outcomes)
                if m2 != None:
                    yards = m2.group(1)
                    if env.args.vlevel > 2:
                        print(f"Name={name}, Total yards={yards}")

                    if name in fixup_dict:
                        name = fixup_dict[name]

                    if name not in player_dict:
                        raise RuntimeError(f"{name} not found in database")

                    player_dict[name].adjust_for_total_yards(yards)

                if env.args.vlevel > 5:
                    print(f"DEBUG {outcomes}")
                    print(f"DEBUG {offer}")


def parse_props(env: Env, player_dict: dict[Player]):
    fname = "in_props/vegasinsider-2022-08-24.html"
    with open(fname, "r") as f:
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


def parse_props2(env: Env, player_dict: dict[Player]):
    csv_fname = "in_props/dk_props_2023-07-23.csv"
    with open(csv_fname, "r", newline="") as f:
        stat_dict = header_to_stat_dict2()
        fixup_dict = name_fixup_dict()
        skip_list = name_skip_list()

        reader = csv.DictReader(f)

        for row in reader:
            if env.args.vlevel > 3:
                print(row)

            name = row["Player Name"]

            if name in fixup_dict:
                name = fixup_dict[name]

            if name in skip_list:
                if env.args.vlevel > 2:
                    print(f"Skipping {name}")
                continue

            if name not in player_dict:
                raise RuntimeError(f"{name} not found in database")

            if env.args.vlevel > 4:
                print(name)

            for k, v in row.items():
                if env.args.vlevel > 4:
                    print(f"  {k} = {v}")

                if k in stat_dict.keys():
                    player_dict[name].props[stat_dict[k]] = v


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


def header_to_stat_dict2() -> dict[str]:
    return {
        "Pass Yards": "pass_yards",
        "Pass TDs": "pass_tds",
        "Ints": "ints",
        "Rush Yards": "rush_yards",
        "Rush TDs": "rush_tds",
        "Rec Yards": "receive_yards",
        "Rec TDs": "receive_tds",
        "Receptions": "receptions",
    }


def props_points_dict() -> dict[str]:
    return {
        "pass_yards": 0.04,
        "pass_tds": 6.0,
        "ints": -2.0,
        "rush_yards": 0.1,
        "rush_tds": 6.0,
        "receive_yards": 0.1,
        "receive_tds": 6.0,
        "receptions": 0.5,
    }


def position_props(position: str) -> list[str]:
    pass_stats = ["pass_yards", "pass_tds", "ints"]
    rush_stats = ["rush_yards", "rush_tds"]
    receive_stats = ["receive_yards", "receive_tds", "receptions"]

    position_dict = {
        "QB": pass_stats + rush_stats,
        "RB": rush_stats + receive_stats,
        "WR": receive_stats + rush_stats,
        "TE": receive_stats,
    }

    return position_dict[position]


def name_skip_list() -> list[str]:
    return {
        "Desmond Ridder",
    }


def name_fixup_dict() -> dict[str]:
    return {
        # Initials
        "A.J. Dillon": "AJ Dillon",
        "D.J. Moore": "DJ Moore",
        "D.K. Metcalf": "DK Metcalf",
        "CJ Stroud": "C.J. Stroud",
        "JK Dobbins": "J.K. Dobbins",
        "TJ Hockenson": "T.J. Hockenson",
        # Suffixes
        "Travis Etienne Jr": "Travis Etienne",
        "Travis Etienne, Jr.": "Travis Etienne",
        "Michael Pittman, Jr.": "Michael Pittman",
        # Misspellings
        "Devin Montgomery": "David Montgomery",
        "Jacobi Meters": "Jakobi Meyers",
    }


def remove_players_with_no_props(
    env: Env, player_dict: dict[Player]
) -> dict[Player]:
    new_dict = {}

    for k, v in player_dict.items():
        if v.props:
            new_dict[k] = v

    return new_dict


def compute_prop_points(env: Env, player_dict: dict[Player]):
    points_dict = env.points_dict

    for _, player in player_dict.items():
        for k, v in player.props.items():
            # Values may have commas that need replaced before float()
            # conversion will work.
            player.prop_points += points_dict[k] * float(v.replace(",", ""))


def display_point_values(env: Env):
    print("Points values:")
    for k, v in env.points_dict.items():
        print(f"   {k}: {v}")
    print()


def display_position(env: Env, player_dict: dict[Player], position: str):
    player_list = []
    for _, player in player_dict.items():
        if player.position == position:
            player_list.append(player)

    player_list.sort(key=lambda player: player.prop_points, reverse=True)

    print(f"{position} Ranks")
    rank = 1
    headers = ["Rank", "Name", "Prop Points", "ADP", "XRank", "FP Rank"]
    headers.extend(position_props(position))
    table = []
    for p in player_list:
        row = [rank, p.name, f"{p.prop_points:.2f}", p.adp, p.xrank, p.fp_rank]
        for k in position_props(position):
            if k in p.props:
                row.append(p.props[k])
            else:
                row.append("")
        table.append(row)
        rank += 1
    print(tabulate(table, headers=headers))
    print("")


def get_props_data(env: Env, info: DataDownload):
    out_dir = f"{env.args.directory}/" if env.args.directory != None else ""

    now = datetime.now()
    out_fname = f"{out_dir}{info.local_file_prefix}-{now.year}-{now.month:02d}-{now.day:02d}.{info.local_file_ext}"

    props_req = urllib.request.Request(
        info.url, headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(props_req) as response, open(
        out_fname, "wb"
    ) as out_file:
        shutil.copyfileobj(response, out_file)


def do_download(env: Env):
    get_props_data(
        env,
        DataDownload(
            "https://www.vegasinsider.com/nfl/odds/player-prop-betting-odds/",
            "vegasinsider",
            "html",
        ),
    )
    get_props_data(
        env,
        DataDownload(
            "https://sportsbook.draftkings.com//sites/US-SB/api/v5/eventgroups/88808/categories/782/subcategories/8415",
            "dk_total_yards",
            "json",
        ),
    )


def props_ev():
    env = Env(props_points_dict())

    if env.args.do_download:
        do_download(env)
        return

    player_dict = {}
    init_player_dict(env, player_dict)
    parse_props2(env, player_dict)
    # parse_total_yards(env, player_dict)
    player_dict = remove_players_with_no_props(env, player_dict)
    compute_prop_points(env, player_dict)

    if env.args.vlevel > 0:
        for k, v in player_dict.items():
            print(v)

    display_point_values(env)
    display_position(env, player_dict, "QB")
    display_position(env, player_dict, "RB")
    display_position(env, player_dict, "WR")
    display_position(env, player_dict, "TE")


if __name__ == "__main__":
    props_ev()
