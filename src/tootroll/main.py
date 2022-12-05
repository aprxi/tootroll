import os
import sys
import json
import argparse

from datetime import datetime
from typing import List, Dict, Any, NoReturn, Optional

from .accounts import profile_update, profile_login, profile_list
from .timeline import TootItem, http_get_toots
from .utils import configure_logger, iso8601_to_timestamp
from .db.parquet import read_parquet, ParquetWriter
from .vars import extract_hostname
from .http.api import app_main


class CustomArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        sys.stderr.write(f"error: {message}\n")
        sys.stderr.write(self.format_help())
        sys.exit(2)


def get_toots(
    base_url: str,
    access_token: str,
    update_type: str,
    limit: int,
) -> int:
    url_params = {
        "local": "false",
    }

    writer = ParquetWriter(f"{extract_hostname(base_url)}/home", limit)
    if update_type == "fill":
        last_id = writer.get_last_ids(limit=1)
        if last_id:
            url_params["min_id"] = str(last_id[0])
    elif update_type == "latest":
        # default is to get latest
        pass
    else:
        sys.stderr.write(
            f"Unknown update option: '{update_type}',\
valid choices: ['latest', 'fill']\n"
        )
        return 1

    http_get_toots(
        base_url,
        access_token,
        writer,
        max_toots=limit,
        url_params=url_params,
    )

    return 0


def cli_main(cli_args: List[str]) -> int:

    module_name = __name__.split(".", 1)[0]
    configure_logger(name=module_name, debug=(os.environ.get("DEBUG", "") != ""))
    parser = CustomArgParser(prog=module_name)

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--web",
        action="store_true",
        help="Start webserver",
    )
    group.add_argument(
        "--configure",
        action="store_true",
        help="Create or update a profile",
    )
    group.add_argument(
        "--show",
        action="store",
        nargs="?",
        metavar="profiles",
        const="profiles",
        help="Show configuration (e.g. list of profiles)",
    )

    # optional arguments
    parser.add_argument(
        "--profile",
        action="store",
        default="default",
        help="Select a profile to use. If left empty, lists configured profiles",
    )
    parser.add_argument(
        "-u",
        "--update",
        action="store",
        nargs="?",
        const="latest",
        help="Get latest data",
    )
    parser.add_argument(
        "-l",
        "--limit",
        action="store",
        default=40,
        type=int,
        help="Limit number of toots. Defaults to 40 -- 1 API-call",
    )

    args = parser.parse_args(args=cli_args)

    if args.web:
        # run as webserver
        app_main()

    elif args.configure:
        response_status = profile_update(name=args.profile)
        if response_status == 0:
            sys.stdout.write(f"Saved profile '{args.profile}' succesfully\n")
        else:
            sys.stderr.write(f"Error saving profile '{args.profile}'\n")
        return response_status

    elif args.show:
        action = args.show.lower()
        if action == "profiles":
            sys.stdout.write("Profiles available:\n")
            sys.stdout.write(json.dumps(profile_list(), indent=4, default=str) + "\n")
            return 0
        else:
            sys.stderr.write(parser.format_help())
            return 1
    else:
        login = profile_login(args.profile)
        if login is None:
            sys.stderr.write(f"Cant get access token for profile: {args.profile}\n")
            return 1

        base_url = f'https://{login["server"]}/api/v1/timelines/home'
        if args.update:
            return get_toots(
                base_url,
                login["access_token"],
                args.update,
                args.limit,
            )
        else:
            toots = read_parquet(url_to_keyname(base_url), args.limit)
            for toot in toots:
                sys.stdout.write(
                    "\n".join(
                        [
                            f"{datetime.fromtimestamp(toot.created_at).isoformat()} {toot.acct}",
                            toot.content[0:600],
                        ]
                    )
                    + "\n\n"
                )
