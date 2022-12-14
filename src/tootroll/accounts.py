import os
import re
import sys
import json

from typing import Dict, List, Optional

from .oauth import verify_credentials
from .utils import write_secrets_file, read_file
from .vars import TOOTROLL_HOME


def account_save(profile: Dict[str, str], access_token: str) -> int:

    account_dir = f'{TOOTROLL_HOME}/{profile["name"]}'
    os.makedirs(account_dir, exist_ok=True)
    token_file = f"{account_dir}/.access_token"
    write_secrets_file(token_file, access_token.encode())
    return 0


def account_list() -> List[Dict[str, str]]:
    if os.path.isdir(TOOTROLL_HOME) is False:
        return []

    accounts: List[Dict[str, str]] = list(
        [
            {"name": dn}
            for dn in os.listdir(TOOTROLL_HOME)
            if re.match("^@[-a-zA-Z0-9_]*@[-a-zA-Z0-9_]*\\.[a-z]*$", dn)
            and os.path.isdir(f"{TOOTROLL_HOME}/{dn}")
        ]
    )
    return accounts


def account_login(name: str) -> Optional[Dict[str, str]]:

    invalid_error = f"Account '{name}' invalid. Run with '--configure' to update.\n"

    account_dir = f"{TOOTROLL_HOME}/{name}"
    if not os.path.isdir(account_dir):
        sys.stderr.write(invalid_error)
        return None

    token_file = f"{account_dir}/.access_token"
    _, host_server = name.rsplit("@", 1)

    profile = {"server": host_server}

    try:
        access_token = read_file(token_file)
        assert isinstance(access_token, str)
        assert access_token != ""
        profile["access_token"] = access_token
    except AssertionError:
        sys.stderr.write(invalid_error)
        return None
    return profile


def account_update(name: str, access_token: Optional[str] = None) -> int:

    sys.stdout.write(f"Configure or Update Account.\n{'-'*40}\n")

    name_input_str = "Name of Account (format: @user@server): "
    if name == "@":
        name = input(name_input_str).lower()
        if not name:
            sys.stderr.write("No input given, exiting...\n")
            return 2
    else:
        sys.stdout.write(f"{name_input_str} {name}\n")

    if name[0] != "@":
        name = f"@{name}"

    if not re.match("^@[-a-zA-Z0-9_]*@[-a-zA-Z0-9_]*\\.[a-z]*$", name):
        sys.stderr.write(f"Invalid account name: {name}\n")
        return 2

    _, host_server = name.rsplit("@", 1)

    if not host_server:
        sys.stderr.write(" server selected!\n")
        return 2

    # private access_token required -- strip leading and trailing spaces
    if not access_token:
        access_token = input("Access token: ").strip()
        if not access_token:
            sys.stderr.write("No input given, exiting...\n")
            return 2

    response = verify_credentials(host_server, access_token)
    if not response:
        # return -- verify_credentials() writes to stderr
        return 2

    return account_save(
        profile={
            "name": name,
            "server": host_server,
            "access_type": "private",
        },
        access_token=access_token,
    )
