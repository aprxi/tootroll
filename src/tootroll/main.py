import os
import sys
import json
import argparse

from datetime import datetime, timedelta
from typing import List, NoReturn

from .accounts import account_update, account_login, account_list
from .fetch import fetch_toots
from .timeline import read_toots
from .db.sqlite import write_toots
from .utils import configure_logger
from .http.api import app_main
from .vars import TOOTROLL_HOME


class CustomArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        sys.stderr.write(f"error: {message}\n")
        sys.stderr.write(self.format_help())
        sys.exit(2)


def cli_main(cli_args: List[str]) -> int:

    module_name = __name__.split(".", 1)[0]
    configure_logger(name=module_name, debug=(os.environ.get("DEBUG", "") != ""))
    parser = CustomArgParser(prog=module_name)

    subparsers = parser.add_subparsers(help="<sub-command> help", dest="command")

    # configure
    parser_configure = subparsers.add_parser("configure", help="Configure accounts")
    parser_configure.add_argument(
        "account",
        nargs="?",
        default="@",
        help="Create (or update) an account. Defaults to all accounts"
    )

    # fetch
    parser_fetch = subparsers.add_parser("fetch", help="Fetch new toots")
    parser_fetch.add_argument(
        "feed",
        nargs="?",
        default="home",
        help="Select feed (e.g. home)"
    )
    parser_fetch.add_argument(
        "-a",
        "--account",
        action="store",
        default="",
        type=str,
        help="Specify account. Defaults to primary account"
    )
    parser_fetch.add_argument(
        "-l",
        "--limit",
        action="store",
        default=400,
        type=int,
        help="Limit number of toots. Defaults to 400 -- 10 API-calls",
    )

    # timeline
    parser_timeline = subparsers.add_parser("timeline", help="Show timeline")
    parser_timeline.add_argument(
        "-a",
        "--account",
        action="store",
        default="",
        type=str,
        help="Specify account. Defaults to primary account"
    )
    parser_timeline.add_argument(
        "timeline",
        nargs="?",
        default="default",
        help="Select timeline"
    )

    parser_timeline.add_argument(
        "-s",
        "--start",
        action="store",
        default=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        type=str,
        help="Start date -- defaults to today - 3 days",
    )
    parser_timeline.add_argument(
        "-e",
        "--end",
        action="store",
        default=datetime.now().strftime("%Y-%m-%d"),
        type=str,
        help="End date -- defaults to today",
    )
    parser_timeline.add_argument(
        "-l",
        "--limit",
        action="store",
        default=40,
        type=int,
        help="Limit number of toots. Defaults to 40",
    )

    # show
    parser_show = subparsers.add_parser("show", help="Show configuration")
    parser_show.add_argument("configuration", help="Show configuration type")

    # web
    parser_web = subparsers.add_parser("web", help="Run webserver")
    parser_web.add_argument("--run", action="store_true", help="Start webserver")

    args = parser.parse_args(args=cli_args)

    if args.command == "timeline":

        if not args.account:
            login_names = [acct["name"] for acct in account_list()]
        else:
            login_names = [args.account]

        if args.timeline == "default":
            # show timeline in chronological order
            for username in login_names:
                toots = read_toots(
                    f"{TOOTROLL_HOME}/{username}/feed",
                    "home",
                    (args.start, args.end),
                    args.limit,
                )
                write_toots(
                    toots,
                    f"{TOOTROLL_HOME}/{username}/timeline",
                    "home",
                )
            pass

        return 0
    elif args.command == "configure":
        account_name = args.account.lower()
        if "@" not in account_name:
            sys.stderr.write(f"Invalid AccountName: {account_name}")
            return 1
        status = account_update(account_name)
        if status == 0:
            sys.stdout.write("Account configuration complete.\n")
        return status
    elif args.command == "fetch":
        if not args.account:
            login_names = [acct["name"] for acct in account_list()]
        else:
            login_names = [args.account]

        if args.feed == "home":
            for username in login_names:
                login = account_login(username)
                if login is None:
                    sys.stderr.write(f"No access token for account: {username}\n")
                    continue

                base_url = f'https://{login["server"]}/api/v1/timelines/home'
                status = fetch_toots(
                    base_url,
                    f"{TOOTROLL_HOME}/{username}/feed",
                    login["access_token"],
                    args.limit,
                    print_stats=True,
                )
                if status != 0:
                    return status
            return 0
        else:
            sys.stderr.write(f"Unknown feed: {args.feed}\n")
            return
    elif args.command == "show":
        if args.configuration == "accounts":
            sys.stdout.write("Accounts configured:\n")
            sys.stdout.write(json.dumps(account_list(), indent=4, default=str) + "\n")
        else:
            sys.stderr.write(parser.format_help())
            return 1
        return 0
    elif args.command == "web":
        # run as webserver
        app_main()
        return 0
    else:
        sys.stderr.write(parser.format_help())
        return 1
