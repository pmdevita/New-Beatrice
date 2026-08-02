import asyncio
from random import choice
import re

import hikari
import atsume
from atsume.command.context import CommandContext, MessageContext
from atsume.discord import fetch_guild_channel
from atsume.settings import settings
from atsume.command import command, CommandModel, event

# from audio.data.audio import AudioFile
# from audio.host import VoiceComponent

from typing import Optional

from pydantic import Field

DIABETES = re.compile("my family history has (\\w+)", re.I)
SOCK_DRAWER = re.compile("there\\'?s nothing happening", re.I)
HI_FILES = [
    ("beatrice_hi1.opus", "You come in here without knocking? What a rude one you are."),
    ("beatrice_hi2.opus", "You're irritating me to death. Either stop it or get blown away."),
    ("beatrice_hi3.opus", "You come in here every day without even knocking. You truly have no manners whatsoever.")
]


class HiModel(CommandModel):
    member: Optional[hikari.Member]


@command("hi", "Beatrice says hi", aliases=["hello", "hey", "howdy", "beatrice", "beako", "betty"])
async def hello(ctx: CommandContext | MessageContext, args: HiModel):
    member: hikari.Member | hikari.User = args.member if args.member else ctx.author
    # if isinstance(member, hikari.Member) and ctx.voice:
    #     guild = member.get_guild()
    #     assert guild is not None
    #     voice_state = guild.get_voice_state(member)
        # if voice_state and voice_state.channel_id:
        #     return await hello_audio(ctx.voice, typing.cast(hikari.GuildTextChannel, ctx.get_channel()),
        #                              typing.cast(hikari.GuildVoiceChannel, guild.get_channel(voice_state.channel_id)))

    name = ""
    if isinstance(member, hikari.Member):
        name = member.display_name
    elif isinstance(member, hikari.User):
        name = member.global_name
    # Todo: Add audio responses
    templates = ["Hmmmmm... hi {}.", "Yes, yes, hello {}.", "Hi {}, I guess.", "I'm busy right now {}, shoo, shoo!"]
    await ctx.respond(choice(templates).format(name))


async def hello_audio(voice: hikari.api.VoiceComponent, text_channel: hikari.GuildTextChannel,
                      voice_channel: hikari.GuildVoiceChannel):
    assert isinstance(voice, VoiceComponent)
    connection = await voice.connect(text_channel.guild_id, voice_channel)
    print(connection)
    line = choice(HI_FILES)
    await connection.queue_and_wait("sfx", AudioFile(str(settings.BASE_DIR / "assets" / line[0])))
    await text_channel.send(line[1])


@command(description="Get the bot's current websocket latency")
async def ping(ctx: CommandContext | MessageContext):
    latency = ctx.bot.heartbeat_latency
    await ctx.respond(f"Hey stop that! ({round(latency * 1000)}ms)")


class BanModel(CommandModel):
    user: hikari.Member = Field(description="The user to ban")


@command("ban", "Ban this user!")
async def ban(ctx: CommandContext | MessageContext, args: BanModel):
    text = f"You're in big trouble {args.user.mention}, I suppose!"
    video_url = "https://cdn.discordapp.com/attachments/984306454133637170/984318182477152306/beatriceban.mov"
    await ctx.respond(text)
    await (await ctx.get_channel()).send(video_url)


@event
async def on_message(bot: hikari.GatewayBot, message: hikari.events.MessageCreateEvent):
    if not message.content:
        return
    result = DIABETES.findall(message.content)
    if result:
        await (await fetch_guild_channel(bot, message.channel_id)).send(f"(There is {result[0].lower()} in my family history) l")
    else:
        result = SOCK_DRAWER.findall(message.content)
        if result:
            await asyncio.sleep(3)
            await (await fetch_guild_channel(bot, message.channel_id)).send(
                "I finally got the wildfire in my sock drawer under control! l")

# Todo: Port sound commands (hello, inhale, mouthful)
