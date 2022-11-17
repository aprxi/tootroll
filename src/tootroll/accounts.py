import os
import re
import sys
import json

from json.decoder import JSONDecodeError
from typing import Dict, List, Optional

from .oauth import verify_credentials, get_access_token
from .utils import write_secrets_file, read_file
from .vars import CONFIG_DIR, SECRETS_DIR, DEFAULT_SERVERS


def profile_save(profile: Dict[str, str], access_token: str) -> int:

    os.makedirs(SECRETS_DIR, exist_ok=True)
    token_file = f'{SECRETS_DIR}/{profile["token_file"]}'

    write_secrets_file(token_file, access_token.encode())

    profile_file = f'{CONFIG_DIR}/{profile["name"]}.profile'
    with open(profile_file, "w") as wfile:
        wfile.write(json.dumps(profile, indent=4, default=str))
    # successfully written files
    return 0


def profile_list() -> List[Dict[str, str]]:
    if os.path.isdir(CONFIG_DIR) is False:
        return []

    profiles: List[Dict[str, str]] = list(
        [
            json.loads(read_file(f"{CONFIG_DIR}/{fn}") or "{}")
            for fn in os.listdir(CONFIG_DIR)
            if re.match("[-a-zA-Z0-9_]*.profile$", fn)
        ]
    )
    return profiles


def profile_login(name: str) -> Optional[Dict[str, str]]:
    profile_file = f"{CONFIG_DIR}/{name}.profile"
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


def profile_update(name: str) -> int:

    sys.stdout.write(f"Configure or Update profile.\n{'-'*40}\n")
    name = input(f"Name of Profile [{name}]: ") or name

    if not re.match("^[-a-zA-Z0-9_]*$", name):
        sys.stderr.write("Invalid profile name\n")
        return 2

    server_prompt = (
        "Select server\n  "
        + "\n  ".join(
            [f"{idx + 1}. {host}" for idx, host in enumerate(DEFAULT_SERVERS)]
        )
        + "\n  4. other..."
    )

    raw_input = input(f"{server_prompt}\n[4]: ") or "4"
    try:
        idx = int(raw_input) - 1
        if idx >= 0 and idx < len(DEFAULT_SERVERS):
            host_server = DEFAULT_SERVERS[idx]
        else:
            # selected server not available
            host_server = input("  other: ") or ""
    except ValueError:
        # assume user typed server name
        host_server = raw_input

    if not host_server:
        sys.stderr.write("No server selected!\n")
        return 2

    private_api = input("Use private API? [y/N]: ").lower() or "N"
    if private_api in ["y", "yes"]:
        access_type = "private"
        # private access_token required
        access_token = input("Access token: ")
        if not access_token:
            sys.stderr.write("Access token required!\n")
            return 2
    else:
        # get public access token
        access_type = "public"
        access_token = get_access_token(host_server) or ""
        if not access_token:
            sys.stderr.write("Cant acquire access token!\n")
            return 2

    response = verify_credentials(host_server, access_token)
    if not response:
        sys.stderr.write("Access token cant be verified!\n")
        return 2

    return profile_save(
        profile={
            "name": name,
            "server": host_server,
            "access_type": access_type,
            "token_file": f"{name}_token.secret",
        },
        access_token=access_token,
    )
