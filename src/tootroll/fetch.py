import re
import sys
import json
import logging
import requests  # type: ignore

from json.decoder import JSONDecodeError
from typing import Dict, List, Tuple, Any

from .db.parquet import ParquetWriter
from .oauth import check_rate_limits
from .toot import TootItem, parse_toot_dict


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


def http_fetch_toots(
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
            toots = [parse_toot_dict(td) for td in json.loads(response.content)]
            toots_received = len(toots)  # count before filtering out un-parsable
            toots: List[TootItem] = list(filter(lambda item: item is not None, toots))
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

        if toots_added < len(toots):
            logger.debug("End of feed reached")
            break

        # url_params["min_id"] = str(toots[0]["id"])

        next_link = response.headers.get("Link", "").split(";", 1)[0].strip("<>")
        max_id_search = re.search("max_id=[0-9]*", next_link)
        if not max_id_search:
            logger.debug("Link does not contain max_id")
            logger.debug(response.headers)
            break
        url_params["max_id"] = (
            re.search("max_id=[0-9]*", next_link).group().split("=", 1)[-1]
        )

        param_str = "&".join([f"{key}={value}" for key, value in url_params.items()])
        link = f"{url_base}?{param_str}"

    writer.close()


def fetch_toots(
    base_url: str,
    destination_path: str,
    access_token: str,
    limit: int,
    print_stats: bool = True,
) -> int:
    url_params = {
        "local": "false",
    }

    writer = ParquetWriter(destination_path, "home", limit)
    http_fetch_toots(
        base_url,
        access_token,
        writer,
        max_toots=limit,
        url_params=url_params,
    )

    if print_stats:
        sys.stdout.write(
            f"toots_total={writer.stat_toots_total},\
toots_added={writer.stat_toots_added}\n"
        )
    return 0
