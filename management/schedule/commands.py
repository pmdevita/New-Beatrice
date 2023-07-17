import typing

import alluka
import hikari
import tanjun

from typing import Annotated, Optional
from tanjun.annotations import Member, Positional
from atsume.settings import settings
import atsume

from .models import *

# Create your commands here.

@atsume.on_open
async def open(client: alluka.Injected[tanjun.Client], component: atsume.Component):
    for alarm in Alarm.objects.all():
        channel = client.cache.get_guild_channel(alarm.channel)
        if channel is None:
            channel = client.cache.get_dm_channel_id(client.cache.get_user(alarm.channel))
        assert isinstance(channel, hikari.TextableChannel) or isinstance(channel, hikari.DMChannel)
        await schedule_alarm(client, alarm.id, alarm.time, alarm.message, channel)


async def schedule_alarm(client: tanjun.Client, id: int, time: datetime, message: str, channel: typing.Union[hikari.DMChannel, hikari.TextableChannel]):
    client.get_component_by_name()

