import sys
import json
import requests  # type: ignore

from json.decoder import JSONDecodeError
from typing import Dict, List, Tuple, Any

from .oauth import check_rate_limits


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
    return request_limit, toot_limit


def http_get_toots(
    link: str, access_token: str, request_limit: int = 1
) -> List[Dict[str, Any]]:

    total_toots: List[Dict[str, Any]] = []
    link_history: List[str] = []

    rate_limit_remaining = 300  # initially assume default

    while rate_limit_remaining > 0 and request_limit > 0:
        request_limit -= 1
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

        link_history.append(link)
        try:
            toots: List[Dict[str, Any]] = json.loads(response.content)
        except JSONDecodeError:
            sys.stderr.write(f"Cant parse response content:{response.content}")
            break

        total_toots += toots

        next_link = response.headers.get("Link", "").split(";", 1)[0].strip("<>")
        if not next_link:
            # no more links to follow
            break
        if next_link in link_history:
            # break on repeat
            break
        # continue
        link = next_link

    return total_toots


def timeline_by_tag(
    login: Dict[str, str], tag: str, max_toots: int = 10
) -> List[Dict[str, Any]]:

    toot_limit, request_limit = calculate_request_limits(max_toots)
    link = f'https://{login["server"]}/api/v1/timelines/tag/{tag}?limit={toot_limit}'

    return http_get_toots(link, login["access_token"], request_limit=request_limit)[
        :max_toots
    ]


def timeline_home(login: Dict[str, str], max_toots: int = 10) -> List[Dict[str, Any]]:

    toot_limit, request_limit = calculate_request_limits(max_toots)
    link = f'https://{login["server"]}/api/v1/timelines/home?limit={toot_limit}'

    return http_get_toots(link, login["access_token"], request_limit=request_limit)[
        :max_toots
    ]


def timeline_public(login: Dict[str, str], max_toots: int = 10) -> List[Dict[str, Any]]:

    toot_limit, request_limit = calculate_request_limits(max_toots)
    link = f'https://{login["server"]}\
/api/v1/timelines/public?false=true&limit={toot_limit}'

    return http_get_toots(link, login["access_token"], request_limit=request_limit)[
        :max_toots
    ]
