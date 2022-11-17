import os

MODULE_NAME = __name__.split(".", 1)[0]

CONFIG_DIR = f'{os.environ.get("HOME", ".")}/.{MODULE_NAME}'
SECRETS_DIR = f"{CONFIG_DIR}/.secrets"
DEFAULT_SERVERS = [
    "mastodon.cloud",
    "mastodon.online",
    "fosstodon.org",
]
