import os
import re

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
