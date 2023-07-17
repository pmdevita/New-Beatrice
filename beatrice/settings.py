import hikari
from atsume.settings.type_hints import *
from zoneinfo import ZoneInfo

COMPONENTS = [
    # "management.basic",
    "management.clean_up",
    "management.console",
    "splatgear2",
]

MIDDLEWARE = [
    "atsume.middleware.aiohttp"
]

HIKARI_LOGGING = True

INTENTS = hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.MESSAGE_CONTENT | hikari.Intents.GUILD_MEMBERS

MESSAGE_PREFIX = None

TIMEZONE = "America/New_York"

