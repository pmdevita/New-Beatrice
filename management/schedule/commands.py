import platform
import typing
from random import choice
from datetime import datetime

import alluka
import hikari
import tanjun
import dateparser  # type: ignore

from typing import Annotated, Optional
from tanjun.annotations import Positional, Str
from atsume.settings import settings
import atsume
from atsume.extensions.timer import Timer

from .models import Alarm

# Create your commands here.


@atsume.on_open
async def on_open(client: alluka.Injected[tanjun.Client], timer: alluka.Injected[Timer], component: atsume.Component):
    for alarm in await Alarm.objects.all():
        timer.schedule_task(alarm.time, send_message, args=[client, alarm])


async def send_message(client: tanjun.Client, alarm: Alarm) -> None:
    assert client.cache is not None
    await client.rest.create_message(alarm.channel, alarm.message)
    channel: hikari.TextableChannel = typing.cast(hikari.TextableChannel,
                                                  client.cache.get_guild_channel(alarm.channel))
    if channel is None:
        user = client.cache.get_user(alarm.channel)
        assert user is not None
        channel = await user.fetch_dm_channel()
    await channel.send(alarm.message)
    await alarm.delete()


def date_countdown(date: datetime):
    return f"<t:{round(date.timestamp())}:R>"


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command("schedule", "sched")
async def add_alarm_cmd(ctx: atsume.Context, timer: alluka.Injected[Timer], client: alluka.Client,
                        time_string: Annotated[Str, "When to set the alarm", Positional()],
                        message: Annotated[Optional[Str], "Optional message", Positional()] = None):
    assert ctx.member is not None
    user_mention = ctx.member.mention

    if message is None:
        templates = ["Ah, {}, your time is up I suppose.", "You can't keep sleeping forever {}, I suppose.",
                     "{}, it's time."]
        message = choice(templates).format(user_mention)

    date = dateparser.parse(time_string, settings={'PREFER_DATES_FROM': 'future'})
    if date is None:
        await ctx.respond("What? I don't know when that is!")
        return

    date = date.astimezone(settings.TIMEZONE)

    channel_id = ctx.channel_id
    if isinstance(ctx.get_channel(), hikari.DMChannel):
        channel_id = ctx.member.id

    alarm = await Alarm.objects.create(channel=channel_id, time=date, message=message)
    timer.schedule_task(alarm.time, send_message, args=[client, alarm])

    templates = ["Very well, I set an alarm for {}.", "Why should I have to keep watch for you? ({})", "Hmmph! ({})"]

    fmt_string = "%B %-d at %-I:%M %p"
    if platform.system() == "Windows":  # Bruh
        fmt_string = "%B %d at %I:%M %p"
    date_string = f"{date.strftime(fmt_string)} {date_countdown(date)}"
    await ctx.respond(choice(templates).format(date_string))
