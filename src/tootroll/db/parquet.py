import os
import logging
import duckdb

import pyarrow.parquet as pq

from dataclasses import astuple
from datetime import datetime
from typing import List, Optional

from ..timeline import TootItem
from ..vars import DATABASE_DIR

logger = logging.getLogger(__name__)


TYPE_CONVERSIONS = {
    int: "INT64",
    str: "VARCHAR",
    Optional[int]: "INT64",
    Optional[str]: "VARCHAR",
}


def write_parquet(filepath: str, table) -> None:

    if os.path.exists(filepath):
        table_original = pq.read_table(
            source=filepath, pre_buffer=False, use_threads=True, memory_map=True
        )
    else:
        table_original = None

    # create new parquetfile, via tempfile to prevent data-loss in case of failure
    tempfile = f"{os.path.dirname(filepath)}/.{os.path.basename(filepath)}"
    handle = pq.ParquetWriter(tempfile, table.schema)

    if table_original:
        handle.write_table(table_original)

    handle.write_table(table)
    handle.close()
    # when succesful, promote tempfile
    os.rename(tempfile, filepath)


def read_parquet(database_name: str, limit: int) -> List[TootItem]:

    parquet_dir = f"{DATABASE_DIR}/{database_name}.parquet"
    parquet_file = f'{parquet_dir}\
/date={datetime.now().strftime("%Y%m%d")}/file-0.parquet'

    if not os.path.exists(parquet_file):
        return None

    pq_str = f"{parquet_dir}/*/*"

    # retrieve the items again
    con = duckdb.connect(database=":memory:")
    con.execute(
        f"SELECT * FROM read_parquet('{pq_str}') ORDER BY created_at DESC LIMIT {limit}"
    )

    return list([TootItem(*item) for item in con.fetchall()])


class ParquetWriter:
    def __init__(
        self,
        database_name: str,
        limit: int,
    ) -> None:
        self.last_ids: List[int] = []

        self.parquet_dir = f"{DATABASE_DIR}/{database_name}.parquet"
        self.parquet_file = f'{self.parquet_dir}\
/date={datetime.now().strftime("%Y%m%d")}/file-0.parquet'

        self.con = duckdb.connect(database=":memory:")
        self.create_table()

        self.stat_toots_added = 0
        self.stat_toots_total = 0
        limit = 2000
        self.last_ids = self.get_last_ids(limit=limit) or self.last_ids

    def create_table(self) -> None:
        table_items = ", ".join(
            tuple(
                f"{keyname} {TYPE_CONVERSIONS[keytype]}"
                for keyname, keytype in TootItem.__annotations__.items()
            )
        )
        self.con.execute(f"CREATE TABLE items({table_items})")

    def get_last_ids(
        self, limit: int = 1, max_id: Optional[int] = None
    ) -> Optional[List[int]]:

        # TODO: rewrite such that both current and previous (e.g. yesterdays)
        # parquet file is read
        if not os.path.exists(self.parquet_file):
            return None

        pq_str = f"{self.parquet_dir}/*/*"
        if max_id:
            base_query = (
                f"SELECT distinct(id) FROM read_parquet('{pq_str}') WHERE id < {max_id}"
            )
        else:
            base_query = f"SELECT distinct(id) FROM read_parquet('{pq_str}')"

        try:
            self.con.execute(f"{base_query} ORDER BY id DESC LIMIT {limit}")
            items = self.con.fetchall()
            if not items or len(items) < 1:
                return None
            return list([int(tup[0]) for tup in items])
        except ValueError:
            return None

    def add_toots(
        self,
        toots: List[TootItem],
    ) -> int:

        toots_to_add = [astuple(toot) for toot in toots if toot.id not in self.last_ids]

        if len(toots_to_add) > 0:
            values_str = ", ".join("?" for _ in range(len(toots_to_add[0])))
            self.con.begin()
            self.con.executemany(
                f"INSERT INTO items VALUES ({values_str})",
                toots_to_add,
            )
            self.con.commit()

        self.last_ids += list([toot[0] for toot in toots_to_add])
        logger.debug(f"Added {len(toots_to_add)} toots")
        self.stat_toots_added += len(toots_to_add)
        return len(toots_to_add)

    def close(self) -> None:

        rel = self.con.table("items")
        arrow_table = rel.arrow()

        output_dir = os.path.dirname(self.parquet_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        write_parquet(self.parquet_file, arrow_table)

        # validate
        self.con.execute(f"SELECT * FROM read_parquet('{self.parquet_dir}/*/*')")
        items = self.con.fetchall()
        logger.debug(f"total items={len(items)},unique={len(set(items))}\n")

        self.con.close()
        self.stat_toots_total = len(items)
