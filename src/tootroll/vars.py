import os

MODULE_NAME = __name__.split(".", 1)[0]

MODULE_DIR = f'{os.environ.get("HOME", ".")}/.{MODULE_NAME}'
SECRETS_DIR = f"{MODULE_DIR}/.secrets"
DATABASE_DIR = f"{MODULE_DIR}/data"
DEFAULT_SERVERS = [
    "mastodon.cloud",
    "mastodon.online",
    "fosstodon.org",
]
