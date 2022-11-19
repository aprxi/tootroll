import os
import json
import duckdb

from datetime import datetime
from typing import List, Dict, Any

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

def timeline_to_parquet(timeline: List[Dict[str, Any]]) -> None:

    toots = []
    for post in timeline:
        toots.append(tuple(v(post[k]) for k, v in TIMELINE_KEYS.items()))

    if len(toots) < 1:
        return
    table_items = ", ".join(tuple(f"{key} {TYPE_CONVERSIONS[type(toots[0][idx])]}" for idx, key in enumerate( list(TIMELINE_KEYS.keys()))))

    database_file = f"{DATABASE_DIR}/db.parquet"
    if not os.path.exists(database_file):
        os.makedirs(DATABASE_DIR, exist_ok=True)
        con = duckdb.connect(database=database_file)
        con.execute(f"CREATE TABLE items({table_items})")
        con.executemany("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?)", toots )
    else:
        con = duckdb.connect(database=database_file)

    # retrieve the items again
    con.execute("SELECT * FROM items")
    for item in con.fetchall():
        print(datetime.fromtimestamp(item[1]), item)

    # con.execute("COPY (SELECT * FROM items) TO 'result-snappy.parquet' (FORMAT 'parquet')")

    # con.execute("EXPORT DATABASE 'target_directory' (FORMAT PARQUET)")
    # print( timeline[0].keys() )
    # print('#'*50)
    # del timeline[0]["account"]
    # print(json.dumps(timeline, indent=4, default=str))
