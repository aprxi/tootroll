import os
import duckdb

from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

from .vars import DATABASE_DIR


def iso8601_to_timestamp(input_str: str) -> int:
    date_str, _ = input_str.split(".", 1)   # for now, ignore timezone
    return int(datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").timestamp())


TIMELINE_KEYS = {
    "id": int,
    "created_at": iso8601_to_timestamp,
    "url": str,
    "replies_count": int,
    "reblogs_count": int,
    "favourites_count": int,
}

TYPE_CONVERSIONS = {
    int: "INT64",
    str: "VARCHAR",
}


def read_parquet_metadata(database_file: str) -> None:
    con = duckdb.connect(database=database_file)
    con.execute(f"DESCRIBE SELECT * FROM parquet_metadata('{database_file}');")
    print( con.fetchall() )


def timeline_last_id(database_file: str) -> Optional[int]:
    if not os.path.exists(database_file):
        return None
    con = duckdb.connect(database=database_file)
    try:
        con.execute(f"SELECT id FROM items ORDER BY id DESC LIMIT 1")
        items = con.fetchall()
        if len(items) < 1:
            return None
        return int(items[0][0])
    except:
        print("ERROR")
        return None

def read_parquet(limit: int) -> None:
    database_file = f"{DATABASE_DIR}/db.parquet"

    # return
    con = duckdb.connect(database=database_file)

    # retrieve the items again
    con.execute(f"SELECT * FROM items ORDER BY created_at DESC LIMIT {limit}")
    items = con.fetchall()
    for item in items:
        # print(item)
        print(datetime.fromtimestamp(item[1]), item)
    print(f"Total items={len(items)},unique={len(set(items))}")



def timeline_to_parquet(timeline: List[Dict[str, Any]]) -> None:

    toots: List[Tuple] = []
    for post in timeline:
        toots.append(tuple(v(post[k]) for k, v in TIMELINE_KEYS.items()))

    if len(toots) < 1:
        return

    database_file = f"{DATABASE_DIR}/db.parquet"
    if not os.path.exists(database_file):
        os.makedirs(DATABASE_DIR, exist_ok=True)
        con = duckdb.connect(database=database_file)
        table_items = ", ".join(tuple(f"{key} {TYPE_CONVERSIONS[type(toots[0][idx])]}" for idx, key in enumerate( list(TIMELINE_KEYS.keys()))))
        con.execute(f"CREATE TABLE items({table_items})")
    else:
        con = duckdb.connect(database=database_file)

    con.executemany("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?)", toots)
