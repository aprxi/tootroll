import os
import logging
import sqlite3

from sqlite3 import Connection

from dataclasses import astuple
from datetime import datetime
from typing import List, Tuple, Optional


from ..toot import TootItem


logger = logging.getLogger(__name__)


TYPE_CONVERSIONS_SQL = {
    int: "INTEGER",
    str: "TEXT",
    Optional[int]: "INTEGER",
    Optional[str]: "TEXT",
}


class SQLWriter:
    def __init__(
        self,
        database_path: str,
        database_name: str,
    ) -> None:
        self.last_ids: List[int] = []

        self.sqlite_dir = f"{database_path}/{database_name}.sqlite"
        self.sqlite_file = f'{self.sqlite_dir}\
/date={datetime.now().strftime("%Y%m%d")}/latest.db'

        self.con = sqlite3.connect(database=":memory:")
        self.create_table()

        self.stat_toots_added = 0
        self.stat_toots_total = 0
        # limit = 2000
        self.last_ids = []  # self.get_last_ids(limit=limit) or self.last_ids

    def create_table(self) -> None:
        table_items = ", ".join(
            tuple(
                f"{keyname} {TYPE_CONVERSIONS_SQL[keytype]}"
                for keyname, keytype in TootItem.__annotations__.items()
            )
        )
        self.con.execute(f"CREATE TABLE items({table_items})")

    def add_toots(
        self,
        toots: List[TootItem],
    ) -> int:

        toots_to_add = [astuple(toot) for toot in toots if toot.id not in self.last_ids]

        if len(toots_to_add) > 0:
            values_str = ", ".join("?" for _ in range(len(toots_to_add[0])))

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

        # dump to file
        # - simple overwrite for now
        # - rewrite to version that merges data
        if not os.path.exists(os.path.dirname(self.sqlite_file)):
            os.makedirs(os.path.dirname(self.sqlite_file), exist_ok=True)
        elif os.path.exists(self.sqlite_file):
            os.unlink(self.sqlite_file)

        file_con = sqlite3.connect(self.sqlite_file)
        for line in self.con.iterdump():
            file_con.execute(line)
            print(line)
        file_con.close()


        self.con.close()
        # self.stat_toots_total = len(items)


def write_toots(
    toots: List[TootItem],
    destination_path: str,
    timeline: str,
) -> int:

    # cut of last 15 numbers to fit javascript max number
    for tid, toot in enumerate(toots):
        toots[tid].id = toot.id % (10**15)

    writer = SQLWriter(destination_path, timeline)

    toots_added = writer.add_toots(toots[:5])

    writer.close()
    print(f"Added:{toots_added} to {writer.sqlite_file}")

    return 0
