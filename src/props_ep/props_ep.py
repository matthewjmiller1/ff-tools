#!/usr/bin/env python3

import argparse
import urllib.request
from dataclasses import dataclass, field
from bs4 import BeautifulSoup


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

    fname = "in_html/vegasinsider-2022-08-14.html"
    with open(fname) as f:
        props_soup = BeautifulSoup(f, "html.parser")
        print(props_soup.prettify())
        for header in props_soup.find_all("h2"):
            print(header.text)
            if header.text == "2022-23 NFL PASSING YARDS TOTALS":
                ul = header.find_next("ul")
                print(ul)
                for li in ul.select("li"):
                    print(li.text)
                    print(li.contents[0].strip())
                    print(li.contents[1].text)


if __name__ == "__main__":
    props_ev()
