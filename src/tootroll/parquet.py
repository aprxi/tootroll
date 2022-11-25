import os
import sys
import errno
import logging
import duckdb

from dataclasses import astuple
from datetime import datetime
from typing import List, Tuple, Dict, Union, Any, Optional

from .timeline import TootItem
from .vars import DATABASE_DIR

logger = logging.getLogger(__name__)


TYPE_CONVERSIONS = {
    int: "INT64",
    str: "VARCHAR",
    Optional[int]: "INT64",
    Optional[str]: "VARCHAR",
}


def read_parquet_metadata(database_file: str) -> None:
    con = duckdb.connect(database=database_file)
    con.execute(f"DESCRIBE SELECT * FROM parquet_metadata('{database_file}');")
    print(con.fetchall())


def read_parquet(database_name: str, limit: int) -> None:
    database_file = f"{DATABASE_DIR}/{database_name}.parquet"
    con = duckdb.connect(database=database_file)

    # retrieve the items again
    con.execute(f"SELECT * FROM items ORDER BY created_at DESC LIMIT {limit}")
    items = con.fetchall()
    try:
        for item in items:
            sys.stdout.write(f"{datetime.fromtimestamp(item[1])},{item}\n")

        sys.stdout.write(f"Total items={len(items)},unique={len(set(items))}]\n")
    except IOError as error:
        if error.errno == errno.EPIPE:
            pass
        else:
            raise error


class ParquetWriter:
    def __init__(
        self,
        database_name: str,
        limit: int,
    ) -> None:
        self.last_ids: List[int] = []
        database_file = f"{DATABASE_DIR}/{database_name}.parquet"
        if not os.path.exists(database_file):
            os.makedirs(DATABASE_DIR, exist_ok=True)
            self.con = duckdb.connect(database=database_file)
            self.create_table()
        else:
            self.con = duckdb.connect(database=database_file)
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
        if max_id:
            base_query = (
                f"SELECT distinct(id) FROM items WHERE id < {max_id} ORDER BY id DESC"
            )
        else:
            base_query = "SELECT distinct(id) FROM items ORDER BY id DESC"

        try:
            self.con.execute(f"{base_query} LIMIT {limit}")
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

        toots_to_add = [
            astuple(toot) for toot in toots
            if toot.id not in self.last_ids
        ]

        if len(toots_to_add) > 1:
            self.con.begin()
            self.con.executemany("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", toots_to_add)
            self.con.commit()

        self.last_ids += list([toot[0] for toot in toots_to_add])
        logger.debug(f"Added {len(toots)} toots")
        return len(toots)

    def close(self) -> None:
        self.con.close()
