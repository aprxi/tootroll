import sys
import json
import logging
import requests  # type: ignore

from json.decoder import JSONDecodeError
from typing import Dict, List, Tuple, Callable, Any

from .oauth import check_rate_limits


logger = logging.getLogger(__name__)

# default number of toots per HTTP request
# note: most servers apply max limit of 40
TOOTS_PER_REQUEST = 40


def calculate_request_limits(max_toots: int) -> Tuple[int, int]:
    """return number of HTTP requests required and initial toot_limit

    initial toot_limit is either max_toots, or the default TOOTS_PER_REQUEST
    because follow-up links include the inital limit"""
    if max_toots > TOOTS_PER_REQUEST:
        toot_limit = TOOTS_PER_REQUEST
        # round up
        request_limit = (max_toots + TOOTS_PER_REQUEST - 1) // TOOTS_PER_REQUEST
    else:
        toot_limit = max_toots
        request_limit = 1
    return toot_limit, request_limit


def http_get_toots(
    url_base: str,
    access_token: str,
    write_callback: Callable[[List[Dict[str, Any]]], None],
    max_toots: int = 1,
    url_params: Dict[str, str] = {},
) -> None:

    toot_limit, request_limit = calculate_request_limits(max_toots)
    url_params.update(
        {
            "limit": str(toot_limit),
        }
    )

    param_str = "&".join([f"{key}={value}" for key, value in url_params.items()])
    link = f"{url_base}?{param_str}"

    link_history: List[str] = []

    rate_limit_remaining = 300  # initially assume default

    while rate_limit_remaining > 0 and request_limit > 0:
        request_limit -= 1
        logger.debug(f"GET {link}")
        response = requests.get(
            link,
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )
        if response.status_code != 200:
            sys.stderr.write(f"HTTP{response.status_code}: {response.content}\n")
            break

        rate_limit_remaining, _ = check_rate_limits(dict(response.headers)) or (0, 0)
        logger.debug(
            f"rate_limit_remaining={rate_limit_remaining},request_limit={request_limit}"
        )

        link_history.append(link)
        try:
            toots: List[Dict[str, Any]] = json.loads(response.content)
        except JSONDecodeError:
            sys.stderr.write(f"Cant parse response content:{response.content}")
            break

        write_callback(toots)

        next_link = response.headers.get("Link", "").split(";", 1)[0].strip("<>")
        if not next_link:
            # no more links to follow
            break
        if next_link in link_history:
            # break on repeat
            break
        # continue
        link = next_link
