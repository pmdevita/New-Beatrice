import asyncio
import logging
from random import choice
import re

import aiohttp
import alluka
import hikari
import tanjun
import atsume
from atsume.settings import settings

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from tanjun.annotations import Member, User, Positional

DIABETES = re.compile("my family history has (\w+)", re.I)
SOCK_DRAWER = re.compile("there\'?s nothing happening", re.I)


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command("hi", "hello", "hey", "howdy", "beatrice", "beako", "betty")
@tanjun.as_slash_command("hi", "Beatrice says hi")
async def hello(ctx: tanjun.abc.Context,
                member: Annotated[Optional[Member], "The user to say hi to.", Positional()] = None
                ):
    member = member if member else ctx.member
    member = member if member else ctx.author
    name = ""
    if isinstance(member, hikari.Member):
        name = member.display_name
    elif isinstance(member, hikari.User):
        name = member.global_name
    # Todo: Add audio responses
    templates = ["Hmmmmm... hi {}.", "Yes, yes, hello {}.", "Hi {}, I guess.", "I'm busy right now {}, shoo, shoo!"]
    await ctx.respond(choice(templates).format(name))


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command("ping")
@tanjun.as_slash_command("ping", "Get the bot's current websocket latency")
async def ping(ctx: tanjun.abc.Context):
    latency = ctx.component.client.shards.heartbeat_latency
    await ctx.respond(f"Hey stop that! ({round(latency * 1000)}ms)")


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command("ban")
@tanjun.as_slash_command("ban", "Ban this user!")
async def ban(ctx: tanjun.abc.Context, member: Annotated[User, "User to ban"]):
    text = f"You're in big trouble {member.mention}, I suppose!"
    video_url = "https://cdn.discordapp.com/attachments/984306454133637170/984318182477152306/beatriceban.mov"
    await ctx.respond(text)
    await ctx.get_channel().send(video_url)


@atsume.with_listener
async def on_message(message: hikari.events.MessageCreateEvent):
    result = DIABETES.findall(message.content)
    if result:
        await (await message.message.fetch_channel()).send(f"(There is {result[0].lower()} in my family history)")
    else:
        result = SOCK_DRAWER.findall(message.content)
        if result:
            await asyncio.sleep(3)
            await (await message.message.fetch_channel()).send(
                "I finally got the wildfire in my sock drawer under control!")


# Todo: Port sound commands (hello, inhale, mouthful)

