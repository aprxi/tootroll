import os
import re
import sys
import json

from json.decoder import JSONDecodeError
from typing import Dict, List, Optional

from .oauth import verify_credentials
from .utils import write_secrets_file, read_file
from .vars import TOOTROLL_HOME, SECRETS_DIR


def profile_save(profile: Dict[str, str], access_token: str) -> int:

    os.makedirs(SECRETS_DIR, exist_ok=True)
    token_file = f'{SECRETS_DIR}/{profile["token_file"]}'

    write_secrets_file(token_file, access_token.encode())

    profile_file = f'{TOOTROLL_HOME}/{profile["name"]}.profile'
    with open(profile_file, "w") as wfile:
        wfile.write(json.dumps(profile, indent=4, default=str))
    # successfully written files
    return 0


def account_list() -> List[Dict[str, str]]:
    if os.path.isdir(TOOTROLL_HOME) is False:
        return []

    accounts: List[Dict[str, str]] = list(
        [
            json.loads(read_file(f"{TOOTROLL_HOME}/{fn}") or "{}")
            for fn in os.listdir(TOOTROLL_HOME)
            if re.match("^@[-a-zA-Z0-9_]*@[-a-zA-Z0-9_]*\\.[a-z]*\\.profile$", fn)
        ]
    )
    return accounts


def account_login(name: str) -> Optional[Dict[str, str]]:
    profile_file = f"{TOOTROLL_HOME}/{name}.profile"
    invalid_error = f"Profile '{name}' invalid. Run with '--configure' to update.\n"

    try:
        contents = read_file(profile_file)
        assert isinstance(contents, str)
        profile: Dict[str, str] = json.loads(contents)
        access_token = read_file(f'{SECRETS_DIR}/{profile["token_file"]}')
        assert isinstance(access_token, str)
        assert access_token != ""
        profile["access_token"] = access_token
        del profile["token_file"]
    except KeyError:
        sys.stderr.write(invalid_error)
        return None
    except AssertionError:
        sys.stderr.write(invalid_error)
        return None
    except JSONDecodeError:
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

    return profile_save(
        profile={
            "name": name,
            "server": host_server,
            "access_type": "private",
            "token_file": f"{name}_token.secret",
        },
        access_token=access_token,
    )
