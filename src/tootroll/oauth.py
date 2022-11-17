import os
import sys
import json
import requests  # type: ignore

from json.decoder import JSONDecodeError
from typing import Dict, Optional, Tuple

from .utils import lower_dict_keys, write_secrets_file
from .vars import SECRETS_DIR


DEFAULT_APP_NAME = "tootroll"


def register_application(server: str) -> Optional[Dict[str, str]]:

    requests_data = {
        "client_name": DEFAULT_APP_NAME,
        "redirect_uris": "urn:ietf:wg:oauth:2.0:oob",
        "scopes": "read write follow push",
    }

    response = requests.post(f"https://{server}/api/v1/apps", data=requests_data)
    if response.status_code != 200:
        sys.stderr.write(f"HTTP{response.status_code}: {response.content}\n")
        return None
    try:
        content: Dict[str, str] = json.loads(response.content.decode())
        return content
    except JSONDecodeError:
        sys.stderr.write(f"Invalid content:{str(response.content)[0:100]}\n")
        return None


def validate_application_secrets(
    secrets_data: Dict[str, str]
) -> Optional[Dict[str, str]]:

    mandatory_keys = ["client_id", "client_secret", "redirect_uri"]
    for key in mandatory_keys:
        try:
            assert key in secrets_data
        except AssertionError:
            sys.stderr.write(f"Secrets data incomplete, missing key:{key}\n")
            return None
    return secrets_data


def application_secrets(server: str) -> Optional[Dict[str, str]]:
    secrets_file = f"{SECRETS_DIR}/{server}_{DEFAULT_APP_NAME}.secret"

    if os.path.exists(secrets_file):
        with open(secrets_file, "r") as rstream:
            try:
                data = json.loads(rstream.read())
            except JSONDecodeError:
                return None
            secrets_data = validate_application_secrets(data)
    else:
        secrets_data = register_application(server)
        if not secrets_data:
            return None
        secrets_data = validate_application_secrets(secrets_data)
        os.makedirs(SECRETS_DIR, exist_ok=True)
        write_secrets_file(
            secrets_file, json.dumps(secrets_data, indent=4, default=str).encode()
        )

    return secrets_data


def check_rate_limits(headers: Dict[str, str]) -> Optional[Tuple[int, int]]:
    headers = lower_dict_keys(headers)
    try:
        api_limit_remaining = int(headers["x-ratelimit-remaining"])
        api_limit = int(headers["x-ratelimit-limit"])
        return api_limit_remaining, api_limit
    except KeyError as error:
        sys.stderr.write(f"HTTP response does not include {error}\n")
        return None
    except ValueError:
        sys.stderr.write("HTTP response does not contain valid ratelimits\n")
        return None


def verify_credentials(server: str, token: str) -> Optional[Tuple[int, int]]:
    response = requests.get(
        f"https://{server}/api/v1/apps/verify_credentials",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    if response.status_code != 200:
        sys.stderr.write(f"HTTP{response.status_code}: {response.content}\n")
        return None
    return check_rate_limits(dict(response.headers))


def get_access_token(server: str) -> Optional[str]:
    client_secrets = application_secrets(server)
    if client_secrets is None:
        return None

    requests_data = {
        "client_id": client_secrets["client_id"],
        "client_secret": client_secrets["client_secret"],
        "redirect_uri": client_secrets["redirect_uri"],
        "grant_type": "client_credentials",
    }

    response = requests.post(
        f"https://{server}/oauth/token",
        data=requests_data,
    )
    if response.status_code != 200:
        sys.stderr.write(f"HTTP{response.status_code}: {response.content}\n")
        return None

    try:
        token_data = json.loads(response.content)
        access_token = token_data["access_token"]
        assert isinstance(access_token, str)
        assert access_token != ""
    except KeyError as error:
        sys.stderr.write(f"HTTP response does not include {error}\n")
        return None
    except JSONDecodeError:
        sys.stderr.write("HTTP response does not contain valid access token\n")
        return None
    except AssertionError:
        sys.stderr.write("HTTP response does not contain valid access token\n")
        return None

    return access_token
