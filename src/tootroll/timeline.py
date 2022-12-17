
from typing import Tuple

from .db.parquet import ParquetReader



def read_toots(
    source_path: str,
    dates: Tuple[str, str],
    limit: int,
) -> int:

    reader = ParquetReader(source_path, "home", dates=dates, limit=limit)
    print(source_path, dates , limit )
    reader.demo( )

    # http_fetch_toots(
    #     base_url,
    #     access_token,
    #     writer,
    #     max_toots=limit,
    #     url_params=url_params,
    # )

    return 0
