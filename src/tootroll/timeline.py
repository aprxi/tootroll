import re
import sys
import json
import logging
import requests  # type: ignore

from json.decoder import JSONDecodeError
from typing import Dict, List, Tuple, Any

from .oauth import check_rate_limits
from .utils import iso8601_to_timestamp

logger = logging.getLogger(__name__)

# default number of toots per HTTP request
# note: most servers apply max limit of 40
TOOTS_PER_REQUEST = 40

# TIMELINE_FUNCTIONS = {
#     "id": int,
#     "created_at": iso8601_to_timestamp,
#     "reblog_created_at": iso8601_to_timestamp,
#     "is_reblog": bool,
#     "url": str,
#     "replies_count": int,
#     "reblogs_count": int,
#     "favourites_count": int,
#     "content": str,
# }
TIMELINE_FUNCTIONS = {
    "id": int,
    "created_at": iso8601_to_timestamp,
    "url": str,
    "replies_count": int,
    "reblogs_count": int,
    "favourites_count": int,
    "content": str,
}


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


# def parse_toot_reblog(toot: Dict[str, Any]) -> Dict[str, Union[int, str, bool]]:
# def parse_toot_regular(toot: Dict[str, Any]) -> Dict[str, Union[int, str, bool]]:


def http_get_toots(
    url_base: str,
    access_token: str,
    writer: Any,
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

        try:
            toots: List[Dict[str, Any]] = json.loads(response.content)
        except JSONDecodeError:
            sys.stderr.write(f"Cant parse response content:{response.content}")
            break

        logger.debug(f"Received {len(toots)} toots")

        if len(toots) < 1:
            break

        toots_validated = [t for t in toots if t["url"] and t["content"]]
        toots_sorted = sorted(toots_validated, key=lambda t: t["id"], reverse=False)
        toots_added = writer.add_toots(toots_sorted)

        if len(toots) < TOOTS_PER_REQUEST or toots_added < len(toots_validated):
            logger.debug("End of timeline reached")
            break

        # url_params["min_id"] = str(toots[0]["id"])

        next_link = response.headers.get("Link", "").split(";", 1)[0].strip("<>")
        max_id_search = re.search("max_id=[0-9]*", next_link)
        if not max_id_search:
            break
        url_params["max_id"] = (
            re.search("max_id=[0-9]*", next_link).group().split("=", 1)[-1]
        )

        param_str = "&".join([f"{key}={value}" for key, value in url_params.items()])
        link = f"{url_base}?{param_str}"

    writer.close()
