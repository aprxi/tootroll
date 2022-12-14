import os
import sys
import json
import argparse

from typing import List, NoReturn

from .accounts import account_update, account_login, account_list
from .timeline import http_get_toots
from .utils import configure_logger
from .db.parquet import ParquetWriter
from .vars import extract_hostname, TOOTROLL_HOME
from .http.api import app_main


class CustomArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        sys.stderr.write(f"error: {message}\n")
        sys.stderr.write(self.format_help())
        sys.exit(2)


def get_toots(
    base_url: str,
    database_path: str,
    access_token: str,
    limit: int,
) -> int:
    url_params = {
        "local": "false",
    }

    writer = ParquetWriter(database_path, f"{extract_hostname(base_url)}/home", limit)

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

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--web",
        action="store_true",
        help="Start webserver",
    )
    group.add_argument(
        "--configure",
        action="store",
        nargs="?",
        metavar="ACCOUNT",
        const="@",
        help="Create or update a profile",
    )
    group.add_argument(
        "--accounts",
        action="store_true",
        help="List accounts",
    )
    group.add_argument(
        "-u",
        "--update",
        action="store",
        nargs="?",
        const="__all__",
        help="Get latest data",
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
        default=400,
        type=int,
        help="Limit number of toots. Defaults to 40 -- 1 API-call",
    )

    args = parser.parse_args(args=cli_args)

    if args.web:
        # run as webserver
        app_main()
        return 0
    elif args.configure:
        account_name = args.configure.lower()
        if "@" not in account_name:
            sys.stderr.write(f"Invalid AccountName: {account_name}")
            return 1
        status = account_update(account_name)
        if status == 0:
            sys.stdout.write("Account configuration complete.\n")
        return status
    elif args.accounts:
        sys.stdout.write("Accounts configured:\n")
        sys.stdout.write(json.dumps(account_list(), indent=4, default=str) + "\n")
        return 0
    elif args.update:

        if args.update == "__all__":
            login_names = [acct["name"] for acct in account_list()]
        else:
            login_names = [args.update]

        for name in login_names:
            login = account_login(name)
            if login is None:
                sys.stderr.write(f"Cant get access token for account: {args.profile}\n")
                continue

            base_url = f'https://{login["server"]}/api/v1/timelines/home'
            status = get_toots(
                base_url,
                f"{TOOTROLL_HOME}/{name}/db",
                login["access_token"],
                args.limit,
            )
            if status != 0:
                return status
        return 0
    else:
        sys.stderr.write(parser.format_help())
        return 1
