import alluka
import hikari
import tanjun
import atsume

from typing import Annotated, Optional
from tanjun.annotations import Member, Positional

from .manager import VoiceConnection


# Create your commands here.


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command("vc")
async def vc_test(ctx: atsume.Context) -> None:
    guild = ctx.get_guild()
    voice = ctx.voice
    if not guild or not voice:
        return
    assert ctx.member is not None
    voice_state = guild.get_voice_state(ctx.member)
    if not voice_state:
        return
    voice_channel_id = voice_state.channel_id
    assert voice_channel_id is not None
    voice_channel = guild.get_channel(voice_channel_id)
    assert isinstance(voice_channel, hikari.GuildVoiceChannel)
    await voice.connect_to(guild, voice_channel, VoiceConnection)




