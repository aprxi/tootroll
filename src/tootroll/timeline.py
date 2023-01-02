from functools import partial
from datetime import datetime

from typing import List, Tuple

from .toot import TootItem
from .nlp.html_text import extract_text
from .db.parquet import ParquetReader
from .db.utils import dedup_toots



def toot_popularity_handicap(age: int) -> float:
    """Compute "handicap" based on age of toot,
    Note: fixed numbers still experimental and likely
    need further tweaking to see what works best.
    """
    threshold = 86400 * 3.
    minimum = 0.02
    maximum = 1.0
    if age >= threshold:
        return minimum
    if age <= 1:
        return maximum
    return max(minimum, 1 - (age / threshold))


def toot_popularity(toot: TootItem, current_time: int, time_handicap: bool = True) -> float:
    """Note: fix numbers still experimental and likely
    need further tweaking to see what works best."""
    weights = {
        "replies": 1,
        "reblog": 8,
        "favourites": 2,
    }
    weighted_count = \
        (toot.replies_count * weights["replies"]) + \
        (toot.reblogs_count * weights["reblog"]) + \
        (toot.favourites_count * weights["favourites"])
    
    # newest toots has/ have less chance to get popular
    # adjust based on age by applying a handicap to older 
    age_in_seconds = current_time - toot.created_at
    if time_handicap:
        handicap = toot_popularity_handicap(age_in_seconds)
    else:
        handicap = 1.
    return weighted_count * handicap


def read_toots(
    source_path: str,
    feed: str,
    dates: Tuple[str, str],
    limit: int,
) -> List[TootItem]:
    reader = ParquetReader(source_path, feed, dates=dates, limit=limit)

    toots = dedup_toots(tuple(TootItem(*t) for t in reader.get()))

    # sort by popularity
    func = partial(toot_popularity, current_time=int(datetime.now().timestamp()))
    toots_sorted = sorted(toots, key=func, reverse=True)
    # de-duplicate toots (e.g. popular reblogs, we only need one)

    # print( len( toots_sorted ))
    # print( toots_sorted[0 ])
    return toots_sorted[:1000]
    # for idx, pop in enumerate(toots_sorted):
    #     print('-'*60)
    #     print(idx, int(func(pop)), int(func(pop, time_handicap=False)), pop.url, datetime.fromtimestamp(pop.ref_created_at or pop.created_at))
    #     print('-'*60)
    #     print(extract_text(pop.content), "\n")
