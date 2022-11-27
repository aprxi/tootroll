import re
import sys
import json
import logging
import requests  # type: ignore

from dataclasses import dataclass
from json.decoder import JSONDecodeError
from typing import Dict, List, Tuple, Optional, Any

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

@dataclass
class TootItem:
    id: int
    created_at: int
    url: str
    acct: str
    replies_count: int
    reblogs_count: int
    favourites_count: int
    content: str
    ref_id: Optional[int] = None
    ref_created_at: Optional[int] = None
    ref_acct: Optional[str] = None


def parse_toot_item(toot_dict: Dict[str, Any]) -> Optional[TootItem]:

    if isinstance(toot_dict["reblog"], dict):
        # reblog
        # copy values from reblog 
        item = toot_dict["reblog"]
        # define ref_ params
        kwargs = {
            "ref_id": int(toot_dict["id"]),
            "ref_created_at": iso8601_to_timestamp(toot_dict["created_at"]),
            "ref_acct": toot_dict["account"]["acct"],
        }
    else:
        # regular blog
        item = toot_dict
        kwargs = {}

    toot_item = TootItem(
        id=int(item["id"]),
        created_at=iso8601_to_timestamp(item["created_at"]),
        url=item["url"],
        acct=item["account"]["acct"],
        replies_count=int(item["replies_count"]),
        reblogs_count=int(item["reblogs_count"]),
        favourites_count=int(item["favourites_count"]),
        content=item["content"],
        **kwargs,
    )
    return toot_item


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

        with open("response.dump", "wb") as stream:
            stream.write(response.content)

        try:
            toots = [parse_toot_item(td) for td in json.loads(response.content)]
            toots_received = len(toots) # count before filtering out un-parsable
            toots: List[TootItem] = list(
                filter(
                    lambda item: item is not None,
                    toots
                ))
            logger.debug(f"TootsReceived={toots_received},TootsValid={len(toots)}")
        except JSONDecodeError:
            sys.stderr.write(f"Cant parse response content:{response.content}")
            break

        if len(toots) > 0:
            toots_added = writer.add_toots(
                sorted(toots, key=lambda t: t.id, reverse=False),
            )
        else:
            toots_added = 0

        if toots_received < TOOTS_PER_REQUEST or toots_added < len(toots):
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
