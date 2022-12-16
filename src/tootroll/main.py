import os
import sys
import json
import argparse

from typing import List, NoReturn

from .accounts import account_update, account_login, account_list
from .timeline import http_get_toots
from .utils import configure_logger
from .db.parquet import ParquetWriter
from .vars import TOOTROLL_HOME
from .http.api import app_main


class CustomArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        sys.stderr.write(f"error: {message}\n")
        sys.stderr.write(self.format_help())
        sys.exit(2)


def get_toots(
    name: str,
    base_url: str,
    access_token: str,
    limit: int,
) -> int:
    url_params = {
        "local": "false",
    }

    database_path = f"{TOOTROLL_HOME}/{name}/timeline"
    writer = ParquetWriter(database_path, "home", limit)
    http_get_toots(
        base_url,
        access_token,
        writer,
        max_toots=limit,
        url_params=url_params,
    )

    sys.stdout.write(
        f"toots_total={writer.stat_toots_total},\
toots_added={writer.stat_toots_added}\n"
    )

    return 0


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
    parser_fetch.add_argument("timeline", help="Select timeline")
    parser_fetch.add_argument(
        "account",
        nargs="?",
        help="Specify account. Defaults to all accounts"
    )
    # optional arguments
    parser_fetch.add_argument(
        "-l",
        "--limit",
        action="store",
        default=400,
        type=int,
        help="Limit number of toots. Defaults to 40 -- 1 API-call",
    )

    # show
    parser_show = subparsers.add_parser("show", help="Show configuration")
    parser_show.add_argument("configuration", help="Show configuration type")

    # web
    parser_web = subparsers.add_parser("web", help="Run webserver")
    parser_web.add_argument("--run", action="store_true", help="Start webserver")

    args = parser.parse_args(args=cli_args)

    if args.command == "web":
        # run as webserver
        app_main()
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
    elif args.command == "show":
        if args.configuration == "accounts":
            sys.stdout.write("Accounts configured:\n")
            sys.stdout.write(json.dumps(account_list(), indent=4, default=str) + "\n")
        else:
            sys.stderr.write(parser.format_help())
            return 1
        return 0
    elif args.command == "fetch":
        if args.timeline == "home":
            if not args.account:
                login_names = [acct["name"] for acct in account_list()]
            else:
                login_names = [args.account]

            for name in login_names:
                login = account_login(name)
                if login is None:
                    sys.stderr.write(f"No access token for account: {name}\n")
                    continue

                base_url = f'https://{login["server"]}/api/v1/timelines/home'
                status = get_toots(
                    name,
                    base_url,
                    login["access_token"],
                    args.limit,
                )
                if status != 0:
                    return status
            return 0
        else:
            sys.stderr.write(f"Unknown timeline: {args.timeline}\n")
            return
    else:
        sys.stderr.write(parser.format_help())
        return 1
