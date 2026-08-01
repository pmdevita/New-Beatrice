import hikari
from pathlib import Path
from dotenv import load_dotenv

from atsume.settings import env
from atsume.settings.type_hints import *
from zoneinfo import ZoneInfo

# There is a strange bug that happens when
# hupper (autoreload), the management console, and
# the audio system are loaded, causing an
# access denied error whenever the audio system tries
# to spawn a new process

BASE_DIR = Path(__file__).parent.parent

load_dotenv(BASE_DIR / ".env")

COMPONENTS = [
    "atsume.contrib.handles_gui",
    "atsume.contrib.handles",
    "management.basic",
    # "management.clean_up",
    # "management.console",
    # "management.schedule",
    # "splatgear2",
    # "suscallout",
    # "audio",
    # "secret_santa",
    # "hurricane"
    # "chatgpt"
]

# EXTENSIONS = [
#     "atsume.extensions.aiohttp.hook_aiohttp",
#     "util.aiohttp_server.hook_aiohttp_server",
#     "atsume.extensions.timer.hook_extension"
# ]

HIKARI_LOGGING = False

INTENTS = hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.MESSAGE_CONTENT | hikari.Intents.GUILD_MEMBERS

COMPONENT_PERMISSIONS_CLASS = "atsume.contrib.handles.permissions.DatabasePermissions"

TIMEZONE = "America/New_York"

# VOICE_COMPONENT = "audio.manager.VoiceComponent"

TOKEN = env("TOKEN")

DATABASE_URL = env("DATABASE_URL")

MESSAGE_PREFIX = env("MESSAGE_PREFIX")

