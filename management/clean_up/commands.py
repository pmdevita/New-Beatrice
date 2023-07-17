import logging
import re
from datetime import timedelta, timezone, datetime

import alluka
import atsume
import hikari
import tanjun

from atsume.settings import settings

from .models import *

# Create your commands here.


@atsume.as_time_schedule(hours=0)
async def clean_up(client: alluka.Injected[tanjun.Client], component: atsume.Component) -> None:
    logging.info("Cleaning up channels...")
    yt_regex = re.compile("(https?://(?:youtube.com|youtu.be))")
    users: list[str] = [user.split("#") for user in settings.CLEAN_UP_USERS]

    for guild_id in component.guilds:
        guild = client.cache.get_guild(guild_id)
        me = guild.get_my_member()
        for channel in guild.get_channels().values():
            if not isinstance(channel, hikari.GuildTextChannel):
                continue
            permissions = await tanjun.permissions.fetch_permissions(client, me, channel=channel)
            if not permissions & hikari.Permissions.READ_MESSAGE_HISTORY & hikari.Permissions.VIEW_CHANNEL:
                continue
            # Why doesn't hikari have a limiter for this thing
            i = 0
            after = datetime.now(tz=timezone.utc) - timedelta(days=30)
            async for message in channel.fetch_history(before=datetime.now() - timedelta(days=3)):
                i += 1
                if i == 1000 or message.timestamp < after:
                    break
                if not message.author:
                    print("Was this user removed?", message.author)
                    continue
                username, discriminator = message.author.username, message.author.discriminator
                for user in users:
                    if user[0] == username and user[1] == discriminator:
                        match = yt_regex.match(message.content)
                        if match is None:
                            continue
                        if "⭐" in [reaction.emoji for reaction in message.reactions]:
                            continue
                        await message.delete()
    logging.info("Clean up complete")
