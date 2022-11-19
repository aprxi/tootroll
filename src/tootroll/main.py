import os
import sys
import json
import argparse

from typing import List, Dict, Any, NoReturn

from .accounts import profile_update, profile_login, profile_list
from .timeline import http_get_toots
from .utils import configure_logger


class CustomArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        sys.stderr.write(f"error: {message}\n")
        sys.stderr.write(self.format_help())
        sys.exit(2)


def timeline_to_stdout(timeline: List[Dict[str, Any]]) -> None:
    sys.stdout.write(json.dumps(timeline, default=str))


def cli_main(cli_args: List[str]) -> int:

    module_name = __name__.split(".", 1)[0]
    configure_logger(name=module_name, debug=(os.environ.get("DEBUG", "") != ""))
    parser = CustomArgParser(prog=module_name)

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--pub",
        action="store_true",
        help="Show public timeline of server",
    )
    group.add_argument(
        "--home",
        action="store_true",
        help="Show home timeline",
    )
    group.add_argument(
        "--tags",
        action="store",
        help="Tag(s). Use comma-separated string to pass a list",
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
        "-l",
        "--limit",
        action="store",
        default=10,
        type=int,
        help="Limit number of toots. Defaults to 10",
    )

    args = parser.parse_args(args=cli_args)

    if args.pub:

        login = profile_login(args.profile)
        if login is None:
            sys.stderr.write(f"Cant get access token for profile: {args.profile}\n")
            return 1

        http_get_toots(
            f'https://{login["server"]}/api/v1/timelines/public',
            login["access_token"],
            timeline_to_stdout,
            max_toots=args.limit,
            url_params={
                "local": "false",
            },
        )
        return 0

    elif args.home:
        login = profile_login(args.profile)
        if login is None:
            sys.stderr.write(f"Cant get access token for profile: {args.profile}\n")
            return 1

        http_get_toots(
            f'https://{login["server"]}/api/v1/timelines/home',
            login["access_token"],
            timeline_to_stdout,
            max_toots=args.limit,
        )
        return 0

    elif args.tags:
        login = profile_login(args.profile)
        if login is None:
            sys.stderr.write(f"Cant get access token for profile: {args.profile}\n")
            return 1

        tags = args.tags.split(",")
        for tag in tags:
            http_get_toots(
                f'https://{login["server"]}/api/v1/timelines/tag/{tag}',
                login["access_token"],
                timeline_to_stdout,
                max_toots=args.limit,
            )
        return 0

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
        sys.stderr.write(parser.format_help())
        return 1
