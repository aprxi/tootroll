import os
import re
import hashlib

from datetime import datetime, timedelta
from typing import List, Set, Optional

from ..toot import TootItem
from ..vars import TOOTROLL_HOME


def list_by_partition(
    username: str,
    feed: str,
    partition_key: str,
    partition_values_filter: Optional[Set[str]] = None,
) -> Optional[List[str]]:

    database_dir = f"{TOOTROLL_HOME}/{username}/feed/{feed}"

    if not os.path.isdir(database_dir):
        return None

    partition_values = list(
        [
            fname.split("=", 1)[1]
            for fname in os.listdir(database_dir)
            if re.match(f"^{partition_key}=.", fname)
            and os.path.isdir(f"{database_dir}/{fname}")
        ]
    )

    if not partition_values:
        return None

    if partition_values_filter:
        # update values such that it only contains requested values
        partition_values = list(
            set(partition_values).intersection(partition_values_filter)
        )

    parquet_files = []
    for pv in sorted(partition_values):
        pv_directory = f"{database_dir}/{partition_key}={pv}"

        parquet_files += list(
            [
                f"{partition_key}={pv}/{pname}"
                for pname in os.listdir(pv_directory)
                if re.match(".*\\.parquet$", pname)
                and os.path.isfile(f"{pv_directory}/{pname}")
            ]
        )

    return parquet_files


def list_partitions_by_date(parquet_dir: str, start_date: str, end_date: str) -> List[str]:
    start_date_dt = datetime.strptime(start_date.replace("-", ""), "%Y%m%d")
    end_date_dt = datetime.strptime(end_date.replace("-", ""), "%Y%m%d")
    delta = end_date_dt - start_date_dt

    partitions_found = sorted([
        fn
        for fn in os.listdir(parquet_dir)
        if re.match("^date=[0-9]{8}$", fn)
        and os.path.isdir(f"{parquet_dir}/{fn}")
    ])
    partition_dates_gen = (
        (start_date_dt + timedelta(days=i)).strftime("date=%Y%m%d")
        for i in range(delta.days + 1)
    )

    return list([
        p_date_str
        for p_date_str in partition_dates_gen
        if p_date_str in partitions_found
    ])


def dedup_toots(toots: List[TootItem]) -> List[TootItem]:
    """Filter out duplicated Toots (mostly reblogs) based on content
    to do this efficiently we first make baskets of toots with equal length,
    then within these baskets we compare md5sums"""
    toot_lengths = [(idx, len(t.content)) for idx, t in enumerate(toots)]
    equal_lengths = {}
    for tl in toot_lengths:
        idx, length = tl
        if length in equal_lengths:
            equal_lengths[length].append(idx)
        else:
            equal_lengths[length] = [idx]

    unique_toots: List[TootItem] = []
    for lst in equal_lengths.values():
        if len(lst) == 1:
            # only one toot for N length, can assume it to be unique
            unique_toots.append(toots[lst[0]])
        else:
            # more than one item in list, compare checksums
            # using dict will ensure only LAST unique copy is passed
            # Note: LAST copy is preferred because this also ensures we pass
            # latest stats on replies, reblogs, favourites, etc.
            checksums = {
                hashlib.md5(toots[idx].content.encode()).hexdigest(): idx
                for idx in lst
            }
            unique_toots += list([toots[idx] for idx in checksums.values()])
    return unique_toots
