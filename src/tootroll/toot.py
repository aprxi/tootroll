import json

from dataclasses import dataclass
from typing import Dict, Optional, Any

from .utils import iso8601_to_timestamp


@dataclass
class TootItem:
    id: int
    acct: str
    avatar: str
    created_at: int
    url: str
    replies_count: int
    reblogs_count: int
    favourites_count: int
    content: str
    in_reply_to_id: Optional[int] = None
    media_attachments: Optional[str] = None
    ref_acct: Optional[str] = None
    ref_created_at: Optional[int] = None


def parse_toot_dict(toot_dict: Dict[str, Any]) -> Optional[TootItem]:

    if isinstance(toot_dict["reblog"], dict):
        # reblog
        # copy values from reblog
        item = toot_dict["reblog"]
        # define ref_ params
        kwargs = {
            "ref_acct": toot_dict["account"]["acct"],
            "ref_created_at": iso8601_to_timestamp(toot_dict["created_at"]),
        }
    else:
        # regular blog
        item = toot_dict
        kwargs = {}

    # "columnize" key toot items to enable efficient re-indexing/ searching.
    # only store data required to show home lineline
    # id should always be from original toot
    toot_item = TootItem(
        id=int(toot_dict["id"]),
        acct=item["account"]["acct"],
        avatar=item["account"]["avatar"],
        created_at=iso8601_to_timestamp(item["created_at"]),
        url=item["url"],
        replies_count=int(item["replies_count"]),
        reblogs_count=int(item["reblogs_count"]),
        favourites_count=int(item["favourites_count"]),
        content=item["content"],
        in_reply_to_id=(
            lambda: int(item["in_reply_to_id"]) if item["in_reply_to_id"] else None
        )(),
        media_attachments=(
            lambda: json.dumps(item["media_attachments"], default=str)
            if item["media_attachments"]
            else None
        )(),
        **kwargs,
    )
    return toot_item
