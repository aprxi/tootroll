import os
from dataclasses import dataclass
from typing import Optional

MODULE_NAME = __name__.split(".", 1)[0]

try:
    TOOTROLL_HOME = os.environ["TOOTROLL_HOME"]
except KeyError:
    TOOTROLL_HOME = f'{os.environ.get("HOME", ".")}/.{MODULE_NAME}'

SECRETS_DIR = f"{TOOTROLL_HOME}/.secrets"
DATABASE_DIR = f"{TOOTROLL_HOME}/data"


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