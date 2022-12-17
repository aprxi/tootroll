import os
import re

from datetime import datetime, timedelta
from typing import List, Set, Optional

from ..vars import DATABASE_DIR


def list_by_partition(
    server: str,
    database: str,
    partition_key: str,
    partition_values_filter: Optional[Set[str]] = None,
) -> Optional[List[str]]:
    directory = f"{DATABASE_DIR}/{server}/{database}"
    if not os.path.isdir(directory):
        return None

    partition_values = list(
        [
            fname.split("=", 1)[1]
            for fname in os.listdir(directory)
            if re.match(f"^{partition_key}=.", fname)
            and os.path.isdir(f"{directory}/{fname}")
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
        pv_directory = f"{directory}/{partition_key}={pv}"

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
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
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
